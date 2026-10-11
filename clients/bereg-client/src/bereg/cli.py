"""Command line interface for bereg-client (``bereg ...``)."""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer

from ._version import __version__
from .client import BeregClient
from .models import ProductCard

app = typer.Typer(
    add_completion=False,
    help="Explore the bereg.ua catalogue from the command line.",
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
    """bereg.ua catalogue client."""


def _money(value: Any) -> str | None:
    return str(value.amount) if value is not None else None


def _card_dict(card: ProductCard) -> dict[str, Any]:
    return {
        "id": card.product_id,
        "name": card.name,
        "price": _money(card.price),
        "old_price": _money(card.old_price),
        "special_price": _money(card.special_price),
        "url": card.url,
    }


def _dump(payload: dict[str, Any]) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command()
def category(
    url: Annotated[str, typer.Argument(help="Category page URL.")],
    limit: Annotated[int, typer.Option(help="Maximum number of items to print.")] = 10,
) -> None:
    """Print one category listing page."""
    with BeregClient() as client:
        page = client.get_category(url)
    _dump(
        {
            "title": page.title,
            "page": page.current_page,
            "pages": page.pages,
            "breadcrumbs": [b.name for b in page.breadcrumbs],
            "items": [_card_dict(c) for c in page.items[:limit]],
        }
    )


@app.command()
def product(
    url: Annotated[str, typer.Argument(help="Product page URL.")],
) -> None:
    """Print a product page (specs + variants)."""
    with BeregClient() as client:
        detail = client.get_product(url)
    _dump(
        {
            "id": detail.product_id,
            "name": detail.name,
            "brand": detail.brand,
            "sku": detail.sku,
            "price": _money(detail.price),
            "old_price": _money(detail.old_price),
            "special_price": _money(detail.special_price),
            "description": detail.description,
            "specifications": [{"label": s.label, "value": s.value} for s in detail.specifications],
            "variants": [
                {
                    "name": v.name,
                    "sku": v.sku,
                    "code": v.code,
                    "price": _money(v.price),
                    "url": v.url,
                }
                for v in detail.variants
            ],
        }
    )


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query.")],
    limit: Annotated[int, typer.Option(help="Maximum number of items to print.")] = 10,
) -> None:
    """Search the catalogue."""
    with BeregClient() as client:
        page = client.search(query)
    _dump(
        {
            "title": page.title,
            "pages": page.pages,
            "items": [_card_dict(c) for c in page.items[:limit]],
        }
    )


@app.command()
def sale(
    limit: Annotated[int, typer.Option(help="Maximum number of items to print.")] = 10,
) -> None:
    """List products currently on sale."""
    with BeregClient() as client:
        page = client.get_sale_page()
    _dump(
        {
            "pages": page.pages,
            "items": [_card_dict(c) for c in page.items[:limit]],
        }
    )


@app.command()
def sitemap(
    kind: Annotated[
        str,
        typer.Argument(help="Which sitemap: products | categories | brands"),
    ],
    limit: Annotated[int, typer.Option(help="Maximum number of URLs to print.")] = 10,
) -> None:
    """Print URLs from the matching XML sitemap."""
    with BeregClient() as client:
        if kind == "categories":
            urls = client.iter_category_urls()
        elif kind == "brands":
            urls = client.iter_brand_urls()
        else:
            urls = client.iter_product_urls()
        rows = []
        for index, url in enumerate(urls):
            if index >= limit:
                break
            rows.append(url)
    _dump({"kind": kind, "items": rows})


@app.command("find-variant")
def find_variant(
    sku: Annotated[str, typer.Argument(help="Vendor SKU (артикул), e.g. 04827196")],
) -> None:
    """Find the first product URL ending with ``-{sku}.html``."""
    with BeregClient() as client:
        url = client.find_variant_url(sku)
    _dump({"sku": sku, "url": url})


if __name__ == "__main__":  # pragma: no cover
    app()
