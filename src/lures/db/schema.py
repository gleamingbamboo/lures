"""Ініціалізація схеми БД: ORM-таблиці + FTS5-індекс."""

from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from .fts import create_fts_table
from .models import Base

__all__ = ["init_db"]


def _as_engine(target: Session | Engine) -> Engine:
    bind = target.get_bind() if isinstance(target, Session) else target
    return bind.engine if isinstance(bind, Connection) else bind


def init_db(target: Session | Engine) -> None:
    """Створити всі таблиці та FTS-індекс, якщо їх ще немає.

    Приймає сесію (:class:`sqlalchemy.orm.Session`) або engine.
    """
    engine = _as_engine(target)
    Base.metadata.create_all(engine)
    create_fts_table(engine)
