"""Streamlit-інтерфейс агрегатора: синхронізація, фільтри, Excel.

Запуск: ``lures-serve`` (або ``streamlit run src/lures/ui.py``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

# Absolute imports (не відносні): Streamlit виконує файл як скрипт, тож `.canonical`
# не резолвиться. Пакет `lures` встановлено, тому `lures.*` працює завжди.
from lures.canonical import BUOYANCY_CODES, CANONICAL_FIELDS
from lures.config import Config, default_db_path, load_config
from lures.db import get_session, init_db, product_bounds, query_products
from lures.export import build_workbook_bytes
from lures.fetch import sync_store
from lures.logging import logger

_DISPLAY_FIELDS: list[tuple[str, str]] = [
    ("store", "Магазин"),
    ("category", "Категорія"),
    *((field.key, field.label) for field in CANONICAL_FIELDS),
]


def _db_path() -> Path:
    return default_db_path()


def _to_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame({label: [row.get(key) for row in rows] for key, label in _DISPLAY_FIELDS})


def _render_sidebar(config: Config) -> None:
    with st.sidebar:
        st.header("Джерела даних")
        codes = [store.code for store in config.stores]
        st.multiselect("Магазини для показу", codes, default=codes, key="display_stores")
        max_pages = st.number_input("Макс. сторінок (0 = всі)", min_value=0, value=0, step=1)
        fetch_details = st.checkbox("Bereg: сторінки товарів (повніше)", value=False)
        if st.button("Оновити дані", type="primary"):
            _run_sync(config, int(max_pages), fetch_details)


def _run_sync(config: Config, max_pages: int, fetch_details: bool) -> None:
    codes = [store.code for store in config.stores]
    progress = st.progress(0.0, text="Підготовка…")
    for index, code in enumerate(codes):
        store_cfg = config.store(code)
        if store_cfg is None:
            continue
        progress.progress(index / len(codes), text=f"{store_cfg.name}: синхронізація…")
        result = sync_store(
            store_cfg, _db_path(), max_pages=max_pages or None, fetch_details=fetch_details
        )
        summary = (
            f"{store_cfg.name}: {result.products} товарів "
            f"(нових {result.new}, оновлено {result.updated}, категорій {result.categories})"
        )
        st.success(summary)
        for error in result.errors:
            st.warning(error)
        progress.progress((index + 1) / len(codes), text=summary)
    progress.empty()
    st.rerun()


def _collect_rows(session: Session, config: Config) -> list[dict[str, Any]]:
    display = st.session_state.get("display_stores") or [store.code for store in config.stores]
    store_code: str | None = display[0] if len(display) == 1 else None

    bounds = product_bounds(session)
    w_max = float(bounds["max_w"] or 60.0)
    l_max = float(bounds["max_l"] or 200.0)

    with st.container(border=True):
        st.subheader("Фільтри")
        c1, c2, c3, c4 = st.columns(4)
        weight_range = c1.slider("Вага, г", 0.0, max(w_max, 1.0), (0.0, max(w_max, 1.0)), 0.5)
        length_range = c2.slider("Довжина, мм", 0.0, max(l_max, 1.0), (0.0, max(l_max, 1.0)), 1.0)
        buoys = c3.multiselect("Плавучість", list(BUOYANCY_CODES))
        on_sale = c4.checkbox("Тільки акції")
        search = st.text_input("Пошук (назва, артикул, бренд, характеристики)", "")

    min_weight = float(weight_range[0]) if weight_range[0] > 0 else None
    max_weight = float(weight_range[1]) if weight_range[1] < w_max else None
    min_length = float(length_range[0]) if length_range[0] > 0 else None
    max_length = float(length_range[1]) if length_range[1] < l_max else None

    return query_products(
        session,
        store=store_code,
        min_weight=min_weight,
        max_weight=max_weight,
        min_length=min_length,
        max_length=max_length,
        buoys=tuple(buoys),
        on_sale=on_sale,
        search=search,
    )


def _render_body(rows: list[dict[str, Any]]) -> None:
    total = len(rows)
    on_sale = sum(1 for row in rows if (row.get("discount_pct") or 0) > 0)
    surf = sum(1 for row in rows if row.get("buoyancy") == "SURF")
    prices = [float(row["price"]) for row in rows if row.get("price") is not None]
    average = sum(prices) / len(prices) if prices else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Позиції", total)
    c2.metric("Акції", on_sale)
    c3.metric("Поверхневі (SURF)", surf)
    c4.metric("Середня ціна, грн", f"{average:.0f}" if prices else "—")

    st.dataframe(_to_frame(rows), use_container_width=True, hide_index=True)

    if rows:
        st.download_button(
            "Скачати в Excel",
            data=build_workbook_bytes(rows),
            file_name="lures.xlsx",
            mime=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        )


def main() -> None:
    st.set_page_config(
        page_title="Приманки (воблери) — агрегатор",
        page_icon="\U0001f3a3",
        layout="wide",
    )
    try:
        config = load_config()
    except Exception as exc:
        logger.exception("Не вдалося завантажити конфігурацію")
        st.error(f"Не вдалося завантажити конфігурацію: {exc}")
        st.stop()
        return

    st.title("Приманки (воблери)")
    with get_session(_db_path()) as session:
        init_db(session)
        _render_sidebar(config)
        rows = _collect_rows(session, config)
        _render_body(rows)


if __name__ == "__main__":
    main()
