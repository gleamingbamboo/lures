"""YAML-конфігурація магазинів і категорій агрегатора."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

__all__ = [
    "CategorySpec",
    "Config",
    "StoreConfig",
    "default_db_path",
    "load_config",
]

DEFAULT_CONFIG_ENV = "LURES_CONFIG"
DEFAULT_DB_ENV = "LURES_DB"


class CategorySpec(BaseModel):
    """Одна категорія магазину (дзеркало таксономії сайту)."""

    code: str
    name: str = ""
    url: str = ""
    filters: str | None = None
    fetch_details: bool = False
    max_pages: int | None = None


class StoreConfig(BaseModel):
    """Один магазин і його категорії."""

    code: str
    name: str = ""
    base_url: str = ""
    client: Literal["flagman", "ibisgear", "bereg"] = "flagman"
    categories: list[CategorySpec] = Field(default_factory=list)

    def category(self, code: str | None) -> CategorySpec | None:
        if code is None:
            return None
        for category in self.categories:
            if category.code == code:
                return category
        return None

    @property
    def client_label(self) -> str:
        return {
            "flagman": "flagman-client",
            "ibisgear": "ibisgear-client",
            "bereg": "bereg-client",
        }[self.client]


class Config(BaseModel):
    """Кореневий документ ``stores.yaml``."""

    stores: list[StoreConfig] = Field(default_factory=list)

    def store(self, code: str | None) -> StoreConfig | None:
        if code is None:
            return None
        for store in self.stores:
            if store.code == code:
                return store
        return None


def _default_path() -> Path:
    value = os.environ.get(DEFAULT_CONFIG_ENV)
    if value:
        return Path(value)
    return Path("config") / "stores.yaml"


def load_config(path: str | Path | None = None) -> Config:
    """Завантажити конфігурацію з YAML (за замовчуванням ``config/stores.yaml``)."""
    config_path = Path(path) if path else _default_path()
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return Config.model_validate(data)


def default_db_path() -> Path:
    value = os.environ.get(DEFAULT_DB_ENV)
    if value:
        return Path(value)
    return Path("data") / "lures.db"
