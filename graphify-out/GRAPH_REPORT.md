# Graph Report - lures  (2026-10-10)

## Corpus Check
- Large corpus: 92 files · ~1,358,230 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 1029 nodes · 2400 edges · 48 communities (27 shown, 21 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 218 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Database Persistence & FTS
- Bereg Catalogue Models
- Flagman HTTP Client Base
- Flagman Client API
- Flagman CLI & Fixtures
- Shared HTTP Client Core
- Docs, Config & Release Notes
- Bereg CLI Commands
- Bereg Client API
- IbisGear Client API
- Bereg HTTP & Errors
- HTTP Client Methods
- IbisGear Product Methods
- IbisGear Taxon Navigation
- Lures CLI & Config
- Text Parsing Helpers
- Sync Orchestration & Config
- Bereg Client Tests
- IbisGear HTTP & Errors
- IbisGear Variants & Search
- Legacy Excel Builder
- Streamlit UI
- Flagman Catalogue Models
- Bereg Sitemap Navigation
- Flagman Model Tests
- Flagman Product Model
- Canonical Column Schema
- Bereg Extractors
- Excel Export
- Extractor Tests
- Bereg Test Fixtures
- Bereg Listing Iteration
- Flagman Filter Models
- Variant & Pricing Concepts
- Flagman Characteristic Model
- Filter Range Model
- Project Packages
- Client Exception Types
- Product Model Concepts

## God Nodes (most connected - your core abstractions)
1. `BeregClient` - 64 edges
2. `IbisGearClient` - 52 edges
3. `FlagmanClient` - 42 edges
4. `BaseHTTPClient` - 29 edges
5. `BaseHTTPClient` - 29 edges
6. `BaseHTTPClient` - 29 edges
7. `Product` - 26 edges
8. `Product` - 23 edges
9. `ProductVariant` - 21 edges
10. `ProductCard` - 20 edges

## Surprising Connections (you probably didn't know these)
- `_bereg_card()` --uses--> `ProductCard`  [INFERRED]
  tests/test_extractors.py → clients/bereg-client/src/bereg/models.py
- `_bereg_detail()` --uses--> `ProductDetail`  [INFERRED]
  tests/test_extractors.py → clients/bereg-client/src/bereg/models.py
- `_sync_flagman()` --calls--> `FlagmanClient`  [INFERRED]
  src/lures/fetch.py → clients/flagman-client/src/flagman/client.py
- `_flagman_product()` --uses--> `Product`  [INFERRED]
  tests/test_extractors.py → clients/flagman-client/src/flagman/models.py
- `_sync_ibisgear()` --calls--> `IbisGearClient`  [INFERRED]
  src/lures/fetch.py → clients/ibisgear-client/src/ibisgear/client.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Lures Aggregator Client Libraries** — clients_bereg_client_readme_beregclient, clients_flagman_client_readme_flagmanclient, clients_ibisgear_client_readme_ibisgearclient [EXTRACTED 1.00]
- **Shared Client Exception Hierarchy** — clients_bereg_client_readme_beregerror, clients_flagman_client_readme_flagmanerror, clients_ibisgear_client_readme_ibisgearerror [INFERRED 0.85]
- **Canonical Ingestion Pipeline** — docs_architecture_canonical_dictionary, docs_architecture_lurerecord, docs_architecture_extractors, docs_architecture_sync_store, docs_architecture_sqlite_schema [EXTRACTED 1.00]

## Communities (48 total, 21 thin omitted)

### Community 0 - "Database Persistence & FTS"
Cohesion: 0.05
Nodes (30): _get_or_create_category(), _get_or_create_store(), upsert_product(), create_fts_table(), _fts_token(), index_product(), search_product_ids(), Base (+22 more)

### Community 1 - "Bereg Catalogue Models"
Cohesion: 0.06
Nodes (44): BeregModel, Breadcrumb, Money, ProductDetail, ProductImage, ProductVariant, SpecGroup, Specification (+36 more)

### Community 2 - "Flagman HTTP Client Base"
Cohesion: 0.05
Nodes (8): BaseHTTPClient, _retry_after_seconds(), FlagmanError, HTTPError, NotFoundError, ParseError, RateLimitError, RequestError

### Community 3 - "Flagman Client API"
Cohesion: 0.10
Nodes (35): _chunks(), FlagmanClient, test_aget_catalog(), test_aiter_products(), test_custom_headers_and_user_agent(), test_get_catalog(), test_get_product_single(), test_get_products_batches_and_dedupes() (+27 more)

### Community 4 - "Flagman CLI & Fixtures"
Cohesion: 0.06
Nodes (22): catalog(), main(), products(), _version_callback(), catalog_payload(), goods_multi_payload(), goods_single_payload(), load_fixture() (+14 more)

### Community 6 - "Docs, Config & Release Notes"
Cohesion: 0.08
Nodes (32): Client CI Pipeline, bereg-client v0.1.0, mypy strict pre-commit hook, BeregClient, Money, ProductCard, XML Sitemap Support, Category Listing Fixture (+24 more)

### Community 7 - "Bereg CLI Commands"
Cohesion: 0.15
Nodes (11): _card_dict(), category(), _dump(), find_variant(), main(), _money(), product(), sale() (+3 more)

### Community 8 - "Bereg Client API"
Cohesion: 0.11
Nodes (3): CategoryPage, parse_listing(), test_parse_listing()

### Community 9 - "IbisGear Client API"
Cohesion: 0.11
Nodes (7): _page_number(), AttributeValue, IbisModel, ProductImage, ProductTag, ProductVariant, TaxonImage

### Community 10 - "Bereg HTTP & Errors"
Cohesion: 0.13
Nodes (6): BeregError, HTTPError, NotFoundError, ParseError, RateLimitError, RequestError

### Community 13 - "IbisGear Taxon Navigation"
Cohesion: 0.08
Nodes (8): Taxon, test_product_parsing(), test_product_single(), test_taxon_parsing(), test_taxon_walk(), test_variant_attributes(), test_variant_discount(), test_variant_prices()

### Community 14 - "Lures CLI & Config"
Cohesion: 0.12
Nodes (6): export_cmd(), import_cmd(), serve_cmd(), default_db_path(), _default_path(), load_config()

### Community 15 - "Text Parsing Helpers"
Cohesion: 0.14
Nodes (9): buoyancy_code(), discount_percent(), match_value(), parse_depth(), parse_float(), wobbler_type(), extract_flagman(), extract_ibisgear() (+1 more)

### Community 16 - "Sync Orchestration & Config"
Cohesion: 0.18
Nodes (12): CategorySpec, StoreConfig, _flagman_specs(), _ibis_specs(), _persist(), sync_all(), _sync_bereg(), _sync_bereg_card_detail() (+4 more)

### Community 17 - "Bereg Client Tests"
Cohesion: 0.22
Nodes (19): BeregClient, _html(), test_aget_category(), test_aget_product(), test_aget_sitemap_index(), test_aiter_category_products_pagination(), test_aiter_sitemap_urls(), test_asearch() (+11 more)

### Community 18 - "IbisGear HTTP & Errors"
Cohesion: 0.13
Nodes (6): HTTPError, IbisGearError, NotFoundError, ParseError, RateLimitError, RequestError

### Community 20 - "Legacy Excel Builder"
Cohesion: 0.14
Nodes (10): build(), buoyancy(), char(), desc_type(), fill_sheet(), filter_formula(), num(), parse_depth() (+2 more)

### Community 21 - "Streamlit UI"
Cohesion: 0.22
Nodes (8): Config, _collect_rows(), _db_path(), main(), _render_body(), _render_sidebar(), _run_sync(), _to_frame()

### Community 22 - "Flagman Catalogue Models"
Cohesion: 0.15
Nodes (5): Breadcrumb, CatalogData, CategoryNode, FlagmanModel, Producer

### Community 24 - "Flagman Model Tests"
Cohesion: 0.15
Nodes (10): Catalog, GoodsResponse, test_catalog_filter_values(), test_catalog_parsing(), test_characteristics_parsing(), test_filter_missing_values_defaults_to_list(), test_filter_range_values(), test_product_helpers() (+2 more)

### Community 27 - "Bereg Extractors"
Cohesion: 0.26
Nodes (5): _card_external_id(), extract_bereg_card(), extract_bereg_detail(), _money(), _price_pair()

### Community 28 - "Excel Export"
Cohesion: 0.28
Nodes (7): build_workbook_bytes(), _column_index(), _fill_sheet(), _filter_formula(), _headers(), _params_sheet(), _widths()

### Community 29 - "Extractor Tests"
Cohesion: 0.24
Nodes (10): _bereg_card(), _bereg_detail(), _flagman_product(), _ibis_product(), test_bereg_card_extractor(), test_bereg_detail_extractor(), test_flagman_discount_cleared_when_no_sale(), test_flagman_extractor() (+2 more)

### Community 30 - "Bereg Test Fixtures"
Cohesion: 0.35
Nodes (8): listing_html(), listing_url(), product_html(), product_sitemap_bytes(), product_url(), _read(), search_html(), sitemap_index_bytes()

### Community 36 - "Variant & Pricing Concepts"
Cohesion: 0.33
Nodes (4): ProductDetail, ProductVariant (bereg), Product Detail Fixture, ProductVariant (ibisgear)

### Community 41 - "Project Packages"
Cohesion: 0.50
Nodes (4): bereg-client, flagman-client, ibisgear-client, lures

### Community 42 - "Client Exception Types"
Cohesion: 1.00
Nodes (3): BeregError, FlagmanError, IbisGearError

## Knowledge Gaps
- **18 isolated node(s):** `bereg-client`, `flagman-client`, `ibisgear-client`, `ProductDetail`, `XML Sitemap Support` (+13 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 393 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BeregClient` connect `Bereg Client Tests` to `Sitemap Streaming Helpers`, `Bereg Catalogue Models`, `Shared HTTP Client Core`, `Bereg CLI Commands`, `Bereg Client API`, `HTTP Transport Types (2)`, `Bereg HTTP & Errors`, `Sync Orchestration & Config`, `Bereg Sitemap Navigation`, `Bereg Listing Iteration`?**
  _High betweenness centrality (0.132) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `BeregClient` (e.g. with `category()` and `find_variant()`) actually correct?**
  _`BeregClient` has 28 INFERRED edges - model-reasoned connections that need verification._
- **What connects `bereg-client`, `flagman-client`, `ibisgear-client` to the rest of the system?**
  _18 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Database Persistence & FTS` be split into smaller, more focused modules?**
  _Cohesion score 0.05378151260504202 - nodes in this community are weakly interconnected._
- **Why does `IbisGearClient` connect `Flagman Client API` to `Flagman CLI & Fixtures`, `HTTP Transport Types`, `IbisGear Client API`, `HTTP Client Methods`, `IbisGear Product Methods`, `IbisGear Taxon Navigation`, `Sync Orchestration & Config`, `IbisGear Variants & Search`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 27 inferred relationships involving `IbisGearClient` (e.g. with `products()` and `taxon()`) actually correct?**
  _`IbisGearClient` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Should `Bereg Catalogue Models` be split into smaller, more focused modules?**
  _Cohesion score 0.05837837837837838 - nodes in this community are weakly interconnected._