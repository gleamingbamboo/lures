"""High level client for the Flagman.ua shop API (``r.flagman.ua``).

The public Flagman.ua frontend is a Nuxt application backed by a JSON API hosted
on ``r.flagman.ua``. Two endpoints power catalog browsing:

* ``GET /site/catalog/{category_id}[/{filter}]`` — returns the ordered product
  ids of a category together with its filters, child categories, breadcrumbs and
  SEO metadata.
* ``GET /api/goods/id/{id,id,...}`` — returns full product details for up to
  ``batch_size`` ids at once (a single id returns an object, multiple ids return
  a list).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Iterator, Mapping, Sequence
from typing import Any
from urllib.parse import quote

from ._base import BaseHTTPClient
from ._version import __version__
from .models import Catalog, GoodsResponse, Product

__all__ = ["DEFAULT_BASE_URL", "FlagmanClient"]

DEFAULT_BASE_URL = "https://r.flagman.ua"
CATALOG_PATH = "/site/catalog/{category_id}"
GOODS_PATH = "/api/goods/id/{ids}"


def _chunks(seq: Sequence[str], size: int) -> Iterator[Sequence[str]]:
    for start in range(0, len(seq), size):
        yield seq[start : start + size]


class FlagmanClient(BaseHTTPClient):
    """Synchronous + asynchronous client for the Flagman.ua JSON API.

    Examples
    --------
    >>> with FlagmanClient() as client:              # doctest: +SKIP
    ...     catalog = client.get_catalog("168794")
    ...     for product in client.iter_products("168794"):
    ...         print(product.display_title, product.price)

    Async usage mirrors the synchronous one::

        async with FlagmanClient() as client:          # doctest: +SKIP
            catalog = await client.aget_catalog("168794")
            async for product in client.aiter_products("168794"):
                ...
    """

    DEFAULT_USER_AGENT = f"flagman-client/{__version__} (+https://github.com/Gleam/flagman-client)"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        batch_size: int = 32,
        user_agent: str | None = None,
        headers: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        merged_headers = {"Accept": "application/json"}
        if headers:
            merged_headers.update(headers)
        super().__init__(
            base_url,
            user_agent=user_agent or self.DEFAULT_USER_AGENT,
            headers=merged_headers,
            **kwargs,
        )
        self.batch_size = max(1, int(batch_size))

    # ------------------------------------------------------------------ #
    # Low-level endpoints
    # ------------------------------------------------------------------ #
    @staticmethod
    def _catalog_url(category_id: str | int, filters: str | None = None) -> str:
        url = CATALOG_PATH.format(category_id=category_id)
        if filters:
            url = f"{url}/{filters.lstrip('/')}"
        return url

    def get_catalog(self, category_id: str | int, filters: str | None = None) -> Catalog:
        """Fetch a category: product ids, filters, children and metadata."""
        payload = self.get_json(self._catalog_url(category_id, filters))
        return Catalog.model_validate(payload)

    async def aget_catalog(self, category_id: str | int, filters: str | None = None) -> Catalog:
        """Asynchronous counterpart of :meth:`get_catalog`."""
        payload = await self.aget_json(self._catalog_url(category_id, filters))
        return Catalog.model_validate(payload)

    def get_products(self, ids: Iterable[str | int]) -> list[Product]:
        """Fetch full product details for ``ids``.

        Ids are de-duplicated (preserving order), chunked into
        :attr:`batch_size` groups and requested in parallel-free batches. The
        returned list follows the order of ``ids``; unknown ids are skipped.
        """
        unique = list(dict.fromkeys(str(item) for item in ids))
        by_id: dict[str, Product] = {}
        for chunk in _chunks(unique, self.batch_size):
            by_id.update(self._fetch_batch(chunk))
        return [by_id[item] for item in unique if item in by_id]

    async def aget_products(self, ids: Iterable[str | int]) -> list[Product]:
        """Asynchronous counterpart of :meth:`get_products`."""
        unique = list(dict.fromkeys(str(item) for item in ids))
        by_id: dict[str, Product] = {}
        for chunk in _chunks(unique, self.batch_size):
            by_id.update(await self._afetch_batch(chunk))
        return [by_id[item] for item in unique if item in by_id]

    def get_product(self, product_id: str | int) -> Product:
        """Fetch a single product by id."""
        products = self.get_products([product_id])
        if not products:
            from .exceptions import NotFoundError

            raise NotFoundError(
                f"Product {product_id!r} not found",
                url=self._goods_url([str(product_id)]),
            )
        return products[0]

    async def aget_product(self, product_id: str | int) -> Product:
        """Asynchronous counterpart of :meth:`get_product`."""
        products = await self.aget_products([product_id])
        if not products:
            from .exceptions import NotFoundError

            raise NotFoundError(
                f"Product {product_id!r} not found",
                url=self._goods_url([str(product_id)]),
            )
        return products[0]

    # ------------------------------------------------------------------ #
    # Batching internals
    # ------------------------------------------------------------------ #
    @staticmethod
    def _goods_url(ids: Sequence[str]) -> str:
        return GOODS_PATH.format(ids=",".join(str(item) for item in ids))

    def _fetch_batch(self, ids: Sequence[str]) -> dict[str, Product]:
        payload = self.get_json(self._goods_url(ids))
        response = GoodsResponse.model_validate(payload)
        return {product.id: product for product in response.data}

    async def _afetch_batch(self, ids: Sequence[str]) -> dict[str, Product]:
        payload = await self.aget_json(self._goods_url(ids))
        response = GoodsResponse.model_validate(payload)
        return {product.id: product for product in response.data}

    # ------------------------------------------------------------------ #
    # Iterators
    # ------------------------------------------------------------------ #
    def iter_products(
        self, category_id: str | int, filters: str | None = None
    ) -> Iterator[Product]:
        """Lazily iterate over every product in a category, batch by batch."""
        catalog = self.get_catalog(category_id, filters)
        for chunk in _chunks(list(catalog.data.goods), self.batch_size):
            yield from self._fetch_batch(chunk).values()

    async def aiter_products(
        self, category_id: str | int, filters: str | None = None
    ) -> AsyncIterator[Product]:
        """Asynchronous counterpart of :meth:`iter_products`."""
        catalog = await self.aget_catalog(category_id, filters)
        for chunk in _chunks(list(catalog.data.goods), self.batch_size):
            batch = await self._afetch_batch(chunk)
            for product in batch.values():
                yield product

    def iter_categories(self, category_id: str | int, *, expand: bool = False) -> Iterator[Any]:
        """Depth-first walk over the category tree below ``category_id``.

        With ``expand=True`` each yielded node is fetched individually to
        discover deeper children that are not embedded in the parent response.
        """
        catalog = self.get_catalog(category_id)
        stack: list[Any] = list(reversed(catalog.data.children))
        while stack:
            node = stack.pop()
            yield node
            children = node.children
            if not children and expand and node.id is not None:
                try:
                    children = self.get_catalog(str(node.id)).data.children
                except Exception:
                    children = []
            stack.extend(reversed(children))

    # ------------------------------------------------------------------ #
    # Search (experimental)
    # ------------------------------------------------------------------ #
    def search(self, query: str) -> dict[str, Any]:
        """Query the (experimental) site search endpoint.

        .. warning::
            The public search endpoint at ``/site/search`` does not currently
            return product results to anonymous clients. Prefer walking
            categories with :meth:`iter_products`. The raw payload is returned
            unchanged so callers can react when the endpoint starts working.
        """
        payload = self.get_json(f"/site/search/{quote(query)}")
        return dict(payload)

    async def asearch(self, query: str) -> dict[str, Any]:
        """Asynchronous counterpart of :meth:`search`."""
        payload = await self.aget_json(f"/site/search/{quote(query)}")
        return dict(payload)
