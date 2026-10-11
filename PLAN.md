# PLAN: План виправлення неузгоджень

Пріоритезація: **Critical** → **High** → **Medium** → **Low** → **Info**

---

## Фаза 1: Critical — Схема БД та канонічні поля

### 1.1 Видалити `sku` з Product моделі (або зробити computed)
- [ ] У `db/models.py`: видалити колонку `sku` або змінити на `hybrid_property`, що повертає `external_id`
- [ ] У `db/crud.py:89`: видалити `product.sku = record.external_id`
- [ ] У `db/fts.py:126`: замінити `sku=record.external_id` на `external_id=record.external_id` (або перейменувати колонку FTS)
- [ ] Міграція БД: видалити колонку `sku` з таблиці `products` (SQLite не підтримує DROP COLUMN — потрібно ре створити таблицю або залишити як є)
- [ ] Оновити тести (`test_db.py`) — перевірити що `sku` більше не повертається

### 1.2 Додати `description` до канонічних полів
- [ ] У `canonical.py`: додати `FieldDef("description", "Опис", "str")` до `CANONICAL_FIELDS`
- [ ] У `LureRecord`: поле `description` вже є (рядок 91) — ОК
- [ ] У `export.py`: автоматично підхопиться через `CANONICAL_FIELDS`
- [ ] Перевірити екстрактори: всі вже передають `description` (flagman:62, ibisgear:78, bereg:115)

### 1.3 Очистити `query_products` від службових колонок
- [ ] У `queries.py:64-71`: явно перелічити потрібні колонки замість `Product.__table__.columns`
- [ ] Повертати лише канонічні + `store_code`, `store_name`, `category_name`

---

## Фаза 2: High — Логіка екстракторів

### 2.1 Уніфікувати розрахунок `discount_pct`
**Варіант А (рекомендований):** Завжди розраховувати в `LureRecord` валідаторі, **не передавати** з екстракторів.
- [ ] У `extractors/flagman.py`: видалити `discount_pct=product.discount_percent` (рядок 56)
- [ ] У `extractors/ibisgear.py`: видалити `discount_pct=variant.discount_percent` (рядок 72)
- [ ] У `extractors/bereg.py`: вже не передає — ОК
- [ ] У `canonical.py:97-98`: валідатор вже розраховує — ОК

**Варіант Б:** Передавати з екстракторів, вимкнути авторахунок у валідаторі.
- Складніший, бо bereg не має готового відсотка.

### 2.2 Виправити Bereg: `external_id` стабільність
- [ ] У `extractors/bereg.py`: `_card_external_id` та `extract_bereg_detail` мають повертати **одне й те саме** для одного товару
- [ ] Пріоритет: `detail.sku` → `detail.product_id` → `card.product_id` → URL
- [ ] Додати тест на відповідність ID картки та деталей

### 2.3 Задокументувати логіку цін Bereg
- [ ] У `extractors/bereg.py`: додати docstring до `_price_pair` з поясненням Magento logic
- [ ] У `docs/architecture.md`: додати примітку про Bereg pricing

---

## Фаза 3: Medium — Конфігурація, індекси, валідація

### 3.1 Виправити logging.yaml env-перемінні
- [ ] У `config.py`: додати `DEFAULT_LOG_DIR_ENV`, `DEFAULT_LOG_LEVEL_CONSOLE_ENV`, `DEFAULT_LOG_LEVEL_FILE_ENV`
- [ ] У `logging.py:_resolve_log_dir`: використовувати `os.environ.get("LURES_LOG_DIR")`
- [ ] У `logging.py:setup_logging`: читати рівні з env якщо передано
- [ ] Або: видалити невикористані з `logging.yaml` (спростіший варіант)

### 3.2 Додати індекси БД
- [ ] У `db/models.py`: додати `index=True` до `Product.updated_at` та `Product.price`
- [ ] Міграція: `CREATE INDEX idx_products_updated_at ON products(updated_at);` тощо

### 3.3 CHECK constraints для enum полів
- [ ] У `db/models.py`: додати `CheckConstraint` для `buoyancy` та `availability`
- [ ] SQLite підтримує CHECK constraints
- [ ] Приклад: `CheckConstraint("buoyancy IN ('F','SP','S','FS','SS','SR','SURF','')", name="ck_buoyancy")`

### 3.4 Винести константи магазинів
- [ ] Створити `src/lures/constants.py` з `StoreCode` Enum або константами
- [ ] Замінити в `config.py`, `extractors/__init__.py`, `fetch.py`

---

## Фаза 4: Low — Кодстайл, CLI, Legacy

### 4.1 Перейменувати `type` → `lure_type`
- [ ] `canonical.py`: `FieldDef("lure_type", "Тип воблера", "str")`
- [ ] `LureRecord`: `lure_type: str = ""`
- [ ] `db/models.py`: колонка `lure_type`
- [ ] Всі екстрактори: `type` → `lure_type`
- [ ] `export.py`, `queries.py`, `ui.py` — оновити посилання
- [ ] Міграція БД: перейменувати колонку

### 4.2 CLI: `max_pages` як Optional[int]
- [ ] `cli.py:30`: `MaxPagesOption = Annotated[int | None, ...] = None`
- [ ] Прибрати `or None` у викликах

### 4.3 Видалити legacy код
- [ ] Видалити `legacy/` директорію
- [ ] Видалити `lures.xlsx`, `test.xlsx`, `flagman_raw.json` з кореня
- [ ] Додати `data/lures.db*` до `.gitignore`
- [ ] Додати `graphify-out/` до `.gitignore`

### 4.4 Bereg `fetch_details` дефолт
- [ ] У `cli.py:33-34`: змінити дефолт на `False` (або убрати дефолт, робити `None` → читати з конфігу)
- [ ] У `fetch.py:230`: `details = fetch_details if fetch_details is not None else category.fetch_details`

### 4.5 PriceHistory: унікальні знімки
- [ ] У `crud.py:116-119`: перед додаванням перевіряти останній запис в `price_history`
- [ ] Якщо `price` і `old_price` ідентичні — не додавати

---

## Фаза 5: Tests & Docs

### 5.1 Розширити тести
- [ ] Тест: однаковий `external_id` в різних магазинах (має бути OK — унікальність по store_id)
- [ ] Тест: FTS пошук кирилицею ("Мінноу", "Воблер")
- [ ] Тест: `discount_pct` розрахунок при різних комбінаціях price/old_price
- [ ] Тест: Bereg card vs detail external_id match
- [ ] Тест: Ibis Gear price_uah conversion

### 5.2 Оновити документацію
- [ ] `docs/architecture.md`: відобразити зміни (sku, description, lure_type, constraints)
- [ ] `README.md`: перевірити посилання на GitHub
- [ ] `clients/*/pyproject.toml`: перевірити посилання на репозиторії

---

## Фаза 6: Версіонування та реліз (пізніше)

### 6.1 Стратегія версіонування
- [ ] Обрати: monorepo (один тег для всіх) або незалежні релізи клієнтів
- [ ] Налаштувати CI/CD для публікації на PyPI
- [ ] Замінити `path` dependencies у `pyproject.toml` на `git+https://...@vX.Y.Z` або PyPI

---

## Порядок виконання (залежності)

```
1.1 (sku) → 1.2 (description) → 1.3 (query cleanup)
                    ↓
2.1 (discount_pct) ← 2.2 (bereg external_id) ← 2.3 (bereg docs)
                    ↓
3.1 (logging) ← 3.2 (indexes) ← 3.3 (constraints) ← 3.4 (constants)
                    ↓
4.1 (lure_type) → 4.2 (CLI) → 4.3 (legacy) → 4.4 (fetch_details) → 4.5 (price_history)
                    ↓
5.1 (tests) → 5.2 (docs)
                    ↓
6.1 (versioning)
```

---

## Команди для перевірки після кожної фази

```bash
# Лінтинг та типи
uv run ruff check .
uv run ruff format --check .
uv run mypy src

# Тести
uv run pytest -q

# Повний цикл імпорт/експорт
uv run lures-import -s flagman -s ibisgear -s bereg --max-pages 1
uv run lures-export -o test_output.xlsx

# Перевірити Excel
# Відкрити test_output.xlsx, перевірити колонки, формули, аркуші
```

---

## Нотатки для розробника

1. **Міграції БД**: SQLite не підтримує `DROP COLUMN` / `RENAME COLUMN` до версії 3.35.0 (2021). Найпростіше — ре створити таблицю через `CREATE TABLE new_products AS SELECT ...` або залишити `sku` як deprecated колонку.

2. **Порядок полів в Excel**: `CANONICAL_FIELDS` задає порядок. При додаванні `description` — він піде в кінець (після `image_url`). Якщо потрібно інше місце — змінити порядок у кортежі.

3. **FTS переіндексація**: після зміни схеми (додавання `description`) потрібно переіндексувати — `sync_all` це робить автоматично при наступному імпорті.

4. **Зворотна сумісність**: якщо зовнішні скрипти читають БД безпосередньо — вони поламаються при видаленні `sku` / перейменуванні `type`. Перевірити чи є такі скрипти.
