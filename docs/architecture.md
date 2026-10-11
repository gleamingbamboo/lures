# Архітектура агрегатора «lures»

Три клієнт-бібліотеки (`clients/flagman-client`, `clients/ibisgear-client`,
`clients/bereg-client`, кожна окремим пакетом, тег `v0.1.0`) реалізують
читання каталогів магазинів. Головний пакет `lures` не робить HTTP-запитів напряму —
він лише зводить моделі трьох клієнтів до **єдиного канонічного контракту**, зберігає
їх у SQLite та показує/експортує.

## 1. Канонічний словник колонок (`src/lures/canonical.py`)

Варіант A спільного типування: спільні типи — це **документований структурний
контракт** (окремого 4-го репозиторію немає). `CANONICAL_FIELDS` — єдине джерело
правди для заголовків Excel, колонок SQLite і фільтрів UI.

| Ключ            | Заголовок        | Тип    | Примітка                          |
| --------------- | ---------------- | ------ | --------------------------------- |
| external_id     | Артикул          | str    | артикул/код товару (SKU)          |
| name            | Назва            | str    |                                   |
| brand           | Виробник         | str    |                                   |
| lure_type       | Тип воблера      | str    | Minnow, Crank, Popper, ...        |
| buoyancy        | Плавучість       | enum   | `F/SP/S/FS/SS/SR/SURF`            |
| weight_g        | Вага, г          | float  |                                   |
| length_mm       | Довжина, мм      | float  |                                   |
| depth_from_m    | Заглиблення від  | float  | метри                             |
| depth_to_m      | Заглиблення до   | float  | метри                             |
| price           | Ціна, грн        | float  | платіжна ціна                     |
| old_price       | Стара ціна, грн  | float  | до знижки (None, якщо немає)      |
| discount_pct    | % акції          | int    | обчислюється автоматично          |
| rating          | Рейтинг          | float  |                                   |
| comments        | Відгуки          | int    |                                   |
| availability    | Наявність        | enum   | `available/out_of_stock/unknown`  |
| url             | Посилання        | str    |                                   |
| image_url       | Фото             | str    |                                   |
| description     | Опис             | str    |                                   |

`LureRecord` — pydantic-модель усіх колонок + службові `store`, `category`. Валідатор:
(1) скидає `old_price <= price`; (2) рахує `discount_pct`, якщо його не задано;
(3) нормалізує enum-поля.

## 2. Екстрактори (`src/lures/extractors/`)

Тонкі адаптери: клієнт-модель → `LureRecord`.

* **flagman** (`extract_flagman`) — `Product.characteristics` (тип воблера із
  характеристики «Тип воблера», або ключові слова назви/опису; плавучість із «Плавучість»
  або евристики назви; `sell_status == "4"` → наявність).
* **ibisgear** (`extract_ibisgear`) — атрибути `default_variant` (вага/довжина/тип/
  плавучість), ціни в **копійках** → гривні (`/100`), `inStock` → наявність.
* **bereg** (`extract_bereg_card` / `extract_bereg_detail`) — картка з listing містить
  лише ціни/фото; детальна сторінка додає характеристики з таблиці «Характеристики».
  `external_id` — завжди `product_id` (є і в картці, і на сторінці товару), тому
  listing і деталі дають той самий ключ; SKU зберігається в характеристиці «Артикул».
  Ціни Magento: `special_price` (якщо є) → платіжна ціна, інакше `price`; стара ціна —
  звичайна `price` (або `old_price`, якщо `price` немає).

Загальні текстові хелпери (`common.py`, перенесені з `build_xlsx.py`):
`TYPE_WORDS`/`DESC_WORDS` (тип воблера), `BUOY_MAP` (слово → код плавучості),
`parse_depth` («до 1.5 м» → `(None, 1.5)`; «0.5–1.2 м» → `(0.5, 1.2)`),
`parse_float`, `match_value` (перше значення характеристики за ключовими словами).

## 3. Схема SQLite (`src/lures/db/`)

Пакет `lures.db` побудовано на **SQLAlchemy 2.0** (типізовані `DeclarativeBase`/
`Mapped`): `models.py` — ORM-моделі, `session.py` — engine + сесії,
`crud.py`/`queries.py` — запис/читання, `fts.py` — FTS5, `migrations.py` — оновлення
наявних баз, `schema.py` — `init_db`.

```
stores (id, code UNIQUE, name, base_url, created_at)
categories (id, store_id FK, code, name, url, UNIQUE(store_id, code))
products (id, store_id FK, category_id FK, external_id, name, brand,
          lure_type, buoyancy, weight_g, length_mm, depth_from_m, depth_to_m,
          price, old_price, discount_pct, rating, comments, availability,
          url, image_url, description, raw_json, extra_json, updated_at,
          UNIQUE(store_id, external_id),
          CHECK(buoyancy IN ('','F','SP','S','FS','SS','SR','SURF')),
          CHECK(availability IN ('available','out_of_stock','unknown')))
product_species (id, product_id FK, attribute, value)
price_history (id, product_id FK, price, old_price, created_at)
products_fts — FTS5(name, external_id, brand, lure_type, species_text)
```

* `raw_json` — оригінальний JSON джерела (повний), `extra_json` — характеристики.
* `product_species` перезаписується на кожній синхронізації.
* `price_history` — знімок **лише коли ціна/стара ціна змінилися** (без дублів).
* Індекси: `products.price`, `products.updated_at` (+ FK-колонки) для швидких фільтрів.
* `sku` видалено: він дублював `external_id`.
* FTS-пошук — `query_products(search=...)` шукає назву/артикул/бренд/тип/характеристики.

`products` має гібридні типізовані колонки + `extra_json`; це дозволяє фільтрувати
вагу/довжину/ціну SQL-запитом, зберігаючи повноту джерела.

## 4. Потоки

**Синхронізація** (`fetch.py` → `sync_store` / `sync_all`):
`Config → client → extractors → db.upsert_product`. Категорії беруться з
`config/stores.yaml` (у них `url`/`filters` — параметр для відповідного клієнта).
`SyncStats` повертає кількість товарів/нових/оновлених і помилки по категоріях.

**Перегляд/експорт**: `query_products` (фільтри ваги/довжини/плаву/акцій/пошуку) →
Streamlit (`ui.py`) або Excel (`export.py`) — «Параметри»/«Усі позиції»/«Тільки акції»,
колонка «Фільтр» на формулах із аркуша «Параметри».

## 5. Як додати магазин або категорію

1. Додайте блок у `config/stores.yaml` (для нового магазину — також `client` + блок у
   `extractors/`).
2. Для категорії: `code` (стабільний ключ), `url`/`filters` за таксономією сайту.
3. `uv run lures-import -s <code>` → перевірте статистику.
4. Для повніших характеристик bereg: `--fetch-details` або `fetch_details: true` у YAML
   (без прапорця береться значення з `stores.yaml`).