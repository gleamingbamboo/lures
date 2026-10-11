"""HTML parsing helpers for bereg.ua pages.

The functions in this module translate the Magento 1 markup currently served by
bereg.ua into the typed models from :mod:`bereg.models`. Selectors were
captured from real pages; they are intentionally tolerant (optional price
containers, fallback attribute sources) so small theme tweaks do not break
parsing entirely.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from .models import (
    Breadcrumb,
    CategoryPage,
    Money,
    ProductCard,
    ProductDetail,
    ProductImage,
    ProductVariant,
    SpecGroup,
    Specification,
)

__all__ = [
    "parse_listing",
    "parse_price",
    "parse_product_detail",
]

PRICE_SUFFIX_RE = re.compile(r"(грн|UAH)", re.IGNORECASE)
ARTIKUL_RE = re.compile(r"Артикул[:\s]*([A-Za-z0-9]+)", re.IGNORECASE)
CODE_RE = re.compile(r"Код[:\s]*(\d+)", re.IGNORECASE)
PRODUCT_ID_RE = re.compile(r"-(\d+)\.html$")
WHITESPACE_RE = re.compile(r"\s+")
# /media/catalog/product/cache/{version}/{kind}/{size}/{hash}/... -> /media/catalog/product/...
CACHE_PATH_RE = re.compile(r"/cache/[^/]+/[^/]+/[^/]+/[^/]+/")
PRODUCT_IMAGE_SELECTOR = 'img[data-src*="/media/catalog/product"]'


def parse_price(text: str | None) -> Money | None:
    """Parse a Magento price string such as ``1 250 грн`` or ``500,50 грн``."""
    if not text:
        return None
    cleaned = PRICE_SUFFIX_RE.sub("", text).strip()
    cleaned = cleaned.replace("\xa0", " ").replace(" ", "").replace(",", ".")
    if not cleaned:
        return None
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    return Money(amount=amount, raw=WHITESPACE_RE.sub(" ", text).strip())


def _normalise_image_url(url: str) -> str:
    """Strip the Magento cache/resize path prefix from a product image URL."""
    return CACHE_PATH_RE.sub("/", url)


def _abs_url(base: str, href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(base, href) if href.startswith("/") else href


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str_attr(element: Any, name: str) -> str | None:
    """Return a single string attribute, ignoring multi-valued attributes."""
    value = element.get(name)
    if isinstance(value, str):
        return value
    return None


def _class_list(element: Any) -> list[str]:
    """Return the CSS classes of an element as a list of strings."""
    value = element.get("class")
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return value.split()
    return []


def _price_from(element: Any) -> Money | None:
    if element is None:
        return None
    return parse_price(element.get_text(" ", strip=True))


def _prices_from_container(
    container: Any,
) -> tuple[Money | None, Money | None, Money | None]:
    """Return ``(regular, old, special)`` prices of a ``span.price-container``."""
    if container is None:
        return None, None, None
    regular = _price_from(container.select_one("span.regular-price-container"))
    old = _price_from(container.select_one("span.old-price-container"))
    special = _price_from(container.select_one("span.special-price-container"))
    return regular, old, special


def _current_page(url: str) -> int | None:
    values = parse_qs(urlparse(url).query).get("p")
    if not values:
        return None
    return _int_or_none(values[0])


def _max_page(soup: BeautifulSoup) -> int | None:
    highest = 0
    found = False
    for anchor in soup.select('a[href*="?p="]'):
        values = parse_qs(urlparse(_str_attr(anchor, "href") or "").query).get("p")
        if not values:
            continue
        found = True
        page = _int_or_none(values[0])
        if page is not None:
            highest = max(highest, page)
    return highest if found else None


def _parse_breadcrumbs(soup: BeautifulSoup) -> list[Breadcrumb]:
    container = soup.select_one("div.breadcrumbs")
    if container is None:
        return []
    crumbs: list[Breadcrumb] = []
    for item in container.select('span[property="itemListElement"]'):
        name_el = item.select_one('span[property="name"]')
        name = name_el.get_text(" ", strip=True) if name_el else None
        anchor = item.select_one('a[property="item"]')
        url = _str_attr(anchor, "href") if anchor else None
        if name:
            crumbs.append(Breadcrumb(name=name, url=url))
    return crumbs


def _parse_product_card(block: Any) -> ProductCard | None:
    link = block.select_one("a.product-image.js-product-link") or block.select_one("a[data-id]")
    href = link.get("href") if link else None
    if not href:
        return None
    name_el = block.select_one("div.h4") or block.select_one("div.title-block")
    name = name_el.get_text(" ", strip=True) if name_el else ""
    image_el = block.select_one(PRODUCT_IMAGE_SELECTOR)
    image = None
    image_alt = None
    if image_el is not None:
        raw = image_el.get("data-src")
        if raw:
            image = _normalise_image_url(str(raw))
        image_alt = image_el.get("alt") or None
    price, old, special = _prices_from_container(block.select_one("span.price-container"))
    return ProductCard(
        product_id=_int_or_none(link.get("data-id")),
        url=str(href),
        name=name,
        price=price,
        old_price=old,
        special_price=special,
        image=image,
        image_alt=image_alt,
    )


def parse_listing(html_text: str, url: str) -> CategoryPage:
    """Parse a category / search / sale listing page."""
    soup = BeautifulSoup(html_text, "lxml")
    title_tag = soup.select_one("h1")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""
    items = []
    for block in soup.select("div.product-item"):
        card = _parse_product_card(block)
        if card is not None:
            items.append(card)
    return CategoryPage(
        url=url,
        title=title,
        breadcrumbs=_parse_breadcrumbs(soup),
        items=items,
        current_page=_current_page(url) or 1,
        pages=_max_page(soup),
    )


def _parse_brand(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    anchor = soup.select_one("div.brand-block a")
    if anchor is None:
        return None, None
    url = _str_attr(anchor, "href")
    name = anchor.get_text(" ", strip=True) or None
    if name is None and url:
        match = re.search(r"/brand/([^/]+)\.html", url)
        if match:
            name = match.group(1)
    return name, url


def _parse_product_id(soup: BeautifulSoup, url: str) -> int | None:
    button = soup.select_one("button.js-add-to-cart[data-params]")
    raw = _str_attr(button, "data-params") if button is not None else None
    if raw:
        try:
            data = json.loads(raw)
            product = data.get("product")
            if product is not None:
                return _int_or_none(product)
        except (ValueError, TypeError):
            pass
    match = PRODUCT_ID_RE.search(url)
    return int(match.group(1)) if match else None


def _parse_main_prices(
    soup: BeautifulSoup,
) -> tuple[Money | None, Money | None, Money | None]:
    container = soup.select_one("div.product-info span.price-container")
    if container is None:
        container = soup.select_one("span.price-container")
    return _prices_from_container(container)


def _parse_gallery_images(soup: BeautifulSoup) -> list[ProductImage]:
    images: list[ProductImage] = []
    seen: set[str] = set()
    scoped = soup.select(f'div[class*="gallery"] {PRODUCT_IMAGE_SELECTOR}')
    if not scoped:
        scoped = soup.select(PRODUCT_IMAGE_SELECTOR)
    for image_el in scoped:
        classes = _class_list(image_el)
        if "js-image-tooltip" in classes:
            continue
        raw = image_el.get("data-src")
        if not raw:
            continue
        url = _normalise_image_url(str(raw))
        if url in seen:
            continue
        seen.add(url)
        images.append(ProductImage(url=url, alt=_str_attr(image_el, "alt") or None))
    return images


def _parse_description(soup: BeautifulSoup) -> str | None:
    block = soup.select_one("div.readmore")
    if block is None:
        return None
    text = block.get_text(" ", strip=True)
    text = text.removeprefix("Характеристики:").strip()
    return text or None


def _parse_spec_groups(soup: BeautifulSoup) -> list[SpecGroup]:
    container = soup.select_one("div.product-specifications-container")
    if container is None:
        return []
    tabs = container.select("div.specifications-tab")
    groups: list[SpecGroup] = []
    for wrap in container.select("div.specifications-wrap"):
        data_tab = wrap.get("data-tab")
        title = ""
        for tab in tabs:
            if tab.get("data-tab") == data_tab:
                title = tab.get_text(" ", strip=True)
                break
        rows: list[Specification] = []
        for row in wrap.select("div.product-specifications-row"):
            label_el = row.select_one("span.label")
            value_el = row.select_one("span.value")
            if label_el is None or value_el is None:
                continue
            label = label_el.get_text(" ", strip=True)
            value = value_el.get_text(" ", strip=True)
            if not label or not value:
                continue
            anchor = value_el.select_one("a")
            rows.append(
                Specification(
                    label=label,
                    value=value,
                    url=_str_attr(anchor, "href") if anchor else None,
                )
            )
        groups.append(SpecGroup(title=title or f"Варіант {len(groups) + 1}", specifications=rows))
    return groups


def _parse_variants(soup: BeautifulSoup) -> list[ProductVariant]:
    table = soup.select_one("table.grouped-items-table")
    if table is None:
        return []
    thead = table.select_one("thead")
    header: list[str] = []
    if thead is not None:
        header = [cell.get_text(" ", strip=True) for cell in thead.select("td")]
    variants: list[ProductVariant] = []
    for row in table.select("tbody tr"):
        row_classes = _class_list(row)
        if "visible-xs" in row_classes or "visible-sm" in row_classes:
            continue  # desktop row duplicated for small screens
        tds = row.select("td")
        name_el = row.select_one("td.variant-name a")
        name = name_el.get_text(" ", strip=True) if name_el else ""
        href = name_el.get("href") if name_el else None
        invariant: dict[str, Any] = {"name": name, "url": href}

        sku_block = row.select_one("td.variant-name div.hidden-xs b")
        sku = None
        if sku_block is not None:
            match = ARTIKUL_RE.search(sku_block.get_text(" ", strip=True))
            if match:
                sku = match.group(1)
        elif name_el is not None:
            match = ARTIKUL_RE.search(name_el.get_text(" ", strip=True))
            if match:
                sku = match.group(1)
        if sku:
            invariant["sku"] = sku

        code_block = row.select_one("td.variant-image div.hidden-xs")
        if code_block is not None:
            match = CODE_RE.search(code_block.get_text(" ", strip=True))
            if match:
                invariant["code"] = match.group(1)

        image_el = row.select_one("td.variant-image img.thumbnail")
        if image_el is not None and image_el.get("data-src"):
            invariant["image"] = _normalise_image_url(str(image_el["data-src"]))

        price_td = row.select_one("td.variant-price")
        if price_td is not None:
            content = price_td.get("content")
            if content:
                try:
                    invariant["price"] = Money(amount=Decimal(str(content).replace(",", ".")))
                except InvalidOperation:
                    invariant["price"] = None
            else:
                invariant["price"] = _price_from(
                    price_td.select_one("span.regular-price span.price")
                )
            invariant["special_price"] = _price_from(
                price_td.select_one("span.special-price span.price")
            )
            invariant["old_price"] = _price_from(price_td.select_one("span.old-price span.price"))

        invariant["available"] = (
            row.select_one("td.variant-button button.js-add-to-cart") is not None
        )

        attributes: list[Specification] = []
        for index, td in enumerate(tds):
            classes = _class_list(td)
            if "variant-attribute" not in classes:
                continue
            value = td.get_text(" ", strip=True)
            label = header[index] if index < len(header) else None
            if label and value:
                attributes.append(Specification(label=label, value=value))
        if not attributes:
            for li in row.select("ul.list-inline.visible-xs li"):
                text = li.get_text(" ", strip=True)
                if ":" not in text:
                    continue
                label, value = text.split(":", 1)
                label = label.strip()
                if label.casefold() in ("код", "артикул"):
                    continue
                attributes.append(Specification(label=label, value=value.strip()))
        invariant["attributes"] = attributes

        variants.append(ProductVariant(**invariant))
    return variants


def parse_product_detail(html_text: str, url: str) -> ProductDetail:
    """Parse a full product page (specs, gallery, «Модифікації» variants)."""
    soup = BeautifulSoup(html_text, "lxml")
    name_tag = soup.select_one("h1")
    name = name_tag.get_text(" ", strip=True) if name_tag else ""
    brand, brand_url = _parse_brand(soup)
    price, old_price, special_price = _parse_main_prices(soup)
    variants = _parse_variants(soup)
    groups = _parse_spec_groups(soup)
    sku = None
    if variants:
        sku = variants[0].sku
    return ProductDetail(
        product_id=_parse_product_id(soup, url),
        url=url,
        name=name,
        brand=brand,
        brand_url=brand_url,
        sku=sku,
        price=price,
        old_price=old_price,
        special_price=special_price,
        images=_parse_gallery_images(soup),
        description=_parse_description(soup),
        breadcrumbs=_parse_breadcrumbs(soup),
        specification_groups=groups,
        variants=variants,
    )
