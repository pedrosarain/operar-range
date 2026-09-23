from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Tick:
    ts_utc: datetime
    symbol: str
    price: float
    quantity: float | None = None
    trade_id: str | None = None


@dataclass(frozen=True)
class ReferenceCandle:
    start_brt: datetime
    end_brt: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class TradeEvent:
    ts_utc: datetime
    kind: str
    price: float
    note: str | None = None
