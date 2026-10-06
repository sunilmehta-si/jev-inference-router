.PHONY: setup check serve demo evaluate evaluate-live secrets
PY = .venv/bin/python

setup:
	python3 -m venv .venv
	$(PY) -m pip install -e '.[dev]' -c requirements-tested.txt

check:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
	.venv/bin/pytest -q

serve:
	.venv/bin/uvicorn jev_router.app:create_app --factory --host 127.0.0.1 --port 8100 --workers 1

demo:
	ROUTER_MODE=demo ROUTER_API_KEY= .venv/bin/uvicorn jev_router.app:create_app --factory --host 127.0.0.1 --port 8100 --workers 1

evaluate:
	$(PY) scripts/evaluate.py --mode demo

evaluate-live:
	$(PY) scripts/evaluate.py --mode live --include-qwen --reverse-options

secrets:
	$(PY) scripts/check_secrets.py
