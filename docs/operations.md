# Operations and boundaries

- Liveness: `/healthz` confirms application process health only. It does not prove
  Jev access, credit balance, or Qwen readiness. A live chat request verifies the chain.
- Invalid router key: HTTP 401. Use ROUTER_API_KEY from this repository's private .env.
- Local generation unavailable: HTTP 503. Check the companion engine on 8001, gateway
  on 8000, LLM_API_KEY, and configured model. Do not substitute a TypeSafe key.
- Jev failure: an explicit `decision_unavailable` clarification result, with no fabricated
  decision and no reported cost. Invalid credentials, quota exhaustion, overload, and
  timeout share a sanitized user message; diagnose account status privately.
- Jev SDK permits one retry with small backoff. A separate eight-second decision
  deadline bounds total decision work. The application has a 45-second total deadline.
- Four concurrent requests and thirty requests per minute are enforced per process.
  Use one worker. Horizontal replicas need shared limits and authentication policy.
- Body size is limited to 16 KiB, including chunked uploads. Questions are limited to
  4000 characters and generated output to 512 tokens. No arbitrary upstream URL comes
  from user requests; the Qwen endpoint is server configuration.
- `/metrics` exposes bounded labels. It does not expose prompts, outputs, or keys.
  Monitor `router_requests_total`, `router_request_seconds`, `router_decision_seconds`,
  and `router_jev_input_tokens_total`. SDK body debug logging is disabled by default.

For a hosted deployment, use TLS, managed secrets, authenticated ingress, private
metrics access, spending limits, and shared rate limits. Container packaging is tested;
public hosting and Kubernetes deployment for this router are not included.

## Secrets and publishing

`.env`, `.env.*`, `typesafe.txt`, virtual environments, and runtime files are ignored.
`.env.example` contains empty placeholders. Docker's context excludes all `.env` files.
The local .env is created with permissions 0600. `scripts/check_secrets.py` checks the
Git index and all historical blobs against locally configured key values without
printing them. CI additionally checks private filenames and common credential prefixes;
CI cannot know your private local values. This is targeted checking, not a comprehensive
credential detection product. Revoke compromised credentials through their provider.

Use your own data and service access. TypeSafe's SDK license and hosted service terms
are separate. This application does not expose TypeSafe as a standalone proxy or train
an imitation model from its outputs. Do not publish private account details, proprietary
logs, or credentials. Reference public TypeSafe documentation instead of copying it.
