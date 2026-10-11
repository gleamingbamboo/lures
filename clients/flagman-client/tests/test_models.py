"""Tests for the pydantic models."""

from __future__ import annotations

from flagman.models import Catalog, Filter, GoodsResponse, Product


def test_catalog_parsing(catalog_payload: dict) -> None:
    catalog = Catalog.model_validate(catalog_payload)
    assert catalog.status == "success"
    assert catalog.isValid is True
    assert catalog.data.goods == ["292051", "292076"]
    assert catalog.data.filters
    assert catalog.metadata["h1"] == "Воблеры"
    assert [crumb.name for crumb in catalog.breadcrumbs] == ["primanky", "vobleri"]


def test_catalog_filter_values(catalog_payload: dict) -> None:
    catalog = Catalog.model_validate(catalog_payload)
    types = [f for f in catalog.data.filters if f.name == "detail_11758"]
    assert types, "expected the vobler-type filter"
    values = types[0].values
    assert any(v.title == "Minnow" for v in values)
    minnow = next(v for v in values if v.title == "Minnow")
    assert minnow.count and minnow.count > 0


def test_filter_range_values() -> None:
    """Range filters (e.g. price) return ``values`` as an object, not a list."""
    price = Filter.model_validate(
        {
            "name": "price",
            "type": "Decimal",
            "unit": "",
            "values": {
                "min": "47.70",
                "max": "1310.00",
                "selected": 0,
                "link": "",
                "selected_min": 0,
                "selected_max": 0,
            },
        }
    )
    assert price.value_list == []
    value_range = price.value_range
    assert value_range is not None
    assert value_range.min == 47.7
    assert value_range.max == 1310.0


def test_filter_missing_values_defaults_to_list() -> None:
    empty = Filter.model_validate({"name": "producer", "values": None})
    assert empty.values == []
    assert empty.value_list == []
    assert empty.value_range is None


def test_characteristics_parsing(goods_multi_payload: dict) -> None:
    response = GoodsResponse.model_validate(goods_multi_payload)
    assert len(response.data) == 2
    product = response.data[0]
    assert product.id == "292051"
    assert product.display_title
    assert product.price is not None
    assert product.characteristic("Довжина") is not None
    assert product.characteristic("Вага") is not None


def test_single_goods_response_is_wrapped(goods_single_payload: dict) -> None:
    response = GoodsResponse.model_validate(goods_single_payload)
    assert len(response.data) == 1
    assert response.data[0].id == "292051"


def test_product_helpers(goods_multi_payload: dict) -> None:
    product = GoodsResponse.model_validate(goods_multi_payload).data[0]
    assert product.url.endswith("/p292051")
    assert product.url.startswith("https://flagman.ua/")
    assert isinstance(product.images, list)
    assert product.main_image is None or product.main_image.startswith("http")
    assert product.is_available in (True, False)
    assert product.discount_percent is None or 0 < product.discount_percent <= 100


def test_product_numeric_coercion() -> None:
    product = Product.model_validate(
        {"id": 123, "price": " 587,25 ", "old_price": "", "rating": None, "images": "x.jpg"}
    )
    assert product.id == "123"
    assert product.price == 587.25
    assert product.old_price is None
    assert product.rating is None
    assert product.images == ["x.jpg"]
