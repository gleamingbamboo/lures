"""ibisgear-client — a typed sync/async client for the ibis-gear.com catalog."""

from __future__ import annotations

from ._base import BaseHTTPClient
from ._version import __version__
from .client import DEFAULT_BASE_URL, IbisGearClient
from .exceptions import (
    HTTPError,
    IbisGearError,
    NotFoundError,
    ParseError,
    RateLimitError,
    RequestError,
)
from .models import (
    AttributeValue,
    Page,
    Product,
    ProductImage,
    ProductTag,
    ProductVariant,
    Taxon,
    TaxonImage,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "AttributeValue",
    "BaseHTTPClient",
    "HTTPError",
    "IbisGearClient",
    "IbisGearError",
    "NotFoundError",
    "Page",
    "ParseError",
    "Product",
    "ProductImage",
    "ProductTag",
    "ProductVariant",
    "RateLimitError",
    "RequestError",
    "Taxon",
    "TaxonImage",
    "__version__",
]
