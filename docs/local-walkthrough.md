# Run and inspect the project locally

## Services

| Service | URL | Purpose |
|---|---|---|
| Jev router UI | http://127.0.0.1:8100/ | Chat and decision inspector |
| Router API docs | http://127.0.0.1:8100/docs | OpenAPI request exploration |
| Router metrics | http://127.0.0.1:8100/metrics | Prometheus exposition |
| Existing inference gateway | http://127.0.0.1:8000/ | Qwen API and original chat page |
| Existing GPU engine | http://127.0.0.1:8001/v1/models | vllm-metal model service |

Jev is hosted by TypeSafe. Qwen runs on the Mac GPU. This repository packages the
router, not a copy of Jev's model or a new Qwen engine.

## Offline demonstration

```sh
git clone https://github.com/sunilmehta-si/jev-inference-router.git
cd jev-inference-router
make setup
make demo
```

Open http://127.0.0.1:8100/. No keys or GPU are needed. Each question routes through
explicitly labeled fixtures. This demonstrates software behavior without generating
real model answers. Only run one process on port 8100 at a time.

## Live mode

Copy `.env.example` to `.env`, keep it private, and set:

| Variable | Value |
|---|---|
| ROUTER_MODE | `live` |
| TYPESAFE_API_KEY | Your TypeSafe key, server-side only |
| TYPESAFE_MODEL | `jev-1.13.0` |
| ROUTER_API_KEY | A random private key for this application |
| LLM_BASE_URL | `http://127.0.0.1:8000/v1` |
| LLM_API_KEY | The existing gateway's private `GATEWAY_API_KEY` |
| LLM_MODEL | `mlx-community/Qwen2.5-7B-Instruct-4bit` |

On Sunil's local setup, ROUTER_API_KEY uses the existing gateway key so the same key
can be used in both local chat pages. Other installations should choose their own.
The TypeSafe key is separate and belongs only in the server's `.env`.

Start the companion engine and gateway in separate terminals:

```sh
cd /Users/sunil/sunilmehta-si-github/llm-inference-platform
MODEL_REVISION=c26a38f6a37d0a51b4e9a1eb3026530fa35d9fed make engine
```

```sh
cd /Users/sunil/sunilmehta-si-github/llm-inference-platform
make gateway
```

The pinned revision also avoids an empty-array issue in the companion startup script
under macOS's system Bash. Wait for the engine to report startup complete.

Then start this application:

```sh
cd /Users/sunil/sunilmehta-si-github/jev-inference-router
make serve
```

Open http://127.0.0.1:8100/, paste **ROUTER_API_KEY** into the left password field,
and enter your question in the center text box. Press Enter or Send question;
Shift+Enter inserts a newline. Keys clear on reload. Questions are independent.

Try these examples:

1. `Explain Kubernetes readiness probes` — local Qwen generation.
2. `How do I set up this router in live mode?` — retrieved documentation plus Qwen.
3. `Fix the broken deployment` — clarification, no generation or execution.
4. `What is the router output token limit?` — deterministic configuration answer.

The right panel shows the selected/effective path, confidence, missing-context
probability, probabilities, timing, estimated cost, and source text. Cost estimates
cover reported Jev input tokens only; retries can add billing not present in a result.
They do not include GPU electricity, hardware amortization, or other providers.

## Verification and evaluation

```sh
make check
make secrets
make evaluate
make evaluate-live
```

The live evaluation makes 48 Jev calls (24 questions plus reversed choices) and 24
local Qwen classification calls. Use synthetic inputs and your own account allowance.
Read `evaluations/README.md` before interpreting results.

## Container

```sh
docker build -t jev-inference-router:local .
docker run --rm -p 127.0.0.1:8100:8100 jev-inference-router:local
```

This starts demo mode. To run live in Docker Desktop, pass `--env-file .env` and
`-e LLM_BASE_URL=http://host.docker.internal:8000/v1`. The Qwen engine remains native
on macOS. Bind only to localhost for this local demonstration.

Ctrl+C stops each foreground service. Stop the router before changing `.env`, then
restart it. Browser Stop cancels the browser fetch; a server request may continue
until its bounded deadline. No cloud deployment was performed.
