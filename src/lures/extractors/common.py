"""Незалежні від магазину хелпери для текстових атрибутів.

Перенесено з оригінального ``build_xlsx.py``; усі функції приймають звичайні
рядки й повертають канонічні значення, тож екстрактори магазинів лишаються
тонкими адаптерами навколо моделей клієнтів.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

__all__ = [
    "BUOY_MAP",
    "DESC_WORDS",
    "SURF_TYPES",
    "TYPE_WORDS",
    "buoyancy_code",
    "discount_percent",
    "match_value",
    "parse_depth",
    "parse_float",
    "wobbler_type",
]

# Слово на сайті -> нормалізований код плавучості.
BUOY_MAP: dict[str, str] = {
    "Плаваючий": "F",
    "Поверхневий": "F",
    "Суспендр": "SP",
    "Тонучий": "S",
    "Швидко тоне": "FS",
    "Повільно тоне": "SS",
    "Повільно cпливає": "SR",
    "Повільно спливає": "SR",
    "Глибоко пірнаючий": "S",
}

# Поверхневі приманки визначаються за типом воблера, а не за плавучістю.
SURF_TYPES: tuple[str, ...] = ("Popper", "Walker")

# Ключові слова моделі/slug -> канонічний тип воблера.
TYPE_WORDS: tuple[tuple[str, str], ...] = (
    ("vib", "Vib/Rattlin"),
    ("rattlin", "Vib/Rattlin"),
    ("crank", "Crank"),
    ("minnow", "Minnow"),
    ("popper", "Popper"),
    ("walker", "Walker"),
    ("swim bait", "Swimbait"),
    ("swimbait", "Swimbait"),
    ("jerk", "Jerkbait"),
    ("cicada", "Cicada"),
    ("fat", "Fat"),
)

# Ключові слова опису -> канонічний тип воблера (фолбек).
DESC_WORDS: tuple[tuple[str, str], ...] = (
    ("міноу", "Minnow"),
    ("мінноу", "Minnow"),
    ("минноу", "Minnow"),
    ("minnow", "Minnow"),
    ("кренк", "Crank"),
    ("крэн", "Crank"),
    ("crank", "Crank"),
    ("шайнер", "Shad"),
    ("шед", "Shad"),
    ("shad", "Shad"),
    ("поппер", "Popper"),
    ("popper", "Popper"),
    ("уокер", "Walker"),
    ("волкер", "Walker"),
    ("walker", "Walker"),
    ("джерк", "Jerkbait"),
    ("jerk", "Jerkbait"),
    ("раттлін", "Vib/Rattlin"),
    ("rattlin", "Vib/Rattlin"),
    ("lipless", "Vib/Rattlin"),
    ("свімбейт", "Swimbait"),
    ("swimbait", "Swimbait"),
    ("цикада", "Cicada"),
    ("cicada", "Cicada"),
    ("фет-кренк", "Fat"),
    ("fat crank", "Fat"),
)


def parse_float(value: str | None) -> float | None:
    """Перше число з рядка як ``float``, інакше ``None``."""
    if value is None:
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value))
    if not match:
        return None
    return float(match.group().replace(",", "."))


def parse_depth(text: str | None) -> tuple[float | None, float | None]:
    """Повертає ``(від, до)`` у метрах.

    * ``"до 1.5 м"`` -> ``(None, 1.5)``
    * ``"0.5 - 1.5 м"`` -> ``(0.5, 1.5)``
    * ``"1.5 м"`` -> ``(1.5, 1.5)``
    """
    if not text:
        return None, None
    cleaned = text.replace("\u2013", "-").replace("\u2014", "-").replace(",", ".")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    numbers = [float(x) for x in re.findall(r"\d*\.?\d+", cleaned)]
    if not numbers:
        return None, None
    if cleaned.startswith("до "):
        return None, numbers[0]
    return min(numbers), max(numbers)


def discount_percent(price: float | None, old_price: float | None) -> int | None:
    """Цілих відсотків знижки; ``None``, якщо знижки немає."""
    if price is None or old_price is None or old_price <= price:
        return None
    return round((old_price - price) / old_price * 100)


def match_value(
    pairs: Iterable[tuple[str, str]],
    *keywords: str,
    exclude: tuple[str, ...] = (),
) -> str | None:
    """Перше значення, у назві якого є будь-яке keyword (і немає exclude)."""
    for title, value in pairs:
        if any(keyword in title for keyword in keywords) and not any(
            bad in title for bad in exclude
        ):
            return value
    return None


def buoyancy_code(raw: str | None, hint: str | None = None) -> str:
    """Код плавучості зі слова; фолбек — евристики за назвою моделі."""
    if raw:
        code = BUOY_MAP.get(raw.strip())
        if code:
            return code
    low = (hint or "").lower()
    if "vib" in low:
        return "S"
    if re.search(r"\d\s*sp\b|\bsp[-_ ]", low) or "sp-" in low or "sp " in low:
        return "SP"
    if re.search(r"\d\s*sr\b|\bsr[-_ ]", low) or "sr-" in low:
        return "SR"
    if "bomber" in low and "model a" in low:
        return "F"
    if re.search(r"\d\s*f\b|\d+f-", low):
        return "F"
    return ""


def wobbler_type(*texts: str) -> str:
    """Канонічний тип воблера: спершу ключові слова назви, потім опису."""
    joined = " ".join((text or "") for text in texts).lower()
    for keyword, label in TYPE_WORDS:
        if keyword in joined:
            return label
    best_index: int | None = None
    best_label = ""
    for keyword, label in DESC_WORDS:
        index = joined.find(keyword)
        if index != -1 and (best_index is None or index < best_index):
            best_index, best_label = index, label
    return best_label
