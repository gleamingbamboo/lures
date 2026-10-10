# Воркфлоу роботи з ibis-gear.com (skill)

Записаний процес, який використовувався для створення `clients/ibisgear-client` —
як досліджувати й парсити ibis-gear.com. Корисно, коли щось зміниться на сайті або
треба додати нові дані.

## Що це за сайт

`ibis-gear.com` — headless (Vue/Nuxt) вітрина поверх **Sylius Shop API v2**
на `https://shop.ibis.net.ua`. API віддає JSON-LD із заголовком
`Accept: application/ld+json`, пагінація — Hydra `view` (1..N).

## Ендпоінти

* `GET /api/v2/shop/taxons` / `.../taxons/{code}` — дерево категорій.
* `GET /api/v2/shop/products-filtered/{taxonCode}?page=N` — товари категорії
  (20 на сторінку). **`itemsPerPage` → HTTP 403** — лише `page`.
* `GET /api/v2/shop/product-variants?product={productIri}&page=N` — усі варіанти.
* `GET /api/v2/shop/products/{code}` — один товар.

## Ключові знахідки

* **Ціни — у копійках** (1 грн = 100). Клієнт віддає `price_uah`. Помилки, коли
  ціну ділити на 100 двічі — класична.
* В `products-filtered` `variants` **обрізаний до одного** — брати атрибути з
  `defaultVariant`, повний список варіантів — окремим запитом `product-variants`.
* Атрибути варіанта: `AttributeValue {code, name, value}`; вага/довжина/тип/
  плавучість лежать у `name` («Вага», «Довжина», «Тип воблера», «Плавучість»).
* URL товару: `https://ibis-gear.com/{topTaxon.slug|rybalstvo}/details/{variant.slug}/`.
* `product-tags` — не для типу воблера; тип визначається за атрибутом або назвою.

## Ведення

* `iter_products(code, max_pages=None)` — ланцюжок сторінок; `Page.has_next`.
* Перевірка живого API: `uv run python -c "from ibisgear import IbisGearClient;
  c=IbisGearClient(); print([(t.code, t.name) for t in c.get_taxons()])"`.
* Моделі толерантні (`extra="allow"`); нові поля API не ламають са.

## Чого уникати

* Не використовувати `itemsPerPage` (403).
* Не плутати `Product.id` (внутрішній) з `Product.code` (SKU-подібний, зовнішній).
* Sitemap.xml в ibis-gear немає — категорії ходять через taxons.