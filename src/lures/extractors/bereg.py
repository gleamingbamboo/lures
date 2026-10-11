"""Адаптери від bereg-client моделей до канонічних LureRecord."""

from __future__ import annotations

from decimal import Decimal

from bereg import ProductCard, ProductDetail

from ..canonical import LureRecord
from ..constants import BEREG
from .common import (
    SURF_TYPES,
    buoyancy_code,
    match_value,
    parse_depth,
    parse_float,
    wobbler_type,
)

__all__ = ["STORE_CODE", "extract_bereg_card", "extract_bereg_detail"]

STORE_CODE = BEREG


def _money(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _price_pair(
    main: Decimal | None, special: Decimal | None, old: Decimal | None
) -> tuple[float | None, float | None]:
    """Канонічні (ціна, стара ціна) з Magento-полів товару.

    Magento 1 віддає три ціни: ``price`` (звичайна), ``special_price``
    (акційна, якщо є) та ``old_price`` (MSRP, якщо заданий). Канонічна
    «платіжна» ціна — це ``special_price`` коли він є, інакше ``price``;
    «стара» ціна — звичайна ``price`` (або ``old_price``, якщо ``price`` немає).
    """
    if special is not None:
        return _money(special), _money(main) if main is not None else _money(old)
    return _money(main), _money(old)


def _external_id(*, product_id: int | None, url: str = "", sku: str = "") -> str:
    """Стабільний ідентифікатор товару, однаковий для картки (listing) і деталей.

    Пріоритет: ``product_id`` (є і в картці, і на сторінці товару) → ``sku`` →
    slug з URL. ``product_id`` стоїть першим саме для того, щоб картка й
    детальна сторінка давали один і той самий ``external_id``.
    """
    if product_id is not None:
        return str(product_id)
    if sku:
        return sku
    return url.rstrip("/").rsplit("/", 1)[-1] if url else ""


def extract_bereg_card(
    card: ProductCard, *, store: str = STORE_CODE, category: str = ""
) -> LureRecord:
    """Мінімальний запис із картки у listing (без характеристик)."""
    price, old_price = _price_pair(
        card.price.amount if card.price else None,
        card.special_price.amount if card.special_price else None,
        card.old_price.amount if card.old_price else None,
    )
    return LureRecord(
        store=store,
        category=category,
        external_id=_external_id(product_id=card.product_id, url=card.url),
        name=card.name,
        price=price,
        old_price=old_price,
        availability="unknown",
        url=card.url,
        image_url=card.image or "",
    )


def extract_bereg_detail(
    detail: ProductDetail, *, store: str = STORE_CODE, category: str = ""
) -> LureRecord:
    """Повний запис зі сторінки товару (з характеристиками)."""
    pairs = [
        (specification.label, specification.value)
        for group in detail.specification_groups
        for specification in group.specifications
    ]
    type_name = match_value(pairs, "Тип воблера", "Тип") or ""
    if not type_name:
        type_name = wobbler_type(detail.name, detail.description or "")
    depth_from, depth_to = parse_depth(match_value(pairs, "аглиб"))
    buoyancy = (
        "SURF" if type_name in SURF_TYPES else buoyancy_code(match_value(pairs, "лав"), detail.name)
    )

    availability = "unknown"
    if detail.variants:
        availability = (
            "available"
            if any(
                variant.available for variant in detail.variants if variant.available is not None
            )
            else "out_of_stock"
        )

    price, old_price = _price_pair(
        detail.price.amount if detail.price else None,
        detail.special_price.amount if detail.special_price else None,
        detail.old_price.amount if detail.old_price else None,
    )

    return LureRecord(
        store=store,
        category=category,
        external_id=_external_id(
            product_id=detail.product_id, url=detail.url, sku=detail.sku or ""
        ),
        name=detail.name,
        brand=detail.brand or "",
        lure_type=type_name,
        buoyancy=buoyancy,
        weight_g=parse_float(match_value(pairs, "Вага", "Маса", exclude=("діапазон",))),
        length_mm=parse_float(match_value(pairs, "Довжина")),
        depth_from_m=depth_from,
        depth_to_m=depth_to,
        price=price,
        old_price=old_price,
        availability=availability,
        url=detail.url,
        image_url=detail.images[0].url if detail.images else "",
        description=detail.description or "",
    )
