"""Командний рядок: ``lures-import`` / ``lures-export`` / ``lures-serve``.

Кожна консольна команда — окремий однокомандний Typer-застосунок (щоб
``lures-import -s flagman`` парсив аргументи). Об'єднаний ``app`` дозволяє
запускати ``python -m lures.cli import ...``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from .config import default_db_path, load_config, load_logging_config
from .db import get_session, init_db, query_products
from .export import build_workbook_bytes
from .fetch import sync_all
from .logging import logger, setup_logging

StoreOption = Annotated[
    list[str] | None,
    typer.Option("--store", "-s", help="Код магазину (можна кілька); порожньо = усі"),
]
ConfigPathOption = Annotated[str, typer.Option("--config", "-c", help="Шлях до stores.yaml")]
DbPathOption = Annotated[str, typer.Option("--db", "-d", help="Шлях до lures.db")]
MaxPagesOption = Annotated[
    int | None, typer.Option("--max-pages", help="Максимум сторінок (порожньо = усі)")
]
FetchDetailsOption = Annotated[
    bool | None,
    typer.Option(
        "--fetch-details/--no-fetch-details",
        help="Bereg: завантажувати сторінки товарів (порожньо = значення з конфігу)",
    ),
]
FetchVariantsOption = Annotated[
    bool,
    typer.Option(
        "--fetch-variants",
        help="Ibis Gear: завантажувати повні варіанти з атрибутами (за замовчуванням увімкнено)",
    ),
]
OutputOption = Annotated[str, typer.Option("--output", "-o", help="Файл Excel")]
SearchOption = Annotated[str, typer.Option("--search", help="Пошук за назвою/артикулом")]
LogLevelOption = Annotated[
    str,
    typer.Option("--log-level", help="Рівень логування консолі (DEBUG, INFO, WARNING, ERROR)"),
]
LogDirOption = Annotated[
    str,
    typer.Option("--log-dir", help="Папка для лог-файлів"),
]


def import_cmd(
    store: StoreOption = None,
    config_path: ConfigPathOption = "",
    db_path: DbPathOption = "",
    max_pages: MaxPagesOption = None,
    fetch_details: FetchDetailsOption = None,
    fetch_variants: FetchVariantsOption = True,
    log_level: LogLevelOption = "",
    log_dir: LogDirOption = "",
) -> None:
    """Синхронізувати магазини з конфігурації у SQLite."""
    setup_logging(load_logging_config(), log_level=log_level or None, log_dir=log_dir or None)
    selected: list[str] = store or []
    config = load_config(config_path or None)
    target = Path(db_path) if db_path else default_db_path()
    results = sync_all(
        config,
        target,
        stores=tuple(selected),
        max_pages=max_pages,
        fetch_details=fetch_details,
        fetch_variants=fetch_variants,
    )
    for result in results:
        status = "OK" if not result.errors else "WARN"
        logger.info(
            "[{status}] {store}: {products} товарів (нових {new}, оновлено {updated})",
            status=status,
            store=result.store,
            products=result.products,
            new=result.new,
            updated=result.updated,
        )
        for error in result.errors:
            logger.error("    ! {error}", error=error)


def export_cmd(
    output: OutputOption = "lures.xlsx",
    db_path: DbPathOption = "",
    search: SearchOption = "",
    log_level: LogLevelOption = "",
    log_dir: LogDirOption = "",
) -> None:
    """Експортувати базу у Excel."""
    setup_logging(load_logging_config(), log_level=log_level or None, log_dir=log_dir or None)
    target = Path(db_path) if db_path else default_db_path()
    with get_session(target) as session:
        init_db(session)
        rows = query_products(session, search=search)
    data = build_workbook_bytes(rows)
    out = Path(output)
    if str(out.parent) not in ("", "."):
        out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    logger.info("Збережено {out} — {count} позицій", out=out, count=len(rows))


def serve_cmd(
    config_path: ConfigPathOption = "",
    db_path: DbPathOption = "",
    log_level: LogLevelOption = "",
    log_dir: LogDirOption = "",
) -> None:
    """Запустити Streamlit-інтерфейс."""
    setup_logging(load_logging_config(), log_level=log_level or None, log_dir=log_dir or None)
    if config_path:
        os.environ.setdefault("LURES_CONFIG", config_path)
    if db_path:
        os.environ.setdefault("LURES_DB", db_path)
    from . import ui

    script = Path(ui.__file__).resolve()
    logger.info("Starting Streamlit UI: {script}", script=script)
    raise typer.Exit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(script)]))


# Однокомандні застосунки для консольних скриптів (lures-import/export/serve).
import_app = typer.Typer(
    help="Синхронізувати магазини з конфігурації у SQLite.", no_args_is_help=True
)
import_app.command()(import_cmd)

export_app = typer.Typer(help="Експортувати базу у Excel.", no_args_is_help=True)
export_app.command()(export_cmd)

serve_app = typer.Typer(help="Запустити Streamlit-інтерфейс.", no_args_is_help=True)
serve_app.command()(serve_cmd)

# Об'єднаний застосунок для ``python -m lures.cli``.
app = typer.Typer(
    help="Агрегатор приманок (воблери) — імпорт, експорт, serve.",
    no_args_is_help=True,
)
app.command("import")(import_cmd)
app.command("export")(export_cmd)
app.command("serve")(serve_cmd)


if __name__ == "__main__":
    app()
