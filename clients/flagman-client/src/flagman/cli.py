"""Command line interface for flagman-client (``flagman ...``)."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from ._version import __version__
from .client import FlagmanClient

app = typer.Typer(
    add_completion=False,
    help="Explore the Flagman.ua catalog from the command line.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """Flagman.ua API client."""


@app.command()
def catalog(
    category_id: Annotated[str, typer.Argument(help="Category id, e.g. 168794")],
    filters: Annotated[str | None, typer.Option(help="Raw filter string")] = None,
) -> None:
    """Print catalog summary for a category."""
    with FlagmanClient() as client:
        data = client.get_catalog(category_id, filters)
    typer.echo(
        json.dumps(
            {
                "title": data.metadata.get("h1_ua") or data.metadata.get("h1"),
                "goods": len(data.data.goods),
                "filters": len(data.data.filters),
                "children": len(data.data.children),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command()
def products(
    category_id: Annotated[str, typer.Argument(help="Category id, e.g. 168794")],
    limit: Annotated[int, typer.Option(help="Maximum number of products to print.")] = 10,
) -> None:
    """Print products of a category as JSON lines."""
    with FlagmanClient() as client:
        for index, product in enumerate(client.iter_products(category_id)):
            if index >= limit:
                break
            typer.echo(
                json.dumps(
                    {
                        "id": product.id,
                        "title": product.display_title,
                        "price": product.price,
                        "old_price": product.old_price,
                        "available": product.is_available,
                        "url": product.url,
                    },
                    ensure_ascii=False,
                )
            )


if __name__ == "__main__":  # pragma: no cover
    app()
