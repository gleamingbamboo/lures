"""Адаптер від flagman-client моделей до канонічних LureRecord."""

from __future__ import annotations

from flagman import Product as FlagmanProduct

from ..canonical import LureRecord
from .common import (
    SURF_TYPES,
    buoyancy_code,
    match_value,
    parse_depth,
    parse_float,
    wobbler_type,
)

__all__ = ["STORE_CODE", "extract_flagman"]

STORE_CODE = "flagman"


def extract_flagman(
    product: FlagmanProduct, *, store: str = STORE_CODE, category: str = ""
) -> LureRecord:
    """Відобразити :class:`~flagman.models.Product` на канонічні колонки."""
    pairs = [
        (characteristic.display_title, characteristic.display_value)
        for characteristic in product.characteristics.values()
    ]
    type_name = match_value(pairs, "Тип воблера") or ""
    if not type_name:
        type_name = wobbler_type(
            product.display_title,
            product.name or "",
            product.description_ua or "",
            product.description or "",
        )
    depth_from, depth_to = parse_depth(match_value(pairs, "аглиб"))
    hint = f"{product.name or ''} {product.title or ''}"
    buoyancy = "SURF" if type_name in SURF_TYPES else buoyancy_code(match_value(pairs, "лав"), hint)

    return LureRecord(
        store=store,
        category=category,
        external_id=product.ext_id or product.id,
        name=product.display_title or product.name or "",
        brand=product.producer.display_name if product.producer else "",
        lure_type=type_name,
        buoyancy=buoyancy,
        weight_g=parse_float(match_value(pairs, "Вага", exclude=("діапазон",))),
        length_mm=parse_float(match_value(pairs, "Довжина")),
        depth_from_m=depth_from,
        depth_to_m=depth_to,
        price=product.price,
        old_price=product.old_price,
        discount_pct=product.discount_percent,
        rating=product.rating,
        comments=product.count_comments,
        availability="available" if product.is_available else "out_of_stock",
        url=product.url,
        image_url=product.main_image or "",
        description=product.description_ua or product.description or "",
    )
