"""Коди магазинів і відповідних клієнт-бібліотек (єдине джерело правди).

Раніше ті самі рядкові літерали дублювалися в ``config.py`` (``Literal``),
``extractors/*.py`` (``STORE_CODE``) і ``fetch.py`` (порівняння клієнтів).
"""

from __future__ import annotations

from typing import Final, Literal

__all__ = [
    "BEREG",
    "CLIENT_CODES",
    "FLAGMAN",
    "IBISGEAR",
    "STORE_CODES",
    "ClientCode",
]

FLAGMAN: Final[Literal["flagman"]] = "flagman"
IBISGEAR: Final[Literal["ibisgear"]] = "ibisgear"
BEREG: Final[Literal["bereg"]] = "bereg"

ClientCode = Literal["flagman", "ibisgear", "bereg"]

CLIENT_CODES: tuple[ClientCode, ...] = (FLAGMAN, IBISGEAR, BEREG)
STORE_CODES: tuple[str, ...] = (FLAGMAN, IBISGEAR, BEREG)
