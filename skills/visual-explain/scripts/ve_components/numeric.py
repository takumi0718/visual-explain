"""Decimal-safe numeric helpers shared by waterfall and slope renderers."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .model import SlopePayload, WaterfallPayload


def is_numeric(value: object) -> bool:
    """True only for int (not bool) or Decimal."""
    return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, Decimal)


def to_decimal(value: int | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(value)


def quantize_percent(value: int | Decimal, lo: int | Decimal, hi: int | Decimal) -> int:
    """Map value in [lo, hi] to an integer percent in [0, 100] (ROUND_HALF_UP)."""
    lo_d, hi_d, val = to_decimal(lo), to_decimal(hi), to_decimal(value)
    if val == lo_d:
        return 0
    if val == hi_d:
        return 100
    pct = (val - lo_d) / (hi_d - lo_d) * Decimal(100)
    return int(pct.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def waterfall_scale_values(payload: WaterfallPayload) -> tuple[list[Decimal], Decimal, Decimal]:
    """Return cumulative scale values (with baseline 0), min, and max."""
    values: list[Decimal] = [Decimal(0), to_decimal(payload.start.value)]
    running = to_decimal(payload.start.value)
    for step in payload.steps:
        running += to_decimal(step.delta)
        values.append(running)
    values.append(to_decimal(payload.end.value))
    lo = min(values)
    hi = max(values)
    return values, lo, hi


def slope_scale_values(payload: SlopePayload) -> tuple[Decimal, Decimal]:
    """Return min and max across all item from/to values (no baseline 0)."""
    values = [to_decimal(item.from_value) for item in payload.items]
    values.extend(to_decimal(item.to_value) for item in payload.items)
    return min(values), max(values)


def slope_y(value: int | Decimal, lo: int | Decimal, hi: int | Decimal) -> int:
    """Map a value into the slope SVG band Y=20..200 (inverted, ROUND_HALF_UP)."""
    lo_d, hi_d, val = to_decimal(lo), to_decimal(hi), to_decimal(value)
    if lo_d == hi_d:
        return 110
    pct = (val - lo_d) / (hi_d - lo_d) * Decimal(180)
    offset = int(pct.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return 200 - offset
