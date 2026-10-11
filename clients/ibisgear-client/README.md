# ibisgear-client

[![CI](https://github.com/Gleam/ibisgear-client/actions/workflows/ci.yml/badge.svg)](https://github.com/Gleam/ibisgear-client/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typed-PEP%20561-blue.svg)](https://peps.python.org/pep-0561/)

A small, well-tested **synchronous + asynchronous** Python client for the
[ibis-gear.com](https://ibis-gear.com) fishing store catalog — a headless
(Vue/Nuxt) storefront powered by the **Sylius Shop API v2** on
`https://shop.ibis.net.ua`.

## Features

- 🔁 **Sync and async** APIs from a single client instance.
- 🧱 **Typed models** (pydantic v2): `Taxon`, `Product`, `ProductVariant`,
  `AttributeValue`, `ProductImage`, `ProductTag`.
- 📄 **Hydra pagination** handled for you (`iter_products`,
  `iter_product_variants`, …).
- 🪙 **Kopeck → hryvnia** helpers (`ProductVariant.price_uah`).
- 🌳 **Taxon tree** traversal and lookup (`get_taxon`, `get_taxons`,
  `Taxon.walk`, `Taxon.find`).
- ♻️ **Retries** with exponential backoff, `Retry-After` support and configurable
  timeouts.
- 🧩 **Dependency injection**: pass your own `httpx` transport for testing.
- 🚦 Optional **rate limiting** via `min_request_interval`.
- 📝 PEP 561 `py.typed` marker.

## Installation

```bash
uv add ibisgear-client
# or
pip install ibisgear-client
```

## Quick start

```python
from ibisgear import IbisGearClient

with IbisGearClient() as client:
    taxon = client.get_taxon("01030100")  # Воблери
    print(taxon.name, taxon.totalProducts)

    for product in client.iter_products("01030100"):
        print(product.brandName, product.price_uah, product.url)
```

### Async

```python
import asyncio
from ibisgear import IbisGearClient


async def main() -> None:
    async with IbisGearClient() as client:
        taxon = await client.aget_taxon("01030100")
        async for product in client.aiter_products("01030100"):
            print(product.code, product.brandName, product.price_uah)


asyncio.run(main())
```

### Fetching ALL variants of a product

The `products-filtered` endpoint embeds only one variant per product, so use
`get_variants_page` / `iter_product_variants` for the full list:

```python
with IbisGearClient() as client:
    for variant in client.iter_product_variants("/api/v2/shop/products/15950111"):
        mass = variant.attribute("massa-g")
        price = variant.price_uah
        print(variant.code, mass.value if mass else "?", price)
```

## API reference

### `IbisGearClient`

| Method | Description |
| --- | --- |
| `get_taxon(code)` / `aget_taxon(code)` | One category with children. |
| `get_taxons()` / `aget_taxons()` | Top-level category tree. |
| `iter_taxons(recursive=True)` / `aiter_taxons(...)` | Depth-first taxon walk. |
| `get_products_page(taxon_code, page)` / `aget_products_page(...)` | One page of product summaries. |
| `iter_products(taxon_code, *, max_pages)` / `aiter_products(...)` | All products of a taxon. |
| `get_product(id_or_code)` / `aget_product(...)` | Single product. |
| `get_variants_page(product_iri, page)` / `aget_variants_page(...)` | One page of variants (30 per page). |
| `iter_product_variants(product_iri, *, max_pages)` / `aiter_product_variants(...)` | All variants of a product. |
| `search(query, page)` / `asearch(query, page)` | Free-text product search. |
| `request(...)` / `arequest(...)` | Raw HTTP escape hatch. |

`product_iri` may be a full IRI (`/api/v2/shop/products/...`) or a bare product
code — both are accepted.

## Models & helpers

```python
product.price_uah  # cheapest variant price in UAH
product.url  # https://ibis-gear.com/{top}/details/{variant_slug}/
product.main_image  # main image URL
variant.price_uah  # price / 100
variant.original_price_uah  # promo reference price / 100
variant.discount_percent  # derived percentage, if any
variant.attribute("massa-g")  # AttributeValue or None
variant.attributes_by_name("Колір товару")
variant.inStock  # availability
taxon.walk()  # taxon + all descendants
taxon.find("01030100")  # find descendant by code
```

Every response keeps the raw payload too (pydantic `extra="allow"`), so
unforeseen fields are never lost.

## CLI

```bash
ibisgear taxons
ibisgear taxon 01030100
ibisgear products 01030100 --limit 20
ibisgear variants /api/v2/shop/products/15950111
```

## Errors

All errors derive from `IbisGearError`:

```
IbisGearError
├── RequestError       # transport failure after all retries
├── HTTPError          # 4xx/5xx (has .status_code and .response)
│   ├── NotFoundError  # 404
│   └── RateLimitError # 429
└── ParseError         # body is not valid JSON
```

## Known quirks

- Sending an `itemsPerPage` query parameter makes the API return **HTTP 403** —
  pagination defaults to 20 products / 30 variants per page. Use `page` only.
- Some custom endpoints (e.g. `product-variants-filtered`) return HTTP 500 and
  should be avoided.
- Prices are transmitted in **kopecks** (1 UAH = 100 kopecks).

## Notes

This project is an independent, unofficial client and is not affiliated with
ibis-gear.com. Please respect the site's terms of service and robots.txt.

## Development

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run mypy src
```

## License

MIT — see [LICENSE](LICENSE).