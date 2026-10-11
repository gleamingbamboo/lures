"""Tests for the synchronous and asynchronous client behaviour."""

from __future__ import annotations

import httpx
import pytest
import respx

from flagman import FlagmanClient
from flagman.exceptions import HTTPError, NotFoundError, ParseError, RateLimitError, RequestError

BASE = "https://r.flagman.ua"


@respx.mock
def test_get_catalog(catalog_payload: dict) -> None:
    respx.get(f"{BASE}/site/catalog/168794").mock(
        return_value=httpx.Response(200, json=catalog_payload)
    )
    with FlagmanClient() as client:
        catalog = client.get_catalog("168794")
    assert catalog.data.goods == ["292051", "292076"]


@respx.mock
async def test_aget_catalog(catalog_payload: dict) -> None:
    respx.get(f"{BASE}/site/catalog/168794").mock(
        return_value=httpx.Response(200, json=catalog_payload)
    )
    async with FlagmanClient() as client:
        catalog = await client.aget_catalog("168794")
    assert catalog.status == "success"


@respx.mock
def test_get_products_batches_and_dedupes(goods_multi_payload: dict) -> None:
    route = respx.get(f"{BASE}/api/goods/id/292076,292051").mock(
        return_value=httpx.Response(200, json=goods_multi_payload)
    )
    with FlagmanClient() as client:
        products = client.get_products(["292076", "292051", "292076"])
    assert route.called
    assert [p.id for p in products] == ["292076", "292051"]


@respx.mock
def test_get_product_single(goods_single_payload: dict) -> None:
    respx.get(f"{BASE}/api/goods/id/292051").mock(
        return_value=httpx.Response(200, json=goods_single_payload)
    )
    with FlagmanClient() as client:
        product = client.get_product("292051")
    assert product.id == "292051"


@respx.mock
def test_iter_products(catalog_payload: dict, goods_multi_payload: dict) -> None:
    respx.get(f"{BASE}/site/catalog/168794").mock(
        return_value=httpx.Response(200, json=catalog_payload)
    )
    respx.get(f"{BASE}/api/goods/id/292051,292076").mock(
        return_value=httpx.Response(200, json=goods_multi_payload)
    )
    with FlagmanClient() as client:
        ids = [p.id for p in client.iter_products("168794")]
    assert ids == ["292051", "292076"]


@respx.mock
async def test_aiter_products(catalog_payload: dict, goods_multi_payload: dict) -> None:
    respx.get(f"{BASE}/site/catalog/168794").mock(
        return_value=httpx.Response(200, json=catalog_payload)
    )
    respx.get(f"{BASE}/api/goods/id/292051,292076").mock(
        return_value=httpx.Response(200, json=goods_multi_payload)
    )
    async with FlagmanClient() as client:
        ids = [p.id async for p in client.aiter_products("168794")]
    assert ids == ["292051", "292076"]


@respx.mock
def test_not_found() -> None:
    respx.get(f"{BASE}/site/catalog/999").mock(return_value=httpx.Response(404))
    with FlagmanClient() as client, pytest.raises(NotFoundError):
        client.get_catalog("999")


@respx.mock
def test_retries_on_server_error(goods_single_payload: dict) -> None:
    route = respx.get(f"{BASE}/api/goods/id/292051").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(503),
            httpx.Response(200, json=goods_single_payload),
        ]
    )
    with FlagmanClient(backoff_factor=0.0) as client:
        product = client.get_product("292051")
    assert product.id == "292051"
    assert route.call_count == 3


@respx.mock
async def test_retries_async(goods_single_payload: dict) -> None:
    route = respx.get(f"{BASE}/api/goods/id/292051").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, json=goods_single_payload),
        ]
    )
    async with FlagmanClient(backoff_factor=0.0) as client:
        product = await client.aget_product("292051")
    assert product.id == "292051"
    assert route.call_count == 2


@respx.mock
def test_rate_limit_raises() -> None:
    respx.get(f"{BASE}/site/catalog/1").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "0"})
    )
    with FlagmanClient(max_retries=1) as client, pytest.raises(RateLimitError):
        client.get_catalog("1")


@respx.mock
def test_transport_error_raises_request_error() -> None:
    respx.get(f"{BASE}/site/catalog/1").mock(side_effect=httpx.ConnectError("boom"))
    with FlagmanClient(max_retries=2, backoff_factor=0.0) as client, pytest.raises(RequestError):
        client.get_catalog("1")


@respx.mock
def test_invalid_json_raises_parse_error() -> None:
    respx.get(f"{BASE}/site/catalog/1").mock(
        return_value=httpx.Response(200, text="<html>not json</html>")
    )
    with FlagmanClient() as client, pytest.raises(ParseError):
        client.get_catalog("1")


@respx.mock
def test_http_error_has_status() -> None:
    respx.get(f"{BASE}/site/catalog/1").mock(return_value=httpx.Response(502))
    with FlagmanClient(max_retries=1) as client, pytest.raises(HTTPError) as excinfo:
        client.get_catalog("1")
    assert excinfo.value.status_code == 502


@respx.mock
def test_custom_headers_and_user_agent(catalog_payload: dict) -> None:
    route = respx.get(f"{BASE}/site/catalog/168794").mock(
        return_value=httpx.Response(200, json=catalog_payload)
    )
    with FlagmanClient(headers={"X-Test": "yes"}, user_agent="my-ua/1.0") as client:
        client.get_catalog("168794")
    request = route.calls[0].request
    assert request.headers["X-Test"] == "yes"
    assert request.headers["User-Agent"] == "my-ua/1.0"
