from types import SimpleNamespace

import pytest

from jev_router.config import Settings
from jev_router.decision import DecisionUnavailable, JevDecider


class StubClient:
    def __init__(self, missing=False):
        self.missing = missing
        self.closed = False

    async def system_one(self, state, questions):
        assert state["question"] == "Explain Linux"
        assert "relevance_0" in questions
        return SimpleNamespace(
            choices={}
            if self.missing
            else {
                "route": SimpleNamespace(
                    choice="local_llm",
                    probabilities={"local_llm": 1, "retrieve": 0, "clarify": 0},
                    confidence=1,
                )
            },
            nouls={"needs_context": SimpleNamespace(noul=0.1)},
            scores={"relevance_0": SimpleNamespace(score=0.2)},
            usage=SimpleNamespace(input_tokens=400),
            model="jev-1.13.0",
        )

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_sdk_response_mapping_and_close():
    client = StubClient()
    decider = JevDecider(Settings(), client)
    result = await decider.decide("Explain Linux", [{"id": "source", "text": "Text"}])
    assert result.relevance == {"source": 0.2}
    assert result.input_tokens == 400 and result.source == "jev"
    await decider.close()
    assert client.closed


@pytest.mark.asyncio
async def test_missing_sdk_answer_fails_closed():
    decider = JevDecider(Settings(), StubClient(missing=True))
    with pytest.raises(DecisionUnavailable):
        await decider.decide("Explain Linux", [{"id": "source", "text": "Text"}])
