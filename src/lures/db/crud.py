"""Запис даних: upsert канонічного рядка приманки.

Стратегія — «швидкий» upsert через ORM: знайти існуючий рядок за
``(store_id, external_id)``, оновити (або створити) його, перезаписати
характеристики, додати знімок ціни та переіндексувати FTS.
"""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..canonical import LureRecord
from .fts import index_product
from .models import Category, PriceHistory, Product, ProductSpecies, Store

__all__ = ["upsert_product"]


def _get_or_create_store(
    session: Session, code: str, *, name: str = "", base_url: str = ""
) -> Store:
    store = session.execute(select(Store).where(Store.code == code)).scalar_one_or_none()
    if store is None:
        store = Store(code=code, name=name, base_url=base_url)
        session.add(store)
        session.flush()
        return store
    if name:
        store.name = name
    if base_url:
        store.base_url = base_url
    return store


def _get_or_create_category(
    session: Session, store_id: int, code: str, *, name: str = "", url: str = ""
) -> Category:
    category = session.execute(
        select(Category).where(Category.store_id == store_id, Category.code == code)
    ).scalar_one_or_none()
    if category is None:
        category = Category(store_id=store_id, code=code, name=name or code, url=url)
        session.add(category)
        session.flush()
        return category
    category.name = name or code
    category.url = url
    return category


def upsert_product(
    session: Session,
    record: LureRecord,
    *,
    raw_json: str = "{}",
    extra_json: str = "{}",
    specs: dict[str, str] | None = None,
    store_name: str = "",
    store_base_url: str = "",
    category_name: str = "",
    category_url: str = "",
) -> tuple[int, bool]:
    """Вставити/оновити товар; повертає ``(id, чи запис новий)``."""
    store = _get_or_create_store(session, record.store, name=store_name, base_url=store_base_url)
    category = _get_or_create_category(
        session,
        store.id,
        record.category,
        name=category_name or record.category,
        url=category_url,
    )

    product = session.execute(
        select(Product).where(
            Product.store_id == store.id,
            Product.external_id == record.external_id,
        )
    ).scalar_one_or_none()
    is_new = product is None
    if product is None:
        product = Product(store_id=store.id, external_id=record.external_id)
        session.add(product)

    product.category_id = category.id
    product.name = record.name
    product.brand = record.brand
    product.lure_type = record.lure_type
    product.buoyancy = record.buoyancy
    product.weight_g = record.weight_g
    product.length_mm = record.length_mm
    product.depth_from_m = record.depth_from_m
    product.depth_to_m = record.depth_to_m
    product.price = record.price
    product.old_price = record.old_price
    product.discount_pct = record.discount_pct
    product.rating = record.rating
    product.comments = record.comments
    product.availability = record.availability
    product.url = record.url
    product.image_url = record.image_url
    product.description = record.description
    product.raw_json = raw_json
    product.extra_json = extra_json
    product.updated_at = func.datetime("now")
    session.flush()

    session.execute(delete(ProductSpecies).where(ProductSpecies.product_id == product.id))
    clean_specs = {key: value for key, value in (specs or {}).items() if value not in ("", None)}
    for attribute, value in clean_specs.items():
        session.add(ProductSpecies(product_id=product.id, attribute=attribute, value=value))

    if record.price is not None:
        last = session.execute(
            select(PriceHistory)
            .where(PriceHistory.product_id == product.id)
            .order_by(PriceHistory.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        # Пишемо знімок лише коли ціна (або стара ціна) справді змінилася,
        # інакше таблиця роздувається дублями на кожен імпорт.
        if last is None or last.price != record.price or last.old_price != record.old_price:
            session.add(
                PriceHistory(product_id=product.id, price=record.price, old_price=record.old_price)
            )

    species_text = " ".join(f"{key} {value}" for key, value in clean_specs.items())
    index_product(
        session,
        product.id,
        name=record.name,
        external_id=record.external_id,
        brand=record.brand,
        lure_type=record.lure_type,
        species_text=species_text,
    )
    return product.id, is_new
