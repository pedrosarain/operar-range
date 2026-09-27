from __future__ import annotations

from operar_range.batch_execution import (
    BATCH_RESULT_SCHEMA,
)


def test_batch_schema_preserves_legacy_trade1_field():
    names = set(
        BATCH_RESULT_SCHEMA.names
    )

    assert (
        "total_weighted_points"
        in names
    )

    assert (
        "trade1_result_points"
        in names
    )


def test_batch_schema_contains_trade2_fields():
    names = set(
        BATCH_RESULT_SCHEMA.names
    )

    required = {
        "trade2_eligible",
        "trade2_occurred",
        "trade2_executed",
        "trade2_winner",
        "trade2_loser",
        "trade2_breakeven",
        "trade2_result_points",
        "consolidated_result_points",
        "trade2_direction",
        "trade2_trigger_level",
        "trade2_entry_timestamp",
        "trade2_entry_trade_number",
        "trade2_first_traded_price",
        "trade2_jumped_entry_level",
        "trade2_final_reason",
        "trade2_final_timestamp",
        "trade2_final_price",
        "trade2_mfe",
        "trade2_mae",
        "trade2_management_json",
        "lifecycle_version",
    }

    assert required.issubset(
        names
    )


def test_batch_schema_does_not_remove_legacy_fields():
    names = set(
        BATCH_RESULT_SCHEMA.names
    )

    legacy = {
        "execution_unit_id",
        "batch_id",
        "experiment_id",
        "management_name",
        "date",
        "trade_status",
        "direction",
        "stop_points",
        "partial_1_points",
        "partial_1_pct",
        "partial_2_points",
        "partial_2_pct",
        "partial_3_points",
        "partial_3_pct",
        "break_even",
        "break_even_after_partial",
        "runner",
        "runner_pct",
        "runner_rule",
        "final_target",
        "position_size",
        "total_weighted_points",
        "final_reason",
        "final_timestamp",
        "final_price",
        "mfe",
        "mae",
        "trajectory_sha256",
        "config_sha256",
        "motor_version",
        "rules_version",
    }

    assert legacy.issubset(
        names
    )
