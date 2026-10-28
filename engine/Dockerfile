# Образ движка: сервер игры и веб-клиент на одном порту.
FROM debian:bookworm-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /bin/uv
ENV UV_PYTHON_INSTALL_DIR=/python \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --locked --no-dev

COPY engine engine
COPY web web

# Render задаёт порт в PORT; без него — 8080.
ENV PORT=8080
EXPOSE 8080
CMD exec /app/.venv/bin/uvicorn engine.adapters.websocket:create_app \
    --factory --host 0.0.0.0 --port "$PORT" \
    --proxy-headers --forwarded-allow-ips "*"
