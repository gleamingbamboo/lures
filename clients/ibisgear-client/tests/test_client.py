"""Tests for the synchronous and asynchronous ibisgear client behaviour."""

from __future__ import annotations

import httpx
import pytest
import respx

from ibisgear import IbisGearClient
from ibisgear.exceptions import NotFoundError, ParseError, RateLimitError, RequestError

BASE = "https://shop.ibis.net.ua"
API = f"{BASE}/api/v2/shop"
PRODUCT_IRI = "/api/v2/shop/products/15950111"


@respx.mock
def test_get_taxon(taxon_payload: dict) -> None:
    respx.get(f"{API}/taxons/01030000").mock(return_value=httpx.Response(200, json=taxon_payload))
    with IbisGearClient() as client:
        taxon = client.get_taxon("01030000")
    assert taxon.name == "Приманки"


@respx.mock
async def test_aget_taxon(taxon_payload: dict) -> None:
    respx.get(f"{API}/taxons/01030000").mock(return_value=httpx.Response(200, json=taxon_payload))
    async with IbisGearClient() as client:
        taxon = await client.aget_taxon("01030000")
    assert taxon.code == "01030000"


@respx.mock
def test_get_taxons(taxon_payload: dict) -> None:
    collection = {
        "@context": "/api/v2/contexts/Taxon",
        "hydra:member": [taxon_payload],
        "hydra:totalItems": 1,
    }
    respx.get(f"{API}/taxons").mock(return_value=httpx.Response(200, json=collection))
    with IbisGearClient() as client:
        taxons = client.get_taxons()
    assert [t.code for t in taxons] == ["01030000"]


@respx.mock
def test_get_products_page(products_page1_payload: dict) -> None:
    respx.get(f"{API}/products-filtered/01030100", params={"page": 1}).mock(
        return_value=httpx.Response(200, json=products_page1_payload)
    )
    with IbisGearClient() as client:
        page = client.get_products_page("01030100")
    assert len(page.items) == 2
    assert page.total is not None
    assert page.page == 1
    assert page.next_page == 2
    assert page.has_next


@respx.mock
def test_iter_products_pagination(
    products_page1_payload: dict, products_page2_payload: dict
) -> None:
    respx.get(f"{API}/products-filtered/01030100", params={"page": 1}).mock(
        return_value=httpx.Response(200, json=products_page1_payload)
    )
    respx.get(f"{API}/products-filtered/01030100", params={"page": 2}).mock(
        return_value=httpx.Response(200, json=products_page2_payload)
    )
    with IbisGearClient() as client:
        ids = [p.id for p in client.iter_products("01030100")]
    assert len(ids) == 3
    assert ids[0] != ids[2]


@respx.mock
async def test_aiter_products_pagination(
    products_page1_payload: dict, products_page2_payload: dict
) -> None:
    respx.get(f"{API}/products-filtered/01030100", params={"page": 1}).mock(
        return_value=httpx.Response(200, json=products_page1_payload)
    )
    respx.get(f"{API}/products-filtered/01030100", params={"page": 2}).mock(
        return_value=httpx.Response(200, json=products_page2_payload)
    )
    async with IbisGearClient() as client:
        ids = [p.id async for p in client.aiter_products("01030100")]
    assert len(ids) == 3


@respx.mock
def test_max_pages(products_page1_payload: dict, products_page2_payload: dict) -> None:
    respx.get(f"{API}/products-filtered/01030100", params={"page": 1}).mock(
        return_value=httpx.Response(200, json=products_page1_payload)
    )
    with IbisGearClient() as client:
        ids = [p.id for p in client.iter_products("01030100", max_pages=1)]
    assert len(ids) == 2


@respx.mock
def test_get_variants_page(variants_payload: dict) -> None:
    respx.get(f"{API}/product-variants", params={"product": PRODUCT_IRI, "page": 1}).mock(
        return_value=httpx.Response(200, json=variants_payload)
    )
    with IbisGearClient() as client:
        page = client.get_variants_page(PRODUCT_IRI)
    assert page.items
    assert page.items[0].attributes


@respx.mock
async def test_aget_variants_page(variants_payload: dict) -> None:
    respx.get(f"{API}/product-variants", params={"product": PRODUCT_IRI, "page": 1}).mock(
        return_value=httpx.Response(200, json=variants_payload)
    )
    async with IbisGearClient() as client:
        page = await client.aget_variants_page(PRODUCT_IRI)
    assert page.items


@respx.mock
def test_variant_iri_normalisation(variants_payload: dict) -> None:
    route = respx.get(f"{API}/product-variants", params={"product": PRODUCT_IRI, "page": 1}).mock(
        return_value=httpx.Response(200, json=variants_payload)
    )
    with IbisGearClient() as client:
        client.get_variants_page("15950111")  # bare code -> IRI
    assert route.called


@respx.mock
def test_get_product(product_payload: dict) -> None:
    respx.get(f"{API}/products/15950111").mock(
        return_value=httpx.Response(200, json=product_payload)
    )
    with IbisGearClient() as client:
        product = client.get_product("15950111")
    assert product.defaultVariant is not None


@respx.mock
def test_search(products_page1_payload: dict) -> None:
    respx.get(f"{API}/products", params={"search": "minnow", "page": 1}).mock(
        return_value=httpx.Response(200, json=products_page1_payload)
    )
    with IbisGearClient() as client:
        page = client.search("minnow")
    assert page.items


@respx.mock
def test_not_found() -> None:
    respx.get(f"{API}/taxons/999").mock(return_value=httpx.Response(404))
    with IbisGearClient() as client, pytest.raises(NotFoundError):
        client.get_taxon("999")


@respx.mock
def test_retries_on_server_error(taxon_payload: dict) -> None:
    route = respx.get(f"{API}/taxons/01030000").mock(
        side_effect=[httpx.Response(500), httpx.Response(200, json=taxon_payload)]
    )
    with IbisGearClient(backoff_factor=0.0) as client:
        client.get_taxon("01030000")
    assert route.call_count == 2


@respx.mock
def test_rate_limit_raises() -> None:
    respx.get(f"{API}/taxons/1").mock(return_value=httpx.Response(429))
    with IbisGearClient(max_retries=1) as client, pytest.raises(RateLimitError):
        client.get_taxon("1")


@respx.mock
def test_transport_error_raises_request_error() -> None:
    respx.get(f"{API}/taxons/1").mock(side_effect=httpx.ConnectError("boom"))
    with IbisGearClient(max_retries=2, backoff_factor=0.0) as client, pytest.raises(RequestError):
        client.get_taxon("1")


@respx.mock
def test_invalid_json_raises_parse_error() -> None:
    respx.get(f"{API}/taxons/1").mock(return_value=httpx.Response(200, text="<html>nope</html>"))
    with IbisGearClient() as client, pytest.raises(ParseError):
        client.get_taxon("1")


@respx.mock
def test_accept_header_set(taxon_payload: dict) -> None:
    route = respx.get(f"{API}/taxons/01030000").mock(
        return_value=httpx.Response(200, json=taxon_payload)
    )
    with IbisGearClient() as client:
        client.get_taxon("01030000")
    assert route.calls[0].request.headers["Accept"] == "application/ld+json"
