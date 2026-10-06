# Jev Inference Router

An observable decision layer for local GPU inference. TypeSafe Jev chooses between
local Qwen generation, retrieval from bundled project documentation, and asking for
clarification. Python enforces the routing policy; the model never executes commands.

Built by [Sunil Mehta](https://github.com/sunilmehta-si), alongside
[llm-inference-platform](https://github.com/sunilmehta-si/llm-inference-platform).

## Build milestones

1. Repository foundation and private configuration.
2. Typed Jev decisions, local inference, retrieval, and tested routing policy.
3. Browser UI, metrics, offline demonstration, and container/CI setup.
4. Reproducible evaluations, live verification, and operational documentation.

The offline demo uses explicitly labeled deterministic fixtures, not Jev predictions.
Live mode requires your own TypeSafe API key. Keys belong in the ignored `.env` file,
never in browser JavaScript, source code, reports, or commits.

## References

- [TypeSafe API](https://docs.typesafe.ai/api)
- [Jev model limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13)
- [Official Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python)

MIT licensed application code. Jev is a separately hosted service under TypeSafe's terms.
