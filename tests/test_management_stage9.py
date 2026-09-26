from __future__ import annotations

import pytest

from operar_range.management import (
    ManagementConfig,
    simulate_management,
    validate_config,
)


def row(
    n,
    price,
    points,
    timestamp=None,
):
    if timestamp is None:
        timestamp = (
            f"2026-08-18T10:30:"
            f"{n:02d}-03:00"
        )

    return {
        "timestamp": timestamp,
        "trade_number": n,
        "price": float(price),
        "points_from_entry": (
            float(points)
        ),
        "favorable_excursion": (
            max(0.0, float(points))
        ),
        "adverse_excursion": (
            max(0.0, -float(points))
        ),
    }


def simulate_long(
    trajectory,
    config,
):
    return simulate_management(
        trajectory=trajectory,
        date="2026-08-18",
        direction="LONG",
        entry_price=1000.0,
        config=config,
    )


def test_long_target():
    result = simulate_long(
        [
            row(1, 1000, 0),
            row(2, 1100, 100),
        ],
        ManagementConfig(
            stop_points=100,
            final_target_points=100,
        ),
    )

    assert (
        result["final_reason"]
        == "FINAL_TARGET"
    )

    assert (
        result["total_weighted_points"]
        == 100
    )


def test_short_target():
    result = simulate_management(
        trajectory=[
            row(1, 1000, 0),
            row(2, 900, 100),
        ],
        date="2026-08-18",
        direction="SHORT",
        entry_price=1000.0,
        config=ManagementConfig(
            stop_points=100,
            final_target_points=100,
        ),
    )

    assert (
        result["final_reason"]
        == "FINAL_TARGET"
    )

    assert (
        result["total_weighted_points"]
        == 100
    )


def test_stop_before_partial():
    result = simulate_long(
        [
            row(1, 1000, 0),
            row(2, 890, -110),
            row(3, 1200, 200),
        ],
        ManagementConfig(
            stop_points=100,
            partial_1_points=100,
            partial_1_pct=50,
        ),
    )

    assert (
        result["final_reason"]
        == "STOP"
    )

    assert (
        result[
            "partial_1_result"
        ]["executed"]
        is False
    )


def test_partial_before_stop():
    result = simulate_long(
        [
            row(1, 1000, 0),
            row(2, 1100, 100),
            row(3, 890, -110),
        ],
        ManagementConfig(
            stop_points=100,
            partial_1_points=100,
            partial_1_pct=50,
        ),
    )

    assert (
        result[
            "partial_1_result"
        ]["executed"]
        is True
    )

    assert (
        result["final_reason"]
        == "STOP"
    )


def test_multiple_partials():
    result = simulate_long(
        [
            row(1, 1000, 0),
            row(2, 1100, 100),
            row(3, 1175, 175),
            row(4, 1200, 200),
        ],
        ManagementConfig(
            stop_points=100,
            partial_1_points=100,
            partial_1_pct=40,
            partial_2_points=175,
            partial_2_pct=30,
            partial_3_points=200,
            partial_3_pct=30,
        ),
    )

    assert (
        result[
            "partial_1_result"
        ]["executed"]
    )

    assert (
        result[
            "partial_2_result"
        ]["executed"]
    )

    assert (
        result[
            "partial_3_result"
        ]["executed"]
    )

    assert (
        result["remaining_position"]
        == 0
    )


def test_break_even_after_partial_1():
    result = simulate_long(
        [
            row(1, 1000, 0),
            row(2, 1125, 125),
            row(3, 1000, 0),
        ],
        ManagementConfig(
            stop_points=170,
            partial_1_points=125,
            partial_1_pct=70,
            break_even_enabled=True,
            break_even_after_partial=1,
        ),
    )

    assert (
        result["final_reason"]
        == "EXIT_BREAK_EVEN"
    )


def test_partial_tick_does_not_trigger_be():
    result = simulate_long(
        [
            row(1, 1000, 0),
            row(2, 1125, 125),
            row(3, 1400, 400),
        ],
        ManagementConfig(
            stop_points=170,
            partial_1_points=125,
            partial_1_pct=70,
            break_even_enabled=True,
            break_even_after_partial=1,
            final_target_points=400,
        ),
    )

    assert (
        result["final_reason"]
        == "FINAL_TARGET"
    )


def test_no_return_to_be():
    result = simulate_long(
        [
            row(1, 1000, 0),
            row(2, 1125, 125),
            row(3, 1200, 200),
        ],
        ManagementConfig(
            stop_points=170,
            partial_1_points=125,
            partial_1_pct=70,
            break_even_enabled=True,
            break_even_after_partial=1,
        ),
    )

    assert (
        result["final_reason"]
        == "END_OF_TRAJECTORY"
    )


def test_final_target():
    result = simulate_long(
        [
            row(1, 1000, 0),
            row(2, 1100, 100),
            row(3, 1400, 400),
        ],
        ManagementConfig(
            stop_points=170,
            partial_1_points=100,
            partial_1_pct=50,
            final_target_points=400,
        ),
    )

    assert (
        result["final_reason"]
        == "FINAL_TARGET"
    )


def test_end_of_trajectory():
    result = simulate_long(
        [
            row(1, 1000, 0),
            row(2, 1050, 50),
        ],
        ManagementConfig(
            stop_points=100,
        ),
    )

    assert (
        result["final_reason"]
        == "END_OF_TRAJECTORY"
    )


def test_jump_over_stop():
    result = simulate_long(
        [
            row(1, 1000, 0),
            row(2, 880, -120),
        ],
        ManagementConfig(
            stop_points=100,
        ),
    )

    event = result[
        "executions"
    ][0]

    assert (
        event[
            "trigger_level"
        ]
        == 900
    )

    assert (
        event[
            "first_traded_price_after_trigger"
        ]
        == 880
    )

    assert (
        event[
            "jumped_trigger_level"
        ]
        is True
    )

    assert (
        event["realized_points"]
        == -120
    )


def test_jump_over_target():
    result = simulate_long(
        [
            row(1, 1000, 0),
            row(2, 1120, 120),
        ],
        ManagementConfig(
            stop_points=100,
            final_target_points=100,
        ),
    )

    event = result[
        "executions"
    ][0]

    assert (
        event[
            "trigger_level"
        ]
        == 1100
    )

    assert (
        event[
            "first_traded_price_after_trigger"
        ]
        == 1120
    )

    assert (
        event[
            "jumped_trigger_level"
        ]
        is True
    )


def test_same_timestamp_trade_number_order():
    timestamp = (
        "2026-08-18T10:30:00.000000-03:00"
    )

    result = simulate_long(
        [
            row(
                1,
                1000,
                0,
                timestamp,
            ),
            row(
                2,
                1100,
                100,
                timestamp,
            ),
            row(
                3,
                900,
                -100,
                timestamp,
            ),
        ],
        ManagementConfig(
            stop_points=100,
            partial_1_points=100,
            partial_1_pct=50,
        ),
    )

    assert (
        result[
            "executions"
        ][0]["trade_number"]
        == 2
    )

    assert (
        result[
            "executions"
        ][1]["trade_number"]
        == 3
    )


def test_invalid_percentages():
    with pytest.raises(
        ValueError
    ):
        validate_config(
            ManagementConfig(
                stop_points=100,
                partial_1_points=100,
                partial_1_pct=70,
                partial_2_points=200,
                partial_2_pct=40,
            )
        )


def test_partial_missing_pct():
    with pytest.raises(
        ValueError
    ):
        validate_config(
            ManagementConfig(
                stop_points=100,
                partial_1_points=100,
            )
        )


def test_be_without_partial_invalid():
    with pytest.raises(
        ValueError
    ):
        validate_config(
            ManagementConfig(
                stop_points=100,
                break_even_enabled=True,
                break_even_after_partial=1,
            )
        )


def test_no_partial_config():
    validate_config(
        ManagementConfig(
            stop_points=100,
            final_target_points=200,
        )
    )


@pytest.mark.parametrize(
    "count",
    [
        1,
        2,
        3,
    ],
)
def test_one_two_three_partials(
    count,
):
    kwargs = {
        "stop_points": 100,
    }

    if count >= 1:
        kwargs.update(
            partial_1_points=100,
            partial_1_pct=20,
        )

    if count >= 2:
        kwargs.update(
            partial_2_points=150,
            partial_2_pct=20,
        )

    if count >= 3:
        kwargs.update(
            partial_3_points=200,
            partial_3_pct=20,
        )

    validate_config(
        ManagementConfig(
            **kwargs
        )
    )