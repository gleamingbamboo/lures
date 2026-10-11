"""YAML-конфігурація магазинів і категорій агрегатора."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from .constants import BEREG, FLAGMAN, IBISGEAR, ClientCode

__all__ = [
    "CategorySpec",
    "Config",
    "LoggingConfig",
    "StoreConfig",
    "default_db_path",
    "load_config",
    "load_logging_config",
]

DEFAULT_CONFIG_ENV = "LURES_CONFIG"
DEFAULT_DB_ENV = "LURES_DB"
DEFAULT_LOG_CONFIG_ENV = "LURES_LOG_CONFIG"
DEFAULT_LOG_DIR_ENV = "LURES_LOG_DIR"
DEFAULT_LOG_LEVEL_CONSOLE_ENV = "LURES_LOG_LEVEL_CONSOLE"
DEFAULT_LOG_LEVEL_FILE_ENV = "LURES_LOG_LEVEL_FILE"


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
    client: ClientCode = FLAGMAN
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
            FLAGMAN: "flagman-client",
            IBISGEAR: "ibisgear-client",
            BEREG: "bereg-client",
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


class ConsoleLogConfig(BaseModel):
    enabled: bool = True
    level: str = "INFO"
    format: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    colorize: bool = True


class FileLogConfig(BaseModel):
    enabled: bool = True
    dir: str = "logs"
    level: str = "DEBUG"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    rotation: str = "1 day"
    retention: str = "30 days"
    compression: str = "zip"
    serialize: bool = False


class LoggingConfig(BaseModel):
    console: ConsoleLogConfig = Field(default_factory=ConsoleLogConfig)
    file: FileLogConfig = Field(default_factory=FileLogConfig)
    intercept_standard_logging: bool = True
    intercept_level: str = "DEBUG"


def _default_path() -> Path:
    value = os.environ.get(DEFAULT_CONFIG_ENV)
    if value:
        return Path(value)
    return Path("config") / "stores.yaml"


def _default_log_config_path() -> Path:
    value = os.environ.get(DEFAULT_LOG_CONFIG_ENV)
    if value:
        return Path(value)
    return Path("config") / "logging.yaml"


def load_config(path: str | Path | None = None) -> Config:
    """Завантажити конфігурацію з YAML (за замовчуванням ``config/stores.yaml``)."""
    config_path = Path(path) if path else _default_path()
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return Config.model_validate(data)


def load_logging_config(path: str | Path | None = None) -> LoggingConfig:
    """Завантажити конфігурацію логування з YAML (за замовчуванням ``config/logging.yaml``)."""
    config_path = Path(path) if path else _default_log_config_path()
    if not config_path.exists():
        return LoggingConfig()
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return LoggingConfig.model_validate(data)


def default_db_path() -> Path:
    value = os.environ.get(DEFAULT_DB_ENV)
    if value:
        return Path(value)
    return Path("data") / "lures.db"
