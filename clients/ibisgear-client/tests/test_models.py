"""Tests for the ibisgear pydantic models."""

from __future__ import annotations

from ibisgear.models import Page, Product, ProductVariant, Taxon


def test_taxon_parsing(taxon_payload: dict) -> None:
    taxon = Taxon.model_validate(taxon_payload)
    assert taxon.name == "Приманки"
    assert taxon.code == "01030000"
    assert len(taxon.children) == 5
    assert taxon.find("01030100") is not None
    leaf = taxon.find("01030100")
    assert leaf is not None and leaf.name == "Воблери"
    assert taxon.totalProducts is not None


def test_taxon_walk(taxon_payload: dict) -> None:
    taxon = Taxon.model_validate(taxon_payload)
    walked = taxon.walk()
    assert walked[0].code == "01030000"
    codes = [node.code for node in walked]
    assert "01030100" in codes  # Воблери is a child of Приманки


def test_product_parsing(products_page1_payload: dict) -> None:
    page = Page[Product](
        items=[Product.model_validate(item) for item in products_page1_payload["hydra:member"]]
    )
    product = page.items[0]
    assert product.id is not None
    assert product.brandName
    assert product.variants
    assert product.price_uah is not None and product.price_uah > 0
    # URL — https://ibis-gear.com/{top_slug}/details/{variant_slug}/
    assert product.url is not None
    assert product.url.startswith("https://ibis-gear.com/")
    assert "/details/" in product.url
    assert product.url.endswith("/")


def test_variant_attributes(variants_payload: dict) -> None:
    page = Page[ProductVariant](
        items=[ProductVariant.model_validate(item) for item in variants_payload["hydra:member"]]
    )
    variant = page.items[0]
    assert variant.attributes
    mass = variant.attribute("massa-g")
    assert mass is not None and mass.value
    model = variant.attribute("model")
    assert model is not None and variant.attribute("proizvoditel") is not None


def test_variant_prices(variants_payload: dict) -> None:
    variant = ProductVariant.model_validate(variants_payload["hydra:member"][0])
    assert variant.price is not None
    assert variant.price_uah == variant.price / 100
    assert variant.original_price_uah == variant.originalPrice / 100
    assert isinstance(variant.inStock, bool)
    assert variant.main_image is None or variant.main_image.startswith("http")


def test_variant_discount() -> None:
    variant = ProductVariant.model_validate(
        {"id": 1, "price": 77100, "originalPrice": 100000, "attributes": []}
    )
    assert variant.discount_percent == 23  # (100000-77100)/100000 = 22.9%


def test_product_single(product_payload: dict) -> None:
    product = Product.model_validate(product_payload)
    assert product.defaultVariant is not None  # an IRI string
    default = product.default_variant
    assert default is not None
    assert product.price_uah == default.price / 100
