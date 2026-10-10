"""Тести SQLAlchemy-шару: upsert, фільтри, FTS, історія цін."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from lures.canonical import LureRecord
from lures.db import (
    get_session,
    init_db,
    product_bounds,
    query_products,
    stats,
    upsert_product,
)


def _record(
    store: str = "flagman",
    external: str = "1",
    *,
    name: str = "Minnow 90",
    price: float = 500.0,
    old_price: float = 600.0,
    weight: float = 10.0,
    buoyancy: str = "SP",
) -> LureRecord:
    return LureRecord(
        store=store,
        category="voblery",
        external_id=external,
        name=name,
        type="Minnow",
        buoyancy=buoyancy,
        weight_g=weight,
        price=price,
        old_price=old_price,
        availability="available",
        url=f"https://{store}/p/{external}",
    )


def _upsert(
    session: Session, record: LureRecord, *, specs: dict[str, str] | None = None
) -> tuple[int, bool]:
    return upsert_product(
        session, record, raw_json="{}", extra_json="{}", specs=specs or {}, store_name="Test"
    )


def test_roundtrip_and_update(tmp_path: Path) -> None:
    with get_session(tmp_path / "lures.db") as session:
        init_db(session)
        pid, is_new = _upsert(session, _record())
        assert is_new is True
        pid2, is_new2 = _upsert(session, _record(price=450.0))
        assert pid2 == pid
        assert is_new2 is False

        rows = query_products(session)
        assert len(rows) == 1
        assert rows[0]["store_code"] == "flagman"
        assert rows[0]["store_name"] == "Test"
        assert rows[0]["category_name"] == "voblery"
        assert rows[0]["price"] == 450.0
        assert rows[0]["discount_pct"] == 25

        assert len(query_products(session, search="minnow")) == 1
        assert query_products(session, search="неіснуюче") == []
        assert len(query_products(session, on_sale=True)) == 1


def test_filters_and_bounds(tmp_path: Path) -> None:
    with get_session(tmp_path / "lures.db") as session:
        init_db(session)
        _upsert(session, _record("flagman", "1", weight=10.0))
        _upsert(
            session,
            _record("bereg", "2", name="Wave Popper", weight=5.0, buoyancy="SURF"),
        )

        assert len(query_products(session, store="flagman")) == 1
        assert len(query_products(session, buoys=("SURF",))) == 1
        assert len(query_products(session, min_weight=6.0)) == 1
        assert len(query_products(session, min_weight=6.0, max_weight=20.0)) == 1
        assert len(query_products(session, max_weight=6.0)) == 1

        bounds = product_bounds(session)
        assert bounds["min_w"] == 5.0
        assert bounds["max_w"] == 10.0

        summary = stats(session)
        assert summary["total"] == 2
        assert summary["surf"] == 1
        assert {store["code"] for store in summary["stores"]} == {"bereg", "flagman"}


def test_price_history_and_species(tmp_path: Path) -> None:
    with get_session(tmp_path / "lures.db") as session:
        init_db(session)
        _upsert(session, _record(price=500.0), specs={"Вага": "10 г"})

        species = (
            session.execute(
                text("SELECT attribute, value FROM product_species ORDER BY attribute")
            )
            .mappings()
            .all()
        )
        assert [(row["attribute"], row["value"]) for row in species] == [("Вага", "10 г")]

        # Наступний upsert без характеристик замінює species порожнім набором.
        _upsert(session, _record(price=420.0))
        species = session.execute(text("SELECT attribute FROM product_species")).all()
        assert species == []

        history = session.execute(text("SELECT price FROM price_history ORDER BY id")).all()
        assert [row[0] for row in history] == [500.0, 420.0]
