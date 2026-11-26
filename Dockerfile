# The base image by digest, so every build starts from the same bytes; Dependabot moves the digest (docker
# ecosystem, after its 14-day cooldown) when python:3.14-slim is rebuilt.
FROM python:3.14-slim@sha256:22eafb370920ad8b429e0aec3fff433e0669968519f5d60469d83729c138b28b
WORKDIR /app
COPY pyproject.toml requirements-tested.txt README.md LICENSE ./
COPY jev_router ./jev_router
RUN pip install --no-cache-dir . -c requirements-tested.txt && useradd --uid 10001 --create-home router
USER 10001
ENV ROUTER_MODE=demo TYPESAFE_LOG_LEVEL=off
EXPOSE 8100
CMD ["uvicorn", "jev_router.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]
