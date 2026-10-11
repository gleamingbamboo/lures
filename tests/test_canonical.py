"""Тести канонічної моделі: розрахунок знижки та нормалізація enum."""

from __future__ import annotations

from lures.canonical import LureRecord


def _record(**kwargs: object) -> LureRecord:
    base = {"store": "flagman", "category": "voblery", "external_id": "1"}
    base.update(kwargs)
    return LureRecord(**base)


def test_discount_computed_from_prices() -> None:
    record = _record(price=100.0, old_price=125.0)
    assert record.discount_pct == 20


def test_discount_rounded() -> None:
    # (600 - 500) / 600 * 100 = 16.67 -> 17
    assert _record(price=500.0, old_price=600.0).discount_pct == 17


def test_no_discount_without_old_price() -> None:
    record = _record(price=100.0)
    assert record.old_price is None
    assert record.discount_pct is None


def test_old_price_cleared_when_not_a_discount() -> None:
    record = _record(price=100.0, old_price=100.0)
    assert record.old_price is None
    assert record.discount_pct is None


def test_unknown_buoyancy_and_availability_are_normalised() -> None:
    record = _record(buoyancy="невідомо", availability="щось")
    assert record.buoyancy == ""
    assert record.availability == "unknown"


def test_canonical_row_contains_description() -> None:
    row = _record(description="Опис").canonical_row()
    assert row["description"] == "Опис"
    assert row["store"] == "flagman"
    assert row["category"] == "voblery"
