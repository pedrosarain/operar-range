from datetime import date, datetime
from zoneinfo import ZoneInfo

import polars as pl

from operar_range.calendar import (
    ny_regular_open_brt,
    reference_candle_window,
)
from operar_range.reference import (
    reconstruct_reference_session,
)


SP = ZoneInfo("America/Sao_Paulo")


def write_parquet(tmp_path, rows):
    path = tmp_path / "ticks.parquet"

    df = pl.DataFrame(
        rows,
        schema={
            "timestamp": pl.Datetime(
                time_unit="ms",
                time_zone="America/Sao_Paulo",
            ),
            "trade_number": pl.Int64,
            "price": pl.Float64,
            "qty": pl.Int64,
        },
    )

    df.write_parquet(path)
    return path


def test_ny_open_during_us_dst():
    result = ny_regular_open_brt(
        date(2026, 8, 18)
    )

    assert result.hour == 10
    assert result.minute == 30


def test_ny_open_outside_us_dst():
    result = ny_regular_open_brt(
        date(2026, 1, 15)
    )

    assert result.hour == 11
    assert result.minute == 30


def test_reference_window_is_dynamic():
    summer_start, summer_end = reference_candle_window(
        date(2026, 8, 18)
    )

    winter_start, winter_end = reference_candle_window(
        date(2026, 1, 15)
    )

    assert (summer_start.hour, summer_start.minute) == (10, 25)
    assert (summer_end.hour, summer_end.minute) == (10, 30)

    assert (winter_start.hour, winter_start.minute) == (11, 25)
    assert (winter_end.hour, winter_end.minute) == (11, 30)


def test_reconstructs_reference_m5(tmp_path):
    rows = {
        "timestamp": [
            datetime(2026, 8, 18, 10, 24, 59, tzinfo=SP),
            datetime(2026, 8, 18, 10, 25, 0, tzinfo=SP),
            datetime(2026, 8, 18, 10, 26, 0, tzinfo=SP),
            datetime(2026, 8, 18, 10, 27, 0, tzinfo=SP),
            datetime(2026, 8, 18, 10, 29, 59, tzinfo=SP),
            datetime(2026, 8, 18, 10, 30, 0, tzinfo=SP),
        ],
        "trade_number": [10, 20, 30, 40, 50, 60],
        "price": [
            100.0,
            110.0,
            120.0,
            90.0,
            105.0,
            200.0,
        ],
        "qty": [1, 2, 3, 4, 5, 100],
    }

    path = write_parquet(tmp_path, rows)

    r = reconstruct_reference_session(
        path,
        date(2026, 8, 18),
    )

    assert r["open"] == 110.0
    assert r["high"] == 120.0
    assert r["low"] == 90.0
    assert r["close"] == 105.0
    assert r["volume"] == 14.0
    assert r["tick_count"] == 4


def test_intraday_high_low_until_open(tmp_path):
    rows = {
        "timestamp": [
            datetime(2026, 8, 18, 9, 0, tzinfo=SP),
            datetime(2026, 8, 18, 9, 30, tzinfo=SP),
            datetime(2026, 8, 18, 10, 25, tzinfo=SP),
            datetime(2026, 8, 18, 10, 29, tzinfo=SP),
        ],
        "trade_number": [10, 20, 30, 40],
        "price": [
            80.0,
            150.0,
            120.0,
            100.0,
        ],
        "qty": [1, 1, 1, 1],
    }

    path = write_parquet(tmp_path, rows)

    r = reconstruct_reference_session(
        path,
        date(2026, 8, 18),
    )

    assert r["intraday_high_until_open"] == 150.0
    assert r["intraday_low_until_open"] == 80.0

    assert r["reference_high_is_intraday_high"] is False
    assert r["reference_low_is_intraday_low"] is False


def test_entry_rule_20_40(tmp_path):
    rows = {
        "timestamp": [
            datetime(2026, 8, 18, 9, 0, tzinfo=SP),
            datetime(2026, 8, 18, 10, 25, tzinfo=SP),
            datetime(2026, 8, 18, 10, 27, tzinfo=SP),
            datetime(2026, 8, 18, 10, 29, tzinfo=SP),
        ],
        "trade_number": [10, 20, 30, 40],
        "price": [
            100.0,
            110.0,
            150.0,
            120.0,
        ],
        "qty": [1, 1, 1, 1],
    }

    path = write_parquet(tmp_path, rows)

    r = reconstruct_reference_session(
        path,
        date(2026, 8, 18),
    )

    assert r["reference_high_is_intraday_high"] is True
    assert r["reference_low_is_intraday_low"] is False

    assert r["buy_offset"] == 40
    assert r["sell_offset"] == 20

    assert r["buy_level"] == 190.0
    assert r["sell_level"] == 90.0