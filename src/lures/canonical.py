"""Універсальний канонічний словник колонок (спільний для всіх магазинів).

Варіант A спільного типування: клієнт-бібліотеки публікують власні моделі, а
цей пакет відображає їх на документований, незалежний від магазину контракт.
Колонки нижче — єдине джерело правди для заголовків Excel, колонок SQLite і
фільтрів Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

__all__ = [
    "AVAILABILITY_CODES",
    "BUOYANCY_CODES",
    "CANONICAL_FIELDS",
    "FIELD_BY_KEY",
    "FieldDef",
    "FieldKind",
    "LureRecord",
]

FieldKind = Literal["str", "float", "int", "enum"]

# Нормалізовані коди плавучості (F=плаваючий, SP=суспендер, S=тонучий, ...).
BUOYANCY_CODES: tuple[str, ...] = ("F", "SP", "S", "FS", "SS", "SR", "SURF")

AVAILABILITY_CODES: tuple[str, ...] = ("available", "out_of_stock", "unknown")


@dataclass(frozen=True)
class FieldDef:
    """Одна канонічна колонка: ключ, український заголовок, тип і enum."""

    key: str
    label: str
    kind: FieldKind
    enum: tuple[str, ...] = ()


CANONICAL_FIELDS: tuple[FieldDef, ...] = (
    FieldDef("external_id", "Артикул", "str"),
    FieldDef("name", "Назва", "str"),
    FieldDef("brand", "Виробник", "str"),
    FieldDef("lure_type", "Тип воблера", "str"),
    FieldDef("buoyancy", "Плавучість", "enum", enum=BUOYANCY_CODES),
    FieldDef("weight_g", "Вага, г", "float"),
    FieldDef("length_mm", "Довжина, мм", "float"),
    FieldDef("depth_from_m", "Заглиблення від, м", "float"),
    FieldDef("depth_to_m", "Заглиблення до, м", "float"),
    FieldDef("price", "Ціна, грн", "float"),
    FieldDef("old_price", "Стара ціна, грн", "float"),
    FieldDef("discount_pct", "% акції", "int"),
    FieldDef("rating", "Рейтинг", "float"),
    FieldDef("comments", "Відгуки", "int"),
    FieldDef("availability", "Наявність", "enum", enum=AVAILABILITY_CODES),
    FieldDef("url", "Посилання", "str"),
    FieldDef("image_url", "Фото", "str"),
    FieldDef("description", "Опис", "str"),
)

FIELD_BY_KEY: dict[str, FieldDef] = {field.key: field for field in CANONICAL_FIELDS}


class LureRecord(BaseModel):
    """Канонічний рядок приманки (незалежний від магазину)."""

    model_config = ConfigDict(populate_by_name=True)

    store: str = ""
    category: str = ""
    external_id: str = ""
    name: str = ""
    brand: str = ""
    lure_type: str = ""
    buoyancy: str = ""
    weight_g: float | None = None
    length_mm: float | None = None
    depth_from_m: float | None = None
    depth_to_m: float | None = None
    price: float | None = None
    old_price: float | None = None
    discount_pct: int | None = None
    rating: float | None = None
    comments: int | None = None
    availability: str = "unknown"
    url: str = ""
    image_url: str = ""
    description: str = ""

    @model_validator(mode="after")
    def _normalise(self) -> LureRecord:
        if self.old_price is not None and self.price is not None and self.old_price <= self.price:
            self.old_price = None
        if self.discount_pct is None and self.price is not None and self.old_price is not None:
            self.discount_pct = round((self.old_price - self.price) / self.old_price * 100)
        if self.buoyancy not in BUOYANCY_CODES:
            self.buoyancy = ""
        if self.availability not in AVAILABILITY_CODES:
            self.availability = "unknown"
        return self

    def canonical_row(self) -> dict[str, object]:
        """Канонічні колонки (магазин/категорія першими, потім словник)."""
        row: dict[str, object] = {"store": self.store, "category": self.category}
        for field in CANONICAL_FIELDS:
            row[field.key] = getattr(self, field.key)
        return row
