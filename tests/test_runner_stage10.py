from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from operar_range.management import (
    ManagementConfig,
    simulate_management,
    validate_config,
)
from operar_range.runner import (
    M5Candle,
    runner_trigger,
)


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def candle(
    start: str,
    open_: float,
    high: float,
    low: float,
    close: float,
    first_trade_number: int = 1,
    last_trade_number: int = 100,
) -> M5Candle:
    start_dt = dt(start)

    return M5Candle(
        start=start_dt,
        end=start_dt + timedelta(minutes=5),
        open=float(open_),
        high=float(high),
        low=float(low),
        close=float(close),
        first_trade_number=first_trade_number,
        last_trade_number=last_trade_number,
    )


def row(
    timestamp: str,
    trade_number: int,
    price: float,
    entry_price: float = 1000.0,
    direction: str = "LONG",
) -> dict:
    if direction == "LONG":
        points = price - entry_price
    else:
        points = entry_price - price

    return {
        "timestamp": timestamp,
        "trade_number": trade_number,
        "price": float(price),
        "points_from_entry": float(points),
        "favorable_excursion": max(
            0.0,
            float(points),
        ),
        "adverse_excursion": max(
            0.0,
            -float(points),
        ),
    }


def test_long_positive_sequence_keeps_latest_positive():
    candles = [
        candle(
            "2026-08-18T10:30:00-03:00",
            1000,
            1050,
            990,
            1040,
        ),
        candle(
            "2026-08-18T10:35:00-03:00",
            1040,
            1100,
            1030,
            1090,
        ),
        candle(
            "2026-08-18T10:40:00-03:00",
            1090,
            1120,
            1080,
            1085,
        ),
    ]

    result = runner_trigger(
        direction="LONG",
        row=row(
            "2026-08-18T10:40:30-03:00",
            500,
            1085,
        ),
        candles=candles,
        activation_timestamp=(
            "2026-08-18T10:30:00-03:00"
        ),
    )

    assert result is None


def test_long_negative_without_break_keeps_runner():
    candles = [
        candle(
            "2026-08-18T10:30:00-03:00",
            1000,
            1100,
            990,
            1080,
        ),
        candle(
            "2026-08-18T10:35:00-03:00",
            1080,
            1090,
            1000,
            1050,
        ),
    ]

    result = runner_trigger(
        direction="LONG",
        row=row(
            "2026-08-18T10:35:30-03:00",
            501,
            1050,
        ),
        candles=candles,
        activation_timestamp=(
            "2026-08-18T10:29:00-03:00"
        ),
    )

    assert result is None


def test_long_negative_breaks_last_positive_low():
    candles = [
        candle(
            "2026-08-18T10:30:00-03:00",
            1000,
            1100,
            990,
            1080,
        ),
        candle(
            "2026-08-18T10:35:00-03:00",
            1080,
            1090,
            980,
            985,
        ),
    ]

    result = runner_trigger(
        direction="LONG",
        row=row(
            "2026-08-18T10:35:30-03:00",
            502,
            985,
        ),
        candles=candles,
        activation_timestamp=(
            "2026-08-18T10:29:00-03:00"
        ),
    )

    assert result is not None
    assert result["trigger_level"] == 990.0
    assert (
        result["protected_candle"]["direction"]
        == "POSITIVE"
    )


def test_short_negative_sequence():
    candles = [
        candle(
            "2026-08-18T10:30:00-03:00",
            1000,
            1010,
            900,
            920,
        ),
        candle(
            "2026-08-18T10:35:00-03:00",
            920,
            930,
            850,
            870,
        ),
        candle(
            "2026-08-18T10:40:00-03:00",
            870,
            900,
            860,
            880,
        ),
    ]

    result = runner_trigger(
        direction="SHORT",
        row=row(
            "2026-08-18T10:40:30-03:00",
            600,
            880,
            direction="SHORT",
        ),
        candles=candles,
        activation_timestamp=(
            "2026-08-18T10:30:00-03:00"
        ),
    )

    assert result is None


def test_short_positive_without_break_keeps_runner():
    candles = [
        candle(
            "2026-08-18T10:30:00-03:00",
            1000,
            1010,
            900,
            920,
        ),
        candle(
            "2026-08-18T10:35:00-03:00",
            920,
            1000,
            910,
            950,
        ),
    ]

    result = runner_trigger(
        direction="SHORT",
        row=row(
            "2026-08-18T10:35:30-03:00",
            601,
            950,
            direction="SHORT",
        ),
        candles=candles,
        activation_timestamp=(
            "2026-08-18T10:29:00-03:00"
        ),
    )

    assert result is None


def test_short_positive_breaks_last_negative_high():
    candles = [
        candle(
            "2026-08-18T10:30:00-03:00",
            1000,
            1010,
            900,
            920,
        ),
        candle(
            "2026-08-18T10:35:00-03:00",
            920,
            1020,
            910,
            1015,
        ),
    ]

    result = runner_trigger(
        direction="SHORT",
        row=row(
            "2026-08-18T10:35:30-03:00",
            602,
            1015,
            direction="SHORT",
        ),
        candles=candles,
        activation_timestamp=(
            "2026-08-18T10:29:00-03:00"
        ),
    )

    assert result is not None
    assert result["trigger_level"] == 1010.0
    assert (
        result["protected_candle"]["direction"]
        == "NEGATIVE"
    )


def test_runner_and_be_be_happens_first():
    trajectory = [
        row(
            "2026-08-18T10:30:00-03:00",
            1,
            1000,
        ),
        row(
            "2026-08-18T10:31:00-03:00",
            2,
            1125,
        ),
        row(
            "2026-08-18T10:32:00-03:00",
            3,
            1000,
        ),
    ]

    candles = [
        candle(
            "2026-08-18T10:30:00-03:00",
            1000,
            1150,
            990,
            1100,
        ),
    ]

    config = ManagementConfig(
        stop_points=170,
        partial_1_points=125,
        partial_1_pct=70,
        break_even_enabled=True,
        break_even_after_partial=1,
        runner_enabled=True,
        runner_pct=30,
        runner_exit_rule="CANDLE_BREAK_M5",
    )

    result = simulate_management(
        trajectory=trajectory,
        date="2026-08-18",
        direction="LONG",
        entry_price=1000,
        config=config,
        runner_candles=candles,
    )

    assert (
        result["partial_1_result"]["executed"]
        is True
    )

    assert (
        result["final_reason"]
        == "EXIT_BREAK_EVEN"
    )


def test_runner_and_be_candle_happens_first():
    trajectory = [
        row(
            "2026-08-18T10:30:00-03:00",
            1,
            1000,
        ),
        row(
            "2026-08-18T10:31:00-03:00",
            2,
            1125,
        ),
        row(
            "2026-08-18T10:40:30-03:00",
            3,
            1080,
        ),
    ]

    candles = [
        candle(
            "2026-08-18T10:30:00-03:00",
            1000,
            1150,
            990,
            1120,
        ),
        candle(
            "2026-08-18T10:35:00-03:00",
            1120,
            1200,
            1100,
            1180,
        ),
        candle(
            "2026-08-18T10:40:00-03:00",
            1180,
            1190,
            1070,
            1080,
        ),
    ]

    config = ManagementConfig(
        stop_points=170,
        partial_1_points=125,
        partial_1_pct=70,
        break_even_enabled=True,
        break_even_after_partial=1,
        runner_enabled=True,
        runner_pct=30,
        runner_exit_rule="CANDLE_BREAK_M5",
    )

    result = simulate_management(
        trajectory=trajectory,
        date="2026-08-18",
        direction="LONG",
        entry_price=1000,
        config=config,
        runner_candles=candles,
    )

    assert (
        result["final_reason"]
        == "EXIT_RUNNER_CANDLE"
    )

    assert (
        result["runner_result"]["executed"]
        is True
    )

    assert (
        result["runner_result"]["trigger_level"]
        == 1100.0
    )


def test_jump_over_runner_level():
    trajectory = [
        row(
            "2026-08-18T10:30:00-03:00",
            1,
            1000,
        ),
        row(
            "2026-08-18T10:31:00-03:00",
            2,
            1125,
        ),
        row(
            "2026-08-18T10:40:30-03:00",
            3,
            1080,
        ),
    ]

    candles = [
        candle(
            "2026-08-18T10:35:00-03:00",
            1120,
            1200,
            1100,
            1180,
        ),
        candle(
            "2026-08-18T10:40:00-03:00",
            1180,
            1190,
            1070,
            1080,
        ),
    ]

    config = ManagementConfig(
        stop_points=170,
        partial_1_points=125,
        partial_1_pct=70,
        runner_enabled=True,
        runner_pct=30,
        runner_exit_rule="CANDLE_BREAK_M5",
    )

    result = simulate_management(
        trajectory=trajectory,
        date="2026-08-18",
        direction="LONG",
        entry_price=1000,
        config=config,
        runner_candles=candles,
    )

    runner = result["runner_result"]

    assert runner["executed"] is True
    assert runner["trigger_level"] == 1100.0

    assert (
        runner[
            "first_traded_price_after_trigger"
        ]
        == 1080.0
    )

    assert (
        runner["jumped_trigger_level"]
        is True
    )


def test_same_timestamp_trade_number_order():
    trajectory = [
        row(
            "2026-08-18T10:30:00-03:00",
            1,
            1000,
        ),
        row(
            "2026-08-18T10:31:00-03:00",
            2,
            1125,
        ),
        row(
            "2026-08-18T10:40:30-03:00",
            100,
            1110,
        ),
        row(
            "2026-08-18T10:40:30-03:00",
            101,
            1090,
        ),
    ]

    candles = [
        candle(
            "2026-08-18T10:35:00-03:00",
            1120,
            1200,
            1100,
            1180,
        ),
        candle(
            "2026-08-18T10:40:00-03:00",
            1180,
            1190,
            1080,
            1090,
        ),
    ]

    config = ManagementConfig(
        stop_points=170,
        partial_1_points=125,
        partial_1_pct=70,
        runner_enabled=True,
        runner_pct=30,
        runner_exit_rule="CANDLE_BREAK_M5",
    )

    result = simulate_management(
        trajectory=trajectory,
        date="2026-08-18",
        direction="LONG",
        entry_price=1000,
        config=config,
        runner_candles=candles,
    )

    assert (
        result["runner_result"]["trade_number"]
        == 101
    )


def test_integral_position_runner():
    trajectory = [
        row(
            "2026-08-18T10:30:00-03:00",
            1,
            1000,
        ),
        row(
            "2026-08-18T10:35:30-03:00",
            2,
            980,
        ),
    ]

    candles = [
        candle(
            "2026-08-18T10:30:00-03:00",
            1000,
            1100,
            990,
            1080,
        ),
        candle(
            "2026-08-18T10:35:00-03:00",
            1080,
            1090,
            970,
            980,
        ),
    ]

    config = ManagementConfig(
        stop_points=170,
        runner_enabled=True,
        runner_pct=100,
        runner_exit_rule="CANDLE_BREAK_M5",
    )

    result = simulate_management(
        trajectory=trajectory,
        date="2026-08-18",
        direction="LONG",
        entry_price=1000,
        config=config,
        runner_candles=candles,
    )

    assert (
        result["runner_result"]["pct"]
        == 100
    )

    assert (
        result["runner_result"]["executed"]
        is True
    )


def test_partial_position_runner():
    config = ManagementConfig(
        stop_points=170,
        partial_1_points=125,
        partial_1_pct=70,
        runner_enabled=True,
        runner_pct=30,
        runner_exit_rule="CANDLE_BREAK_M5",
    )

    validate_config(config)


def test_invalid_partial_plus_runner_percentage():
    config = ManagementConfig(
        stop_points=170,
        partial_1_points=100,
        partial_1_pct=80,
        runner_enabled=True,
        runner_pct=30,
        runner_exit_rule="CANDLE_BREAK_M5",
    )

    with pytest.raises(ValueError):
        validate_config(config)


def test_runner_requires_percentage():
    config = ManagementConfig(
        stop_points=170,
        runner_enabled=True,
        runner_pct=None,
        runner_exit_rule="CANDLE_BREAK_M5",
    )

    with pytest.raises(ValueError):
        validate_config(config)


def test_runner_requires_supported_rule():
    config = ManagementConfig(
        stop_points=170,
        runner_enabled=True,
        runner_pct=100,
        runner_exit_rule="INVALID_RULE",
    )

    with pytest.raises(ValueError):
        validate_config(config)


def test_runner_disabled_rejects_runner_pct():
    config = ManagementConfig(
        stop_points=170,
        runner_enabled=False,
        runner_pct=30,
    )

    with pytest.raises(ValueError):
        validate_config(config)