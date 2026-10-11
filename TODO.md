# TODO: Неузгодження в проекті Lures

Цей файл документує всі знайдені неузгодження, баги та технічний борг. Використовуй його як чек-лист при фіксах.

Легенда: ✅ виправлено · 🟡 частково / за дизайном · ⬜ відкрито · ⏭️ відкладено

---

## 1. Схема БД vs Канонічні поля (Critical) — ✅

| Проблема | Статус | Деталі |
|----------|--------|--------|
| ~~`sku` в БД дублює `external_id`~~ | ✅ | Колонку видалено (`models.py`), міграція `migrations.py`, `crud.py`, FTS. |
| ~~`description` в БД, але не в каноні~~ | ✅ | Додано `FieldDef("description", "Опис", "str")`; підхоплюється export/UI. |
| `raw_json` / `extra_json` / `updated_at` | ✅ | Службові; `query_products` їх більше не повертає, задокументовано. |
| ~~FTS використовує `sku`~~ | ✅ | Колонки FTS: `name, external_id, brand, lure_type, species_text`, авто-перебудова. |

---

## 2. Екстрактори: неузгоджена логіка знижок (High) — ✅

`discount_pct` завжди рахує `LureRecord`-валідатор; з екстракторів (flagman/ibisgear) прибрано.
Файли: `extractors/flagman.py`, `extractors/ibisgear.py`, `canonical.py`.

---

## 3. Берег: ціни та наявність (High) — 🟡

| Проблема | Статус | Деталі |
|----------|--------|--------|
| Логіка `_price_pair` | ✅ | Docstring з Magento-логікою + розділ в `docs/architecture.md`. |
| SKU vs external_id | ✅ | `external_id` = `product_id` (є і в картці, і в деталях); SKU збережено як `Артикул` у спеках. |
| Наявність з картки | 🟡 | Listing-картка не містить стоку — `unknown` за дизайном; точна наявність лише з `fetch_details`. |

---

## 4. Ibis Gear: ціни в копійках (Medium) — ✅

Використання `price_uah`/`original_price_uah` правильне; поведінку зафіксовано тестом
(`test_ibisgear_extractor`: 99990 → 999.9).

---

## 5. Конфігурація логування: env-перемінні (Medium) — ✅

`logging.py` тепер читає `LURES_LOG_DIR`, `LURES_LOG_LEVEL_CONSOLE`, `LURES_LOG_LEVEL_FILE`
з правильним пріоритетом; константи додані в `config.py`.

---

## 6. Константи магазинів: дублювання (Low) — ✅

Створено `src/lures/constants.py` (єдине джерело правди); використано в `config.py`,
`extractors/*`, `fetch.py`.

---

## 7. `type` як назва поля (Low) — ✅

Перейменовано `type` → `lure_type` у `canonical.py`, `models.py`, екстракторах, FTS, тестах;
міграція перейменовує колонку.

---

## 8. CLI: `max_pages=0` vs `None` (Low) — ✅

`--max-pages` тепер `Optional[int]` (порожньо = усі), без `or None` у викликах.

---

## 9. Query API: зайві колонки (Low) — ✅

`query_products` повертає лише канонічні поля + `store_code`/`store_name`/`category_name`.
UI-ключі виправлено (`store_name`/`category_name`).

---

## 10. Legacy код / артефакти (Low) — ✅

`.gitignore` розширено (`graphify-out/`, `logs/`, `flagman_raw.json`); артефакти знято з
відслідковування git (`git rm --cached`), файли лишаються на диску за рішенням користувача.
`legacy/` і `skill/` збережено як довідку.

---

## 11. Тести: edge-cases (Medium) — ✅

Додано: однаковий `external_id` у різних магазинах, дедуп `price_history`, FTS кирилицею,
bereg card/detail id match, комбінації `discount_pct`, наявність `description` у каноні.

---

## 12. Документація: застарілі посилання (Low) — ✅

URL виправлено на реальний акаунт `github.com/gleamingbamboo/*` (перевірено; старий `Gleam` — 404).
Уточнено, що `clients/` — пакети одного монорепозиторію (не окремі git-репо).

---

## 13. Відсутні індекси БД (Medium) — ✅

`index=True` для `Product.price` та `Product.updated_at`; міграція створює індекси.

---

## 14. Streamlit UI: абсолютні імпорти (Low) — ⬜

`ui.py` використовує `from lures....` — працює при встановленому пакеті. Залишено як є.

---

## 15. Категорії: code vs name (Low) — ✅ (за дизайном)

Екстрактори ставлять `category=code`; UI/експорт показують `name`. Консистентно.

---

## 16. Bereg: `fetch_details` конфіг vs CLI (Low) — ✅

CLI `--fetch-details/--no-fetch-details` — тристановий (default `None` = значення з `stores.yaml`).

---

## 17. Версіонування: всі v0.1.0 (Info) — ⏭️

Стратегія публікації (monorepo vs окремі релізи) відкладена.

---

## 18. Валідація enum в БД (Medium) — ✅

Додано `CheckConstraint` для `buoyancy` та `availability`; міграція перебудовує стару таблицю.

---

## 19. PriceHistory при кожному upsert (Info) — ✅

Знімок додається лише коли `price`/`old_price` змінилися.

---

## 20. Graphify / Skill артефакти (Info) — ✅

`graphify-out/` знято з відслідковування. `skill/ibisgear-workflow.md` лишено як внутрішню довідку.

---

## 21. Міграція пошкоджувала FK-посилання (Critical) — ✅

`PRAGMA foreign_keys=OFF` виставлявся на **іншому** з'єднанні, ніж `ALTER TABLE products
RENAME TO products_old`, тож SQLite переписав `REFERENCES products` у дочірніх таблицях
(`product_species`, `price_history`) на `products_old`, а потім його дропав. Будь-який
`INSERT/DELETE` падав з `no such table: main.products_old`.

Виправлено: усі DDL виконуються на одному з'єднанні з `foreign_keys=OFF` +
`legacy_alter_table=ON`; додано ідемпотентний ремонт уже пошкоджених дочірніх таблиць
(`_repair_dangling_fk`). Перевірено: `PRAGMA integrity_check` = ok, `foreign_key_check` = [].

---

## 22. Логування: SQL-спам у консолі (Medium) — ✅

`intercept_level: "DEBUG"` застосовувався до «шумних» логерів (`sqlalchemy.engine`), тож
кожен `INSERT/SELECT` друкувався на рівні INFO. Дефолт змінено на `"WARNING"`
(`config.py`, `config/logging.yaml`).

---

## 23. UI: мультивибір магазинів ігнорувався (Medium) — ✅

`_collect_rows` ставив `store=display[0] if len(display)==1 else None`, тож при виборі 2+
магазинів показувались **усі** (включно з невибраними). Додано параметр `stores` у
`query_products`; UI передає весь список. Тест: `test_filters_and_bounds` (`stores`).

---

## 24. UI: застарілий параметр + перебудова Excel на кожній взаємодії (Low) — ✅

* `st.dataframe(..., use_container_width=True)` → `width="stretch"` (deprecation у Streamlit 1.65).
* `build_workbook_bytes` (~2 МБ, ~5 с) викликався на кожному rerun → обгорнуто в
  `st.cache_data` (`_workbook_bytes`).

---

## Залишилось (відкриті)

- ⬜ **14** Streamlit: запуск `streamlit run src/lures/ui.py` без `uv sync` (абсолютні імпорти).
- 🟡 **3** Bereg: наявність з listing-картки неможлива (лише з detail).
- ⏭️ **17** Версіонування/публікація клієнтів (Фаза 6 у `PLAN.md`).
- ℹ️ `--max-pages` не обмежує flagman (його клієнт не має посторінкового API) — за дизайном.
