"""bereg-client — a typed sync/async client for the bereg.ua (Magento 1) catalogue."""

from __future__ import annotations

from ._base import BaseHTTPClient
from ._version import __version__
from .client import DEFAULT_BASE_URL, DEFAULT_USER_AGENT, BeregClient
from .exceptions import (
    BeregError,
    HTTPError,
    NotFoundError,
    ParseError,
    RateLimitError,
    RequestError,
)
from .models import (
    Breadcrumb,
    CategoryPage,
    Money,
    ProductCard,
    ProductDetail,
    ProductImage,
    ProductVariant,
    SitemapEntry,
    SpecGroup,
    Specification,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_USER_AGENT",
    "BaseHTTPClient",
    "BeregClient",
    "BeregError",
    "Breadcrumb",
    "CategoryPage",
    "HTTPError",
    "Money",
    "NotFoundError",
    "ParseError",
    "ProductCard",
    "ProductDetail",
    "ProductImage",
    "ProductVariant",
    "RateLimitError",
    "RequestError",
    "SitemapEntry",
    "SpecGroup",
    "Specification",
    "__version__",
]
