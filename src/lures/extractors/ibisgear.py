"""Адаптер від ibisgear-client моделей до канонічних LureRecord."""

from __future__ import annotations

from ibisgear import Product as IbisProduct
from ibisgear import ProductVariant

from ..canonical import LureRecord
from ..constants import IBISGEAR
from .common import (
    SURF_TYPES,
    buoyancy_code,
    match_value,
    parse_depth,
    parse_float,
    wobbler_type,
)

__all__ = ["STORE_CODE", "extract_ibisgear"]

STORE_CODE = IBISGEAR


def _variant_pairs(variant: ProductVariant | None) -> list[tuple[str, str]]:
    if variant is None:
        return []
    return [
        (f"{attribute.name or ''} {attribute.code or ''}".strip(), attribute.value or "")
        for attribute in variant.attributes
    ]


def extract_ibisgear(
    product: IbisProduct,
    *,
    store: str = STORE_CODE,
    category: str = "",
    variant: ProductVariant | None = None,
) -> LureRecord:
    """Відобразити :class:`~ibisgear.models.Product` на канонічні колонки."""
    variant = variant or product.default_variant
    pairs = _variant_pairs(variant)
    hint = " ".join(
        filter(
            None,
            (
                variant.name if variant else None,
                product.code or "",
            ),
        )
    )
    name = (variant.name if variant and variant.name else "") or product.code or ""
    type_name = match_value(pairs, "Тип воблера", "Тип") or ""
    if not type_name:
        type_name = wobbler_type(hint)
    depth_from, depth_to = parse_depth(match_value(pairs, "аглиб"))
    buoyancy = "SURF" if type_name in SURF_TYPES else buoyancy_code(match_value(pairs, "лав"), hint)

    availability = "unknown"
    if variant is not None:
        availability = "available" if variant.inStock else "out_of_stock"

    return LureRecord(
        store=store,
        category=category,
        external_id=(variant.code if variant and variant.code else "") or product.code or "",
        name=name,
        brand=product.brandName or "",
        lure_type=type_name,
        buoyancy=buoyancy,
        weight_g=parse_float(match_value(pairs, "Вага", "Маса", exclude=("діапазон",))),
        length_mm=parse_float(match_value(pairs, "Довжина")),
        depth_from_m=depth_from,
        depth_to_m=depth_to,
        price=product.price_uah,
        old_price=variant.original_price_uah if variant else None,
        rating=product.averageRating,
        comments=product.totalReviews,
        availability=availability,
        url=product.url or "",
        image_url=product.main_image or "",
    )
