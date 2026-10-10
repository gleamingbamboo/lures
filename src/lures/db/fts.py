"""FTS5-індекс над товарами.

SQLAlchemy не має нативної підтримки віртуальних таблиць SQLite FTS5, тому
DDL/DML виконуємо через :func:`sqlalchemy.text`, а читаємо лише ``rowid``
товарів — далі фільтруємо ORM-запит по ``Product.id``.
"""

from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

__all__ = ["create_fts_table", "index_product", "search_product_ids"]

_COLUMNS = "name, sku, brand, type_text, species_text"


def create_fts_table(engine: Engine) -> None:
    """Створити віртуальну таблицю ``products_fts``, якщо її ще немає."""
    with engine.begin() as conn:
        conn.execute(
            text(f"CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5({_COLUMNS})")
        )


def _fts_token(term: str) -> str:
    """Загорнути пошуковий термін у лапки FTS5 (екрануючи внутрішні лапки)."""
    return '"' + term.replace('"', '""') + '"'


def index_product(
    session: Session,
    product_id: int,
    *,
    name: str,
    sku: str,
    brand: str,
    type_text: str,
    species_text: str,
) -> None:
    """Переіндексувати один товар (видалити старий рядок і вставити новий)."""
    session.execute(text("DELETE FROM products_fts WHERE rowid = :id"), {"id": product_id})
    session.execute(
        text(
            "INSERT INTO products_fts (rowid, name, sku, brand, type_text, species_text) "
            "VALUES (:id, :name, :sku, :brand, :type_text, :species_text)"
        ),
        {
            "id": product_id,
            "name": name,
            "sku": sku,
            "brand": brand,
            "type_text": type_text,
            "species_text": species_text,
        },
    )


def search_product_ids(session: Session, term: str) -> list[int]:
    """Повернути ``id`` товарів, що відповідають FTS-запиту."""
    cleaned = term.strip()
    if not cleaned:
        return []
    rows = session.execute(
        text("SELECT rowid FROM products_fts WHERE products_fts MATCH :term"),
        {"term": _fts_token(cleaned)},
    ).scalars()
    return [int(row) for row in rows]
