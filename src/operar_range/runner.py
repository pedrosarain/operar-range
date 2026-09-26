from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


@dataclass(frozen=True)
class M5Candle:
    start: datetime
    end: datetime
    open: float
    high: float
    low: float
    close: float
    first_trade_number: int
    last_trade_number: int

    @property
    def direction(self) -> str:
        if self.close > self.open:
            return "POSITIVE"

        if self.close < self.open:
            return "NEGATIVE"

        return "NEUTRAL"

    def as_dict(self) -> dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "direction": self.direction,
            "first_trade_number": self.first_trade_number,
            "last_trade_number": self.last_trade_number,
        }


def _bucket_start(
    timestamp: datetime,
) -> datetime:
    minute = (
        timestamp.minute
        // 5
        * 5
    )

    return timestamp.replace(
        minute=minute,
        second=0,
        microsecond=0,
    )


def build_m5_candles_from_parquet(
    parquet_path: str | Path,
    batch_size: int = 131_072,
) -> list[M5Candle]:
    parquet_path = Path(parquet_path)

    if not parquet_path.exists():
        raise FileNotFoundError(
            parquet_path
        )

    parquet = pq.ParquetFile(
        parquet_path
    )

    candles: list[M5Candle] = []

    current_start: datetime | None = None
    current_open: float | None = None
    current_high: float | None = None
    current_low: float | None = None
    current_close: float | None = None
    first_trade_number: int | None = None
    last_trade_number: int | None = None

    previous_timestamp: datetime | None = None
    previous_trade_number: int | None = None

    def flush() -> None:
        nonlocal current_start
        nonlocal current_open
        nonlocal current_high
        nonlocal current_low
        nonlocal current_close
        nonlocal first_trade_number
        nonlocal last_trade_number

        if current_start is None:
            return

        candles.append(
            M5Candle(
                start=current_start,
                end=(
                    current_start
                    + timedelta(minutes=5)
                ),
                open=float(
                    current_open
                ),
                high=float(
                    current_high
                ),
                low=float(
                    current_low
                ),
                close=float(
                    current_close
                ),
                first_trade_number=int(
                    first_trade_number
                ),
                last_trade_number=int(
                    last_trade_number
                ),
            )
        )

    for batch in parquet.iter_batches(
        columns=[
            "timestamp",
            "trade_number",
            "price",
        ],
        batch_size=batch_size,
    ):
        timestamps = (
            batch.column(
                "timestamp"
            ).to_pylist()
        )

        trade_numbers = (
            batch.column(
                "trade_number"
            ).to_pylist()
        )

        prices = (
            batch.column(
                "price"
            ).to_pylist()
        )

        for (
            timestamp,
            raw_trade_number,
            raw_price,
        ) in zip(
            timestamps,
            trade_numbers,
            prices,
        ):
            trade_number = int(
                raw_trade_number
            )

            price = float(
                raw_price
            )

            if (
                previous_timestamp
                is not None
            ):
                if (
                    timestamp
                    < previous_timestamp
                ):
                    raise ValueError(
                        "Ticks are not ordered "
                        "by timestamp."
                    )

                if (
                    timestamp
                    == previous_timestamp
                    and trade_number
                    < previous_trade_number
                ):
                    raise ValueError(
                        "Ticks with identical "
                        "timestamp are not ordered "
                        "by trade_number."
                    )

            previous_timestamp = (
                timestamp
            )
            previous_trade_number = (
                trade_number
            )

            bucket = _bucket_start(
                timestamp
            )

            if (
                current_start
                is None
            ):
                current_start = bucket
                current_open = price
                current_high = price
                current_low = price
                current_close = price
                first_trade_number = (
                    trade_number
                )
                last_trade_number = (
                    trade_number
                )
                continue

            if bucket != current_start:
                flush()

                current_start = bucket
                current_open = price
                current_high = price
                current_low = price
                current_close = price
                first_trade_number = (
                    trade_number
                )
                last_trade_number = (
                    trade_number
                )
                continue

            current_high = max(
                current_high,
                price,
            )

            current_low = min(
                current_low,
                price,
            )

            current_close = price
            last_trade_number = (
                trade_number
            )

    flush()

    return candles


def candle_for_timestamp(
    candles: list[M5Candle],
    timestamp: datetime,
) -> M5Candle | None:
    bucket = _bucket_start(
        timestamp
    )

    for candle in candles:
        if candle.start == bucket:
            return candle

    return None


def protected_candle_for_runner(
    *,
    candles: list[M5Candle],
    direction: str,
    activation_timestamp: datetime,
    current_timestamp: datetime,
) -> M5Candle | None:
    wanted_direction = (
        "POSITIVE"
        if direction == "LONG"
        else "NEGATIVE"
    )

    eligible = [
        candle
        for candle in candles
        if (
            candle.end
            <= current_timestamp
            and candle.end
            > activation_timestamp
            and candle.direction
            == wanted_direction
        )
    ]

    if not eligible:
        return None

    return eligible[-1]


def runner_trigger(
    *,
    direction: str,
    row: dict[str, Any],
    candles: list[M5Candle],
    activation_timestamp: str,
) -> dict[str, Any] | None:
    timestamp = datetime.fromisoformat(
        row["timestamp"]
    )

    activated_at = (
        datetime.fromisoformat(
            activation_timestamp
        )
    )

    if timestamp <= activated_at:
        return None

    current_candle = (
        candle_for_timestamp(
            candles,
            timestamp,
        )
    )

    if current_candle is None:
        return None

    protected = (
        protected_candle_for_runner(
            candles=candles,
            direction=direction,
            activation_timestamp=(
                activated_at
            ),
            current_timestamp=timestamp,
        )
    )

    if protected is None:
        return None

    price = float(
        row["price"]
    )

    if direction == "LONG":
        current_is_opposite = (
            price
            < current_candle.open
        )

        trigger_level = (
            protected.low
        )

        triggered = (
            current_is_opposite
            and price <= trigger_level
        )

    elif direction == "SHORT":
        current_is_opposite = (
            price
            > current_candle.open
        )

        trigger_level = (
            protected.high
        )

        triggered = (
            current_is_opposite
            and price >= trigger_level
        )

    else:
        raise ValueError(
            f"Unsupported direction: "
            f"{direction}"
        )

    if not triggered:
        return None

    return {
        "trigger_level": (
            float(trigger_level)
        ),
        "protected_candle": (
            protected.as_dict()
        ),
        "current_candle": (
            current_candle.as_dict()
        ),
    }