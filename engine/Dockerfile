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

EXPOSE 8080
CMD ["/app/.venv/bin/uvicorn", "engine.adapters.websocket:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8080", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
