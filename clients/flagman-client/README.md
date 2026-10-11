# flagman-client

[![CI](https://github.com/Gleam/flagman-client/actions/workflows/ci.yml/badge.svg)](https://github.com/Gleam/flagman-client/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typed-PEP%20561-blue.svg)](https://peps.python.org/pep-0561/)

A small, well-tested **synchronous + asynchronous** Python client for the internal
[Flagman.ua](https://flagman.ua) shop API (`r.flagman.ua`).

The Flagman.ua storefront is a Nuxt application talking to a JSON API. This
library wraps the two endpoints that matter for catalog work and gives you
typed pydantic models for free.

## Features

- 🔁 **Sync and async** APIs from a single client instance.
- 🧱 **Typed models** (pydantic v2): `Catalog`, `CategoryNode`, `Filter`,
  `Product`, `Producer`, `Characteristic`, `Breadcrumb`.
- 📦 **Automatic batching** of the `/api/goods/id/...` endpoint (de-duplication
  and order preservation included).
- 🕸️ **Lazy iterators** over a category, batch by batch.
- 🌳 **Category tree** traversal (`iter_categories`).
- ♻️ **Retries** with exponential backoff, `Retry-After` support and configurable
  timeouts.
- 🧩 **Dependency injection**: pass your own `httpx` transport for testing.
- 🚦 Optional **rate limiting** via `min_request_interval`.
- 📝 PEP 561 `py.typed` marker — works with `mypy`/`pyright` out of the box.

## Installation

```bash
uv add flagman-client
# or
pip install flagman-client
```

## Quick start

```python
from flagman import FlagmanClient

with FlagmanClient() as client:
    catalog = client.get_catalog("168794")  # category id
    print(len(catalog.data.goods), "products")
    print([f.display_title for f in catalog.data.filters])

    for product in client.iter_products("168794"):
        print(product.display_title, product.price, product.url)
```

### Async

```python
import asyncio
from flagman import FlagmanClient


async def main() -> None:
    async with FlagmanClient() as client:
        catalog = await client.aget_catalog("168794")
        async for product in client.aiter_products("168794"):
            print(product.id, product.display_title, product.price)


asyncio.run(main())
```

### Batching product details

```python
with FlagmanClient(batch_size=32) as client:
    products = client.get_products(["292051", "292076", "304489"])
    for product in products:
        print(product.id, product.discount_percent, product.main_image)
```

## API reference

### `FlagmanClient`

| Method | Description |
| --- | --- |
| `get_catalog(category_id, filters=None)` / `aget_catalog(...)` | Category: product ids, filters, children, metadata. |
| `get_products(ids)` / `aget_products(ids)` | Full details for many ids (batched, de-duplicated, order-preserving). |
| `get_product(id)` / `aget_product(id)` | A single product (raises `NotFoundError` when missing). |
| `iter_products(category_id, filters=None)` / `aiter_products(...)` | Lazy iterator over a category. |
| `iter_categories(category_id, expand=False)` | Depth-first walk over the category tree. |
| `search(query)` / `asearch(query)` | ⚠️ Experimental; see below. |
| `request(...)` / `arequest(...)` | Raw HTTP escape hatch with retries. |
| `get_json(url)` / `aget_json(url)` | GET + JSON decode. |

### Configuration

```python
FlagmanClient(
    base_url="https://r.flagman.ua",
    batch_size=32,
    timeout=30.0,
    max_retries=3,
    backoff_factor=0.5,
    min_request_interval=0.0,
    headers={"X-Test": "1"},
    user_agent="my-app/1.0",
    transport=None,  # bring your own httpx transport
)
```

All keyword arguments except `batch_size` are forwarded to the shared
`BaseHTTPClient`.

## Models

`Product` exposes several conveniences:

```python
product.display_title  # title_ua or title
product.is_available  # sell_status == "4"
product.discount_percent  # derived from price / old_price
product.main_image  # first image
product.url  # https://flagman.ua/{slug}/p{id}
product.characteristic("Довжина", "Довжина")
```

## CLI

```bash
flagman catalog 168794
flagman products 168794 --limit 20
```

## Errors

All errors derive from `FlagmanError`:

```
FlagmanError
├── RequestError      # transport failure after all retries
├── HTTPError         # 4xx/5xx (has .status_code and .response)
│   ├── NotFoundError # 404
│   └── RateLimitError# 429
└── ParseError        # body is not valid JSON
```

## Notes & limitations

- The public search endpoint (`/site/search/...`) currently returns no results to
  anonymous clients; `search()` is provided but should be considered
  experimental. Prefer walking categories with `iter_products()`.
- This project is an independent, unofficial client and is not affiliated with
  Flagman.ua. Please respect the site's terms of service and robots.txt.

## Development

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run mypy src
```

## License

MIT — see [LICENSE](LICENSE).
