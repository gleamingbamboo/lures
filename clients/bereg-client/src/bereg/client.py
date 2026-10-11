"""bereg.ua (Magento 1) catalogue client."""

from __future__ import annotations

import gzip
import io
from collections.abc import AsyncIterator, Iterator
from typing import Any
from urllib.parse import urlencode

from lxml import etree

from ._base import BaseHTTPClient
from .exceptions import ParseError
from .models import CategoryPage, ProductCard, ProductDetail, SitemapEntry
from .parsing import parse_listing, parse_product_detail

__all__ = ["DEFAULT_BASE_URL", "DEFAULT_USER_AGENT", "BeregClient"]

DEFAULT_BASE_URL = "https://bereg.ua"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
SITEMAP_INDEX_PATH = "/sitemap.xml"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


class BeregClient(BaseHTTPClient):
    """A cursor into the bereg.ua catalogue.

    Synchronous methods (``get_category``, ``get_product``, ...) and their
    ``a``-prefixed async counterparts share the same parsing logic and models.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        locale: str = "uk",
        **kwargs: Any,
    ) -> None:
        if "user_agent" not in kwargs:
            kwargs["user_agent"] = DEFAULT_USER_AGENT
        self.locale = locale
        super().__init__(base_url, **kwargs)

    # ------------------------------------------------------------------ #
    # HTML fetching
    # ------------------------------------------------------------------ #
    def _get_html(self, url: str, **kwargs: Any) -> str:
        response = self.request("GET", url, **kwargs)
        content_type = response.headers.get("content-type", "").lower()
        if "charset=" in content_type:
            return response.text
        return response.content.decode("utf-8", errors="replace")

    async def _aget_html(self, url: str, **kwargs: Any) -> str:
        response = await self.arequest("GET", url, **kwargs)
        content_type = response.headers.get("content-type", "").lower()
        if "charset=" in content_type:
            return response.text
        return response.content.decode("utf-8", errors="replace")

    @staticmethod
    def _page_url(url: str, page: int | None) -> str:
        if page is None:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}p={page}"

    @property
    def search_url(self) -> str:
        return f"{self.base_url}/{self.locale}/catalogsearch/result/"

    @property
    def sale_url(self) -> str:
        return f"{self.base_url}/{self.locale}/sale.html"

    # ------------------------------------------------------------------ #
    # Category listings
    # ------------------------------------------------------------------ #
    def get_category(self, url: str, *, page: int | None = None) -> CategoryPage:
        """Fetch and parse one listing page of a category."""
        target = self._page_url(url, page)
        return parse_listing(self._get_html(target), target)

    async def aget_category(self, url: str, *, page: int | None = None) -> CategoryPage:
        """Asynchronous counterpart of :meth:`get_category`."""
        target = self._page_url(url, page)
        return parse_listing(await self._aget_html(target), target)

    def iter_category_products(
        self, url: str, *, max_pages: int | None = None
    ) -> Iterator[ProductCard]:
        """Yield every product of a category, page after page.

        The first page is fetched to learn the total page count; ``max_pages``
        caps how many pages are walked.
        """
        first = self.get_category(url)
        yield from first.items
        pages = first.pages or 1
        if max_pages is not None:
            pages = min(pages, max_pages)
        for page in range(2, pages + 1):
            yield from self.get_category(url, page=page).items

    async def aiter_category_products(
        self, url: str, *, max_pages: int | None = None
    ) -> AsyncIterator[ProductCard]:
        """Asynchronous counterpart of :meth:`iter_category_products`."""
        first = await self.aget_category(url)
        for card in first.items:
            yield card
        pages = first.pages or 1
        if max_pages is not None:
            pages = min(pages, max_pages)
        for page in range(2, pages + 1):
            page_result = await self.aget_category(url, page=page)
            for card in page_result.items:
                yield card

    # ------------------------------------------------------------------ #
    # Product details
    # ------------------------------------------------------------------ #
    def get_product(self, url: str) -> ProductDetail:
        """Fetch and parse one product page."""
        return parse_product_detail(self._get_html(url), url)

    async def aget_product(self, url: str) -> ProductDetail:
        """Asynchronous counterpart of :meth:`get_product`."""
        return parse_product_detail(await self._aget_html(url), url)

    # ------------------------------------------------------------------ #
    # Search & sale
    # ------------------------------------------------------------------ #
    def search(self, query: str, *, page: int = 1) -> CategoryPage:
        """Full-text search; results are listing-shaped."""
        url = self._search_url(self.search_url, query, page)
        return parse_listing(self._get_html(url), url)

    async def asearch(self, query: str, *, page: int = 1) -> CategoryPage:
        """Asynchronous counterpart of :meth:`search`."""
        url = self._search_url(self.search_url, query, page)
        return parse_listing(await self._aget_html(url), url)

    @staticmethod
    def _search_url(base: str, query: str, page: int) -> str:
        """Build a search URL without relying on httpx query merging."""
        params: dict[str, str] = {"q": query}
        if page > 1:
            params["p"] = str(page)
        return f"{base}?{urlencode(params)}"

    def get_sale_page(self, *, page: int = 1) -> CategoryPage:
        """Fetch and parse the «Знижки» (sale) listing."""
        url = self._page_url(self.sale_url, page)
        return parse_listing(self._get_html(url), url)

    async def aget_sale_page(self, *, page: int = 1) -> CategoryPage:
        """Asynchronous counterpart of :meth:`get_sale_page`."""
        url = self._page_url(self.sale_url, page)
        return parse_listing(await self._aget_html(url), url)

    def iter_sale_products(self, *, max_pages: int | None = None) -> Iterator[ProductCard]:
        """Yield every product currently on sale, page after page."""
        first = self.get_sale_page()
        yield from first.items
        pages = first.pages or 1
        if max_pages is not None:
            pages = min(pages, max_pages)
        for page in range(2, pages + 1):
            yield from self.get_sale_page(page=page).items

    # ------------------------------------------------------------------ #
    # XML sitemaps
    # ------------------------------------------------------------------ #
    def get_sitemap_index(self) -> list[SitemapEntry]:
        """Parse ``sitemap.xml`` into its ``<sitemap>`` entries."""
        data = self.request("GET", f"{self.base_url}{SITEMAP_INDEX_PATH}").content
        return self._parse_sitemap_index(data)

    async def aget_sitemap_index(self) -> list[SitemapEntry]:
        """Asynchronous counterpart of :meth:`get_sitemap_index`."""
        response = await self.arequest("GET", f"{self.base_url}{SITEMAP_INDEX_PATH}")
        return self._parse_sitemap_index(response.content)

    @staticmethod
    def _parse_sitemap_index(xml: bytes) -> list[SitemapEntry]:
        try:
            root = etree.fromstring(xml)
        except etree.XMLSyntaxError as exc:
            raise ParseError(f"Invalid sitemap index XML: {exc}") from exc
        entries: list[SitemapEntry] = []
        for child in root:
            loc = (
                child.findtext(f"{{{SITEMAP_NS}}}loc")
                if child.tag == f"{{{SITEMAP_NS}}}sitemap"
                else None
            )
            if not loc:
                continue
            lastmod = child.findtext(f"{{{SITEMAP_NS}}}lastmod")
            entries.append(SitemapEntry(url=loc.strip(), lastmod=(lastmod or "").strip() or None))
        return entries

    @staticmethod
    def _decompress(data: bytes) -> bytes:
        if data[:2] == b"\x1f\x8b":
            try:
                return gzip.decompress(data)
            except OSError:
                pass
        return data

    @staticmethod
    def _iter_locs(xml: bytes) -> Iterator[str]:
        """Stream ``<loc>`` values out of a urlset/sitemapindex XML payload."""
        try:
            context = etree.iterparse(
                io.BytesIO(xml),
                events=("end",),
                tag=f"{{{SITEMAP_NS}}}loc",
            )
            for _event, element in context:
                text = element.text
                element.clear()
                if text:
                    yield text.strip()
        except etree.XMLSyntaxError as exc:
            raise ParseError(f"Invalid sitemap XML: {exc}") from exc

    def iter_sitemap_urls(self, url: str) -> Iterator[str]:
        """Yield every ``<loc>`` of a (gzipped) sitemap as a streaming generator."""
        data = self.request("GET", url).content
        yield from self._iter_locs(self._decompress(data))

    async def aiter_sitemap_urls(self, url: str) -> AsyncIterator[str]:
        """Asynchronous counterpart of :meth:`iter_sitemap_urls`."""
        data = (await self.arequest("GET", url)).content
        for loc in self._iter_locs(self._decompress(data)):
            yield loc

    def _iter_sitemap_urls_matching(self, fragment: str) -> Iterator[str]:
        seen: set[str] = set()
        for entry in self.get_sitemap_index():
            if fragment not in entry.url:
                continue
            for loc in self.iter_sitemap_urls(entry.url):
                if loc not in seen:
                    seen.add(loc)
                    yield loc

    def iter_category_urls(self) -> Iterator[str]:
        """Yield every category URL from the ``category`` sitemaps (deduplicated)."""
        yield from self._iter_sitemap_urls_matching("category.xml.gz")

    def iter_product_urls(self) -> Iterator[str]:
        """Yield every available-product URL from the ``product-available`` sitemaps."""
        yield from self._iter_sitemap_urls_matching("product-available.xml.gz")

    def iter_brand_urls(self) -> Iterator[str]:
        """Yield every brand URL from the ``brand`` sitemaps (deduplicated)."""
        yield from self._iter_sitemap_urls_matching("brand.xml.gz")

    def find_variant_url(self, sku: str) -> str | None:
        """Find the first product URL ending with ``-{sku}.html``.

        Variant URLs carry the printable артикул (SKU) as their trailing
        segment, e.g. ``.../vobler-...-04827196.html`` for SKU ``04827196``.
        """
        suffix = f"-{sku}.html"
        for url in self.iter_product_urls():
            if url.endswith(suffix):
                return url
        return None

    async def afind_variant_url(self, sku: str) -> str | None:
        """Asynchronous counterpart of :meth:`find_variant_url`."""
        suffix = f"-{sku}.html"
        for entry in await self.aget_sitemap_index():
            if "product-available.xml.gz" not in entry.url:
                continue
            async for loc in self.aiter_sitemap_urls(entry.url):
                if loc.endswith(suffix):
                    return loc
        return None
