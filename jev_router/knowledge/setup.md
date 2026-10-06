# Router setup and local services

Jev Inference Router is a separate application on port 8100. Run `make setup`, copy
`.env.example` to `.env`, and run `make serve`. The browser UI is at
http://127.0.0.1:8100/. API documentation is at /docs, and metrics are at /metrics.
Offline demo mode needs no API keys and makes no external requests. Live mode requires
TYPESAFE_API_KEY and ROUTER_API_KEY on the server. The browser uses ROUTER_API_KEY;
it never needs the TypeSafe key. Restart the application after changing .env.

The companion llm-inference-platform gateway listens on port 8000 and its Qwen engine
on port 8001. Configure LLM_BASE_URL=http://127.0.0.1:8000/v1 and LLM_API_KEY using
that gateway's private GATEWAY_API_KEY. Qwen runs on Apple Silicon through vllm-metal.
Jev runs through TypeSafe's hosted API, not on the Mac GPU.
