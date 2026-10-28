# Движок Live

[![Python](https://img.shields.io/badge/python-3.15-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/uv-managed-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![pytest](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![WebSocket](https://img.shields.io/badge/protocol-WebSocket-010101)](https://developer.mozilla.org/docs/Web/API/WebSockets_API)

Движок игры **Live** — сетевой игры для 2–6 игроков по мотивам
[Buckshot Roulette](https://en.wikipedia.org/wiki/Buckshot_Roulette).
Главное отличие — каморный ряд, выложенный перед игроками: камору для
выстрела выбирает сам игрок.

Движок — сервер: ведёт одну игру за одним столом, говорит с клиентами JSON
по WebSocket (`/ws`) и сам отдаёт прототип веб-клиента на `/`.

## Документация

Правила игры, устройство движка и журнал решений живут на сайте проекта
(исходники — в [`docs/`](../docs/) корня репозитория):

- [Правила](../docs/rules/index.md) — что происходит в игре;
- [Движок](../docs/engine/index.md) — архитектура и журнал решений.

## Запуск

```bash
cd engine
uv sync
uv run uvicorn engine.adapters.websocket:create_app --factory
```

Открыть <http://localhost:8000>, «Сесть за стол». Ботов за стол:

```bash
uv run python -m tools.net_bot --count 2
```

Летопись партии словами правил:

```bash
uv run python -m tools.chronicle --seed 42 --players 3 --rounds 1
```

## Проверки

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```
