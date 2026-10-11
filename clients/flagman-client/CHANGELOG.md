# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-10

### Added

- Initial release.
- `FlagmanClient` with synchronous and asynchronous APIs.
- Typed pydantic v2 models: `Catalog`, `CategoryNode`, `Filter`, `Product`, `Producer`,
  `Characteristic`, `Breadcrumb`.
- High level helpers:
  - `get_catalog()` / `aget_catalog()` — category tree, filters and product ids.
  - `get_products()` / `aget_products()` — batched product details (auto chunking + de-duplication).
  - `get_product()` / `aget_product()` — single product.
  - `iter_products()` / `aiter_products()` — lazy iterators over a category.
  - `iter_categories()` — depth-first walk over a category tree.
- Shared HTTP core with retries, exponential backoff, `Retry-After` support,
  configurable timeouts, custom headers, injectable transports and optional rate limiting.
- Exception hierarchy: `FlagmanError`, `HTTPError`, `NotFoundError`, `RateLimitError`,
  `TransportError`, `ParseError`.
- `flagman` CLI (`flagman catalog`, `flagman products`).
- Test suite with `pytest`, `pytest-asyncio` and `respx` (no network access required).

[Unreleased]: https://github.com/Gleam/flagman-client/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Gleam/flagman-client/releases/tag/v0.1.0
