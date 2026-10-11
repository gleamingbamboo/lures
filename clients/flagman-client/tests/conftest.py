"""Shared pytest fixtures for the flagman-client test suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def catalog_payload() -> dict[str, Any]:
    return load_fixture("catalog.json")


@pytest.fixture(scope="session")
def goods_multi_payload() -> dict[str, Any]:
    return load_fixture("goods_multi.json")


@pytest.fixture(scope="session")
def goods_single_payload() -> dict[str, Any]:
    return load_fixture("goods_single.json")
