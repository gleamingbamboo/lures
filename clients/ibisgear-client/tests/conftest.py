"""Shared pytest fixtures for the ibisgear-client test suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def taxon_payload() -> dict[str, Any]:
    return load_fixture("taxon.json")


@pytest.fixture(scope="session")
def products_page1_payload() -> dict[str, Any]:
    return load_fixture("products_page1.json")


@pytest.fixture(scope="session")
def products_page2_payload() -> dict[str, Any]:
    return load_fixture("products_page2.json")


@pytest.fixture(scope="session")
def variants_payload() -> dict[str, Any]:
    return load_fixture("variants.json")


@pytest.fixture(scope="session")
def product_payload() -> dict[str, Any]:
    return load_fixture("product.json")
