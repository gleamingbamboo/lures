"""Command line interface for ibisgear-client (``ibisgear ...``)."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from ._version import __version__
from .client import IbisGearClient

app = typer.Typer(
    add_completion=False,
    help="Explore the ibis-gear.com catalog from the command line.",
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
    """ibis-gear.com catalog client."""


@app.command()
def taxons() -> None:
    """List top-level categories of the shop tree."""
    with IbisGearClient() as client:
        for taxon in client.iter_taxons(recursive=False):
            typer.echo(f"{taxon.code}\t{taxon.name}\t{taxon.totalProducts}")


@app.command()
def taxon(
    code: Annotated[str, typer.Argument(help="Taxon code, e.g. 01030100")],
) -> None:
    """Show a category and its children."""
    with IbisGearClient() as client:
        node = client.get_taxon(code)
    typer.echo(
        json.dumps(
            {
                "code": node.code,
                "name": node.name,
                "slug": node.slug,
                "totalProducts": node.totalProducts,
                "children": [
                    {"code": c.code, "name": c.name, "products": c.totalProducts}
                    for c in node.children
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command()
def products(
    taxon_code: Annotated[str, typer.Argument(help="Taxon code, e.g. 01030100")],
    limit: Annotated[int, typer.Option(help="Maximum number of products to print.")] = 10,
) -> None:
    """Print products of a taxon as JSON lines."""
    with IbisGearClient() as client:
        for index, product in enumerate(client.iter_products(taxon_code)):
            if index >= limit:
                break
            typer.echo(
                json.dumps(
                    {
                        "id": product.id,
                        "code": product.code,
                        "brand": product.brandName,
                        "price": product.price_uah,
                        "url": product.url,
                    },
                    ensure_ascii=False,
                )
            )


@app.command()
def variants(
    product_iri: Annotated[str, typer.Argument(help="Product IRI or code")],
    limit: Annotated[int, typer.Option(help="Maximum number of variants to print.")] = 10,
) -> None:
    """Print variants of a product as JSON lines."""
    with IbisGearClient() as client:
        for index, variant in enumerate(client.iter_product_variants(product_iri)):
            if index >= limit:
                break
            typer.echo(
                json.dumps(
                    {
                        "id": variant.id,
                        "code": variant.code,
                        "name": variant.name,
                        "price": variant.price_uah,
                        "inStock": variant.inStock,
                        "attributes": len(variant.attributes),
                    },
                    ensure_ascii=False,
                )
            )


if __name__ == "__main__":  # pragma: no cover
    app()
