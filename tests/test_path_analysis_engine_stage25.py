from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

import operar_range.path_analysis_engine as engine


def _trajectory(
    points: list[
        tuple[
            str,
            int,
            float,
        ]
    ],
) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "timestamp": [
                timestamp
                for (
                    timestamp,
                    _,
                    _,
                )
                in points
            ],
            "trade_number": [
                trade_number
                for (
                    _,
                    trade_number,
                    _,
                )
                in points
            ],
            "price": [
                price
                for (
                    _,
                    _,
                    price,
                )
                in points
            ],
        }
    )


def _analyze(
    trajectory: pl.DataFrame,
    *,
    trade: str = "TRADE_1",
    direction: str = "LONG",
    entry_price: float = 1000.0,
    entry_timestamp: str = (
        "2026-01-01T10:00:00-03:00"
    ),
    entry_trade_number: int = 10,
    trade2_eligible: bool = False,
    trade2_occurred: bool = False,
    trade2_executed: bool = False,
) -> list[dict]:
    return engine.analyze_trade_path(
        research_id="RES-TEST",
        dataset_id="DS-TEST",
        experiment_id="EXP-TEST",
        config_sha256="config",
        motor_version="motor",
        rules_version="rules",
        trajectory_sha256="trajectory",
        session_date="2026-01-01",
        trade=trade,
        direction=direction,
        entry_price=entry_price,
        entry_timestamp=(
            entry_timestamp
        ),
        entry_trade_number=(
            entry_trade_number
        ),
        trajectory=trajectory,
        trade2_eligible=(
            trade2_eligible
        ),
        trade2_occurred=(
            trade2_occurred
        ),
        trade2_executed=(
            trade2_executed
        ),
    )


def _row(
    rows: list[dict],
    *,
    target: int,
    stop: int,
) -> dict:
    matches = [
        row
        for row in rows
        if (
            row[
                "target_points"
            ]
            == target
            and row[
                "stop_points"
            ]
            == stop
        )
    ]

    assert len(matches) == 1

    return matches[0]


def test_contract_levels():
    assert engine.TARGET_LEVELS == (
        100,
        125,
        150,
        175,
        200,
        250,
        300,
        350,
        400,
        500,
        600,
        800,
        1000,
    )

    assert engine.STOP_LEVELS == (
        100,
        125,
        150,
        175,
        200,
    )


def test_output_cardinality():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    1010.0,
                ),
            ]
        )
    )

    assert len(rows) == (
        len(
            engine.TARGET_LEVELS
        )
        * len(
            engine.STOP_LEVELS
        )
    )


def test_chronological_order_is_required():
    trajectory = _trajectory(
        [
            (
                "2026-01-01T10:00:00-03:00",
                20,
                1000.0,
            ),
            (
                "2026-01-01T10:00:00-03:00",
                10,
                1010.0,
            ),
        ]
    )

    with pytest.raises(
        ValueError,
        match="not ordered chronologically",
    ):
        _analyze(
            trajectory,
            entry_trade_number=20,
        )


def test_exact_entry_is_required():
    trajectory = _trajectory(
        [
            (
                "2026-01-01T10:00:00-03:00",
                11,
                1000.0,
            ),
            (
                "2026-01-01T10:00:01-03:00",
                20,
                1100.0,
            ),
        ]
    )

    with pytest.raises(
        ValueError,
        match="Exact entry event not found",
    ):
        _analyze(
            trajectory,
            entry_trade_number=10,
        )


def test_entry_tick_does_not_count_as_zero_return():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    1100.0,
                ),
            ]
        )
    )

    row = _row(
        rows,
        target=100,
        stop=100,
    )

    assert (
        row[
            "first_zero_return_occurred"
        ]
        is False
    )

    assert (
        row[
            "first_zero_return_timestamp"
        ]
        is None
    )


def test_target_before_first_zero():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    1100.0,
                ),
                (
                    "2026-01-01T10:00:02-03:00",
                    30,
                    1000.0,
                ),
            ]
        )
    )

    row = _row(
        rows,
        target=100,
        stop=100,
    )

    assert (
        row[
            "target_reached"
        ]
        is True
    )

    assert row[
        "target_zero_relation"
    ] == (
        "TARGET_BEFORE_FIRST_ZERO_RETURN"
    )


def test_target_after_first_zero():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    990.0,
                ),
                (
                    "2026-01-01T10:00:02-03:00",
                    30,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:03-03:00",
                    40,
                    1100.0,
                ),
            ]
        )
    )

    row = _row(
        rows,
        target=100,
        stop=100,
    )

    assert row[
        "target_zero_relation"
    ] == (
        "TARGET_AFTER_FIRST_ZERO_RETURN"
    )


def test_zero_return_timestamp_and_trade_number():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    995.0,
                ),
                (
                    "2026-01-01T10:00:02-03:00",
                    30,
                    1000.0,
                ),
            ]
        )
    )

    row = rows[0]

    assert (
        row[
            "first_zero_return_occurred"
        ]
        is True
    )

    assert row[
        "first_zero_return_timestamp"
    ] == (
        "2026-01-01T10:00:02-03:00"
    )

    assert (
        row[
            "first_zero_return_trade_number"
        ]
        == 30
    )


def test_absence_of_zero_return():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    990.0,
                ),
                (
                    "2026-01-01T10:00:02-03:00",
                    30,
                    1100.0,
                ),
            ]
        )
    )

    assert all(
        row[
            "first_zero_return_occurred"
        ]
        is False
        for row
        in rows
    )


def test_stop_before_target():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    900.0,
                ),
                (
                    "2026-01-01T10:00:02-03:00",
                    30,
                    1100.0,
                ),
            ]
        )
    )

    row = _row(
        rows,
        target=100,
        stop=100,
    )

    assert (
        row[
            "stop_reached"
        ]
        is True
    )

    assert (
        row[
            "stop_before_target"
        ]
        is True
    )

    assert (
        row[
            "stop_after_target"
        ]
        is False
    )


def test_stop_after_target():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    1100.0,
                ),
                (
                    "2026-01-01T10:00:02-03:00",
                    30,
                    900.0,
                ),
            ]
        )
    )

    row = _row(
        rows,
        target=100,
        stop=100,
    )

    assert (
        row[
            "stop_before_target"
        ]
        is False
    )

    assert (
        row[
            "stop_after_target"
        ]
        is True
    )


def test_multiple_targets_use_first_chronological_hit():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    1125.0,
                ),
                (
                    "2026-01-01T10:00:02-03:00",
                    30,
                    1200.0,
                ),
            ]
        )
    )

    target100 = _row(
        rows,
        target=100,
        stop=100,
    )

    target125 = _row(
        rows,
        target=125,
        stop=100,
    )

    target150 = _row(
        rows,
        target=150,
        stop=100,
    )

    assert (
        target100[
            "target_trade_number"
        ]
        == 20
    )

    assert (
        target125[
            "target_trade_number"
        ]
        == 20
    )

    assert (
        target150[
            "target_trade_number"
        ]
        == 30
    )


def test_target_1000_plus():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    1995.0,
                ),
                (
                    "2026-01-01T10:00:02-03:00",
                    30,
                    2000.0,
                ),
            ]
        )
    )

    row = _row(
        rows,
        target=1000,
        stop=100,
    )

    assert (
        row[
            "target_label"
        ]
        == "1000+"
    )

    assert (
        row[
            "target_reached"
        ]
        is True
    )

    assert (
        row[
            "target_trade_number"
        ]
        == 30
    )


def test_short_direction():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    900.0,
                ),
                (
                    "2026-01-01T10:00:02-03:00",
                    30,
                    1100.0,
                ),
            ]
        ),
        direction="SHORT",
    )

    row = _row(
        rows,
        target=100,
        stop=100,
    )

    assert (
        row[
            "target_reached"
        ]
        is True
    )

    assert (
        row[
            "stop_reached"
        ]
        is True
    )

    assert (
        row[
            "target_trade_number"
        ]
        == 20
    )

    assert (
        row[
            "stop_trade_number"
        ]
        == 30
    )


def test_trade2_absent_flags_are_preserved():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    1100.0,
                ),
            ]
        )
    )

    assert all(
        row[
            "trade2_eligible"
        ]
        is False
        and row[
            "trade2_occurred"
        ]
        is False
        and row[
            "trade2_executed"
        ]
        is False
        for row
        in rows
    )


def test_trade2_existing_repeats_same_path_structure():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    990.0,
                ),
                (
                    "2026-01-01T10:00:02-03:00",
                    30,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:03-03:00",
                    40,
                    1200.0,
                ),
            ]
        ),
        trade="TRADE_2",
        trade2_eligible=True,
        trade2_occurred=True,
        trade2_executed=True,
    )

    row = _row(
        rows,
        target=200,
        stop=100,
    )

    assert (
        row[
            "trade"
        ]
        == "TRADE_2"
    )

    assert (
        row[
            "trade2_eligible"
        ]
        is True
    )

    assert (
        row[
            "trade2_occurred"
        ]
        is True
    )

    assert (
        row[
            "trade2_executed"
        ]
        is True
    )

    assert (
        row[
            "target_reached"
        ]
        is True
    )

    assert row[
        "target_zero_relation"
    ] == (
        "TARGET_AFTER_FIRST_ZERO_RETURN"
    )


def test_determinism():
    trajectory = _trajectory(
        [
            (
                "2026-01-01T10:00:00-03:00",
                10,
                1000.0,
            ),
            (
                "2026-01-01T10:00:01-03:00",
                20,
                1100.0,
            ),
            (
                "2026-01-01T10:00:02-03:00",
                30,
                900.0,
            ),
        ]
    )

    first = _analyze(
        trajectory
    )

    second = _analyze(
        trajectory
    )

    assert first == second


def test_idempotence_and_input_not_mutated():
    trajectory = _trajectory(
        [
            (
                "2026-01-01T10:00:00-03:00",
                10,
                1000.0,
            ),
            (
                "2026-01-01T10:00:01-03:00",
                20,
                1100.0,
            ),
            (
                "2026-01-01T10:00:02-03:00",
                30,
                900.0,
            ),
        ]
    )

    before = trajectory.clone()

    first = _analyze(
        trajectory
    )

    second = _analyze(
        trajectory
    )

    assert first == second

    assert trajectory.equals(
        before
    )


def test_all_lineage_fields_are_present():
    rows = _analyze(
        _trajectory(
            [
                (
                    "2026-01-01T10:00:00-03:00",
                    10,
                    1000.0,
                ),
                (
                    "2026-01-01T10:00:01-03:00",
                    20,
                    1100.0,
                ),
            ]
        )
    )

    row = rows[0]

    assert (
        row[
            "research_id"
        ]
        == "RES-TEST"
    )

    assert (
        row[
            "dataset_id"
        ]
        == "DS-TEST"
    )

    assert (
        row[
            "experiment_id"
        ]
        == "EXP-TEST"
    )

    assert (
        row[
            "config_sha256"
        ]
        == "config"
    )

    assert (
        row[
            "trajectory_sha256"
        ]
        == "trajectory"
    )

    assert row[
        "path_analysis_version"
    ] == (
        engine.PATH_ANALYSIS_ENGINE_VERSION
    )


def test_schema_contains_required_stage25_fields():
    required = {
        "research_id",
        "dataset_id",
        "experiment_id",
        "session_date",
        "direction",
        "entry_price",
        "first_zero_return_occurred",
        "first_zero_return_timestamp",
        "first_zero_return_trade_number",
        "target_points",
        "target_reached",
        "target_timestamp",
        "target_trade_number",
        "target_zero_relation",
        "stop_points",
        "stop_reached",
        "stop_timestamp",
        "stop_trade_number",
        "stop_before_target",
        "stop_after_target",
    }

    assert required.issubset(
        set(
            engine.PATH_ANALYSIS_SCHEMA.names
        )
    )


def test_analysis_function_is_read_only(
    tmp_path: Path,
):
    trajectory = _trajectory(
        [
            (
                "2026-01-01T10:00:00-03:00",
                10,
                1000.0,
            ),
            (
                "2026-01-01T10:00:01-03:00",
                20,
                1100.0,
            ),
        ]
    )

    before = list(
        tmp_path.rglob(
            "*"
        )
    )

    _analyze(
        trajectory
    )

    after = list(
        tmp_path.rglob(
            "*"
        )
    )

    assert before == after
