from __future__ import annotations

from copy import deepcopy

from operar_range.management import (
    ManagementConfig,
    simulate_management,
)
from operar_range.trade_lifecycle import (
    TradeLifecycleConfig,
    simulate_trade_lifecycle,
)


def _row(
    *,
    timestamp: str,
    trade_number: int,
    price: float,
) -> dict:
    return {
        "timestamp": timestamp,
        "trade_number": trade_number,
        "price": price,
        "points_from_entry": 0.0,
        "favorable_excursion": 0.0,
        "adverse_excursion": 0.0,
    }


def _config(
    *,
    stop: float = 100.0,
    target: float | None = 100.0,
) -> ManagementConfig:
    return ManagementConfig(
        stop_points=stop,
        partial_1_points=None,
        partial_1_pct=None,
        partial_2_points=None,
        partial_2_pct=None,
        partial_3_points=None,
        partial_3_pct=None,
        break_even_enabled=False,
        break_even_after_partial=None,
        runner_enabled=False,
        runner_pct=None,
        runner_exit_rule=None,
        final_target_points=target,
        position_size=1.0,
    )


def _trade1_stop(
    *,
    direction: str = "LONG",
    entry_price: float = 1000.0,
    stop_price: float = 900.0,
) -> dict:
    trajectory = [
        _row(
            timestamp="2026-01-01T10:30:00-03:00",
            trade_number=10,
            price=entry_price,
        ),
        _row(
            timestamp="2026-01-01T10:31:00-03:00",
            trade_number=20,
            price=stop_price,
        ),
    ]

    return simulate_management(
        trajectory=trajectory,
        date="2026-01-01",
        direction=direction,
        entry_price=entry_price,
        config=_config(
            stop=100.0,
            target=100.0,
        ),
    )


def test_trade2_does_not_exist_without_trade1():
    result = simulate_trade_lifecycle(
        trajectory=[],
        date="2026-01-01",
        trade1_status="NO_TRADE_1",
        direction=None,
        entry_price=None,
        management_config=_config(),
        trade1_management=None,
    )

    assert result["trade2_occurred"] is False
    assert result["trade2_executed"] is False
    assert result["trade2"]["reason"] == "NO_TRADE_1"
    assert result["consolidated_result_points"] is None


def test_trade2_is_eligible_after_stop():
    trade1 = _trade1_stop()

    trajectory = [
        _row(
            timestamp="2026-01-01T10:30:00-03:00",
            trade_number=10,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:31:00-03:00",
            trade_number=20,
            price=900.0,
        ),
        _row(
            timestamp="2026-01-01T10:32:00-03:00",
            trade_number=30,
            price=950.0,
        ),
    ]

    result = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=_config(),
        trade1_management=trade1,
    )

    assert result["trade2"]["eligible"] is True
    assert result["trade2_occurred"] is False
    assert result["trade2"]["reason"] == "TRIGGER_NOT_REVISITED"


def test_trade2_not_eligible_after_non_stop():
    config = _config(
        stop=100.0,
        target=100.0,
    )

    trade1 = simulate_management(
        trajectory=[
            _row(
                timestamp="2026-01-01T10:30:00-03:00",
                trade_number=10,
                price=1000.0,
            ),
            _row(
                timestamp="2026-01-01T10:31:00-03:00",
                trade_number=20,
                price=1100.0,
            ),
        ],
        date="2026-01-01",
        direction="LONG",
        entry_price=1000.0,
        config=config,
    )

    result = simulate_trade_lifecycle(
        trajectory=[
            _row(
                timestamp="2026-01-01T10:30:00-03:00",
                trade_number=10,
                price=1000.0,
            ),
            _row(
                timestamp="2026-01-01T10:31:00-03:00",
                trade_number=20,
                price=1100.0,
            ),
        ],
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=config,
        trade1_management=trade1,
    )

    assert result["trade2"]["eligible"] is False
    assert result["trade2_occurred"] is False
    assert (
        result["trade2"]["reason"]
        == "TRADE_1_RESULT_NOT_ELIGIBLE"
    )


def test_trade2_uses_same_trigger():
    trade1 = _trade1_stop()

    trajectory = [
        _row(
            timestamp="2026-01-01T10:30:00-03:00",
            trade_number=10,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:31:00-03:00",
            trade_number=20,
            price=900.0,
        ),
        _row(
            timestamp="2026-01-01T10:32:00-03:00",
            trade_number=30,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:33:00-03:00",
            trade_number=40,
            price=1100.0,
        ),
    ]

    result = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=_config(),
        trade1_management=trade1,
    )

    assert result["trade2"]["trigger_level"] == 1000.0
    assert result["trade2"]["entry_trade_number"] == 30


def test_trade2_uses_same_direction():
    trade1 = _trade1_stop(
        direction="SHORT",
        entry_price=1000.0,
        stop_price=1100.0,
    )

    trajectory = [
        _row(
            timestamp="2026-01-01T10:30:00-03:00",
            trade_number=10,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:31:00-03:00",
            trade_number=20,
            price=1100.0,
        ),
        _row(
            timestamp="2026-01-01T10:32:00-03:00",
            trade_number=30,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:33:00-03:00",
            trade_number=40,
            price=900.0,
        ),
    ]

    result = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="SHORT",
        entry_price=1000.0,
        management_config=_config(),
        trade1_management=trade1,
    )

    assert result["trade2"]["direction"] == "SHORT"


def test_trade2_winner():
    trade1 = _trade1_stop()

    trajectory = [
        _row(
            timestamp="2026-01-01T10:30:00-03:00",
            trade_number=10,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:31:00-03:00",
            trade_number=20,
            price=900.0,
        ),
        _row(
            timestamp="2026-01-01T10:32:00-03:00",
            trade_number=30,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:33:00-03:00",
            trade_number=40,
            price=1100.0,
        ),
    ]

    result = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=_config(),
        trade1_management=trade1,
    )

    assert result["trade2_winner"] is True
    assert result["trade2_loser"] is False
    assert result["trade2_breakeven"] is False
    assert result["trade2_result_points"] > 0


def test_trade2_loser():
    trade1 = _trade1_stop()

    trajectory = [
        _row(
            timestamp="2026-01-01T10:30:00-03:00",
            trade_number=10,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:31:00-03:00",
            trade_number=20,
            price=900.0,
        ),
        _row(
            timestamp="2026-01-01T10:32:00-03:00",
            trade_number=30,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:33:00-03:00",
            trade_number=40,
            price=900.0,
        ),
    ]

    result = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=_config(),
        trade1_management=trade1,
    )

    assert result["trade2_loser"] is True
    assert result["trade2_result_points"] < 0


def test_trade2_breakeven():
    config = ManagementConfig(
        stop_points=100.0,
        partial_1_points=50.0,
        partial_1_pct=100.0,
        partial_2_points=None,
        partial_2_pct=None,
        partial_3_points=None,
        partial_3_pct=None,
        break_even_enabled=True,
        break_even_after_partial=1,
        runner_enabled=False,
        runner_pct=None,
        runner_exit_rule=None,
        final_target_points=None,
        position_size=1.0,
    )

    trade1 = _trade1_stop()

    trajectory = [
        _row(
            timestamp="2026-01-01T10:30:00-03:00",
            trade_number=10,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:31:00-03:00",
            trade_number=20,
            price=900.0,
        ),
        _row(
            timestamp="2026-01-01T10:32:00-03:00",
            trade_number=30,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:33:00-03:00",
            trade_number=40,
            price=1050.0,
        ),
    ]

    result = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=config,
        trade1_management=trade1,
    )

    assert result["trade2_executed"] is True


def test_consolidated_result_is_trade1_plus_trade2():
    trade1 = _trade1_stop()

    trajectory = [
        _row(
            timestamp="2026-01-01T10:30:00-03:00",
            trade_number=10,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:31:00-03:00",
            trade_number=20,
            price=900.0,
        ),
        _row(
            timestamp="2026-01-01T10:32:00-03:00",
            trade_number=30,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:33:00-03:00",
            trade_number=40,
            price=1100.0,
        ),
    ]

    result = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=_config(),
        trade1_management=trade1,
    )

    expected = (
        float(
            trade1[
                "total_weighted_points"
            ]
        )
        + float(
            result[
                "trade2_result_points"
            ]
        )
    )

    assert (
        result[
            "consolidated_result_points"
        ]
        == expected
    )


def test_lifecycle_is_deterministic():
    trade1 = _trade1_stop()

    trajectory = [
        _row(
            timestamp="2026-01-01T10:30:00-03:00",
            trade_number=10,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:31:00-03:00",
            trade_number=20,
            price=900.0,
        ),
        _row(
            timestamp="2026-01-01T10:32:00-03:00",
            trade_number=30,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:33:00-03:00",
            trade_number=40,
            price=1100.0,
        ),
    ]

    kwargs = {
        "trajectory": trajectory,
        "date": "2026-01-01",
        "trade1_status": "TRADE_1",
        "direction": "LONG",
        "entry_price": 1000.0,
        "management_config": _config(),
        "trade1_management": trade1,
    }

    first = simulate_trade_lifecycle(
        **deepcopy(
            kwargs
        )
    )

    second = simulate_trade_lifecycle(
        **deepcopy(
            kwargs
        )
    )

    assert first == second


def test_eligibility_is_configurable():
    config = _config()

    trade1 = simulate_management(
        trajectory=[
            _row(
                timestamp="2026-01-01T10:30:00-03:00",
                trade_number=10,
                price=1000.0,
            ),
            _row(
                timestamp="2026-01-01T10:31:00-03:00",
                trade_number=20,
                price=1100.0,
            ),
        ],
        date="2026-01-01",
        direction="LONG",
        entry_price=1000.0,
        config=config,
    )

    result = simulate_trade_lifecycle(
        trajectory=[
            _row(
                timestamp="2026-01-01T10:30:00-03:00",
                trade_number=10,
                price=1000.0,
            ),
            _row(
                timestamp="2026-01-01T10:31:00-03:00",
                trade_number=20,
                price=1100.0,
            ),
            _row(
                timestamp="2026-01-01T10:32:00-03:00",
                trade_number=30,
                price=1000.0,
            ),
        ],
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=config,
        trade1_management=trade1,
        lifecycle_config=TradeLifecycleConfig(
            eligible_after=(
                "FINAL_TARGET",
            )
        ),
    )

    assert result["trade2"]["eligible"] is True


def test_trade2_breakeven_result():
    trade1 = _trade1_stop()

    config = ManagementConfig(
        stop_points=170.0,
        partial_1_points=125.0,
        partial_1_pct=70.0,
        partial_2_points=None,
        partial_2_pct=None,
        partial_3_points=None,
        partial_3_pct=None,
        break_even_enabled=True,
        break_even_after_partial=1,
        runner_enabled=False,
        runner_pct=None,
        runner_exit_rule=None,
        final_target_points=None,
        position_size=100.0,
    )

    trajectory = [
        _row(
            timestamp="2026-01-01T10:30:00-03:00",
            trade_number=10,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:31:00-03:00",
            trade_number=20,
            price=900.0,
        ),
        _row(
            timestamp="2026-01-01T10:32:00-03:00",
            trade_number=30,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:33:00-03:00",
            trade_number=40,
            price=1125.0,
        ),
        _row(
            timestamp="2026-01-01T10:34:00-03:00",
            trade_number=50,
            price=1000.0,
        ),
    ]

    result = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=config,
        trade1_management=trade1,
    )

    assert result["trade2_executed"] is True
    assert result["trade2"]["final_reason"] == "EXIT_BREAK_EVEN"

    expected_trade2 = (
        125.0
        * 70.0
        / 100.0
    )

    assert result["trade2_result_points"] == expected_trade2
    assert result["trade2_winner"] is True
    assert result["trade2_breakeven"] is False


def test_trade2_runner_reuses_management_engine():
    from datetime import datetime, timedelta

    from operar_range.runner import (
        M5Candle,
    )

    trade1 = _trade1_stop()

    config = ManagementConfig(
        stop_points=170.0,
        partial_1_points=125.0,
        partial_1_pct=70.0,
        partial_2_points=None,
        partial_2_pct=None,
        partial_3_points=None,
        partial_3_pct=None,
        break_even_enabled=True,
        break_even_after_partial=1,
        runner_enabled=True,
        runner_pct=30.0,
        runner_exit_rule="CANDLE_BREAK_M5",
        final_target_points=None,
        position_size=100.0,
    )

    def candle(
        start: str,
        open_: float,
        high: float,
        low: float,
        close: float,
        first_trade_number: int,
        last_trade_number: int,
    ) -> M5Candle:
        start_dt = datetime.fromisoformat(
            start
        )

        return M5Candle(
            start=start_dt,
            end=(
                start_dt
                + timedelta(
                    minutes=5
                )
            ),
            open=open_,
            high=high,
            low=low,
            close=close,
            first_trade_number=(
                first_trade_number
            ),
            last_trade_number=(
                last_trade_number
            ),
        )

    trajectory = [
        _row(
            timestamp="2026-01-01T10:29:00-03:00",
            trade_number=10,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:29:30-03:00",
            trade_number=20,
            price=900.0,
        ),
        _row(
            timestamp="2026-01-01T10:30:00-03:00",
            trade_number=30,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:31:00-03:00",
            trade_number=40,
            price=1125.0,
        ),
        _row(
            timestamp="2026-01-01T10:40:30-03:00",
            trade_number=50,
            price=1080.0,
        ),
    ]

    candles = [
        candle(
            "2026-01-01T10:30:00-03:00",
            1000.0,
            1150.0,
            990.0,
            1120.0,
            30,
            40,
        ),
        candle(
            "2026-01-01T10:35:00-03:00",
            1120.0,
            1200.0,
            1100.0,
            1180.0,
            41,
            45,
        ),
        candle(
            "2026-01-01T10:40:00-03:00",
            1180.0,
            1190.0,
            1070.0,
            1080.0,
            46,
            50,
        ),
    ]

    result = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=config,
        trade1_management=trade1,
        runner_candles=candles,
    )

    assert result["trade2_executed"] is True
    assert result["trade2"]["management"]["runner_result"]["executed"] is True
    assert result["trade2"]["final_reason"] == "EXIT_RUNNER_CANDLE"
    assert (
        result["trade2"]["management"]["runner_result"]["trigger_level"]
        == 1100.0
    )


def test_lifecycle_input_is_idempotent_and_not_mutated():
    trade1 = _trade1_stop()

    trajectory = [
        _row(
            timestamp="2026-01-01T10:30:00-03:00",
            trade_number=10,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:31:00-03:00",
            trade_number=20,
            price=900.0,
        ),
        _row(
            timestamp="2026-01-01T10:32:00-03:00",
            trade_number=30,
            price=1000.0,
        ),
        _row(
            timestamp="2026-01-01T10:33:00-03:00",
            trade_number=40,
            price=1100.0,
        ),
    ]

    original_trajectory = deepcopy(
        trajectory
    )

    original_trade1 = deepcopy(
        trade1
    )

    first = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=_config(),
        trade1_management=trade1,
    )

    second = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-01-01",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=_config(),
        trade1_management=trade1,
    )

    assert first == second
    assert trajectory == original_trajectory
    assert trade1 == original_trade1




def test_trade2_disabled_does_not_evaluate_eligibility():
    trajectory = [
        {
            "timestamp": "2026-08-18T10:30:00-03:00",
            "trade_number": 1,
            "price": 1000.0,
        },
        {
            "timestamp": "2026-08-18T10:31:00-03:00",
            "trade_number": 2,
            "price": 830.0,
        },
        {
            "timestamp": "2026-08-18T10:32:00-03:00",
            "trade_number": 3,
            "price": 1000.0,
        },
        {
            "timestamp": "2026-08-18T10:33:00-03:00",
            "trade_number": 4,
            "price": 1200.0,
        },
    ]

    config = ManagementConfig(
        stop_points=170.0,
        final_target_points=400.0,
    )

    trade1_management = {
        "final_reason": "STOP",
        "total_weighted_points": -170.0,
        "executions": [
            {
                "timestamp": (
                    "2026-08-18T10:31:00-03:00"
                ),
                "trade_number": 2,
            }
        ],
    }

    result = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-08-18",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=config,
        trade1_management=(
            trade1_management
        ),
        lifecycle_config=(
            TradeLifecycleConfig(
                trade2_enabled=False,
                eligible_after=(
                    "STOP",
                ),
            )
        ),
    )

    assert (
        result["trade2"]["eligible"]
        is False
    )

    assert (
        result["trade2"]["reason"]
        == "TRADE2_DISABLED"
    )

    assert (
        result["trade2_occurred"]
        is False
    )

    assert (
        result["trade2_executed"]
        is False
    )

    assert (
        result["trade2_result_points"]
        is None
    )

    assert (
        result[
            "consolidated_result_points"
        ]
        == -170.0
    )


def test_trade2_disabled_ignores_revisited_trigger():
    trajectory = [
        {
            "timestamp": "2026-08-18T10:30:00-03:00",
            "trade_number": 1,
            "price": 1000.0,
        },
        {
            "timestamp": "2026-08-18T10:31:00-03:00",
            "trade_number": 2,
            "price": 830.0,
        },
        {
            "timestamp": "2026-08-18T10:32:00-03:00",
            "trade_number": 3,
            "price": 1000.0,
        },
        {
            "timestamp": "2026-08-18T10:33:00-03:00",
            "trade_number": 4,
            "price": 1400.0,
        },
    ]

    config = ManagementConfig(
        stop_points=170.0,
        final_target_points=400.0,
    )

    trade1_management = {
        "final_reason": "STOP",
        "total_weighted_points": -170.0,
        "executions": [
            {
                "timestamp": (
                    "2026-08-18T10:31:00-03:00"
                ),
                "trade_number": 2,
            }
        ],
    }

    result = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-08-18",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=config,
        trade1_management=(
            trade1_management
        ),
        lifecycle_config=(
            TradeLifecycleConfig(
                trade2_enabled=False,
            )
        ),
    )

    assert (
        result["trade2"]["exists"]
        is False
    )

    assert (
        result["trade2"]["entry_timestamp"]
        is None
    )

    assert (
        result["trade2"]["management"]
        is None
    )

    assert (
        result["trade2_result_points"]
        is None
    )


def test_trade2_enabled_preserves_historical_behavior():
    trajectory = [
        {
            "timestamp": "2026-08-18T10:30:00-03:00",
            "trade_number": 1,
            "price": 1000.0,
        },
        {
            "timestamp": "2026-08-18T10:31:00-03:00",
            "trade_number": 2,
            "price": 830.0,
        },
        {
            "timestamp": "2026-08-18T10:32:00-03:00",
            "trade_number": 3,
            "price": 1000.0,
        },
        {
            "timestamp": "2026-08-18T10:33:00-03:00",
            "trade_number": 4,
            "price": 1400.0,
        },
    ]

    config = ManagementConfig(
        stop_points=170.0,
        final_target_points=400.0,
    )

    trade1_management = {
        "final_reason": "STOP",
        "total_weighted_points": -170.0,
        "executions": [
            {
                "timestamp": (
                    "2026-08-18T10:31:00-03:00"
                ),
                "trade_number": 2,
            }
        ],
    }

    explicit_on = simulate_trade_lifecycle(
        trajectory=trajectory,
        date="2026-08-18",
        trade1_status="TRADE_1",
        direction="LONG",
        entry_price=1000.0,
        management_config=config,
        trade1_management=(
            trade1_management
        ),
        lifecycle_config=(
            TradeLifecycleConfig(
                trade2_enabled=True,
            )
        ),
    )

    historical_default = (
        simulate_trade_lifecycle(
            trajectory=trajectory,
            date="2026-08-18",
            trade1_status="TRADE_1",
            direction="LONG",
            entry_price=1000.0,
            management_config=config,
            trade1_management=(
                trade1_management
            ),
        )
    )

    assert explicit_on == historical_default
