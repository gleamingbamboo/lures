"""Typed pydantic v2 models and the pagination helper for the ibis-gear API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "AttributeValue",
    "Page",
    "Product",
    "ProductImage",
    "ProductTag",
    "ProductVariant",
    "Taxon",
    "TaxonImage",
]

# https://ibis-gear.com/{top_slug}/details/{variant_slug}/
SITE_URL = "https://ibis-gear.com"
TOP_SLUG_FALLBACK = "rybalstvo"


class IbisModel(BaseModel):
    """Base model: tolerant to extra fields the API may add."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
    )


@dataclass
class Page[T: BaseModel]:
    """A single Hydra-paginated page of items."""

    items: list[T]
    total: int | None = None
    page: int = 1
    pages: int | None = None
    next_page: int | None = None
    previous_page: int | None = None

    @property
    def has_next(self) -> bool:
        return self.next_page is not None and self.next_page > self.page

    @property
    def has_previous(self) -> bool:
        return self.previous_page is not None and self.previous_page < self.page


class TaxonImage(IbisModel):
    type: str | None = None
    path: str | None = None

    @property
    def url(self) -> str | None:
        return self.path


class Taxon(IbisModel):
    iri: str | None = Field(default=None, alias="@id")
    type: str | None = Field(default=None, alias="@type")
    id: int | None = None
    code: str | None = None
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    position: int | None = None
    enabled: bool | None = None
    isWeapon: bool | None = None
    parent: str | None = None
    totalProducts: int | None = None
    images: list[TaxonImage] = Field(default_factory=list)
    children: list[Taxon] = Field(default_factory=list)

    @property
    def url(self) -> str | None:
        if not self.slug:
            return None
        return f"{SITE_URL}/{self.slug}/"

    def walk(self) -> list[Taxon]:
        """Return this taxon and all descendants (depth-first, pre-order)."""
        result: list[Taxon] = [self]
        for child in self.children:
            result.extend(child.walk())
        return result

    def find(self, code: str) -> Taxon | None:
        """Find a descendant taxon (or itself) by code."""
        if self.code == code:
            return self
        for child in self.children:
            found = child.find(code)
            if found is not None:
                return found
        return None


class AttributeValue(IbisModel):
    """A product-variant attribute, e.g. weight, color or model code."""

    id: int | None = None
    code: str | None = None
    name: str | None = None
    value: str | None = None
    valueCode: str | None = None
    slug: str | None = None
    siteDisplay: bool | None = None


class ProductImage(IbisModel):
    type: str | None = None
    path: str | None = None

    @property
    def url(self) -> str | None:
        return self.path


class ProductTag(IbisModel):
    code: str | None = None
    name: str | None = None


class ProductVariant(IbisModel):
    """A concrete sellable unit (SKU) of a product.

    Prices are transmitted in **kopecks** (1 UAH = 100 kopecks); use
    :attr:`price_uah` / :attr:`original_price_uah` for hryvnia values.
    """

    iri: str | None = Field(default=None, alias="@id")
    type: str | None = Field(default=None, alias="@type")
    id: int | None = None
    code: str | None = None
    slug: str | None = None
    name: str | None = None
    inStock: bool | None = None
    price: int | None = None
    originalPrice: int | None = None
    product: str | None = None
    images: list[ProductImage] = Field(default_factory=list)
    attributes: list[AttributeValue] = Field(default_factory=list)
    productTags: list[ProductTag] = Field(default_factory=list)
    channelHostname: str | None = None

    @field_validator("product", mode="before")
    @classmethod
    def _product_ref(cls, value: Any) -> Any:
        """Accept either an IRI string or an embedded product object."""
        if isinstance(value, dict):
            return value.get("@id") or value.get("id")
        return value

    @property
    def price_uah(self) -> float | None:
        return None if self.price is None else self.price / 100

    @property
    def original_price_uah(self) -> float | None:
        return None if self.originalPrice is None else self.originalPrice / 100

    @property
    def discount_percent(self) -> int | None:
        if self.price is None or self.originalPrice is None or self.originalPrice <= self.price:
            return None
        return round((self.originalPrice - self.price) / self.originalPrice * 100)

    @property
    def main_image(self) -> str | None:
        for image in self.images:
            if image.type == "main" or image.path:
                return image.url
        return None

    def attribute(self, code: str) -> AttributeValue | None:
        for attribute in self.attributes:
            if attribute.code == code:
                return attribute
        return None

    def attributes_by_name(self, name: str) -> list[AttributeValue]:
        return [attribute for attribute in self.attributes if attribute.name == name]


class Product(IbisModel):
    """A product (parent) with its variants.

    In ``products-filtered`` responses the embedded ``variants`` list is
    typically **truncated to one item**; use ``get_product_variants()`` to fetch
    every variant of a product.
    """

    iri: str | None = Field(default=None, alias="@id")
    type: str | None = Field(default=None, alias="@type")
    id: int | None = None
    code: str | None = None
    brandName: str | None = None
    mainTaxon: Taxon | None = Field(default=None, alias="mainTaxon")
    topTaxon: Taxon | None = Field(default=None, alias="topTaxon")
    defaultVariant: str | None = Field(default=None, alias="defaultVariant")
    variants: list[ProductVariant] = Field(default_factory=list)
    variantsCount: int | None = None
    averageRating: float | None = None
    totalReviews: int | None = None
    minPrice: int | None = None
    maxPrice: int | None = None
    channelHostname: str | None = None

    @field_validator("defaultVariant", mode="before")
    @classmethod
    def _default_variant_ref(cls, value: Any) -> Any:
        """The API returns the default variant as an IRI string (or a full object)."""
        if isinstance(value, dict):
            return value.get("@id") or value.get("id")
        return value

    @field_validator("variants", mode="before")
    @classmethod
    def _variants(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return [value]
        return value

    @property
    def default_variant(self) -> ProductVariant | None:
        """Resolve the default variant from the embedded ``variants`` list."""
        if not self.variants:
            return None
        if self.defaultVariant:
            for variant in self.variants:
                if variant.iri == self.defaultVariant or str(variant.id) in str(
                    self.defaultVariant
                ):
                    return variant
        return self.variants[0]

    @property
    def price_uah(self) -> float | None:
        """Cheapest variant price in hryvnia."""
        prices = [v.price for v in self.variants if v.price is not None]
        if prices:
            return min(prices) / 100
        if self.minPrice is not None:
            return self.minPrice / 100
        return None

    @property
    def url(self) -> str | None:
        slug = self.topTaxon.slug if self.topTaxon and self.topTaxon.slug else TOP_SLUG_FALLBACK
        variant = self.default_variant
        if variant is None or not variant.slug:
            return None
        return f"{SITE_URL}/{slug}/details/{variant.slug}/"

    @property
    def main_image(self) -> str | None:
        variant = self.default_variant
        return variant.main_image if variant else None


Taxon.model_rebuild()
