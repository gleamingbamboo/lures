"""flagman-client — a typed sync/async client for the Flagman.ua shop API."""

from __future__ import annotations

from ._base import BaseHTTPClient
from ._version import __version__
from .client import DEFAULT_BASE_URL, FlagmanClient
from .exceptions import (
    FlagmanError,
    HTTPError,
    NotFoundError,
    ParseError,
    RateLimitError,
    RequestError,
)
from .models import (
    Breadcrumb,
    Catalog,
    CatalogData,
    CategoryNode,
    Characteristic,
    Filter,
    FilterRange,
    FilterValue,
    GoodsResponse,
    Producer,
    Product,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "BaseHTTPClient",
    "Breadcrumb",
    "Catalog",
    "CatalogData",
    "CategoryNode",
    "Characteristic",
    "Filter",
    "FilterRange",
    "FilterValue",
    "FlagmanClient",
    "FlagmanError",
    "GoodsResponse",
    "HTTPError",
    "NotFoundError",
    "ParseError",
    "Producer",
    "Product",
    "RateLimitError",
    "RequestError",
    "__version__",
]
