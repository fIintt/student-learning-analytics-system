FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY README.md ./
COPY src ./src
COPY sql ./sql
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

RUN useradd --create-home app && mkdir -p data/raw data/rejected && chown -R app:app /app
USER app

CMD ["python", "src/pipeline/main.py"]