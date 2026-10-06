import asyncio
import secrets
import time
from collections import deque
from contextlib import asynccontextmanager
from importlib.resources import files

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

from .config import Settings
from .decision import DecisionUnavailable, DemoDecider, JevDecider, effective_route
from .generation import DemoGenerator, GenerationUnavailable, LocalGenerator
from .models import ChatRequest
from .retrieval import Knowledge

CLARIFY = (
    "Please provide the specific service, goal, error message, and relevant context. "
    "This application can explain and recommend steps; it does not execute infrastructure changes."
)


class BodyLimit:
    def __init__(self, app, limit=16384):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.limit:
                return await JSONResponse({"detail": "Request body exceeds 16 KiB"}, 413)(
                    scope, receive, send
                )
            chunks.append(message)
            if not message.get("more_body"):
                break

        async def replay():
            if chunks:
                return chunks.pop(0)
            return await receive()

        await self.app(scope, replay, send)


def configuration_answer(question, settings):
    text = question.lower().rstrip("?. ")
    if text in {
        "what is the router output token limit",
        "what is this router's output token limit",
    }:
        return "This router accepts a maximum of 512 output tokens per request."
    if text in {"what port does this router use", "where is this router's ui"}:
        return "The default local UI is http://127.0.0.1:8100/."
    if text in {"what mode is this router running in", "what is the router mode"}:
        return f"This router is running in {settings.mode} mode."
    return None


def create_app(settings=None, decider=None, generator=None):
    settings = settings or Settings.from_env()
    decider = decider or (JevDecider(settings) if settings.mode == "live" else DemoDecider())
    generator = generator or (
        LocalGenerator(settings) if settings.mode == "live" else DemoGenerator()
    )
    knowledge = Knowledge()
    registry = CollectorRegistry()
    requests = Counter(
        "router_requests_total", "Completed requests", ["route", "outcome"], registry=registry
    )
    latency = Histogram("router_request_seconds", "Total request latency", registry=registry)
    decision_latency = Histogram("router_decision_seconds", "Decision latency", registry=registry)
    input_tokens = Counter(
        "router_jev_input_tokens_total", "Jev billable input tokens", registry=registry
    )
    state = {"active": 0}
    arrivals = deque()

    @asynccontextmanager
    async def lifespan(app):
        yield
        await decider.close()
        await generator.close()

    app = FastAPI(title="Jev Inference Router", version="0.1.0", lifespan=lifespan)
    app.add_middleware(BodyLimit)

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    def authenticate(request):
        if settings.router_key:
            expected = "Bearer " + settings.router_key
            actual = request.headers.get("authorization", "")
            if not secrets.compare_digest(actual.encode(), expected.encode()):
                raise HTTPException(401, "Invalid router API key")

    @app.get("/healthz")
    async def health():
        return {"status": "ok", "mode": settings.mode}

    @app.get("/api/config")
    async def config():
        return {
            "mode": settings.mode,
            "auth_required": bool(settings.router_key),
            "jev_model": settings.typesafe_model,
            "llm_model": settings.llm_model,
            "confidence_min": settings.confidence_min,
            "max_output_tokens": 512,
        }

    @app.get("/metrics")
    async def metrics():
        return Response(generate_latest(registry), media_type="text/plain; version=0.0.4")

    @app.get("/")
    async def index():
        path = files("jev_router").joinpath("static/index.html")
        if not path.is_file():
            return JSONResponse(
                {"message": "Backend available; browser UI arrives in milestone 3."}
            )
        return FileResponse(str(path))

    @app.get("/assets/{name}")
    async def asset(name: str):
        if name not in {"app.js", "style.css"}:
            raise HTTPException(404)
        return FileResponse(str(files("jev_router").joinpath("static", name)))

    @app.post("/api/chat")
    async def chat(payload: ChatRequest, request: Request):
        authenticate(request)
        now = time.monotonic()
        while arrivals and arrivals[0] < now - 60:
            arrivals.popleft()
        if len(arrivals) >= 30:
            raise HTTPException(
                429, "Thirty requests per minute allowed", headers={"Retry-After": "60"}
            )
        if state["active"] >= 4:
            raise HTTPException(
                429, "Four requests are already active", headers={"Retry-After": "2"}
            )
        arrivals.append(now)
        state["active"] += 1
        start = time.perf_counter()
        route, outcome = "clarify", "error"
        try:
            async with asyncio.timeout(settings.request_timeout):
                answer = configuration_answer(payload.question, settings)
                if answer:
                    route, outcome = "configuration", "ok"
                    return {
                        "mode": settings.mode,
                        "route": route,
                        "policy_reason": "deterministic_allowlist",
                        "decision": None,
                        "sources": [],
                        "answer": answer,
                        "timing": {"decision_ms": 0, "generation_ms": 0, "total_ms": 0},
                        "estimated_jev_cost_usd": 0,
                        "generation_model": None,
                    }
                documents = knowledge.search(payload.question)
                try:
                    decision = await decider.decide(payload.question, documents)
                except DecisionUnavailable:
                    outcome = "decision_unavailable"
                    return {
                        "mode": settings.mode,
                        "route": "clarify",
                        "decision": None,
                        "policy_reason": outcome,
                        "sources": [],
                        "answer": "Jev is unavailable. Retry later; no decision was accepted.",
                        "timing": {"total_ms": round((time.perf_counter() - start) * 1000, 2)},
                        "estimated_jev_cost_usd": None,
                        "generation_model": None,
                    }
                decision_latency.observe(decision.duration_ms / 1000)
                if decision.source == "jev":
                    input_tokens.inc(decision.input_tokens)
                route, reason, relevant = effective_route(
                    decision, documents, settings.confidence_min
                )
                generated_at = time.perf_counter()
                if route == "clarify":
                    answer = CLARIFY
                else:
                    answer = await generator.answer(payload.question, relevant, payload.max_tokens)
                outcome = "ok"
                return {
                    "mode": settings.mode,
                    "route": route,
                    "policy_reason": reason,
                    "decision": decision.model_dump(),
                    "sources": [
                        {"id": d["id"], "text": d["text"], "relevance": decision.relevance[d["id"]]}
                        for d in relevant
                    ],
                    "answer": answer,
                    "timing": {
                        "decision_ms": round(decision.duration_ms, 2),
                        "generation_ms": round((time.perf_counter() - generated_at) * 1000, 2),
                        "total_ms": round((time.perf_counter() - start) * 1000, 2),
                    },
                    "estimated_jev_cost_usd": round(decision.input_tokens * 0.042 / 1_000_000, 9),
                    "generation_model": (
                        settings.llm_model if settings.mode == "live" else "offline-demo"
                    )
                    if route != "clarify"
                    else None,
                }
        except GenerationUnavailable:
            outcome = "generation_unavailable"
            raise HTTPException(
                503, "Local Qwen gateway unavailable. Check port 8000 and LLM_API_KEY."
            ) from None
        except TimeoutError:
            outcome = "timeout"
            raise HTTPException(504, "Request exceeded its time budget") from None
        finally:
            state["active"] -= 1
            requests.labels(route, outcome).inc()
            latency.observe(time.perf_counter() - start)

    return app
