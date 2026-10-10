# Lures — агрегатор приманок (воблери)

Скрейпер і вітрина воблерів з трьох українських магазинів риболовлі:

| Магазин      | Клієнт-бібліотека            | API/джерело                    |
| ------------ | ---------------------------- | ------------------------------ |
| flagman.ua   | `flagman-client` (v0.1.0)    | внутрішній JSON API `r.flagman.ua` |
| ibis-gear.com| `ibisgear-client` (v0.1.0)   | Sylius Shop API v2 (json-ld)   |
| bereg.ua     | `bereg-client` (v0.1.0)      | Magento 1 HTML (з sitemap)     |

Три клієнт-бібліотеки лежать у [`clients/`](clients/) (окремі git-репозиторії,
`*v0.1.0`), головний застосунок у цьому репозиторії агрегує їх в один
**канонічний** формат, зберігає у SQLite (`data/lures.db`), показує у
Streamlit та експортує в Excel.

## Швидкий старт

```powershell
uv sync --dev            # встановлює застосунок + клієнти (path-editables)
uv run lures-import -s flagman -s ibisgear -s bereg   # наповнити базу
uv run lures-serve       # Streamlit: локально http://localhost:8501
uv run lures-export -o lures.xlsx
```

Конфігурація магазинів і категорій — [`config/stores.yaml`](config/stores.yaml)
(змінні середовища `LURES_CONFIG`, `LURES_DB` для перевизначення).

## Структура

```
clients/                   трьох окремі git-репо клієнт-бібліотек
config/stores.yaml         магазини/категорії (категорії дзеркалять таксономії сайтів)
src/lures/
  canonical.py             універсальний канонічний словник колонок + LureRecord
  extractors/              адаптери: клієнт-моделі -> канонічні записи
  db/                      SQLAlchemy 2.0: моделі, сесії, CRUD, FTS-пошук
  fetch.py                 оркестрація синхронізації
  export.py                Excel (openpyxl), літери/формули у стилі build_xlsx.py
  ui.py                    Streamlit-інтерфейс
  cli.py                   lures-import / lures-export / lures-serve
docs/architecture.md       опис канонічної схеми, DB-схеми та потоків
skill/ibisgear-workflow.md записаний воркфлоу роботи з ibis-gear
```

## Канонічні колонки

Дивись [`docs/architecture.md`](docs/architecture.md) — усі магазини зводяться
до одного словника колонок (тип воблера, плавучість `F/SP/S/FS/SS/SR/SURF`,
вага, довжина, заглиблення, ціни, рейтинг, наявність, посилання, фото).

## Тести

```powershell
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

## Ліцензія

MIT.