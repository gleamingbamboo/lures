"""Тести екстракторів: клієнт-моделі -> канонічні LureRecord."""

from __future__ import annotations

from bereg.models import ProductCard, ProductDetail
from flagman.models import Product as FlagmanProduct
from ibisgear.models import Product as IbisProduct

from lures.extractors import (
    extract_bereg_card,
    extract_bereg_detail,
    extract_flagman,
    extract_ibisgear,
)
from lures.extractors.common import parse_depth


def _flagman_product(old_price: str = "600") -> FlagmanProduct:
    return FlagmanProduct.model_validate(
        {
            "id": "123",
            "ext_id": "V-123",
            "title": "Cool Minnow 90SP",
            "name": "cool-minnow-90sp",
            "producer": {"title": "Xor", "title_ua": "ТзОВ Хор"},
            "price": "500",
            "old_price": old_price,
            "rating": 4.5,
            "count_comments": 12,
            "sell_status": "4",
            "images": ["https://flagman.ua/media/img.jpg"],
            "description_ua": "Classic minnow with a long cast.",
            "characteristics": {
                "w": {"title": "Вага", "title_ua": "Вага", "value": "10 г", "value_ua": "10 г"},
                "d": {
                    "title": "Заглиблення",
                    "title_ua": "Заглиблення, м",
                    "value_ua": "0.5 \u2013 1.2 м",
                },
            },
        }
    )


def test_flagman_extractor() -> None:
    record = extract_flagman(_flagman_product())
    assert record.store == "flagman"
    assert record.external_id == "V-123"
    assert record.name == "Cool Minnow 90SP"
    assert record.brand == "ТзОВ Хор"
    assert record.lure_type == "Minnow"
    assert record.buoyancy == "SP"
    assert record.weight_g == 10.0
    assert record.depth_from_m == 0.5
    assert record.depth_to_m == 1.2
    assert record.price == 500.0
    assert record.old_price == 600.0
    assert record.discount_pct == 17
    assert record.rating == 4.5
    assert record.comments == 12
    assert record.availability == "available"
    assert record.url == "https://flagman.ua/cool-minnow-90sp/p123"


def test_flagman_discount_cleared_when_no_sale() -> None:
    record = extract_flagman(_flagman_product(old_price="500"))
    assert record.old_price is None
    assert record.discount_pct is None


def _ibis_product() -> IbisProduct:
    return IbisProduct.model_validate(
        {
            "@id": "/api/v2/shop/products/555",
            "id": 555,
            "code": "IBIS-90-SP",
            "brandName": "Megabass",
            "averageRating": 4.5,
            "totalReviews": 7,
            "minPrice": 99990,
            "defaultVariant": "/api/v2/shop/product-variants/111",
            "variants": [
                {
                    "@id": "/api/v2/shop/product-variants/111",
                    "id": 111,
                    "code": "IBIS-90-SP",
                    "slug": "ibis-90-sp",
                    "name": "IBIS 90 SP",
                    "inStock": True,
                    "price": 99990,
                    "originalPrice": 119990,
                    "attributes": [
                        {"code": "weight", "name": "Вага", "value": "14 г"},
                        {"code": "length", "name": "Довжина", "value": "90 мм"},
                        {"code": "type", "name": "Тип воблера", "value": "Minnow"},
                        {"code": "buoyancy", "name": "Плавучість", "value": "Суспендр"},
                    ],
                }
            ],
        }
    )


def test_ibisgear_extractor() -> None:
    record = extract_ibisgear(_ibis_product())
    assert record.store == "ibisgear"
    assert record.external_id == "IBIS-90-SP"
    assert record.name == "IBIS 90 SP"
    assert record.brand == "Megabass"
    assert record.lure_type == "Minnow"
    assert record.buoyancy == "SP"
    assert record.weight_g == 14.0
    assert record.length_mm == 90.0
    assert record.price == 999.9
    assert record.old_price == 1199.9
    assert record.discount_pct == 17
    assert record.rating == 4.5
    assert record.comments == 7
    assert record.availability == "available"


def _bereg_card() -> ProductCard:
    return ProductCard.model_validate(
        {
            "product_id": 2242113,
            "url": "https://bereg.ua/uk/spinning/primanki/voblery/x.html",
            "name": "Flat Minnow 90",
            "price": {"amount": "450.00", "currency": "UAH"},
            "special_price": {"amount": "350.00", "currency": "UAH"},
            "image": "https://bereg.ua/media/catalog/product/i/m/img.jpg",
        }
    )


def test_bereg_card_extractor() -> None:
    record = extract_bereg_card(_bereg_card())
    assert record.store == "bereg"
    assert record.external_id == "2242113"
    assert record.name == "Flat Minnow 90"
    assert record.price == 350.0
    assert record.old_price == 450.0
    assert record.discount_pct == 22
    assert record.availability == "unknown"
    assert record.image_url == "https://bereg.ua/media/catalog/product/i/m/img.jpg"


def _bereg_detail() -> ProductDetail:
    return ProductDetail.model_validate(
        {
            "product_id": 2242113,
            "url": "https://bereg.ua/uk/spinning/primanki/voblery/flat-minnow-90.html",
            "name": "Flat Minnow 90",
            "brand": "Bereg",
            "sku": "FM-90",
            "price": {"amount": "450.00"},
            "special_price": {"amount": "350.00"},
            "images": [
                {
                    "url": "https://bereg.ua/media/catalog/product/i/m/img.jpg",
                    "alt": "Flat Minnow 90",
                }
            ],
            "description": "Classic minnow with a long cast.",
            "specification_groups": [
                {
                    "title": "Характеристики",
                    "specifications": [
                        {"label": "Тип воблера", "value": "Minnow"},
                        {"label": "Вага", "value": "14 г"},
                        {"label": "Довжина", "value": "90 мм"},
                        {"label": "Заглиблення", "value": "0.5 - 1.2 м"},
                        {"label": "Плавучість", "value": "Плаваючий"},
                    ],
                }
            ],
            "variants": [
                {
                    "name": "green",
                    "sku": "FM-90",
                    "available": True,
                    "price": {"amount": "350.00"},
                }
            ],
        }
    )


def test_bereg_detail_extractor() -> None:
    record = extract_bereg_detail(_bereg_detail())
    assert record.store == "bereg"
    assert record.external_id == "FM-90"
    assert record.brand == "Bereg"
    assert record.lure_type == "Minnow"
    assert record.buoyancy == "F"
    assert record.weight_g == 14.0
    assert record.length_mm == 90.0
    assert record.depth_from_m == 0.5
    assert record.depth_to_m == 1.2
    assert record.price == 350.0
    assert record.old_price == 450.0
    assert record.discount_pct == 22
    assert record.availability == "available"


def test_parse_depth_variants() -> None:
    assert parse_depth("до 1.5 м") == (None, 1.5)
    assert parse_depth("1.5 м") == (1.5, 1.5)
    assert parse_depth("0.5 \u2013 1.2 м") == (0.5, 1.2)
    assert parse_depth("0,5-1,2") == (0.5, 1.2)
    assert parse_depth(None) == (None, None)
    assert parse_depth("без заглиблення") == (None, None)
