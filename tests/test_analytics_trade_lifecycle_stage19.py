from __future__ import annotations

from operar_range.analytics import (
    METRICS_SCHEMA,
    calculate_metrics,
)


def _row(
    *,
    date: str,
    trade1: float | None,
    trade2: float | None,
    trade2_occurred: bool,
    trade2_winner: bool = False,
    trade2_loser: bool = False,
    trade2_breakeven: bool = False,
) -> dict:
    return {
        "date": date,
        "trade_status": (
            "TRADE_1"
            if trade1 is not None
            else "NO_TRADE_1"
        ),
        "total_weighted_points": (
            trade1
        ),
        "trade1_result_points": (
            trade1
        ),
        "trade2_occurred": (
            trade2_occurred
        ),
        "trade2_executed": (
            trade2_occurred
        ),
        "trade2_winner": (
            trade2_winner
        ),
        "trade2_loser": (
            trade2_loser
        ),
        "trade2_breakeven": (
            trade2_breakeven
        ),
        "trade2_result_points": (
            trade2
        ),
        "consolidated_result_points": (
            (
                trade1 + trade2
            )
            if (
                trade1 is not None
                and trade2 is not None
            )
            else trade1
        ),
    }


def test_metrics_schema_contains_stage19_fields():
    names = set(
        METRICS_SCHEMA.names
    )

    required = {
        "trade2_occurred_count",
        "trade2_executed_count",
        "trade2_winning_count",
        "trade2_losing_count",
        "trade2_breakeven_count",
        "trade2_total_result_points",
        "consolidated_total_result_points",
    }

    assert required.issubset(
        names
    )


def test_legacy_total_weighted_points_remains_trade1_only():
    rows = [
        _row(
            date="2026-01-01",
            trade1=-100.0,
            trade2=200.0,
            trade2_occurred=True,
            trade2_winner=True,
        ),
        _row(
            date="2026-01-02",
            trade1=50.0,
            trade2=None,
            trade2_occurred=False,
        ),
    ]

    metrics = calculate_metrics(
        rows=rows,
        experiment_id="EXP-1",
        config_sha256="cfg",
        motor_version="motor",
        rules_version="rules",
        source_results_sha256="results",
        source_manifest_sha256="manifest",
    )

    assert (
        metrics[
            "total_weighted_points"
        ]
        == -50.0
    )

    assert (
        metrics[
            "trade2_total_result_points"
        ]
        == 200.0
    )

    assert (
        metrics[
            "consolidated_total_result_points"
        ]
        == 150.0
    )


def test_trade2_counts_are_descriptive_only():
    rows = [
        _row(
            date="2026-01-01",
            trade1=-100.0,
            trade2=100.0,
            trade2_occurred=True,
            trade2_breakeven=True,
        ),
        _row(
            date="2026-01-02",
            trade1=-100.0,
            trade2=200.0,
            trade2_occurred=True,
            trade2_winner=True,
        ),
        _row(
            date="2026-01-03",
            trade1=-100.0,
            trade2=-100.0,
            trade2_occurred=True,
            trade2_loser=True,
        ),
        _row(
            date="2026-01-04",
            trade1=100.0,
            trade2=None,
            trade2_occurred=False,
        ),
    ]

    metrics = calculate_metrics(
        rows=rows,
        experiment_id="EXP-1",
        config_sha256="cfg",
        motor_version="motor",
        rules_version="rules",
        source_results_sha256="results",
        source_manifest_sha256="manifest",
    )

    assert (
        metrics[
            "trade2_occurred_count"
        ]
        == 3
    )

    assert (
        metrics[
            "trade2_executed_count"
        ]
        == 3
    )

    assert (
        metrics[
            "trade2_winning_count"
        ]
        == 1
    )

    assert (
        metrics[
            "trade2_losing_count"
        ]
        == 1
    )

    assert (
        metrics[
            "trade2_breakeven_count"
        ]
        == 1
    )
