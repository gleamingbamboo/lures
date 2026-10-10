"""Екстрактори магазинів: клієнт-моделі -> канонічний LureRecord."""

from __future__ import annotations

from .bereg import STORE_CODE as BEREG_CODE
from .bereg import extract_bereg_card, extract_bereg_detail
from .flagman import STORE_CODE as FLAGMAN_CODE
from .flagman import extract_flagman
from .ibisgear import STORE_CODE as IBISGEAR_CODE
from .ibisgear import extract_ibisgear

__all__ = [
    "BEREG_CODE",
    "FLAGMAN_CODE",
    "IBISGEAR_CODE",
    "extract_bereg_card",
    "extract_bereg_detail",
    "extract_flagman",
    "extract_ibisgear",
]
