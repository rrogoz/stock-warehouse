# One image for DEV and PROD; only configuration differs (ADR-002).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first, so this layer is cached between code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src ./src
COPY config ./config
COPY reference ./reference
COPY dbt ./dbt
RUN uv sync --frozen --no-dev

RUN useradd --create-home sw
USER sw

ENTRYPOINT ["python", "-m", "engine"]
