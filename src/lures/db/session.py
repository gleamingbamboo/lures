"""Керування engine та сесіями SQLAlchemy.

Один ``Engine`` на абсолютний шлях до БД кешується в межах процесу. Сесії —
короткоживучі: для запису використовуйте контекстний менеджер :func:`get_session`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

__all__ = [
    "connect",
    "create_engine_for",
    "dispose_engines",
    "get_session",
    "session_factory",
]

_ENGINES: dict[str, Engine] = {}


def _sqlite_url(db_path: str | Path) -> str:
    path = Path(db_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


def _set_sqlite_pragma(dbapi_connection: object, _connection_record: object) -> None:
    """Увімкнути WAL та зовнішні ключі для кожного нового з'єднання."""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_engine_for(db_path: str | Path) -> Engine:
    """Повернути (кешований) ``Engine`` для шляху до БД."""
    key = str(Path(db_path).resolve())
    engine = _ENGINES.get(key)
    if engine is None:
        engine = create_engine(
            _sqlite_url(db_path),
            connect_args={"check_same_thread": False},
            future=True,
        )
        event.listen(engine, "connect", _set_sqlite_pragma)
        _ENGINES[key] = engine
    return engine


def session_factory(db_path: str | Path) -> sessionmaker[Session]:
    """Побудувати фабрику сесій для БД."""
    return sessionmaker(bind=create_engine_for(db_path), expire_on_commit=False, future=True)


def connect(db_path: str | Path) -> Session:
    """Відкрити сесію (виклик сумісності; закривайте через ``session.close()``)."""
    return session_factory(db_path)()


@contextmanager
def get_session(db_path: str | Path) -> Iterator[Session]:
    """Сесія як контекстний менеджер: commit при успіху, rollback при помилці."""
    session = session_factory(db_path)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def dispose_engines() -> None:
    """Закрити всі кешовані engine (для тестів і завершення процесу)."""
    for engine in _ENGINES.values():
        engine.dispose()
    _ENGINES.clear()
