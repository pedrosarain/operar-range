from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class EntryRule:
    normal_offset_points: float = 20.0
    intraday_extreme_offset_points: float = 40.0


def entry_trigger(
    *,
    side: Side,
    reference_high: float,
    reference_low: float,
    is_intraday_high: bool,
    is_intraday_low: bool,
    rule: EntryRule = EntryRule(),
) -> float:
    """Return the theoretical trigger price for Trade 1.

    Operational rule supplied by the trader:
    - BUY: reference candle high + 20 points.
    - SELL: reference candle low - 20 points.
    - If the relevant reference extreme is also the intraday high/low up to that
      moment, use 40 points instead, to avoid stop-trigger noise around the
      day's extreme.
    """
    if side == Side.BUY:
        offset = (
            rule.intraday_extreme_offset_points
            if is_intraday_high
            else rule.normal_offset_points
        )
        return reference_high + offset

    offset = (
        rule.intraday_extreme_offset_points
        if is_intraday_low
        else rule.normal_offset_points
    )
    return reference_low - offset
