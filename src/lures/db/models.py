"""SQLAlchemy 2.0-моделі сховища агрегатора приманок.

Схема (детальніше — ``docs/architecture.md``):

* ``stores``           — магазини;
* ``categories``       — категорії магазину (дзеркало таксономії сайту);
* ``products``         — канонічні рядки-приманки, ``UNIQUE(store_id, external_id)``;
* ``product_species``  — характеристики (атрибут -> значення);
* ``price_history``    — знімки ціни на кожну синхронізацію.

FTS5-індекс ``products_fts`` не є ORM-моделлю — його створює :mod:`lures.db.fts`.
"""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

__all__ = [
    "Base",
    "Category",
    "PriceHistory",
    "Product",
    "ProductSpecies",
    "Store",
]


class Base(DeclarativeBase):
    """Спільний декларативний базовий клас усіх ORM-моделей."""


class Store(Base):
    """Один магазин-джерело (flagman, ibisgear, bereg, ...)."""

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    base_url: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("datetime('now')")
    )

    categories: Mapped[list[Category]] = relationship(
        back_populates="store", cascade="all, delete-orphan"
    )
    products: Mapped[list[Product]] = relationship(
        back_populates="store", cascade="all, delete-orphan"
    )


class Category(Base):
    """Категорія магазину (дзеркало таксономії сайту)."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("store_id", "code", name="uq_categories_store_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    url: Mapped[str] = mapped_column(String, nullable=False, default="")

    store: Mapped[Store] = relationship(back_populates="categories")
    products: Mapped[list[Product]] = relationship(back_populates="category")


class Product(Base):
    """Канонічний рядок-приманка (незалежний від магазину)."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("store_id", "external_id", name="uq_products_store_external"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    external_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    sku: Mapped[str] = mapped_column(String, nullable=False, default="")
    brand: Mapped[str] = mapped_column(String, nullable=False, default="")
    type: Mapped[str] = mapped_column(String, nullable=False, default="")
    buoyancy: Mapped[str] = mapped_column(String, nullable=False, default="")
    weight_g: Mapped[float | None] = mapped_column(Float)
    length_mm: Mapped[float | None] = mapped_column(Float)
    depth_from_m: Mapped[float | None] = mapped_column(Float)
    depth_to_m: Mapped[float | None] = mapped_column(Float)
    price: Mapped[float | None] = mapped_column(Float)
    old_price: Mapped[float | None] = mapped_column(Float)
    discount_pct: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[float | None] = mapped_column(Float)
    comments: Mapped[int | None] = mapped_column(Integer)
    availability: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    url: Mapped[str] = mapped_column(String, nullable=False, default="")
    image_url: Mapped[str] = mapped_column(String, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    extra_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("datetime('now')")
    )

    store: Mapped[Store] = relationship(back_populates="products")
    category: Mapped[Category | None] = relationship(back_populates="products")
    species: Mapped[list[ProductSpecies]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    prices: Mapped[list[PriceHistory]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductSpecies(Base):
    """Одна характеристика товару (атрибут -> значення)."""

    __tablename__ = "product_species"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    attribute: Mapped[str] = mapped_column(String, nullable=False, default="")
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")

    product: Mapped[Product] = relationship(back_populates="species")


class PriceHistory(Base):
    """Знімок ціни товару на кожну синхронізацію."""

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    price: Mapped[float | None] = mapped_column(Float)
    old_price: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("datetime('now')")
    )

    product: Mapped[Product] = relationship(back_populates="prices")
