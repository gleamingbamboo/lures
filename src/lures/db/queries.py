"""Читання даних: канонічні рядки, межі для слайдерів і загальна статистика."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..canonical import CANONICAL_FIELDS
from .fts import search_product_ids
from .models import Category, Product, Store

__all__ = ["product_bounds", "query_products", "stats"]


def query_products(
    session: Session,
    *,
    store: str | None = None,
    min_weight: float | None = None,
    max_weight: float | None = None,
    min_length: float | None = None,
    max_length: float | None = None,
    buoys: tuple[str, ...] = (),
    on_sale: bool = False,
    search: str = "",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Канонічні рядки + магазин/категорія, з опціональними фільтрами."""
    stmt = (
        select(
            Product,
            Store.code.label("store_code"),
            Store.name.label("store_name"),
            Category.name.label("category_name"),
        )
        .join(Store, Store.id == Product.store_id)
        .outerjoin(Category, Category.id == Product.category_id)
    )

    if store:
        stmt = stmt.where(Store.code == store)
    if min_weight is not None:
        stmt = stmt.where(Product.weight_g >= min_weight)
    if max_weight is not None:
        stmt = stmt.where(Product.weight_g <= max_weight)
    if min_length is not None:
        stmt = stmt.where(Product.length_mm >= min_length)
    if max_length is not None:
        stmt = stmt.where(Product.length_mm <= max_length)
    if buoys:
        stmt = stmt.where(Product.buoyancy.in_(buoys))
    if on_sale:
        stmt = stmt.where(func.coalesce(Product.discount_pct, 0) > 0)
    if search.strip():
        matched_ids = search_product_ids(session, search)
        stmt = stmt.where(Product.id.in_(matched_ids))

    stmt = stmt.order_by(Product.updated_at.desc(), Product.id.desc())
    if limit is not None:
        stmt = stmt.limit(limit)

    rows: list[dict[str, Any]] = []
    for product, store_code, store_name, category_name in session.execute(stmt).all():
        # Лише канонічні колонки (+ назви магазину/категорії) — без службових
        # полів ``raw_json`` / ``extra_json`` / ``updated_at``.
        data: dict[str, Any] = {
            field.key: getattr(product, field.key) for field in CANONICAL_FIELDS
        }
        data["store_code"] = store_code
        data["store_name"] = store_name
        data["category_name"] = category_name
        rows.append(data)
    return rows


def product_bounds(session: Session) -> dict[str, float | None]:
    """Мінімальні/максимальні вага, довжина та ціна (для слайдерів UI)."""
    row = session.execute(
        select(
            func.min(Product.weight_g),
            func.max(Product.weight_g),
            func.min(Product.length_mm),
            func.max(Product.length_mm),
            func.min(Product.price),
            func.max(Product.price),
        )
    ).one()
    keys = ("min_w", "max_w", "min_l", "max_l", "min_p", "max_p")
    return {
        key: (float(value) if value is not None else None)
        for key, value in zip(keys, row, strict=True)
    }


def stats(session: Session) -> dict[str, Any]:
    """Загальні лічильники для дашборда."""
    total = session.scalar(select(func.count()).select_from(Product)) or 0
    on_sale = (
        session.scalar(
            select(func.count())
            .select_from(Product)
            .where(func.coalesce(Product.discount_pct, 0) > 0)
        )
        or 0
    )
    surf = (
        session.scalar(select(func.count()).select_from(Product).where(Product.buoyancy == "SURF"))
        or 0
    )
    store_rows = session.execute(
        select(Store.code, Store.name, func.count(Product.id).label("products"))
        .outerjoin(Product, Product.store_id == Store.id)
        .group_by(Store.id)
        .order_by(Store.code)
    ).all()
    stores = [
        {"code": code, "name": name, "products": products} for code, name, products in store_rows
    ]
    return {
        "total": int(total),
        "on_sale": int(on_sale),
        "surf": int(surf),
        "stores": stores,
    }
