"""FTS5-індекс над товарами.

SQLAlchemy не має нативної підтримки віртуальних таблиць SQLite FTS5, тому
DDL/DML виконуємо через :func:`sqlalchemy.text`, а читаємо лише ``rowid``
товарів — далі фільтруємо ORM-запит по ``Product.id``.
"""

from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

__all__ = ["create_fts_table", "index_product", "rebuild_fts", "search_product_ids"]

_COLUMNS = ("name", "external_id", "brand", "lure_type", "species_text")
_COLUMNS_SQL = ", ".join(_COLUMNS)


def _existing_columns(engine: Engine) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(products_fts)")).all()
    return [row[1] for row in rows]


def _create(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(f"CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5({_COLUMNS_SQL})")
        )


def create_fts_table(engine: Engine) -> None:
    """Створити віртуальну таблицю ``products_fts``, якщо її ще немає.

    Якщо таблиця існує зі старою схемою колонок — вона перебудовується.
    """
    columns = _existing_columns(engine)
    if columns and columns != list(_COLUMNS):
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE products_fts"))
        columns = []
    _create(engine)
    if not columns:
        rebuild_fts(engine)


def rebuild_fts(engine: Engine) -> None:
    """Повністю переіндексувати FTS з таблиць ``products`` / ``product_species``."""
    columns = _existing_columns(engine)
    if columns != list(_COLUMNS):
        return
    species_sql = (
        "COALESCE((SELECT group_concat(attribute || ' ' || value, ' ') "
        "FROM product_species WHERE product_id = p.id), '')"
    )
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM products_fts"))
        conn.execute(
            text(
                "INSERT INTO products_fts "
                "(rowid, name, external_id, brand, lure_type, species_text) "
                f"SELECT p.id, p.name, p.external_id, p.brand, p.lure_type, {species_sql} "
                "FROM products p"
            )
        )


def _fts_token(term: str) -> str:
    """Загорнути пошуковий термін у лапки FTS5 (екрануючи внутрішні лапки)."""
    return '"' + term.replace('"', '""') + '"'


def index_product(
    session: Session,
    product_id: int,
    *,
    name: str,
    external_id: str,
    brand: str,
    lure_type: str,
    species_text: str,
) -> None:
    """Переіндексувати один товар (видалити старий рядок і вставити новий)."""
    session.execute(text("DELETE FROM products_fts WHERE rowid = :id"), {"id": product_id})
    session.execute(
        text(
            "INSERT INTO products_fts "
            "(rowid, name, external_id, brand, lure_type, species_text) "
            "VALUES (:id, :name, :external_id, :brand, :lure_type, :species_text)"
        ),
        {
            "id": product_id,
            "name": name,
            "external_id": external_id,
            "brand": brand,
            "lure_type": lure_type,
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
