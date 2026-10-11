"""Parser tests against the trimmed HTML fixtures captured from bereg.ua."""

from __future__ import annotations

from decimal import Decimal

from bereg.models import CategoryPage, Money, ProductDetail
from bereg.parsing import parse_listing, parse_price, parse_product_detail


def test_parse_price_plain() -> None:
    money = parse_price("1 250 грн")
    assert money is not None
    assert money.amount == Decimal("1250")
    assert money.currency == "UAH"
    assert money.raw == "1 250 грн"


def test_parse_price_non_breaking_spaces() -> None:
    money = parse_price("1\xa0250\xa0грн")
    assert money is not None
    assert money.amount == Decimal("1250")


def test_parse_price_decimal_comma() -> None:
    money = parse_price("500,50 грн")
    assert money is not None
    assert money.amount == Decimal("500.50")


def test_parse_price_garbage() -> None:
    assert parse_price(None) is None
    assert parse_price("") is None
    assert parse_price("not a price") is None


def test_parse_listing(listing_html: str, listing_url: str) -> None:
    page = parse_listing(listing_html, listing_url)
    assert isinstance(page, CategoryPage)
    assert page.title == "Мінноу"
    assert page.pages == 5
    assert page.current_page == 1
    assert len(page.items) == 3
    assert [b.name for b in page.breadcrumbs] == [
        "Головна",
        "Хижак",
        "Приманки",
        "Воблери",
        "Мінноу",
    ]


def test_parse_listing_regular_card(listing_html: str, listing_url: str) -> None:
    page = parse_listing(listing_html, listing_url)
    card = page.items[0]
    assert card.product_id == 1162
    assert card.name.startswith("Воблер Daiwa")
    assert card.price is not None and card.price.amount == Decimal("1250")
    assert card.special_price is None
    assert card.old_price is None
    assert card.on_sale is False
    assert card.url == "https://bereg.ua/uk/vobler-daiwa-mt-monsterwake-156f.html"


def test_parse_listing_sale_card(listing_html: str, listing_url: str) -> None:
    page = parse_listing(listing_html, listing_url)
    sale = [c for c in page.items if c.on_sale]
    assert len(sale) == 1
    card = sale[0]
    assert card.special_price is not None and card.special_price.amount == Decimal("459")
    assert card.old_price is not None and card.old_price.amount == Decimal("765")
    assert card.price is None


def test_parse_listing_card_images_normalised(listing_html: str, listing_url: str) -> None:
    page = parse_listing(listing_html, listing_url)
    assert len(page.items) == 3
    for card in page.items:
        assert card.image is not None
        assert card.image.startswith("https://bereg.ua/media/catalog/product/")
        assert "/cache/" not in str(card.image)


def test_parse_product_detail(product_html: str, product_url: str) -> None:
    detail = parse_product_detail(product_html, product_url)
    assert isinstance(detail, ProductDetail)
    assert detail.product_id == 1162
    assert detail.name == "Воблер Daiwa Morethan Monsterwake 156F 156mm 40g"
    assert detail.brand == "DAIWA"
    assert detail.brand_url == "https://bereg.ua/uk/brand/daiwa.html"
    assert detail.sku == "04827196"
    assert detail.price is not None and detail.price.amount == Decimal("1250")
    assert detail.description
    assert len(detail.images) == 2
    assert detail.main_image is not None
    assert "/cache/" not in detail.main_image


def test_parse_product_detail_specifications(product_html: str, product_url: str) -> None:
    detail = parse_product_detail(product_html, product_url)
    assert len(detail.specification_groups) == 3
    labels = {s.label for s in detail.specifications}
    assert "Вага, г" in labels
    assert "Довжина, мм" in labels
    specs = {s.label: s.value for s in detail.specifications}
    assert specs["Вага, г"] == "40"
    assert specs["Довжина, мм"] == "156"


def test_parse_product_detail_variants(product_html: str, product_url: str) -> None:
    detail = parse_product_detail(product_html, product_url)
    assert len(detail.variants) == 3
    first = detail.variants[0]
    assert first.sku == "04827196"
    assert first.code == "2242113"
    assert first.price is not None and first.price.amount == Decimal("1250")
    assert first.available is True
    assert first.url is not None and first.url.endswith("-04827196.html")
    assert first.name.startswith("Воблер Daiwa Morethan Monsterwake")
    attribute_map = {a.label: a.value for a in first.attributes}
    assert attribute_map["Вага, г"] == "40"
    assert attribute_map["Довжина, мм"] == "156"
    assert attribute_map["Тип"] == "Мінноу"
    assert attribute_map["Плавучесть"] == "Плаваючий"


def test_parse_product_detail_money_types(product_html: str, product_url: str) -> None:
    detail = parse_product_detail(product_html, product_url)
    assert isinstance(detail.price, Money)
    assert all(isinstance(v.price, Money) for v in detail.variants)
