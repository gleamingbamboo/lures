# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-10

### Added

- Initial release.
- `IbisGearClient` with synchronous and asynchronous APIs.
- Typed pydantic v2 models for the Sylius Shop API v2 payloads:
  `Taxon`, `TaxonImage`, `Product`, `ProductVariant`, `AttributeValue`,
  `ProductImage`, `ProductTag`.
- Hydra pagination support: `get_products_page()`, `get_variants_page()`,
  `iter_products()`, `iter_product_variants()`.
- Kopeck → hryvnia helpers (`ProductVariant.price_uah`).
- Category tree helpers: `get_taxon()`, `get_taxons()`, `get_product()`.
- Shared HTTP core with retries, exponential backoff, `Retry-After` support,
  configurable timeouts, custom headers, injectable transports and optional
  rate limiting.
- Exception hierarchy: `IbisGearError`, `HTTPError`, `NotFoundError`,
  `RateLimitError`, `RequestError`, `ParseError`.
- `ibisgear` CLI (`ibisgear taxon`, `ibisgear products`, `ibisgear variants`).
- Test suite with `pytest`, `pytest-asyncio` and `respx` (no network access).

[Unreleased]: https://github.com/Gleam/ibisgear-client/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Gleam/ibisgear-client/releases/tag/v0.1.0