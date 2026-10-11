# bereg-client

[![CI](https://github.com/Gleam/bereg-client/actions/workflows/ci.yml/badge.svg)](https://github.com/Gleam/bereg-client/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typed-PEP%20561-blue.svg)](https://peps.python.org/pep-0561/)

A small, well-tested **synchronous + asynchronous** Python client for the
[bereg.ua](https://bereg.ua) store catalogue. The storefront runs on
Magento 1, so this library parses server-rendered HTML instead of calling a
public JSON API. You get typed pydantic models for free.

## Features

- 🔁 **Sync and async** APIs from a single client instance.
- 🧱 **Typed models** (pydantic v2): `ProductCard`, `ProductDetail`,
  `ProductVariant`, `Specification`, `Money`, `Breadcrumb`, `CategoryPage`.
- 🗂️ **Category listings** with pager detection (`?p=N`) and lazy per-page
  iterators.
- 🔍 **Search** (`/uk/catalogsearch/result/?q=...`) and the **sale page**
  (`/uk/sale.html`), parsed with the same listing parser.
- 🧬 **Product details**: description, gallery, «Характеристики» spec groups
  (one per variant tab) and the «Модифікації» variants table (артикул, код,
  price, per-variant attributes).
- 🗺️ **XML sitemaps**: `sitemap.xml` index, gzipped `category` / `product-available`
  / `brand` sitemaps, plus `find_product_url(product_id)`.
- ♻️ **Retries** with exponential backoff, `Retry-After` support and configurable
  timeouts.
- 🧩 **Dependency injection**: pass your own `httpx` transport for testing.
- 🚦 Optional **rate limiting** via `min_request_interval`.
- 📝 PEP 561 `py.typed` marker — works with `mypy`/`pyright` out of the box.
- 🌐 Sends a realistic browser **User-Agent** by default (Magento 1 blocks
  generic bot agents).

## Installation

```bash
uv add bereg-client
# or
pip install bereg-client
```

## Quick start

```python
from bereg import BeregClient

with BeregClient() as client:
    page = client.get_category("https://bereg.ua/uk/spinning/primanki/voblery/minnou.html")
    print(page.title, len(page.items), "products on page", page.current_page)
    print("total pages:", page.pages)
    print(page.items[0].name, page.items[0].price.amount, page.items[0].url)
```

### Lazy iteration over every product in a category

```python
with BeregClient() as client:
    for card in client.iter_category_products(
        "https://bereg.ua/uk/spinning/primanki/voblery/minnou.html"
    ):
        print(card.product_id, card.name, card.price.amount)
```

### Async

```python
import asyncio
from bereg import BeregClient


async def main() -> None:
    async with BeregClient() as client:
        product = await client.aget_product(
            "https://bereg.ua/uk/vobler-daiwa-mt-monsterwake-156f.html"
        )
        print(product.name, product.brand)
        for variant in product.variants:
            print(variant.sku, variant.price.amount, variant.url)


asyncio.run(main())
```

### Product details

```python
with BeregClient() as client:
    product = client.get_product("https://bereg.ua/uk/vobler-daiwa-mt-monsterwake-156f.html")
    print(product.name, product.brand, product.sku, product.price.amount)
    for spec in product.specifications:
        print(spec.label, "->", spec.value)
    for variant in product.variants:  # Модифікації
        print(variant.name, variant.sku, variant.price.amount)
```

### Search & sale

```python
with BeregClient() as client:
    results = client.search("minnow")
    print(len(results.items), "hits for", results.title)

    sale = client.get_sale_page()
    print(len(sale.items), "items on sale")
```

### Sitemaps

```python
with BeregClient() as client:
    index = client.get_sitemap_index()
    print([e.url for e in index if "product" in e.url])

    count = 0
    for url in client.iter_product_urls():
        print(url)
        count += 1
        if count >= 3:
            break

    # variant URLs end with the printable артикул (SKU):
    print(client.find_variant_url("04827196"))
```

## API reference

### `BeregClient`

| Method | Description |
| --- | --- |
| `get_category(url, page=None)` / `aget_category(...)` | Category listing page (items, pager, breadcrumbs). |
| `iter_category_products(url, max_pages=None)` / `aiter_category_products(...)` | Lazy per-page iterator over a category. |
| `get_product(url)` / `aget_product(url)` | Full product detail (specs + variants). |
| `search(query, page=1)` / `asearch(...)` | Full-text search results (listing-shaped). |
| `get_sale_page(page=1)` / `aget_sale_page(...)` | `sale.html` listing. |
| `get_sitemap_index()` / `aget_sitemap_index()` | Entries of `sitemap.xml`. |
| `iter_sitemap_urls(url)` / `aiter_sitemap_urls(...)` | `<loc>` values of any (gzipped) sitemap. |
| `iter_category_urls()` / `iter_product_urls()` / `iter_brand_urls()` | Deduplicated URLs from the matching sitemaps. |
| `find_variant_url(sku)` / `afind_variant_url(...)` | Scan product sitemaps for `-{sku}.html`. |
| `request(...)` / `arequest(...)` | Raw HTTP escape hatch with retries. |

### Configuration

```python
BeregClient(
    base_url="https://bereg.ua",
    timeout=30.0,
    max_retries=3,
    backoff_factor=0.5,
    min_request_interval=0.0,
    headers={"X-Test": "1"},
    user_agent="my-app/1.0",
    transport=None,  # bring your own httpx transport
)
```

All keyword arguments are forwarded to the shared `BaseHTTPClient`. The default
`user_agent` is a realistic desktop Chrome string.

## Models

- `ProductCard`: link + `product_id` (from `data-id`), name, prices, image.
- `ProductDetail`: name, brand, sku, prices, gallery, description,
  `specifications` (default variant) and `specification_groups` (one per
  variant tab), plus `variants` parsed from the «Модифікації» table.
- `ProductVariant`: name, url, `sku` (артикул), `code` (код), price, image,
  attributes.
- `Money`: `Decimal` amount + currency (always `UAH`).
- `CategoryPage`: title (h1), breadcrumbs, items, `current_page` / `pages`.

Example conveniences:

```python
card.on_sale  # special price present?
product.main_image  # first normalised gallery image
product.specifications  # specs of the first variant tab
```

## CLI

```bash
bereg category https://bereg.ua/uk/spinning/primanki/voblery/minnou.html
bereg product https://bereg.ua/uk/vobler-daiwa-mt-monsterwake-156f.html
bereg search minnow --limit 5
bereg sale --limit 5
bereg sitemap products --limit 3
bereg find-variant 04827196
```

## Errors

All errors derive from `BeregError`:

```
BeregError
├── RequestError      # transport failure after all retries
├── HTTPError         # 4xx/5xx (has .status_code and .response)
│   ├── NotFoundError # 404
│   └── RateLimitError# 429
└── ParseError        # body cannot be decoded/parsed
```

## Notes & limitations

- This is an HTML scraper, not an API client. The selectors target the current
  bereg.ua theme and may need updating if the site redesigns.
- Grouped-product ids (from `data-id` / `data-params`) are NOT part of product
  URLs, so `find_variant_url()` matches the printable артикул (SKU) that ends
  variant URLs instead.
- Variant `code`s (e.g. `2242113`) are Magento product ids, `sku`/`артикул`
  (e.g. `04827196`) are the printable vendor codes.
- Sitemap sitemaps are gzipped and can be large (tens of thousands of URLs);
  the iterators stream them in a memory-friendly way (one HTTP request per
  sitemap file).
- This project is an independent, unofficial client and is not affiliated with
  bereg.ua. Please respect the site's terms of service and robots.txt.

## Development

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run mypy src
```

## License

MIT — see [LICENSE](LICENSE).