"""High level client for the ibis-gear.com catalog.

ibis-gear.com is a headless (Vue/Nuxt) storefront backed by the **Sylius Shop
API v2** exposed on ``https://shop.ibis.net.ua``. This client wraps the
read-only endpoints that power catalog browsing:

* ``GET /api/v2/shop/taxons`` / ``.../taxons/{code}`` — category tree.
* ``GET /api/v2/shop/products-filtered/{taxonCode}?page=N`` — paginated product
  summaries (20 per page; the API rejects ``itemsPerPage`` with HTTP 403).
* ``GET /api/v2/shop/product-variants?product={iri}&page=N`` — all variants of a
  product with full attributes (30 per page).
* ``GET /api/v2/shop/products/{code}`` — a single product.

All endpoints speak JSON-LD (``Accept: application/ld+json``) and paginate with
the Hydra ``view`` convention. Prices are transmitted in **kopecks**.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Mapping
from typing import Any
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel

from ._base import BaseHTTPClient
from ._version import __version__
from .models import Page, Product, ProductVariant, Taxon

__all__ = ["DEFAULT_BASE_URL", "IbisGearClient"]

DEFAULT_BASE_URL = "https://shop.ibis.net.ua"
API_PREFIX = "/api/v2/shop"


def _page_number(url: str | None) -> int | None:
    """Extract the ``page`` query parameter from a Hydra ``@id`` / view URL."""
    if not url:
        return None
    values = parse_qs(urlparse(url).query).get("page")
    if not values:
        return None
    try:
        return int(values[0])
    except ValueError:
        return None


def _parse_page[T: BaseModel](payload: dict[str, Any], model: type[T]) -> Page[T]:
    """Turn a raw Hydra collection payload into a typed :class:`Page`."""
    member = payload.get("hydra:member") or []
    view = payload.get("hydra:view") or {}
    current = _page_number(payload.get("@id"))
    return Page(
        items=[model.model_validate(item) for item in member],
        total=payload.get("hydra:totalItems"),
        page=current or 1,
        pages=_page_number(view.get("hydra:last")),
        next_page=_page_number(view.get("hydra:next")),
        previous_page=_page_number(view.get("hydra:previous")),
    )


class IbisGearClient(BaseHTTPClient):
    """Synchronous + asynchronous client for the ibis-gear Sylius Shop API.

    Examples
    --------
    >>> with IbisGearClient() as client:            # doctest: +SKIP
    ...     taxon = client.get_taxon("01030100")    # Воблери
    ...     for product in client.iter_products("01030100"):
    ...         print(product.brandName, product.price_uah)

    Async usage mirrors the synchronous one::

        async with IbisGearClient() as client:      # doctest: +SKIP
            taxon = await client.aget_taxon("01030100")
            async for product in client.aiter_products("01030100"):
                ...
    """

    DEFAULT_USER_AGENT = (
        f"ibisgear-client/{__version__} (+https://github.com/Gleam/ibisgear-client)"
    )

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        user_agent: str | None = None,
        headers: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        merged_headers = {"Accept": "application/ld+json"}
        if headers:
            merged_headers.update(headers)
        super().__init__(
            base_url,
            user_agent=user_agent or self.DEFAULT_USER_AGENT,
            headers=merged_headers,
            **kwargs,
        )

    # ------------------------------------------------------------------ #
    # Taxons (categories)
    # ------------------------------------------------------------------ #
    def get_taxon(self, code: str) -> Taxon:
        """Fetch a single taxon (category) by code, with its children."""
        payload = self.get_json(f"{API_PREFIX}/taxons/{code}")
        return Taxon.model_validate(payload)

    async def aget_taxon(self, code: str) -> Taxon:
        """Asynchronous counterpart of :meth:`get_taxon`."""
        payload = await self.aget_json(f"{API_PREFIX}/taxons/{code}")
        return Taxon.model_validate(payload)

    def get_taxons(self) -> list[Taxon]:
        """Fetch the top-level taxons of the shop catalog tree."""
        payload = self.get_json(f"{API_PREFIX}/taxons")
        member = payload.get("hydra:member") or []
        return [Taxon.model_validate(item) for item in member]

    async def aget_taxons(self) -> list[Taxon]:
        """Asynchronous counterpart of :meth:`get_taxons`."""
        payload = await self.aget_json(f"{API_PREFIX}/taxons")
        member = payload.get("hydra:member") or []
        return [Taxon.model_validate(item) for item in member]

    def iter_taxons(self, recursive: bool = True) -> Iterator[Taxon]:
        """Iterate over all taxons; depth-first when ``recursive=True``."""
        for root in self.get_taxons():
            if recursive:
                yield from root.walk()
            else:
                yield root

    async def aiter_taxons(self, recursive: bool = True) -> AsyncIterator[Taxon]:
        """Asynchronous counterpart of :meth:`iter_taxons`."""
        roots = await self.aget_taxons()
        for root in roots:
            if recursive:
                for taxon in root.walk():
                    yield taxon
            else:
                yield root

    # ------------------------------------------------------------------ #
    # Products
    # ------------------------------------------------------------------ #
    def get_products_page(self, taxon_code: str, page: int = 1) -> Page[Product]:
        """Fetch one page of products for a taxon code."""
        payload = self.get_json(
            f"{API_PREFIX}/products-filtered/{taxon_code}", params={"page": page}
        )
        return _parse_page(payload, Product)

    async def aget_products_page(self, taxon_code: str, page: int = 1) -> Page[Product]:
        """Asynchronous counterpart of :meth:`get_products_page`."""
        payload = await self.aget_json(
            f"{API_PREFIX}/products-filtered/{taxon_code}", params={"page": page}
        )
        return _parse_page(payload, Product)

    def iter_products(self, taxon_code: str, *, max_pages: int | None = None) -> Iterator[Product]:
        """Iterate over every product in a taxon, following Hydra pagination."""
        page = 1
        visited = 0
        while True:
            if max_pages is not None and visited >= max_pages:
                return
            result = self.get_products_page(taxon_code, page)
            visited += 1
            yield from result.items
            if not result.has_next or result.next_page is None:
                return
            page = result.next_page

    async def aiter_products(
        self, taxon_code: str, *, max_pages: int | None = None
    ) -> AsyncIterator[Product]:
        """Asynchronous counterpart of :meth:`iter_products`."""
        page = 1
        visited = 0
        while True:
            if max_pages is not None and visited >= max_pages:
                return
            result = await self.aget_products_page(taxon_code, page)
            visited += 1
            for product in result.items:
                yield product
            if not result.has_next or result.next_page is None:
                return
            page = result.next_page

    def get_product(self, id_or_code: str | int) -> Product:
        """Fetch a single product by numeric id or string code."""
        payload = self.get_json(f"{API_PREFIX}/products/{id_or_code}")
        return Product.model_validate(payload)

    async def aget_product(self, id_or_code: str | int) -> Product:
        """Asynchronous counterpart of :meth:`get_product`."""
        payload = await self.aget_json(f"{API_PREFIX}/products/{id_or_code}")
        return Product.model_validate(payload)

    # ------------------------------------------------------------------ #
    # Variants
    # ------------------------------------------------------------------ #
    def get_variants_page(self, product_iri: str, page: int = 1) -> Page[ProductVariant]:
        """Fetch one page of variants for a product (IRI or code)."""
        payload = self.get_json(
            f"{API_PREFIX}/product-variants",
            params={"product": self._normalise_product_iri(product_iri), "page": page},
        )
        return _parse_page(payload, ProductVariant)

    async def aget_variants_page(self, product_iri: str, page: int = 1) -> Page[ProductVariant]:
        """Asynchronous counterpart of :meth:`get_variants_page`."""
        payload = await self.aget_json(
            f"{API_PREFIX}/product-variants",
            params={"product": self._normalise_product_iri(product_iri), "page": page},
        )
        return _parse_page(payload, ProductVariant)

    def iter_product_variants(
        self, product_iri: str, *, max_pages: int | None = None
    ) -> Iterator[ProductVariant]:
        """Iterate over every variant of a product."""
        page = 1
        visited = 0
        while True:
            if max_pages is not None and visited >= max_pages:
                return
            result = self.get_variants_page(product_iri, page)
            visited += 1
            yield from result.items
            if not result.has_next or result.next_page is None:
                return
            page = result.next_page

    async def aiter_product_variants(
        self, product_iri: str, *, max_pages: int | None = None
    ) -> AsyncIterator[ProductVariant]:
        """Asynchronous counterpart of :meth:`iter_product_variants`."""
        page = 1
        visited = 0
        while True:
            if max_pages is not None and visited >= max_pages:
                return
            result = await self.aget_variants_page(product_iri, page)
            visited += 1
            for variant in result.items:
                yield variant
            if not result.has_next or result.next_page is None:
                return
            page = result.next_page

    # ------------------------------------------------------------------ #
    # Search (best effort)
    # ------------------------------------------------------------------ #
    def search(self, query: str, page: int = 1) -> Page[Product]:
        """Search products by free text (``/products?search=...``)."""
        payload = self.get_json(f"{API_PREFIX}/products", params={"search": query, "page": page})
        return _parse_page(payload, Product)

    async def asearch(self, query: str, page: int = 1) -> Page[Product]:
        """Asynchronous counterpart of :meth:`search`."""
        payload = await self.aget_json(
            f"{API_PREFIX}/products", params={"search": query, "page": page}
        )
        return _parse_page(payload, Product)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalise_product_iri(product_iri: str) -> str:
        """Accept either a bare product code or an IRI like ``/api/v2/shop/products/...``."""
        if product_iri.startswith("/") or product_iri.startswith("http"):
            return product_iri
        return f"{API_PREFIX}/products/{product_iri}"
