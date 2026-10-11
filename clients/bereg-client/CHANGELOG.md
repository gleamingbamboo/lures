# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-10

### Added

- Synchronous and asynchronous `BeregClient` with retries/backoff, timeouts,
  rate limiting and injectable `httpx` transport (shared `BaseHTTPClient`).
- HTML parsers for category listings (`div.product-item`, `?p=N` pager),
  product detail pages («Характеристики» spec groups and «Модифікації»
  variants table), search results (`/uk/catalogsearch/result/`) and the sale
  page (`/uk/sale.html`).
- Money parsing for Magento prices (`1 250 грн`, `500,50 грн`).
- XML sitemap support: `sitemap.xml` index, gzipped `category`,
  `product-available` and `brand` sitemaps with streaming `<loc>` iterators
  and `find_product_url()`.
- `BeregError` exception hierarchy.
- CLI (`bereg ...`) covering category, product, search, sale and sitemap
  commands.
- Tests (pytest + respx), ruff + mypy strict, GitHub Actions CI, pre-commit
  hooks, `py.typed`.