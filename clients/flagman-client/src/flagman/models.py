"""Typed pydantic v2 models for the Flagman.ua API payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "Breadcrumb",
    "Catalog",
    "CatalogData",
    "CategoryNode",
    "Characteristic",
    "Filter",
    "FilterRange",
    "FilterValue",
    "GoodsResponse",
    "Producer",
    "Product",
]

BASE_URL = "https://flagman.ua"


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".").replace("\u00a0", "").replace(" ", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


class FlagmanModel(BaseModel):
    """Base model: tolerant to extra fields the API may add."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
    )


class Producer(FlagmanModel):
    """Brand / manufacturer."""

    id: str | None = None
    title: str | None = None
    title_ua: str | None = None
    name: str | None = None
    status: str | int | None = None

    @property
    def display_name(self) -> str:
        return self.title_ua or self.title or ""


class Characteristic(FlagmanModel):
    """A single product characteristic (length, weight, buoyancy, ...)."""

    id: str | None = None
    title: str | None = None
    title_ua: str | None = None
    unit: str | None = None
    type: str | None = None
    value: str | None = None
    value_ua: str | None = None

    @property
    def display_title(self) -> str:
        return self.title_ua or self.title or ""

    @property
    def display_value(self) -> str:
        return self.value_ua or self.value or ""


class Breadcrumb(FlagmanModel):
    """One element of the breadcrumb trail / category node."""

    id: str | None = None
    title: str | None = None
    title_ua: str | None = None
    name: str | None = None
    name_ua: str | None = None
    status: str | int | None = None
    image: str | None = None
    type: str | None = None
    children: list[CategoryNode] = Field(default_factory=list)

    @property
    def display_title(self) -> str:
        return self.title_ua or self.title or ""


class CategoryNode(FlagmanModel):
    """A node of the catalog tree (as returned in ``data.children``)."""

    id: str | int | None = None
    title: str | None = None
    title_ua: str | None = None
    name: str | None = None
    name_ua: str | None = None
    status: str | int | None = None
    image: str | None = None
    type: str | None = None
    children: list[CategoryNode] = Field(default_factory=list)

    @property
    def display_title(self) -> str:
        return self.title_ua or self.title or ""


class FilterValue(FlagmanModel):
    """An option inside a catalog filter."""

    id: str | int | None = None
    title: str | None = None
    title_ua: str | None = None
    name: str | None = None
    count: int | None = None
    selected: int | bool | None = None
    link: str | None = None
    showLink: bool | None = None

    @property
    def display_title(self) -> str:
        return self.title_ua or self.title or ""


class FilterRange(FlagmanModel):
    """Numeric bounds of a range filter (for example ``price``: min/max).

    The API returns these under the same ``values`` key as categorical filter
    options, but as an object instead of a list.
    """

    min: float | None = None
    max: float | None = None
    selected: int | bool | None = None
    selected_min: float | None = None
    selected_max: float | None = None
    link: str | None = None

    @field_validator("min", "max", "selected_min", "selected_max", mode="before")
    @classmethod
    def _numbers(cls, value: Any) -> float | None:
        return _coerce_float(value)


class Filter(FlagmanModel):
    """A catalog filter (for example ``Тип воблера`` or ``Виробник``).

    ``values`` is a list of selectable :class:`FilterValue` for categorical
    filters, or a :class:`FilterRange` (min/max) for numeric range filters such
    as ``price``.
    """

    id: str | int | None = None
    title: str | None = None
    title_ua: str | None = None
    name: str | None = None
    type: str | None = None
    order: int | str | None = None
    unit: str | None = None
    description: str | None = None
    description_ua: str | None = None
    values: list[FilterValue] | FilterRange = Field(default_factory=list)

    @field_validator("values", mode="before")
    @classmethod
    def _default_values(cls, value: Any) -> Any:
        return [] if value is None else value

    @property
    def display_title(self) -> str:
        return self.title_ua or self.title or ""

    @property
    def value_list(self) -> list[FilterValue]:
        """Selectable options (empty for range filters)."""
        return self.values if isinstance(self.values, list) else []

    @property
    def value_range(self) -> FilterRange | None:
        """Numeric bounds for range filters (``None`` for categorical ones)."""
        return self.values if isinstance(self.values, FilterRange) else None

    def value_by_id(self, value_id: str | int) -> FilterValue | None:
        for value in self.value_list:
            if str(value.id) == str(value_id):
                return value
        return None


class CatalogData(FlagmanModel):
    """The ``data`` section of a catalog response."""

    goods: list[str] = Field(default_factory=list)
    filters: list[Filter] = Field(default_factory=list)
    children: list[CategoryNode] = Field(default_factory=list)

    @field_validator("goods", mode="before")
    @classmethod
    def _stringify_ids(cls, value: Any) -> list[str]:
        if value is None:
            return []
        return [str(item) for item in value]


class Catalog(FlagmanModel):
    """A full ``GET /site/catalog/{id}`` response."""

    status: str | None = None
    isValid: bool | None = None
    data: CatalogData = Field(default_factory=CatalogData)
    breadcrumbs: list[Breadcrumb] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Product(FlagmanModel):
    """A single product as returned by ``GET /api/goods/id/{ids}``."""

    id: str
    parent_id: str | None = None
    title: str | None = None
    title_ua: str | None = None
    name: str | None = None
    name_ua: str | None = None
    ext_id: str | None = None
    group_id: str | None = None
    series_id: str | None = None
    producer_id: str | None = None
    price: float | None = None
    old_price: float | None = None
    skuID: str | None = None
    rating: float | None = None
    count_comments: int | None = None
    sell_status: str | int | None = None
    showPrice: bool | None = None
    images: list[str] = Field(default_factory=list)
    description: str | None = None
    description_ua: str | None = None
    producer: Producer | None = None
    characteristics: dict[str, Characteristic] = Field(default_factory=dict)
    breadcrumbs: list[Breadcrumb] = Field(default_factory=list)
    mpath: str | None = None

    # ---------------------------------------------------------------- #
    # Normalisers
    # ---------------------------------------------------------------- #
    @field_validator("price", "old_price", "rating", mode="before")
    @classmethod
    def _numbers(cls, value: Any) -> float | None:
        return _coerce_float(value)

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    @field_validator("images", mode="before")
    @classmethod
    def _images(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [value]
        return [str(item) for item in value]

    @field_validator("characteristics", mode="before")
    @classmethod
    def _characteristics(cls, value: Any) -> dict[str, Any]:
        return value or {}

    # ---------------------------------------------------------------- #
    # Convenience helpers
    # ---------------------------------------------------------------- #
    @property
    def display_title(self) -> str:
        return self.title_ua or self.title or ""

    @property
    def is_available(self) -> bool:
        """``sell_status == 4`` means the item is in stock."""
        return str(self.sell_status) == "4"

    @property
    def discount_percent(self) -> int | None:
        if self.price is None or self.old_price is None or self.old_price <= self.price:
            return None
        return round((self.old_price - self.price) / self.old_price * 100)

    @property
    def main_image(self) -> str | None:
        return self.images[0] if self.images else None

    @property
    def url(self) -> str:
        slug = self.name or self.id
        return f"{BASE_URL}/{slug}/p{self.id}"

    def characteristic(
        self, *keywords: str, exclude: tuple[str, ...] = ()
    ) -> Characteristic | None:
        """Find the first characteristic whose title contains any keyword."""
        for characteristic in self.characteristics.values():
            title = f"{characteristic.title_ua or ''} {characteristic.title or ''}"
            if any(keyword in title for keyword in keywords) and not any(
                bad in title for bad in exclude
            ):
                return characteristic
        return None


class GoodsResponse(FlagmanModel):
    """A ``GET /api/goods/id/{ids}`` response.

    For a single id the API returns an object instead of a list; both shapes are
    normalised into a list here.
    """

    status: str | None = None
    data: list[Product] = Field(default_factory=list)

    @field_validator("data", mode="before")
    @classmethod
    def _wrap_single(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, dict):
            return [value]
        return value


# Resolve forward references for the recursive CategoryNode model.
Breadcrumb.model_rebuild()
CategoryNode.model_rebuild()
