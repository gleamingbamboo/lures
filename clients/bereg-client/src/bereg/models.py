"""Typed pydantic v2 models for bereg.ua (Magento 1) catalogue pages."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "Breadcrumb",
    "CategoryPage",
    "Money",
    "ProductCard",
    "ProductDetail",
    "ProductImage",
    "ProductVariant",
    "SitemapEntry",
    "SpecGroup",
    "Specification",
]


class BeregModel(BaseModel):
    """Base model: tolerant to markup details that change between page versions."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class Money(BeregModel):
    """A parsed price: decimal amount plus the currency and the raw text."""

    amount: Decimal
    currency: str = "UAH"
    raw: str = ""


class Breadcrumb(BeregModel):
    """One entry of the ``div.breadcrumbs`` trail."""

    name: str
    url: str | None = None


class Specification(BeregModel):
    """A single ``label -> value`` row of the product specification table."""

    label: str
    value: str
    url: str | None = None


class SpecGroup(BeregModel):
    """Specifications belonging to one variant tab («Характеристики»)."""

    title: str
    specifications: list[Specification] = Field(default_factory=list)


class ProductCard(BeregModel):
    """A product teaser found in a category / search / sale listing."""

    product_id: int | None = None
    url: str
    name: str
    price: Money | None = None
    old_price: Money | None = None
    special_price: Money | None = None
    image: str | None = None
    image_alt: str | None = None

    @property
    def on_sale(self) -> bool:
        """Whether the card carries a special (discounted) price."""
        return self.special_price is not None


class CategoryPage(BeregModel):
    """A parsed listing page (category, search or sale)."""

    url: str
    title: str
    breadcrumbs: list[Breadcrumb] = Field(default_factory=list)
    items: list[ProductCard] = Field(default_factory=list)
    current_page: int = 1
    pages: int | None = None

    @property
    def has_next(self) -> bool:
        """True when another listing page exists after the current one."""
        return self.pages is None or self.current_page < self.pages


class ProductImage(BeregModel):
    """One normalised gallery image of a product."""

    url: str
    alt: str | None = None


class ProductVariant(BeregModel):
    """A row of the «Модифікації» table (one colour/modification)."""

    name: str
    url: str | None = None
    sku: str | None = None
    code: str | None = None
    image: str | None = None
    price: Money | None = None
    old_price: Money | None = None
    special_price: Money | None = None
    available: bool | None = None
    attributes: list[Specification] = Field(default_factory=list)


class ProductDetail(BeregModel):
    """A fully parsed product page.

    ``specifications`` is a convenience property returning the specs of the
    first variant tab; use ``specification_groups`` to address every tab.
    """

    product_id: int | None = None
    url: str
    name: str
    brand: str | None = None
    brand_url: str | None = None
    sku: str | None = None
    price: Money | None = None
    old_price: Money | None = None
    special_price: Money | None = None
    images: list[ProductImage] = Field(default_factory=list)
    description: str | None = None
    breadcrumbs: list[Breadcrumb] = Field(default_factory=list)
    specification_groups: list[SpecGroup] = Field(default_factory=list)
    variants: list[ProductVariant] = Field(default_factory=list)

    @property
    def main_image(self) -> str | None:
        """First normalised gallery image, if any."""
        return self.images[0].url if self.images else None

    @property
    def specifications(self) -> list[Specification]:
        """Specifications of the default (first) variant tab."""
        if self.specification_groups:
            return self.specification_groups[0].specifications
        return []


class SitemapEntry(BeregModel):
    """One ``<sitemap>``/``<url>`` entry of a sitemap document."""

    url: str
    lastmod: str | None = None
