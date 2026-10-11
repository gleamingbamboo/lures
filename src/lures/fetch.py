"""Оркестрація синхронізації: клієнт-бібліотеки -> DB через екстрактори."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from bereg import BeregClient, ProductCard, ProductDetail
from flagman import FlagmanClient
from flagman import Product as FlagmanProduct
from ibisgear import IbisGearClient, ProductVariant
from sqlalchemy.orm import Session

from .canonical import LureRecord
from .config import CategorySpec, Config, StoreConfig
from .db import get_session, init_db, upsert_product
from .extractors import (
    FLAGMAN_CODE,
    IBISGEAR_CODE,
    extract_bereg_card,
    extract_bereg_detail,
    extract_flagman,
    extract_ibisgear,
)
from .logging import logger

__all__ = ["SyncStats", "sync_all", "sync_store"]


@dataclass
class SyncStats:
    """Підсумок синхронізації одного магазину."""

    store: str
    categories: int = 0
    products: int = 0
    new: int = 0
    updated: int = 0
    errors: list[str] = field(default_factory=list)


def sync_store(
    store_cfg: StoreConfig,
    db_path: str | Path,
    *,
    max_pages: int | None = None,
    fetch_details: bool = True,
    fetch_variants: bool = True,
) -> SyncStats:
    """Синхронізувати один магазин у ``db_path``."""
    stats = SyncStats(store=store_cfg.code)
    with get_session(db_path) as session:
        init_db(session)
        if store_cfg.client == FLAGMAN_CODE:
            _sync_flagman(session, store_cfg, stats, max_pages)
        elif store_cfg.client == IBISGEAR_CODE:
            _sync_ibisgear(session, store_cfg, stats, max_pages, fetch_variants)
        else:
            _sync_bereg(session, store_cfg, stats, max_pages, fetch_details)
    return stats


def sync_all(
    config: Config,
    db_path: str | Path,
    *,
    stores: tuple[str, ...] = (),
    max_pages: int | None = None,
    fetch_details: bool = True,
    fetch_variants: bool = True,
) -> list[SyncStats]:
    """Синхронізувати (підмножину) магазинів конфігурації."""
    results: list[SyncStats] = []
    for store_cfg in config.stores:
        if stores and store_cfg.code not in stores:
            continue
        results.append(
            sync_store(
                store_cfg,
                db_path,
                max_pages=max_pages,
                fetch_details=fetch_details,
                fetch_variants=fetch_variants,
            )
        )
    return results


def _persist(
    session: Session,
    record: LureRecord,
    stats: SyncStats,
    *,
    raw: str,
    specs: dict[str, str],
    store_cfg: StoreConfig,
    category_name: str = "",
    category_url: str = "",
) -> None:
    stats.products += 1
    _, is_new = upsert_product(
        session,
        record,
        raw_json=raw,
        extra_json=json.dumps(specs, ensure_ascii=False),
        specs=specs,
        store_name=store_cfg.name,
        store_base_url=store_cfg.base_url,
        category_name=category_name or record.category,
        category_url=category_url,
    )
    if is_new:
        stats.new += 1
    else:
        stats.updated += 1


def _sync_flagman(
    session: Session, store_cfg: StoreConfig, stats: SyncStats, max_pages: int | None
) -> None:
    del max_pages  # iter_products flagman не підтримує обмеження сторінок
    client = FlagmanClient()
    for category in store_cfg.categories:
        category_id = category.url or category.code
        if not category_id:
            stats.errors.append(f"{category.code}: порожній id категорії")
            continue
        stats.categories += 1
        try:
            for product in client.iter_products(category_id, category.filters or None):
                record = extract_flagman(product, store=store_cfg.code, category=category.code)
                _persist(
                    session,
                    record,
                    stats,
                    raw=product.model_dump_json(),
                    specs=_flagman_specs(product),
                    store_cfg=store_cfg,
                    category_name=category.name,
                    category_url=category_id,
                )
        except Exception:
            logger.exception("flagman: помилка категорії %s", category.code)
            stats.errors.append(f"{category.code}: критична помилка синхронізації")


def _flagman_specs(product: FlagmanProduct) -> dict[str, str]:
    return {
        characteristic.display_title: characteristic.display_value
        for characteristic in product.characteristics.values()
        if characteristic.display_value
    }


def _sync_ibisgear(
    session: Session,
    store_cfg: StoreConfig,
    stats: SyncStats,
    max_pages: int | None,
    fetch_variants: bool = True,
) -> None:
    client = IbisGearClient()
    for category in store_cfg.categories:
        taxon = category.url or category.code
        if not taxon:
            stats.errors.append(f"{category.code}: порожній код таксона")
            continue
        stats.categories += 1
        try:
            for product in client.iter_products(taxon, max_pages=max_pages):
                # Fetch full variants with attributes if enabled
                variant = product.default_variant
                if fetch_variants and variant and product.iri:
                    try:
                        # Get all variants with full attributes from product-variants endpoint
                        # Use product.iri (the product IRI), not variant.iri (the variant IRI)
                        full_variants = list(client.iter_product_variants(product.iri, max_pages=1))
                        if full_variants:
                            # Find matching variant by IRI or use first
                            for v in full_variants:
                                if v.iri == variant.iri or str(v.id) in str(variant.iri):
                                    variant = v
                                    break
                            else:
                                variant = full_variants[0]
                    except Exception:
                        logger.warning("ibisgear: не вдалося завантажити варіанти для %s", product.code, exc_info=True)
                
                record = extract_ibisgear(product, store=store_cfg.code, category=category.code, variant=variant)
                _persist(
                    session,
                    record,
                    stats,
                    raw=product.model_dump_json(),
                    specs=_ibis_specs(variant),
                    store_cfg=store_cfg,
                    category_name=category.name,
                    category_url=category.url,
                )
        except Exception:
            logger.exception("ibisgear: помилка категорії %s", category.code)
            stats.errors.append(f"{category.code}: критична помилка синхронізації")


def _ibis_specs(variant: ProductVariant | None) -> dict[str, str]:
    if variant is None:
        return {}
    return {
        attribute.name or attribute.code or "атрибут": attribute.value or ""
        for attribute in variant.attributes
        if attribute.value
    }


def _sync_bereg(
    session: Session,
    store_cfg: StoreConfig,
    stats: SyncStats,
    max_pages: int | None,
    fetch_details: bool,
) -> None:
    client = BeregClient()
    for category in store_cfg.categories:
        url = category.url
        if not url:
            stats.errors.append(f"{category.code}: порожній URL категорії")
            continue
        stats.categories += 1
        details = fetch_details or category.fetch_details
        try:
            for card in client.iter_category_products(url, max_pages=max_pages):
                if details:
                    _sync_bereg_card_detail(session, card, store_cfg, stats, category, client)
                else:
                    record = extract_bereg_card(card, store=store_cfg.code, category=category.code)
                    _persist(
                        session,
                        record,
                        stats,
                        raw=card.model_dump_json(),
                        specs={},
                        store_cfg=store_cfg,
                        category_name=category.name,
                        category_url=category.url,
                    )
        except Exception:
            logger.exception("bereg: помилка категорії %s", category.code)
            stats.errors.append(f"{category.code}: критична помилка синхронізації")


def _sync_bereg_card_detail(
    session: Session,
    card: ProductCard,
    store_cfg: StoreConfig,
    stats: SyncStats,
    category: CategorySpec,
    client: BeregClient,
) -> None:
    try:
        detail: ProductDetail = client.get_product(card.url)
    except Exception:
        logger.warning("bereg: не вдалося завантажити %s", card.url, exc_info=True)
        record = extract_bereg_card(card, store=store_cfg.code, category=category.code)
        _persist(
            session,
            record,
            stats,
            raw=card.model_dump_json(),
            specs={},
            store_cfg=store_cfg,
            category_name=category.name,
            category_url=category.url,
        )
        return
    record = extract_bereg_detail(detail, store=store_cfg.code, category=category.code)
    specs = {
        specification.label: specification.value
        for group in detail.specification_groups
        for specification in group.specifications
    }
    _persist(
        session,
        record,
        stats,
        raw=detail.model_dump_json(),
        specs=specs,
        store_cfg=store_cfg,
        category_name=category.name,
        category_url=category.url,
    )
