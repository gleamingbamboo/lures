"""Client tests for bereg-client using respx-mocked HTTP responses."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx

from bereg import BeregClient
from bereg.exceptions import NotFoundError, RateLimitError
from bereg.models import CategoryPage, ProductCard, ProductDetail, SitemapEntry

LISTING_URL = "https://bereg.ua/uk/spinning/primanki/voblery/minnou.html"
PRODUCT_URL = "https://bereg.ua/uk/vobler-daiwa-mt-monsterwake-156f.html"
SEARCH_URL = "https://bereg.ua/uk/catalogsearch/result/"
SALE_URL = "https://bereg.ua/uk/sale.html"
SITEMAP_INDEX_URL = "https://bereg.ua/sitemap.xml"
PRODUCT_SITEMAP_URL = "https://bereg.ua/media/mageit_sitemap/1/product-available.xml.gz"


def _html(body: str) -> httpx.Response:
    return httpx.Response(
        200,
        content=body.encode("utf-8"),
        headers={"content-type": "text/html; charset=utf-8"},
    )


def test_get_category(respx_mock: respx.MockRouter, listing_html: str, listing_url: str) -> None:
    respx_mock.get(listing_url).mock(return_value=_html(listing_html))
    with BeregClient() as client:
        page = client.get_category(listing_url)
    assert isinstance(page, CategoryPage)
    assert page.title == "Мінноу"
    assert len(page.items) == 3
    assert page.pages == 5


def test_get_category_paged(
    respx_mock: respx.MockRouter, listing_html: str, listing_url: str
) -> None:
    paged = f"{listing_url}?p=2"
    respx_mock.get(paged).mock(return_value=_html(listing_html))
    with BeregClient() as client:
        page = client.get_category(listing_url, page=2)
    assert page.current_page == 2


async def test_aget_category(
    respx_mock: respx.MockRouter, listing_html: str, listing_url: str
) -> None:
    respx_mock.get(listing_url).mock(return_value=_html(listing_html))
    async with BeregClient() as client:
        page = await client.aget_category(listing_url)
    assert page.title == "Мінноу"
    assert len(page.items) == 3


def test_get_product(respx_mock: respx.MockRouter, product_html: str, product_url: str) -> None:
    respx_mock.get(product_url).mock(return_value=_html(product_html))
    with BeregClient() as client:
        detail = client.get_product(product_url)
    assert isinstance(detail, ProductDetail)
    assert detail.product_id == 1162
    assert detail.brand == "DAIWA"
    assert detail.price is not None and detail.price.amount == Decimal("1250")
    assert len(detail.variants) == 3


async def test_aget_product(
    respx_mock: respx.MockRouter, product_html: str, product_url: str
) -> None:
    respx_mock.get(product_url).mock(return_value=_html(product_html))
    async with BeregClient() as client:
        detail = await client.aget_product(product_url)
    assert detail.sku == "04827196"
    assert len(detail.images) == 2


def test_search(respx_mock: respx.MockRouter, search_html: str) -> None:
    respx_mock.get(f"{SEARCH_URL}?q=minnow").mock(return_value=_html(search_html))
    with BeregClient() as client:
        page = client.search("minnow")
    assert isinstance(page, CategoryPage)
    assert page.title.startswith("Результати")
    assert len(page.items) == 2


async def test_asearch(respx_mock: respx.MockRouter, search_html: str) -> None:
    respx_mock.get(f"{SEARCH_URL}?q=minnow").mock(return_value=_html(search_html))
    async with BeregClient() as client:
        page = await client.asearch("minnow")
    assert len(page.items) == 2


def test_get_sale_page(respx_mock: respx.MockRouter, listing_html: str) -> None:
    respx_mock.get(f"{SALE_URL}?p=1").mock(return_value=_html(listing_html))
    with BeregClient() as client:
        page = client.get_sale_page()
    assert len(page.items) == 3


def test_iter_category_products_pagination(
    respx_mock: respx.MockRouter,
    listing_html: str,
    search_html: str,
    listing_url: str,
) -> None:
    # first page claims 5 pages; max_pages limits the walk to 2 pages
    page2 = f"{listing_url}?p=2"
    respx_mock.get(page2).mock(return_value=_html(search_html))
    respx_mock.get(listing_url).mock(return_value=_html(listing_html))
    with BeregClient() as client:
        cards = list(client.iter_category_products(listing_url, max_pages=2))
    assert len(cards) == 3 + 2
    assert all(isinstance(c, ProductCard) for c in cards)
    # page 3 was never requested
    assert not any("p=3" in str(c.request.url) for c in respx_mock.calls)


async def test_aiter_category_products_pagination(
    respx_mock: respx.MockRouter,
    listing_html: str,
    search_html: str,
    listing_url: str,
) -> None:
    page2 = f"{listing_url}?p=2"
    respx_mock.get(page2).mock(return_value=_html(search_html))
    respx_mock.get(listing_url).mock(return_value=_html(listing_html))
    async with BeregClient() as client:
        cards = [c async for c in client.aiter_category_products(listing_url, max_pages=2)]
    assert len(cards) == 5


def test_retry_then_success(
    respx_mock: respx.MockRouter, listing_html: str, listing_url: str
) -> None:
    respx_mock.get(listing_url).mock(
        side_effect=[
            httpx.Response(503, content=b"unavailable"),
            _html(listing_html),
        ]
    )
    with BeregClient(max_retries=2, backoff_factor=0.01) as client:
        page = client.get_category(listing_url)
    assert len(page.items) == 3
    assert len(respx_mock.calls) == 2


def test_rate_limit_raises(respx_mock: respx.MockRouter, listing_url: str) -> None:
    respx_mock.get(listing_url).mock(return_value=httpx.Response(429, content=b"slow down"))
    with BeregClient(max_retries=2, backoff_factor=0.01) as client, pytest.raises(RateLimitError):
        client.get_category(listing_url)
    assert len(respx_mock.calls) == 2


def test_not_found_raises(respx_mock: respx.MockRouter, listing_url: str) -> None:
    respx_mock.get(listing_url).mock(return_value=httpx.Response(404, content=b"missing"))
    with BeregClient() as client, pytest.raises(NotFoundError):
        client.get_category(listing_url)


def test_get_sitemap_index(respx_mock: respx.MockRouter, sitemap_index_bytes: bytes) -> None:
    respx_mock.get(SITEMAP_INDEX_URL).mock(
        return_value=httpx.Response(200, content=sitemap_index_bytes)
    )
    with BeregClient() as client:
        index = client.get_sitemap_index()
    assert len(index) >= 16
    assert all(isinstance(entry, SitemapEntry) for entry in index)
    assert any("product-available.xml.gz" in e.url for e in index)


async def test_aget_sitemap_index(respx_mock: respx.MockRouter, sitemap_index_bytes: bytes) -> None:
    respx_mock.get(SITEMAP_INDEX_URL).mock(
        return_value=httpx.Response(200, content=sitemap_index_bytes)
    )
    async with BeregClient() as client:
        index = await client.aget_sitemap_index()
    assert any("category.xml.gz" in e.url for e in index)


def test_iter_product_urls_and_find_variant(
    respx_mock: respx.MockRouter,
    sitemap_index_bytes: bytes,
    product_sitemap_bytes: bytes,
) -> None:
    respx_mock.get(SITEMAP_INDEX_URL).mock(
        return_value=httpx.Response(200, content=sitemap_index_bytes)
    )
    # the real index references the product sitemap twice (shop views 1 and 2)
    respx_mock.get(PRODUCT_SITEMAP_URL).mock(
        return_value=httpx.Response(200, content=product_sitemap_bytes)
    )
    respx_mock.get(PRODUCT_SITEMAP_URL.replace("/1/", "/2/")).mock(
        return_value=httpx.Response(200, content=product_sitemap_bytes)
    )
    with BeregClient() as client:
        urls = list(client.iter_product_urls())
        variant_url = client.find_variant_url("04827196")
    assert "https://bereg.ua/uk/vobler-daiwa-mt-monsterwake-156f.html" in urls
    assert (
        variant_url
        == "https://bereg.ua/uk/vobler-daiwa-morethan-monsterwake-156f-156mm-40g-3d-konoshir-04827196.html"
    )


async def test_aiter_sitemap_urls(
    respx_mock: respx.MockRouter, product_sitemap_bytes: bytes
) -> None:
    respx_mock.get(PRODUCT_SITEMAP_URL).mock(
        return_value=httpx.Response(200, content=product_sitemap_bytes)
    )
    async with BeregClient() as client:
        urls = [u async for u in client.aiter_sitemap_urls(PRODUCT_SITEMAP_URL)]
    assert len(urls) == 3
    assert all(u.startswith("https://") for u in urls)
