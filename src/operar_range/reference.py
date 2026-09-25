from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import polars as pl

from operar_range.calendar import (
    ny_regular_open_brt,
    reference_candle_window,
)


def _validate_normalized_schema(lf: pl.LazyFrame) -> None:
    required = {
        "timestamp",
        "trade_number",
        "price",
        "qty",
    }

    columns = set(lf.collect_schema().names())
    missing = required - columns

    if missing:
        raise ValueError(
            f"Normalized data is missing required columns: {sorted(missing)}"
        )


def reconstruct_reference_session(
    parquet_path: str | Path,
    session_date: date,
) -> dict:
    """Reconstruct the M5 immediately before the NY regular open.

    Important boundary convention:
    - reference candle: [start, NY open)
    - intraday high/low: all ticks strictly before NY open

    Therefore a tick stamped exactly at the NY opening instant belongs to the
    post-open market, not to the reference candle or pre-open intraday range.
    """

    parquet_path = Path(parquet_path)

    if not parquet_path.exists():
        raise FileNotFoundError(parquet_path)

    ny_open_brt = ny_regular_open_brt(session_date)
    candle_start, candle_end = reference_candle_window(
        session_date,
        timeframe_minutes=5,
    )

    lf = pl.scan_parquet(parquet_path)
    _validate_normalized_schema(lf)

    pre_open = lf.filter(
        pl.col("timestamp") < pl.lit(ny_open_brt)
    )

    pre_open_summary = (
        pre_open.select(
            pl.len().alias("pre_open_ticks"),
            pl.col("price").max().alias("intraday_high"),
            pl.col("price").min().alias("intraday_low"),
        )
        .collect(engine="streaming")
    )

    if pre_open_summary["pre_open_ticks"][0] == 0:
        raise ValueError(
            f"No ticks found before NY open for session {session_date}"
        )

    intraday_high = float(
        pre_open_summary["intraday_high"][0]
    )
    intraday_low = float(
        pre_open_summary["intraday_low"][0]
    )

    candle = (
        lf.filter(
            (pl.col("timestamp") >= pl.lit(candle_start))
            & (pl.col("timestamp") < pl.lit(candle_end))
        )
        .sort(
            ["timestamp", "trade_number"]
        )
        .collect(engine="streaming")
    )

    if candle.height == 0:
        raise ValueError(
            "No ticks found inside reference candle window "
            f"{candle_start.isoformat()} -> {candle_end.isoformat()}"
        )

    reference_open = float(candle["price"][0])
    reference_high = float(candle["price"].max())
    reference_low = float(candle["price"].min())
    reference_close = float(candle["price"][-1])

    volume = float(candle["qty"].sum())
    tick_count = candle.height

    high_is_intraday_high = (
        reference_high == intraday_high
    )
    low_is_intraday_low = (
        reference_low == intraday_low
    )

    buy_offset = 40 if high_is_intraday_high else 20
    sell_offset = 40 if low_is_intraday_low else 20

    buy_level = reference_high + buy_offset
    sell_level = reference_low - sell_offset

    return {
        "date": session_date.isoformat(),
        "source_parquet": parquet_path.name,
        "ny_open_brt": ny_open_brt.isoformat(),
        "reference_candle_start": candle_start.isoformat(),
        "reference_candle_end": candle_end.isoformat(),
        "open": reference_open,
        "high": reference_high,
        "low": reference_low,
        "close": reference_close,
        "volume": volume,
        "tick_count": tick_count,
        "intraday_high_until_open": intraday_high,
        "intraday_low_until_open": intraday_low,
        "reference_high_is_intraday_high": high_is_intraday_high,
        "reference_low_is_intraday_low": low_is_intraday_low,
        "buy_offset": buy_offset,
        "sell_offset": sell_offset,
        "buy_level": buy_level,
        "sell_level": sell_level,
    }


def write_reference_report(
    parquet_path: str | Path,
    session_date: date,
    output_path: str | Path,
) -> dict:
    report = reconstruct_reference_session(
        parquet_path=parquet_path,
        session_date=session_date,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return report