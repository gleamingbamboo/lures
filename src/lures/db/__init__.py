"""SQLite-сховище агрегатора: моделі, сесії, CRUD, FTS-пошук.

Публічний API зберігає сумісність зі старим ``lures.db``:

* :func:`connect` / :func:`get_session` / :func:`init_db` — життєвий цикл БД;
* :func:`upsert_product` — запис канонічного рядка;
* :func:`query_products` / :func:`product_bounds` / :func:`stats` — читання.

Усі функції працюють із :class:`sqlalchemy.orm.Session`.
"""

from __future__ import annotations

from .crud import upsert_product
from .models import Base, Category, PriceHistory, Product, ProductSpecies, Store
from .queries import product_bounds, query_products, stats
from .schema import init_db
from .session import (
    connect,
    create_engine_for,
    dispose_engines,
    get_session,
    session_factory,
)

__all__ = [
    "Base",
    "Category",
    "PriceHistory",
    "Product",
    "ProductSpecies",
    "Store",
    "connect",
    "create_engine_for",
    "dispose_engines",
    "get_session",
    "init_db",
    "product_bounds",
    "query_products",
    "session_factory",
    "stats",
    "upsert_product",
]
