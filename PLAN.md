# PLAN: План виправлення неузгоджень

Статус: **Фази 1–5 виконано** (коміти `6eae89b`, `cc3621d`, далі tests/docs).
Фаза 7 (runtime smoke-тест і фікси) — виконано. Фаза 6 (версіонування) — відкладена.
Перевірка: `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy src` · `uv run pytest -q` (19 passed).

Пріоритезація: **Critical** → **High** → **Medium** → **Low** → **Info**

---

## Фаза 1: Critical — Схема БД та канонічні поля — ✅

### 1.1 Видалити `sku` з Product моделі
- [x] `db/models.py`: колонку `sku` видалено
- [x] `db/crud.py`: прибрано `product.sku = record.external_id`
- [x] `db/fts.py`: FTS-колонку перейменовано на `external_id`
- [x] Міграція: `migrations.py` (DROP COLUMN + перебудова), ідемпотентна
- [x] Тести оновлено

### 1.2 Додати `description` до канонічних полів
- [x] `canonical.py`: `FieldDef("description", "Опис", "str")`
- [x] `export.py`/UI підхоплюють автоматично
- [x] Екстрактори вже передають `description`

### 1.3 Очистити `query_products` від службових колонок
- [x] `queries.py`: лише канонічні + `store_code`, `store_name`, `category_name`
- [x] UI-ключі виправлено (`store_name`/`category_name`)

---

## Фаза 2: High — Логіка екстракторів — ✅

### 2.1 Уніфікувати розрахунок `discount_pct` (Варіант А)
- [x] `flagman.py`: прибрано `discount_pct=...`
- [x] `ibisgear.py`: прибрано `discount_pct=...`
- [x] `bereg.py`: вже не передає
- [x] `canonical.py`: валідатор рахує

### 2.2 Bereg `external_id` стабільність
- [x] `_external_id()`: `product_id` → `sku` → slug URL
- [x] Картка й деталі дають однаковий `external_id`
- [x] Тест `test_bereg_external_id_is_stable`
- [x] SKU збережено як `Артикул` у спеках (`fetch.py`)

### 2.3 Задокументувати логіку цін Bereg
- [x] Docstring `_price_pair`
- [x] `docs/architecture.md` — примітка про Magento pricing

---

## Фаза 3: Medium — Конфігурація, індекси, валідація — ✅

### 3.1 Logging env-перемінні
- [x] `config.py`: `DEFAULT_LOG_DIR_ENV` / `DEFAULT_LOG_LEVEL_CONSOLE_ENV` / `DEFAULT_LOG_LEVEL_FILE_ENV`
- [x] `logging.py`: коректний пріоритет для каталогу й рівнів

### 3.2 Індекси БД
- [x] `index=True` для `Product.updated_at`, `Product.price`
- [x] Міграція створює `ix_products_updated_at`, `ix_products_price`

### 3.3 CHECK constraints
- [x] `CheckConstraint` `ck_products_buoyancy`, `ck_products_availability`
- [x] Міграція перебудовує стару таблицю

### 3.4 Константи магазинів
- [x] `src/lures/constants.py` (`FLAGMAN`/`IBISGEAR`/`BEREG`, `ClientCode`)
- [x] Замінено в `config.py`, `extractors/*`, `fetch.py`

---

## Фаза 4: Low — Кодстайл, CLI — ✅

### 4.1 `type` → `lure_type`
- [x] `canonical.py`, `LureRecord`, `db/models.py`, екстрактори, FTS, тести, міграція

### 4.2 CLI: `max_pages` як `Optional[int]`
- [x] `MaxPagesOption = Annotated[int | None, ...] = None`
- [x] Прибрано `or None`

### 4.3 Legacy / артефакти — ✅ (рішення користувача)
- [x] `.gitignore`: `graphify-out/`, `logs/`, `flagman_raw.json`
- [x] `git rm --cached` (файли лишаються на диску)
- [x] `data/lures.db*` уже ігнорується

### 4.4 Bereg `fetch_details` дефолт
- [x] CLI `--fetch-details/--no-fetch-details`, default `None` → значення з конфігу
- [x] `fetch.py`: `category.fetch_details if fetch_details is None else fetch_details`
- [x] Додатково: per-category `max_pages` у `stores.yaml` тепер застосовується

### 4.5 PriceHistory: унікальні знімки
- [x] `crud.py`: пишемо лише при зміні `price`/`old_price`

---

## Фаза 5: Tests & Docs — ✅

### 5.1 Розширити тести
- [x] `external_id` у різних магазинах (scoped by store)
- [x] FTS кирилицею (`мінноу`, `Воблер`)
- [x] `discount_pct` комбінації (`test_canonical.py`)
- [x] Bereg card vs detail `external_id`
- [x] Ibis Gear `price_uah` conversion (99990 → 999.9)
- [x] Дедуп `price_history`

### 5.2 Документація
- [x] `docs/architecture.md`: sku/description/lure_type/constraints/міграції/bereg
- [x] `README.md`: «окремі пакети монорепо» замість «окремі git-репо»
- [x] `clients/*/pyproject.toml` + корінь: URL → `github.com/gleamingbamboo/*`

---

## Фаза 6: Версіонування та реліз (відкладено) — ⏭️

### 6.1 Стратегія версіонування
- [ ] Обрати: monorepo (один тег) або незалежні релізи клієнтів
- [ ] Налаштувати CI/CD для публікації на PyPI
- [ ] Замінити `path` dependencies у `pyproject.toml` на `git+https://...@vX.Y.Z` або PyPI

---

## Фаза 7: Runtime smoke-тест і фікси — ✅

Запуск реального циклу (import усіх магазинів → export → Streamlit UI + `AppTest`) виявив:

### 7.1 Міграція ламала FK (Critical)
- [x] Усі DDL на одному з'єднанні з `foreign_keys=OFF` + `legacy_alter_table=ON`
- [x] Ремонт `products_old`-посилань (`_repair_dangling_fk`) — ідемпотентно
- [x] Перевірка: `integrity_check` ok, `foreign_key_check` [], 3618 рядків збережено

### 7.2 Логування: SQL-спам
- [x] `intercept_level` → `WARNING` (дефолт + `logging.yaml`)

### 7.3 UI: мультивибір магазинів
- [x] `query_products(stores=...)`; UI передає весь список
- [x] Тест у `test_filters_and_bounds`

### 7.4 UI: deprecation + кеш Excel
- [x] `width="stretch"` замість `use_container_width`
- [x] `_workbook_bytes` під `st.cache_data`

---

## Команди для перевірки

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q

# Повний цикл імпорт/експорт (потребує мережі)
uv run lures-import -s flagman -s ibisgear -s bereg --max-pages 1
uv run lures-export -o test_output.xlsx
```

---

## Нотатки для розробника

1. **Міграції БД**: `migrations.py` виконується з `init_db`; SQLite ≥ 3.35 підтримує
   `DROP COLUMN`/`RENAME COLUMN` (перевірено на 3.47). CHECK-обмеження вимагають
   перебудови таблиці (з `PRAGMA foreign_keys=OFF`).
2. **Порядок полів в Excel**: `CANONICAL_FIELDS`; `description` — останній.
3. **FTS переіндексація**: `create_fts_table` перебудовує індекс автоматично при зміні схеми.
4. **Зворотна сумісність**: зовнішні скрипти, що читають `products.sku`/`products.type`
   напряму, поламаються — використовуйте `external_id`/`lure_type`.
