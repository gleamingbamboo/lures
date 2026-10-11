"""Легкі міграції SQLite-схеми для вже створених баз.

``Base.metadata.create_all`` не змінює наявні таблиці, тому для баз, створених
старішими версіями застосунку, тут виконується одноразове оновлення:

* ``products.sku`` (дублікат ``external_id``) — видаляється;
* ``products.type`` — перейменовується на ``lure_type``;
* CHECK-обмеження ``buoyancy`` / ``availability`` — додаються через перебудову
  таблиці (SQLite не вміє ``ALTER TABLE ... ADD CONSTRAINT``);
* індекси ``products.price`` / ``products.updated_at`` — додаються;
* пошкоджені FK-посилання на ``products_old`` (наслідок старого баґа перебудови)
  — виправляються перебудовою дочірніх таблиць.

Міграція ідемпотентна: на актуальній схемі нічого не робить.

Важливо: перейменування таблиць виконується на **тому самому** з'єднанні, де
виставлено ``PRAGMA foreign_keys=OFF`` та ``legacy_alter_table=ON``. Інакше
SQLite переписує ``REFERENCES`` у дочірніх таблицях на тимчасову назву
(``products_old``).
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, inspect, text

from .models import Base, Product

__all__ = ["migrate"]

_INDEXES: tuple[tuple[str, str], ...] = (
    ("ix_products_price", "products (price)"),
    ("ix_products_updated_at", "products (updated_at)"),
)

# Дочірні таблиці, що посилаються на ``products``.
_CHILD_TABLES: tuple[str, ...] = ("product_species", "price_history")


def _table_sql(engine: Engine, name: str) -> str:
    with engine.connect() as conn:
        return (
            conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = :name"),
                {"name": name},
            ).scalar()
            or ""
        )


@contextmanager
def _ddl_connection(engine: Engine) -> Iterator[Connection]:
    """З'єднання з вимкненими FK та legacy-режимом ALTER TABLE.

    Усі структурні зміни мають виконуватися саме на цьому з'єднанні, щоб
    SQLite не переписував FK-посилання при ``RENAME``.
    """
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        conn.exec_driver_sql("PRAGMA legacy_alter_table=ON")
        try:
            yield conn
            conn.commit()
        finally:
            with contextlib.suppress(Exception):
                conn.exec_driver_sql("PRAGMA legacy_alter_table=OFF")
                conn.exec_driver_sql("PRAGMA foreign_keys=ON")


def _drop_explicit_indexes(conn: Connection, table: str) -> None:
    """Прибрати явні індекси таблиці (перед перейменуванням)."""
    names = conn.execute(
        text(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'index' AND tbl_name = :table AND sql IS NOT NULL"
        ),
        {"table": table},
    ).scalars()
    for name in list(names):
        conn.exec_driver_sql(f'DROP INDEX IF EXISTS "{name}"')


def _rebuild_products(engine: Engine, old_columns: set[str]) -> None:
    """Перебудувати ``products`` з новою схемою, зберігши дані.

    Відповідність колонок «джерело → ціль»: однойменні беруться як є, а
    ``type`` (стара назва) відображається на ``lure_type``.
    """
    pairs: list[tuple[str, str]] = []
    for column in (c.name for c in Product.__table__.columns):
        if column in old_columns:
            pairs.append((column, column))
        elif column == "lure_type" and "type" in old_columns:
            pairs.append(("lure_type", "type"))
    target_list = ", ".join(target for target, _ in pairs)
    source_list = ", ".join(source for _, source in pairs)

    with _ddl_connection(engine) as conn:
        _drop_explicit_indexes(conn, "products")
        conn.exec_driver_sql("ALTER TABLE products RENAME TO products_old")
        Base.metadata.create_all(conn)
        conn.exec_driver_sql(
            f"INSERT INTO products ({target_list}) SELECT {source_list} FROM products_old"
        )
        conn.exec_driver_sql("DROP TABLE products_old")


def _rebuild_child(engine: Engine, name: str) -> None:
    """Перебудувати дочірню таблицю (напр. для виправлення FK на ``products``)."""
    columns = [column.name for column in Base.metadata.tables[name].columns]
    column_list = ", ".join(columns)
    with _ddl_connection(engine) as conn:
        _drop_explicit_indexes(conn, name)
        conn.exec_driver_sql(f'ALTER TABLE "{name}" RENAME TO "{name}_old"')
        Base.metadata.create_all(conn)
        conn.exec_driver_sql(
            f'INSERT INTO "{name}" ({column_list}) SELECT {column_list} FROM "{name}_old"'
        )
        conn.exec_driver_sql(f'DROP TABLE "{name}_old"')


def _repair_dangling_fk(engine: Engine) -> None:
    """Виправити дочірні таблиці, що посилаються на неіснуючий ``products_old``."""
    for name in _CHILD_TABLES:
        if "products_old" in _table_sql(engine, name):
            _rebuild_child(engine, name)


def migrate(engine: Engine) -> None:
    """Оновити схему наявної бази до актуальної (ідемпотентно)."""
    inspector = inspect(engine)
    if not inspector.has_table("products"):
        return

    # Спершу лікуємо наслідки старого баґа, якщо вони є.
    _repair_dangling_fk(engine)

    columns = {column["name"] for column in inspector.get_columns("products")}

    if "sku" in columns or ("type" in columns and "lure_type" not in columns):
        # Перебудова покриває і видалення sku, і перейменування type -> lure_type.
        _rebuild_products(engine, columns)
        columns.discard("sku")
        columns.discard("type")
        columns.add("lure_type")
    elif "ck_products_buoyancy" not in _table_sql(engine, "products"):
        _rebuild_products(engine, columns)

    with engine.begin() as conn:
        for name, target in _INDEXES:
            conn.exec_driver_sql(f"CREATE INDEX IF NOT EXISTS {name} ON {target}")
