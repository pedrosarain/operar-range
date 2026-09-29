from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from operar_range.trade1 import (
    reconstruct_trade1,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


def _normalized(
    filename: str,
) -> Path:
    return (
        PROJECT_ROOT
        / "data"
        / "normalized"
        / filename
    )


def test_20260818_trade1_occurs_inside_immediate_next_candle():
    path = _normalized(
        "winv26_ticks_20260818_enriched.parquet"
    )

    if not path.exists():
        pytest.skip(
            "Real 2026-08-18 sample unavailable."
        )

    result = reconstruct_trade1(
        parquet_path=path,
        session_date=date(
            2026,
            8,
            18,
        ),
    )

    assert (
        result["entry_found"]
        is True
    )

    assert (
        result["direction"]
        == "LONG"
    )

    assert (
        result["entry_trigger_level"]
        == 170480.0
    )

    assert (
        result["entry_timestamp"]
        == "2026-08-18T10:30:29.741000-03:00"
    )

    assert (
        result["entry_trade_number"]
        == 14559560
    )


def test_20260819_breakout_after_immediate_next_candle_is_no_trade():
    path = _normalized(
        "winv26_ticks_20260819_enriched.parquet"
    )

    if not path.exists():
        pytest.skip(
            "Real 2026-08-19 sample unavailable."
        )

    result = reconstruct_trade1(
        parquet_path=path,
        session_date=date(
            2026,
            8,
            19,
        ),
    )

    assert (
        result["trade1_status"]
        == "NO_TRADE_1"
    )

    assert (
        result["entry_found"]
        is False
    )

    assert (
        result["direction"]
        is None
    )

    assert (
        result["trade1_window_start"]
        == "2026-08-19T10:30:00-03:00"
    )

    assert (
        result["trade1_window_end"]
        == "2026-08-19T10:35:00-03:00"
    )


def test_trade1_window_is_exactly_immediate_m5_after_ny_open():
    path = _normalized(
        "winv26_ticks_20260819_enriched.parquet"
    )

    if not path.exists():
        pytest.skip(
            "Real 2026-08-19 sample unavailable."
        )

    result = reconstruct_trade1(
        parquet_path=path,
        session_date=date(
            2026,
            8,
            19,
        ),
    )

    assert (
        result["trade1_window_start"]
        == "2026-08-19T10:30:00-03:00"
    )

    assert (
        result["trade1_window_end"]
        == "2026-08-19T10:35:00-03:00"
    )
