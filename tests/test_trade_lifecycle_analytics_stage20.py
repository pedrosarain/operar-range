from __future__ import annotations

from copy import deepcopy

import pytest

from operar_range.trade_lifecycle_analytics import (
    calculate_comparison,
    calculate_consolidated_analytics,
    calculate_trade2_analytics,
)


def _row(
    *,
    date: str,
    trade1: float,
    trade2: float | None,
    trade2_eligible: bool,
    trade2_executed: bool,
    trade2_winner: bool = False,
    trade2_loser: bool = False,
    trade2_breakeven: bool = False,
    trade2_management_json: str | None = None,
) -> dict:
    consolidated = (
        trade1
        if trade2 is None
        else trade1 + trade2
    )

    return {
        "date": date,
        "trade1_result_points": trade1,
        "trade2_eligible": trade2_eligible,
        "trade2_occurred": trade2_executed,
        "trade2_executed": trade2_executed,
        "trade2_winner": trade2_winner,
        "trade2_loser": trade2_loser,
        "trade2_breakeven": trade2_breakeven,
        "trade2_result_points": trade2,
        "consolidated_result_points": consolidated,
        "trade2_management_json": (
            trade2_management_json
        ),
    }


COMMON = {
    "experiment_id": "EXP-1",
    "config_sha256": "cfg",
    "motor_version": "motor",
    "rules_version": "rules",
    "source_results_sha256": "results",
    "source_manifest_sha256": "manifest",
}


def test_trade2_analytics_without_trade2():
    rows = [
        _row(
            date="2026-01-01",
            trade1=100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
        _row(
            date="2026-01-02",
            trade1=-100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
    ]

    result = calculate_trade2_analytics(
        rows=rows,
        **COMMON,
    )

    assert result["trade2_eligible_count"] == 0
    assert result["trade2_occurred_count"] == 0
    assert result["trade2_executed_count"] == 0
    assert result["trade2_weighted_result_points"] == 0.0


def test_trade2_analytics_with_trade2():
    rows = [
        _row(
            date="2026-01-01",
            trade1=-100.0,
            trade2=150.0,
            trade2_eligible=True,
            trade2_executed=True,
            trade2_winner=True,
        ),
        _row(
            date="2026-01-02",
            trade1=-100.0,
            trade2=-50.0,
            trade2_eligible=True,
            trade2_executed=True,
            trade2_loser=True,
        ),
        _row(
            date="2026-01-03",
            trade1=-100.0,
            trade2=0.0,
            trade2_eligible=True,
            trade2_executed=True,
            trade2_breakeven=True,
        ),
    ]

    result = calculate_trade2_analytics(
        rows=rows,
        **COMMON,
    )

    assert result["trade2_eligible_count"] == 3
    assert result["trade2_executed_count"] == 3
    assert result["trade2_winning_count"] == 1
    assert result["trade2_losing_count"] == 1
    assert result["trade2_breakeven_count"] == 1
    assert result["trade2_weighted_result_points"] == 100.0


def test_recovery_requires_full_cycle_recovery():
    rows = [
        _row(
            date="2026-01-01",
            trade1=-170.0,
            trade2=100.0,
            trade2_eligible=True,
            trade2_executed=True,
            trade2_winner=True,
        ),
        _row(
            date="2026-01-02",
            trade1=-170.0,
            trade2=170.0,
            trade2_eligible=True,
            trade2_executed=True,
            trade2_winner=True,
        ),
        _row(
            date="2026-01-03",
            trade1=-170.0,
            trade2=250.0,
            trade2_eligible=True,
            trade2_executed=True,
            trade2_winner=True,
        ),
    ]

    result = calculate_consolidated_analytics(
        rows=rows,
        **COMMON,
    )

    assert result["cycles_with_trade2"] == 3
    assert result["recovered_cycle_count"] == 2
    assert result["recovery_pct"] == pytest.approx(
        2 / 3 * 100.0
    )


def test_consolidated_expectancy():
    rows = [
        _row(
            date="2026-01-01",
            trade1=-100.0,
            trade2=200.0,
            trade2_eligible=True,
            trade2_executed=True,
            trade2_winner=True,
        ),
        _row(
            date="2026-01-02",
            trade1=100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
        _row(
            date="2026-01-03",
            trade1=-50.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
    ]

    result = calculate_consolidated_analytics(
        rows=rows,
        **COMMON,
    )

    # Consolidado: +100, +100, -50 = +150 / 3
    assert result["total_result_points"] == 150.0
    assert result["expectancy_points_per_cycle"] == 50.0
    assert result["average_cycle_points"] == 50.0


def test_consolidated_profit_factor():
    rows = [
        _row(
            date="2026-01-01",
            trade1=100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
        _row(
            date="2026-01-02",
            trade1=200.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
        _row(
            date="2026-01-03",
            trade1=-100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
    ]

    result = calculate_consolidated_analytics(
        rows=rows,
        **COMMON,
    )

    assert result["gross_profit_points"] == 300.0
    assert result["gross_loss_points"] == -100.0
    assert result["profit_factor"] == 3.0


def test_consolidated_payoff():
    rows = [
        _row(
            date="2026-01-01",
            trade1=100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
        _row(
            date="2026-01-02",
            trade1=300.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
        _row(
            date="2026-01-03",
            trade1=-100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
        _row(
            date="2026-01-04",
            trade1=-100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
    ]

    result = calculate_consolidated_analytics(
        rows=rows,
        **COMMON,
    )

    # avg win = 200, avg loss = -100
    assert result["payoff_ratio"] == 2.0


def test_consolidated_drawdown():
    rows = [
        _row(
            date="2026-01-01",
            trade1=100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
        _row(
            date="2026-01-02",
            trade1=-50.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
        _row(
            date="2026-01-03",
            trade1=-100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
        _row(
            date="2026-01-04",
            trade1=200.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
    ]

    result = calculate_consolidated_analytics(
        rows=rows,
        **COMMON,
    )

    assert result["max_drawdown_points"] == 150.0
    assert result["max_drawdown_start_date"] == "2026-01-01"
    assert result["max_drawdown_end_date"] == "2026-01-03"


def test_trade2_percentage():
    rows = [
        _row(
            date="2026-01-01",
            trade1=-100.0,
            trade2=100.0,
            trade2_eligible=True,
            trade2_executed=True,
        ),
        _row(
            date="2026-01-02",
            trade1=100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
    ]

    result = calculate_consolidated_analytics(
        rows=rows,
        **COMMON,
    )

    assert result["total_cycles"] == 2
    assert result["cycles_with_trade2"] == 1
    assert result["cycles_without_trade2"] == 1
    assert result["trade2_pct"] == 50.0


def test_comparison_trade1_vs_consolidated():
    trade1 = {
        "experiment_id": "EXP-1",
        "config_sha256": "cfg",
        "motor_version": "motor",
        "rules_version": "rules",
        "total_weighted_points": 100.0,
        "expectancy_points_per_trade": 10.0,
        "profit_factor": 1.5,
        "max_drawdown_points": 200.0,
        "win_rate_pct": 50.0,
    }

    consolidated = {
        "experiment_id": "EXP-1",
        "config_sha256": "cfg",
        "motor_version": "motor",
        "rules_version": "rules",
        "total_result_points": 180.0,
        "expectancy_points_per_cycle": 18.0,
        "profit_factor": 2.0,
        "max_drawdown_points": 150.0,
        "win_rate_pct": 60.0,
        "source_results_sha256": "results",
        "source_manifest_sha256": "manifest",
    }

    result = calculate_comparison(
        trade1_metrics=trade1,
        consolidated_metrics=consolidated,
    )

    assert result["difference_total_result_points"] == 80.0
    assert result["difference_expectancy_points"] == 8.0
    assert result["difference_profit_factor"] == 0.5
    assert result["difference_max_drawdown_points"] == -50.0
    assert result["difference_win_rate_pct"] == 10.0


def test_no_trade2_consolidated_equals_trade1_values():
    rows = [
        _row(
            date="2026-01-01",
            trade1=100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
        _row(
            date="2026-01-02",
            trade1=-50.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
    ]

    result = calculate_consolidated_analytics(
        rows=rows,
        **COMMON,
    )

    assert result["total_result_points"] == 50.0
    assert result["cycles_with_trade2"] == 0
    assert result["recovery_pct"] is None


def test_stage20_is_deterministic_and_idempotent():
    rows = [
        _row(
            date="2026-01-01",
            trade1=-100.0,
            trade2=150.0,
            trade2_eligible=True,
            trade2_executed=True,
            trade2_winner=True,
        ),
        _row(
            date="2026-01-02",
            trade1=100.0,
            trade2=None,
            trade2_eligible=False,
            trade2_executed=False,
        ),
    ]

    original = deepcopy(
        rows
    )

    first = calculate_consolidated_analytics(
        rows=rows,
        **COMMON,
    )

    second = calculate_consolidated_analytics(
        rows=rows,
        **COMMON,
    )

    assert first == second
    assert rows == original
