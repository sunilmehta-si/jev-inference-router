import asyncio

import httpx
import pytest

from jev_router.app import create_app
from jev_router.config import Settings
from jev_router.decision import DecisionUnavailable, DemoDecider, effective_route
from jev_router.generation import DemoGenerator, LocalGenerator
from jev_router.models import Decision


def decision(**overrides):
    values = dict(
        selected_route="local_llm",
        probabilities={"local_llm": 1, "retrieve": 0, "clarify": 0},
        confidence=1,
        needs_context=0,
        model="test",
        source="demo",
    )
    return Decision(**(values | overrides))


def test_uncertainty_and_retrieval_gate():
    assert effective_route(decision(confidence=0.2), [], 0.65)[1] == "low_confidence"
    assert effective_route(decision(needs_context=0.8), [], 0.65)[1] == "needs_context"
    d = decision(
        selected_route="retrieve", probabilities={"local_llm": 0, "retrieve": 1, "clarify": 0}
    )
    assert effective_route(d, [], 0.65)[1] == "no_relevant_document"
    assert (
        effective_route(d.model_copy(update={"relevance": {"a": 2}}), [{"id": "a"}], 0.65)[0]
        == "retrieve"
    )


@pytest.mark.parametrize(
    "probabilities",
    [
        {"local_llm": 0.9, "retrieve": 0.9, "clarify": 0},
        {"local_llm": float("nan"), "retrieve": 0, "clarify": 0},
        {"local_llm": 1, "unknown": 0},
    ],
)
def test_invalid_upstream_distribution(probabilities):
    with pytest.raises(ValueError):
        decision(probabilities=probabilities)


@pytest.mark.asyncio
async def test_public_configuration_has_no_secrets_and_auth_required():
    app = create_app(
        Settings(mode="live", typesafe_key="secret-typesafe", router_key="private-router"),
        DemoDecider(),
        DemoGenerator(),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.get("/api/config")
        assert "secret-typesafe" not in response.text and "private-router" not in response.text
        assert (await client.post("/api/chat", json={"question": "hello"})).status_code == 401
        response = await client.post(
            "/api/chat",
            json={"question": "Explain Linux"},
            headers={"Authorization": "Bearer private-router"},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_demo_routes_and_limits():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(create_app(Settings())), base_url="http://test"
    ) as client:
        response = (
            await client.post(
                "/api/chat", json={"question": "What is the router output token limit?"}
            )
        ).json()
        assert response["route"] == "configuration" and response["decision"] is None
        response = (
            await client.post("/api/chat", json={"question": "How do I set up this router?"})
        ).json()
        assert response["route"] == "retrieve" and response["decision"]["source"] == "demo"
        assert response["sources"]
        assert (await client.post("/api/chat", json={"question": " "})).status_code == 422
        assert (
            await client.post("/api/chat", json={"question": "hi", "max_tokens": 513})
        ).status_code == 422
        assert (await client.post("/api/chat", content=b"x" * 17000)).status_code == 413
        for _ in range(28):
            await client.post("/api/chat", json={"question": "hello"})
        assert (await client.post("/api/chat", json={"question": "hello"})).status_code == 429
        metrics = (await client.get("/metrics")).text
        assert "router_requests_total" in metrics and "How do I" not in metrics


class Unavailable(DemoDecider):
    async def decide(self, *args):
        raise DecisionUnavailable("raw credential should never appear")


@pytest.mark.asyncio
async def test_upstream_failure_is_sanitized():
    app = create_app(Settings(), Unavailable(), DemoGenerator())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.post("/api/chat", json={"question": "Explain Linux"})
        assert response.json()["policy_reason"] == "decision_unavailable"
        assert response.json()["decision"] is None
        assert "raw credential" not in response.text


@pytest.mark.asyncio
async def test_local_generation_failure_sanitized():
    def handler(request):
        return httpx.Response(401, text="secret provider response")

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app = create_app(Settings(), DemoDecider(), LocalGenerator(Settings(), upstream))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.post("/api/chat", json={"question": "Explain Linux"})
        assert response.status_code == 503 and "secret provider" not in response.text
    await upstream.aclose()


class Slow(DemoDecider):
    def __init__(self):
        self.cancelled = False

    async def decide(self, *args):
        try:
            await asyncio.sleep(10)
        finally:
            self.cancelled = True


@pytest.mark.asyncio
async def test_deadline_cancels_work_and_releases_capacity():
    slow = Slow()
    app = create_app(Settings(request_timeout=0.01), slow, DemoGenerator())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        for _ in range(5):
            assert (
                await client.post("/api/chat", json={"question": "Explain Linux"})
            ).status_code == 504
        assert slow.cancelled


@pytest.mark.asyncio
async def test_inflight_limit():
    class Blocked(DemoDecider):
        async def decide(self, *args):
            await event.wait()
            return decision()

    event = asyncio.Event()
    app = create_app(Settings(), Blocked(), DemoGenerator())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        jobs = [
            asyncio.create_task(client.post("/api/chat", json={"question": "Explain Linux"}))
            for _ in range(4)
        ]
        await asyncio.sleep(0.05)
        assert (
            await client.post("/api/chat", json={"question": "Explain Linux"})
        ).status_code == 429
        event.set()
        assert all(r.status_code == 200 for r in await asyncio.gather(*jobs))
