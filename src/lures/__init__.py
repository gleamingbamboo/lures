"""lures — агрегатор приманок (воблери) з flagman.ua, ibis-gear.com, bereg.ua.

Один канонічний формат (:mod:`lures.canonical`), SQLite-сховище, Streamlit UI і
Excel-експорт поверх трьох незалежних клієнт-бібліотек у ``clients/``.
"""

from __future__ import annotations

from ._version import __version__
from .canonical import BUOYANCY_CODES, CANONICAL_FIELDS, FIELD_BY_KEY, LureRecord
from .logging import logger, setup_logging

__all__ = [
    "BUOYANCY_CODES",
    "CANONICAL_FIELDS",
    "FIELD_BY_KEY",
    "LureRecord",
    "__version__",
    "logger",
    "setup_logging",
]
