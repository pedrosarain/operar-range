from __future__ import annotations

from operar_range.batch_executor import (
    _requires_runner_candles,
)
from operar_range.constraint_engine import (
    evaluate_trade2_effective_config,
)
from operar_range.experiment_generator import (
    assign_experiment_ids,
    generate_configurations,
)
from operar_range.trade_lifecycle_analytics import (
    calculate_consolidated_analytics,
    calculate_trade2_analytics,
)
from operar_range.trade2_configuration import (
    CONFIGURE,
    TRADE2_MANAGEMENT_CUSTOM,
    TRADE2_MANAGEMENT_INHERIT,
)


BASE_CONFIG = {
    "stop_points": 170.0,
    "partial_1_points": 125.0,
    "partial_1_pct": 70.0,
    "partial_2_points": None,
    "partial_2_pct": None,
    "partial_3_points": None,
    "partial_3_pct": None,
    "break_even_enabled": True,
    "break_even_after_partial": 1,
    "runner_enabled": False,
    "runner_pct": None,
    "runner_rule": None,
    "final_target_points": 400.0,
}


def _analytics_row(
    *,
    date: str,
    trade1: float,
) -> dict:
    return {
        "date": date,
        "trade1_result_points": trade1,
        "trade2_eligible": False,
        "trade2_occurred": False,
        "trade2_executed": False,
        "trade2_winner": False,
        "trade2_loser": False,
        "trade2_breakeven": False,
        "trade2_result_points": None,
        "consolidated_result_points": trade1,
        "trade2_management_json": None,
    }


COMMON = {
    "experiment_id": "EXP-STAGE21",
    "config_sha256": "cfg",
    "motor_version": "motor",
    "rules_version": "rules",
    "source_results_sha256": "results",
    "source_manifest_sha256": "manifest",
}


def test_hash_off_differs_from_on_inherit():
    off = generate_configurations(
        base_config=BASE_CONFIG,
        parameter_definition={},
        trade2_enabled=False,
        trade2_management_mode=(
            TRADE2_MANAGEMENT_INHERIT
        ),
    )

    on = generate_configurations(
        base_config=BASE_CONFIG,
        parameter_definition={},
        trade2_enabled=True,
        trade2_management_mode=(
            TRADE2_MANAGEMENT_INHERIT
        ),
    )

    assigned = assign_experiment_ids(
        configurations=[
            off[0],
            on[0],
        ]
    )

    assert (
        assigned[0][2]
        != assigned[1][2]
    )

    assert (
        assigned[0][0]
        != assigned[1][0]
    )


def test_legacy_hash_behavior_remains_distinct_from_explicit_stage21():
    legacy = generate_configurations(
        base_config=BASE_CONFIG,
        parameter_definition={},
    )

    explicit_on = generate_configurations(
        base_config=BASE_CONFIG,
        parameter_definition={},
        trade2_enabled=True,
        trade2_management_mode=(
            TRADE2_MANAGEMENT_INHERIT
        ),
    )

    assigned = assign_experiment_ids(
        configurations=[
            legacy[0],
            explicit_on[0],
        ]
    )

    assert (
        assigned[0][2]
        != assigned[1][2]
    )


def test_generator_custom_trade2_parameter_space():
    configs = generate_configurations(
        base_config=BASE_CONFIG,
        parameter_definition={
            "stop_points": {
                "values": [
                    165.0,
                    170.0,
                ]
            }
        },
        trade2_enabled=True,
        trade2_management_mode=(
            TRADE2_MANAGEMENT_CUSTOM
        ),
        trade2_base_overrides={
            "trade2_stop_mode": CONFIGURE,
        },
        trade2_parameter_definition={
            "trade2_stop_points": {
                "values": [
                    120.0,
                    125.0,
                ]
            }
        },
    )

    assert len(configs) == 4

    pairs = {
        (
            row["stop_points"],
            row["trade2_stop_points"],
        )
        for row in configs
    }

    assert pairs == {
        (165.0, 120.0),
        (165.0, 125.0),
        (170.0, 120.0),
        (170.0, 125.0),
    }


def test_constraint_rejects_trade2_off_with_override():
    row = {
        **BASE_CONFIG,
        "trade2_enabled": False,
        "trade2_management_mode": (
            TRADE2_MANAGEMENT_INHERIT
        ),
        "trade2_stop_mode": CONFIGURE,
        "trade2_stop_points": 120.0,
    }

    errors, warnings = (
        evaluate_trade2_effective_config(
            row
        )
    )

    assert warnings == []

    assert len(errors) == 1

    assert (
        errors[0].rule_code
        == "C015"
    )


def test_constraint_accepts_trade2_off_without_override():
    row = {
        **BASE_CONFIG,
        "trade2_enabled": False,
        "trade2_management_mode": (
            TRADE2_MANAGEMENT_INHERIT
        ),
    }

    errors, warnings = (
        evaluate_trade2_effective_config(
            row
        )
    )

    assert errors == []
    assert warnings == []


def test_batch_planner_trade2_off_does_not_require_trade2_runner():
    experiment = {
        **BASE_CONFIG,
        "trade2_enabled": False,
        "trade2_management_mode": (
            TRADE2_MANAGEMENT_INHERIT
        ),
        "trade2_runner_mode": "INHERIT",
    }

    assert (
        _requires_runner_candles(
            experiment
        )
        is False
    )


def test_batch_planner_trade1_runner_still_requires_candles_when_trade2_off():
    experiment = {
        **BASE_CONFIG,
        "runner_enabled": True,
        "runner_pct": 30.0,
        "runner_rule": "CANDLE_BREAK_M5",
        "trade2_enabled": False,
        "trade2_management_mode": (
            TRADE2_MANAGEMENT_INHERIT
        ),
    }

    assert (
        _requires_runner_candles(
            experiment
        )
        is True
    )


def test_analytics_trade2_off_has_zero_trade2_cycles():
    rows = [
        _analytics_row(
            date="2026-01-01",
            trade1=100.0,
        ),
        _analytics_row(
            date="2026-01-02",
            trade1=-170.0,
        ),
    ]

    trade2 = calculate_trade2_analytics(
        rows=rows,
        **COMMON,
    )

    consolidated = (
        calculate_consolidated_analytics(
            rows=rows,
            **COMMON,
        )
    )

    assert (
        trade2[
            "trade2_executed_count"
        ]
        == 0
    )

    assert (
        consolidated[
            "cycles_with_trade2"
        ]
        == 0
    )

    assert (
        consolidated[
            "total_result_points"
        ]
        == -70.0
    )

    assert (
        consolidated[
            "expectancy_points_per_cycle"
        ]
        == -35.0
    )


def test_stage21_generation_is_deterministic():
    kwargs = {
        "base_config": BASE_CONFIG,
        "parameter_definition": {
            "stop_points": {
                "values": [
                    165.0,
                    170.0,
                ]
            }
        },
        "trade2_enabled": True,
        "trade2_management_mode": (
            TRADE2_MANAGEMENT_CUSTOM
        ),
        "trade2_base_overrides": {
            "trade2_stop_mode": CONFIGURE,
        },
        "trade2_parameter_definition": {
            "trade2_stop_points": {
                "values": [
                    120.0,
                    125.0,
                ]
            }
        },
    }

    first = generate_configurations(
        **kwargs
    )

    second = generate_configurations(
        **kwargs
    )

    assert first == second

    first_ids = assign_experiment_ids(
        configurations=first
    )

    second_ids = assign_experiment_ids(
        configurations=second
    )

    assert first_ids == second_ids
