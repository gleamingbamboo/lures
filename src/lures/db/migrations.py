"""Легкі міграції SQLite-схеми для вже створених баз.

``Base.metadata.create_all`` не змінює наявні таблиці, тому для баз, створених
старішими версіями застосунку, тут виконується одноразове оновлення:

* ``products.sku`` (дублікат ``external_id``) — видаляється;
* ``products.type`` — перейменовується на ``lure_type``;
* CHECK-обмеження ``buoyancy`` / ``availability`` — додаються через перебудову
  таблиці (SQLite не вміє ``ALTER TABLE ... ADD CONSTRAINT``);
* індекси ``products.price`` / ``products.updated_at`` — додаються.

Міграція ідемпотентна: на актуальній схемі нічого не робить.
"""

from __future__ import annotations

from sqlalchemy import Engine, inspect, text

from .models import Base, Product

__all__ = ["migrate"]

_INDEXES: tuple[tuple[str, str], ...] = (
    ("ix_products_price", "products (price)"),
    ("ix_products_updated_at", "products (updated_at)"),
)


def _table_sql(engine: Engine, name: str) -> str:
    with engine.connect() as conn:
        return (
            conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = :name"),
                {"name": name},
            ).scalar()
            or ""
        )


def _without_foreign_keys(engine: Engine) -> None:
    """Вимкнути перевірку FK на з'єднанні (працює лише поза транзакцією)."""
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        conn.commit()


def _rebuild_products(engine: Engine, old_columns: set[str]) -> None:
    """Перебудувати ``products`` з новою схемою, зберігши дані."""
    target = [column.name for column in Product.__table__.columns]
    shared = [column for column in target if column in old_columns]
    column_list = ", ".join(shared)

    _without_foreign_keys(engine)
    with engine.begin() as conn:
        # Явні індекси лишаються прив'язаними до перейменованої таблиці під тими
        # самими іменами — прибираємо їх, щоб create_all створив нові.
        indexes = conn.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'index' AND tbl_name = 'products' AND sql IS NOT NULL"
            )
        ).scalars()
        for index_name in list(indexes):
            conn.exec_driver_sql(f'DROP INDEX IF EXISTS "{index_name}"')
        conn.exec_driver_sql("ALTER TABLE products RENAME TO products_old")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(
                text(f"INSERT INTO products ({column_list}) SELECT {column_list} FROM products_old")
            )
        _without_foreign_keys(engine)
        with engine.begin() as conn:
            conn.exec_driver_sql("DROP TABLE products_old")
    except Exception:
        _without_foreign_keys(engine)
        with engine.begin() as conn:
            conn.exec_driver_sql("DROP TABLE IF EXISTS products")
            conn.exec_driver_sql("ALTER TABLE products_old RENAME TO products")
        raise


def migrate(engine: Engine) -> None:
    """Оновити схему наявної бази до актуальної (ідемпотентно)."""
    inspector = inspect(engine)
    if not inspector.has_table("products"):
        return

    columns = {column["name"] for column in inspector.get_columns("products")}

    if "sku" in columns:
        _without_foreign_keys(engine)
        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE products DROP COLUMN sku")
        columns.discard("sku")

    if "type" in columns and "lure_type" not in columns:
        _without_foreign_keys(engine)
        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE products RENAME COLUMN type TO lure_type")
        columns.discard("type")
        columns.add("lure_type")

    if "ck_products_buoyancy" not in _table_sql(engine, "products"):
        _rebuild_products(engine, columns)

    with engine.begin() as conn:
        for name, target in _INDEXES:
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {target}"))
