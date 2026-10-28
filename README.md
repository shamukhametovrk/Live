# Live

[![MkDocs](https://img.shields.io/badge/MkDocs-1.6-526CFE?logo=materialformkdocs&logoColor=white)](https://www.mkdocs.org/)
[![Material for MkDocs](https://img.shields.io/badge/theme-Material-526CFE?logo=materialformkdocs&logoColor=white)](https://squidfunk.github.io/mkdocs-material/)
[![uv](https://img.shields.io/badge/uv-managed-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Docs](https://github.com/CaseyJohnson-RS/Live/actions/workflows/docs.yml/badge.svg)](https://caseyjohnson-rs.github.io/Live/)
[![Engine](https://github.com/CaseyJohnson-RS/Live/actions/workflows/engine.yml/badge.svg)](https://github.com/CaseyJohnson-RS/Live/actions/workflows/engine.yml)

**Live** — компьютерная игра по мотивам русской рулетки. Этот репозиторий
объединяет всё, из чего она строится: правила, движок и клиент.

Сайт с правилами и документацией: <https://caseyjohnson-rs.github.io/Live/>

## Что где лежит

```text
docs/                   исходники сайта: правила, движок, клиент
engine/                 движок на Python: код, тесты, веб-клиент, свой pyproject.toml
client/                 настоящий клиент на Godot (пока пусто)
mkdocs.yml              настройки сайта и навигация
pyproject.toml          зависимости сайта (uv)
```

Документация лежит отдельно от кода: текст о движке — в `docs/engine/`, сам
движок — в `engine/`. Сайт публикуется на GitHub Pages при каждом пуше в
`main`, тесты движка гоняются на каждый пуш.

## Как поиграть

Движок отдаёт прототип клиента сам:

```bash
cd engine
uv run uvicorn engine.adapters.websocket:create_app --factory
```

Открыть <http://localhost:8000>. Подробнее — в [README движка](engine/README.md).

## Локальный запуск сайта

```bash
uv sync
uv run mkdocs serve
```

Сайт откроется на <http://127.0.0.1:8000/>. Проверка, как в CI:

```bash
uv run mkdocs build --strict
```

---

© 2026 Casey Johnson. Все права защищены.
