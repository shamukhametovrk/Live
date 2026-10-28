# Live

[![MkDocs](https://img.shields.io/badge/MkDocs-1.6-526CFE?logo=materialformkdocs&logoColor=white)](https://www.mkdocs.org/)
[![Material for MkDocs](https://img.shields.io/badge/theme-Material-526CFE?logo=materialformkdocs&logoColor=white)](https://squidfunk.github.io/mkdocs-material/)
[![uv](https://img.shields.io/badge/uv-managed-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Docs](https://github.com/CaseyJohnson-RS/Live/actions/workflows/docs.yml/badge.svg)](https://caseyjohnson-rs.github.io/Live/)

**Live** — компьютерная игра по мотивам русской рулетки. Этот репозиторий
объединяет всё, из чего она строится: правила, движок и клиент.

Сайт с правилами и документацией: <https://caseyjohnson-rs.github.io/Live/>

## Что где лежит

```text
docs/                   исходники сайта (MkDocs Material)
├── index.md            главная: три раздела
├── rules/              правила: обзор, свод глав, каталог предметов, глоссарий
├── engine/             движок: архитектура и журнал решений
├── client/             клиент
├── assets/             картинки для страниц
└── stylesheets/        тема «Бутылочное стекло»: палитра, общее, карточки, правила
engine/                 движок на Python: код, тесты, свой pyproject.toml
client/                 клиент (пока пусто)
mkdocs.yml              настройки сайта и навигация
pyproject.toml          зависимости сайта (uv)
```

Документация лежит отдельно от кода: текст о движке — в `docs/engine/`, сам
движок — в `engine/`. Сайт публикуется на GitHub Pages при каждом пуше в
`main`.

## Локальный запуск сайта

```bash
uv sync
uv run mkdocs serve
```

Сайт откроется на <http://127.0.0.1:8000/>. Проверка, как в CI:

```bash
uv run mkdocs build --strict
```

## Тесты движка

```bash
cd engine
uv sync
uv run pytest
```

Подробнее — в [engine/README.md](engine/README.md).

---

© 2026 Casey Johnson. Все права защищены.
