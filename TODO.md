# TODO: Неузгодження в проекті Lures

Цей файл документує всі знайдені неузгодження, баги та технічний борг. Використовуй його як чек-лист при фіксах.

---

## 1. Схема БД vs Канонічні поля (Critical)

| Проблема | Деталі | Файли |
|----------|--------|-------|
| **`sku` в БД дублює `external_id`** | `Product.sku` завжди = `external_id` (crud.py:89). Канонічні поля (`CANONICAL_FIELDS`) не мають `sku`. | `db/models.py:83`, `db/crud.py:89`, `canonical.py` |
| **`description` в БД, але не в каноні** | `Product.description` є в моделі, але відсутній у `CANONICAL_FIELDS`. Експорт/Excel його не показує. | `db/models.py:99`, `canonical.py:44-62`, `export.py` |
| **`raw_json` / `extra_json` / `updated_at` в БД** | Службові колонки, не частина канонічної схеми. Нормально для внутрішнього використання, але не документовано. | `db/models.py:100-104` |
| **FTS використовує `sku` як `external_id`** | `fts.py:126` передає `sku=record.external_id` — ОК, але назва плутає. | `db/fts.py:126`, `db/crud.py:126` |

---

## 2. Екстрактори: неузгоджену логіка знижок (High)

| Магазин | Проблема |
|---------|----------|
| **flagman** | Передає `discount_pct=product.discount_percent` (з моделі клієнта) |
| **ibisgear** | Передає `discount_pct=variant.discount_percent` (з моделі клієнта) |
| **bereg** | **Не передає** `discount_pct` — розраховується в `LureRecord` валідаторі (canonical.py:97-98) |
| **Результат** | Різна поведінка: у bereg знижка перераховується при кожному upsert, у інших — береться з API. Можливі розбіжності. |

**Файли:** `extractors/flagman.py:56`, `extractors/ibisgear.py:72`, `extractors/bereg.py`, `canonical.py:97-98`

---

## 3. Берег: ціни та наявність (High)

| Проблема | Деталі |
|----------|--------|
| **Логіка `_price_pair`** | `special_price` → `price` (платіжна), `price` → `old_price`. Специфчно для Magento, але не задокументовано в архітектурі. |
| **Наявність з картки** | `extract_bereg_card` ставить `availability="unknown"`, а `extract_bereg_detail` — з варіантів. При `--fetch-details=false` всі товари = unknown. |
| **SKU vs external_id** | `extract_bereg_detail` використовує `detail.sku` або `product_id`, а картка — `product_id` або URL. Може давати різні `external_id` для одного товару. |

**Файли:** `extractors/bereg.py:28-35, 43-62, 65-116`, `fetch.py:232-246`

---

## 4. Ibis Gear: ціни в копійках (Medium)

- У моделях клієнта (`ibisgear-client`) ціни в **копійках** (`price: int`), властивості `price_uah` / `original_price_uah` ділять на 100.
- Екстрактор (`extractors/ibisgear.py:70-71`) використовує `product.price_uah` та `variant.original_price_uah` — **правильно**.
- Але `product.minPrice` / `maxPrice` теж в копійках, `price_uah` property ділить на 100.
- **Ризик**: якщо зміниться API клієнта, екстрактор поламається тихо.

**Файли:** `clients/ibisgear-client/src/ibisgear/models.py:146-147, 163-168, 246-253`, `extractors/ibisgear.py:70-71`

---

## 5. Конфігурація логування: невикористані env-перемінні (Medium)

`config/logging.yaml` документує:
- `LURES_LOG_DIR`
- `LURES_LOG_LEVEL_CONSOLE`
- `LURES_LOG_LEVEL_FILE`

Але в коді (`config.py`, `logging.py`) використовуються лише:
- `LURES_CONFIG` (stores.yaml)
- `LURES_DB` (шлях до БД)
- `LURES_LOG_CONFIG` (шлях до logging.yaml)

**Файли:** `config/logging.yaml:2-5`, `config.py:22-24`, `logging.py:48-51`

---

## 6. Константи магазинів: дублювання (Low)

- `config.py:44` — `Literal["flagman", "ibisgear", "bereg"]`
- `extractors/__init__.py:7-10` — `FLAGMAN_CODE`, `IBISGEAR_CODE`, `BEREG_CODE`
- `fetch.py:55-60` — порівнює `store_cfg.client == FLAGMAN_CODE`

**Рішення:** винести в окремий модуль `constants.py` або Enum.

---

## 7. Type hints / MyPy: `type` як назва поля (Low)

- `canonical.py:48` — `FieldDef("type", "Тип воблера", "str")`
- `LureRecord` має поле `type: str = ""`
- `Product` має колонку `type`
- `type` — built-in Python. Працює, але плутає IDE/лінтери.

**Рішення:** перейменувати на `lure_type` або `wobbler_type` у всьому проекті.

---

## 8. CLI: `max_pages=0` vs `None` (Low)

- `cli.py:30` — `MaxPagesOption = Annotated[int, ...]`, default=0
- `cli.py:70` — `max_pages=max_pages or None`
- `fetch.py:47, 122, 160, 220` — приймає `int | None`
- **Працює правильно** (0 → None), але неочевидно. Краще `Optional[int]` з default=None.

---

## 9. Query API: повертає зайві колонки (Low)

`queries.py:64-71` повертає **всі** колонки `Product.__table__.columns`:
- `sku`, `raw_json`, `extra_json`, `updated_at` — не в каноні
- `store_code`, `store_name`, `category_name` — додаткові

Експорт (`export.py`) фільтрує через `CANONICAL_FIELDS`, але UI (`ui.py:36`) показує все.

---

## 10. Legacy код в репозиторії (Low)

- `legacy/fetch_flagman.py` — старий скрейпер (urllib, потоки)
- `legacy/build_xlsx.py` — старий Excel-генератор
- `lures.xlsx`, `test.xlsx`, `flagman_raw.json` — артефакти
- `data/lures.db*` — SQLite файли (повинні бути в `.gitignore`)

---

## 11. Тести: не покривають edge-cases (Medium)

- Немає тестів на: конфлікт `external_id` при зміні магазину, FTS пошук з кирилицею, історія цін при зміненні `old_price`, обробка `None` в числових полях.

---

## 12. Документація: застарілі посилання (Low)

- `README.md:51` — `Repository = "https://github.com/Gleam/lures"` — перевірити чи актуально
- `clients/*/pyproject.toml` — посилання на `github.com/Gleam/*-client` — перевірити

---

## 13. Відсутні індекси БД (Medium)

- `Product.updated_at` — немає індексу, але сортування в `query_products` по ньому (`order_by(Product.updated_at.desc())`)
- `Product.price` — фільтр `on_sale` використовує `discount_pct`, але пошук по ціновому діапазону — по `price` без індексу

---

## 14. Streamlit UI: жорсткі залежності (Low)

- `ui.py:17` — абсолютні імпорти `from lures.canonical ...` (коментар: Streamlit виконує як скрипт)
- Працює бо пакет встановлений (`uv sync`), але ломається при `streamlit run src/lures/ui.py` без install.

---

## 15. Категорії: code vs name в записах (Low)

- Екстрактори ставлять `category=category.code` (напр. `"voblery"`)
- БД зберігає `Category.code` і `Category.name`
- `query_products` повертає `category_name` (назву), а не код
- UI показує назву, CLI/експорт — теж. Консистентно, але неочевидно.

---

## 16. Bereg: `fetch_details` в конфігу vs CLI (Low)

- `config.py:34` — `CategorySpec.fetch_details: bool = False`
- `fetch.py:230` — `details = fetch_details or category.fetch_details`
- CLI `--fetch-details` (default=True) **перекриває** конфіг. Логіка: CLI має пріоритет, але дефолт True в CLI vs False в конфігу — неузгодженість.

---

## 17. Версіонування: всі v0.1.0 (Info)

- `lures`: 0.1.0
- `flagman-client`: 0.1.0
- `ibisgear-client`: 0.1.0
- `bereg-client`: 0.1.0
- Якщо публікувати на PyPI — потрібна стратегія версіонування (monorepo vs окремі релізи).

---

## 18. Відсутня валідація enum в БД (Medium)

- `buoyancy` — String без CHECK constraint (допустимі: `BUOYANCY_CODES`)
- `availability` — String без CHECK constraint (допустимі: `AVAILABILITY_CODES`)
- Валідація лише в `LureRecord` (Pydantic), але прямий SQL може записати будь-що.

---

## 19. PriceHistory: зберігається при кожному upsert (Info)

- `crud.py:116-119` — додає запис якщо `record.price is not None`
- Це створює запис навіть якщо ціна не змінилася. Можна оптимізувати: порівнювати з останнім.

---

## 20. Graphify / Skill артефакти (Info)

- `graphify-out/` — кеш аналізу коду (не в `.gitignore`)
- `skill/ibisgear-workflow.md` — локальний воркфлоу, не документація проекту
