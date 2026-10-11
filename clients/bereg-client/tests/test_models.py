"""Tests for the pydantic models of bereg-client."""

from __future__ import annotations

from decimal import Decimal

from bereg.models import (
    CategoryPage,
    Money,
    ProductCard,
    ProductDetail,
    ProductImage,
    ProductVariant,
    SpecGroup,
    Specification,
)


def test_money_defaults() -> None:
    money = Money(amount=Decimal("1250"))
    assert money.currency == "UAH"
    assert money.raw == ""


def test_money_keeps_raw_text() -> None:
    money = Money(amount=Decimal("1250"), raw="1 250 грн")
    assert money.raw == "1 250 грн"


def test_product_card_on_sale() -> None:
    plain = ProductCard(url="https://bereg.ua/uk/x.html", name="X")
    assert plain.on_sale is False

    discounted = ProductCard(
        url="https://bereg.ua/uk/x.html",
        name="X",
        special_price=Money(amount=Decimal("459")),
    )
    assert discounted.on_sale is True


def test_category_page_has_next() -> None:
    page = CategoryPage(url="https://bereg.ua/uk/x.html", title="X", current_page=1, pages=5)
    assert page.has_next is True

    last = CategoryPage(url="https://bereg.ua/uk/x.html", title="X", current_page=5, pages=5)
    assert last.has_next is False

    unknown = CategoryPage(url="https://bereg.ua/uk/x.html", title="X", current_page=1, pages=None)
    assert unknown.has_next is True


def test_product_detail_properties() -> None:
    detail = ProductDetail(
        url="https://bereg.ua/uk/x.html",
        name="X",
        images=[ProductImage(url="https://bereg.ua/media/catalog/product/1/1/x.jpg", alt="X")],
        specification_groups=[
            SpecGroup(
                title="Variant",
                specifications=[Specification(label="weight", value="40")],
            )
        ],
        variants=[ProductVariant(name="V", sku="04827196")],
    )
    assert detail.main_image == "https://bereg.ua/media/catalog/product/1/1/x.jpg"
    assert [(s.label, s.value) for s in detail.specifications] == [("weight", "40")]


def test_product_detail_without_images_or_specs() -> None:
    detail = ProductDetail(url="https://bereg.ua/uk/x.html", name="X")
    assert detail.main_image is None
    assert detail.specifications == []
    assert detail.variants == []
