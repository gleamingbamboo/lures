"""Shared fixtures for the bereg-client test-suite."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def listing_url() -> str:
    return "https://bereg.ua/uk/spinning/primanki/voblery/minnou.html"


@pytest.fixture
def listing_html() -> str:
    return _read("listing.html")


@pytest.fixture
def product_url() -> str:
    return "https://bereg.ua/uk/vobler-daiwa-mt-monsterwake-156f.html"


@pytest.fixture
def product_html() -> str:
    return _read("product.html")


@pytest.fixture
def search_html() -> str:
    return _read("search.html")


@pytest.fixture
def product_sitemap_bytes() -> bytes:
    return (FIXTURES / "product-available.xml.gz").read_bytes()


@pytest.fixture
def sitemap_index_bytes() -> bytes:
    return (FIXTURES / "sitemap.xml").read_bytes()
