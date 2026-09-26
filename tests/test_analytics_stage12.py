from __future__ import annotations

import random

from operar_range.analytics import (
    calculate_metrics,
)


BASE = {
    "experiment_id": "EXP-TEST",
    "config_sha256": "a" * 64,
    "motor_version": "test-motor",
    "rules_version": "test-rules",
    "source_results_sha256": "b" * 64,
    "source_manifest_sha256": "c" * 64,
}


def row(
    date,
    result=None,
    status="TRADE_1",
):
    return {
        "date": date,
        "trade_status": status,
        "total_weighted_points": result,
    }


def metrics(rows):
    return calculate_metrics(
        rows=rows,
        **BASE,
    )


def test_only_gains():
    result = metrics(
        [
            row("2026-01-01", 100),
            row("2026-01-02", 200),
        ]
    )

    assert result[
        "winning_trades"
    ] == 2

    assert result[
        "gross_profit_points"
    ] == 300

    assert result[
        "profit_factor"
    ] is None

    assert result[
        "profit_factor_status"
    ] == "NO_LOSSES"


def test_only_losses():
    result = metrics(
        [
            row("2026-01-01", -100),
            row("2026-01-02", -200),
        ]
    )

    assert result[
        "losing_trades"
    ] == 2

    assert result[
        "gross_loss_points"
    ] == -300

    assert result[
        "profit_factor"
    ] == 0


def test_gains_and_losses():
    result = metrics(
        [
            row("2026-01-01", 200),
            row("2026-01-02", -100),
        ]
    )

    assert result[
        "total_weighted_points"
    ] == 100

    assert result[
        "average_weighted_points"
    ] == 50


def test_breakeven():
    result = metrics(
        [
            row("2026-01-01", 0),
        ]
    )

    assert result[
        "breakeven_trades"
    ] == 1

    assert result[
        "zero_result_days"
    ] == 1


def test_no_trade_excluded():
    result = metrics(
        [
            row("2026-01-01", 100),
            row(
                "2026-01-02",
                None,
                "NO_TRADE_1",
            ),
        ]
    )

    assert result[
        "sessions_total"
    ] == 2

    assert result[
        "trade1_count"
    ] == 1

    assert result[
        "no_trade1_count"
    ] == 1

    assert result[
        "trade_frequency_pct"
    ] == 50


def test_profit_factor():
    result = metrics(
        [
            row("2026-01-01", 300),
            row("2026-01-02", -100),
        ]
    )

    assert result[
        "profit_factor"
    ] == 3


def test_profit_factor_no_losses():
    result = metrics(
        [
            row("2026-01-01", 100),
        ]
    )

    assert result[
        "profit_factor"
    ] is None

    assert result[
        "profit_factor_status"
    ] == "NO_LOSSES"


def test_payoff():
    result = metrics(
        [
            row("2026-01-01", 200),
            row("2026-01-02", -100),
        ]
    )

    assert result[
        "payoff_ratio"
    ] == 2


def test_expectancy():
    result = metrics(
        [
            row("2026-01-01", 100),
            row("2026-01-02", -50),
        ]
    )

    assert result[
        "expectancy_points_per_trade"
    ] == 25


def test_drawdown():
    result = metrics(
        [
            row("2026-01-01", 100),
            row("2026-01-02", -40),
            row("2026-01-03", -30),
        ]
    )

    assert result[
        "max_drawdown_points"
    ] == 70

    assert result[
        "max_drawdown_start_date"
    ] == "2026-01-01"

    assert result[
        "max_drawdown_end_date"
    ] == "2026-01-03"


def test_drawdown_recovery():
    result = metrics(
        [
            row("2026-01-01", 100),
            row("2026-01-02", -50),
            row("2026-01-03", 100),
        ]
    )

    assert result[
        "max_drawdown_points"
    ] == 50


def test_consecutive_losses():
    result = metrics(
        [
            row("2026-01-01", -10),
            row("2026-01-02", -20),
            row("2026-01-03", -30),
            row("2026-01-04", 50),
        ]
    )

    assert result[
        "max_consecutive_losses"
    ] == 3


def test_consecutive_wins():
    result = metrics(
        [
            row("2026-01-01", 10),
            row("2026-01-02", 20),
            row("2026-01-03", 30),
            row("2026-01-04", -50),
        ]
    )

    assert result[
        "max_consecutive_wins"
    ] == 3


def test_chronological_ordering():
    ordered = [
        row("2026-01-01", 100),
        row("2026-01-02", -50),
        row("2026-01-03", 20),
    ]

    shuffled = list(ordered)

    random.Random(
        12345
    ).shuffle(shuffled)

    assert metrics(
        ordered
    ) == metrics(
        shuffled
    )


def test_period_start_end():
    result = metrics(
        [
            row("2026-03-20", 10),
            row("2026-01-10", 20),
        ]
    )

    assert result[
        "period_start"
    ] == "2026-01-10"

    assert result[
        "period_end"
    ] == "2026-03-20"


def test_year_field():
    result = calculate_metrics(
        rows=[
            row(
                "2026-01-01",
                100,
            )
        ],
        year=2026,
        month=None,
        **BASE,
    )

    assert result["year"] == 2026
    assert result["month"] is None


def test_month_field():
    result = calculate_metrics(
        rows=[
            row(
                "2026-08-01",
                100,
            )
        ],
        year=2026,
        month=8,
        **BASE,
    )

    assert result["year"] == 2026
    assert result["month"] == 8


def test_determinism():
    rows = [
        row("2026-01-01", 100),
        row("2026-01-02", -50),
        row("2026-01-03", 0),
    ]

    assert (
        metrics(rows)
        == metrics(rows)
    )


def test_independent_experiments():
    first = calculate_metrics(
        rows=[
            row(
                "2026-01-01",
                100,
            )
        ],
        experiment_id="EXP-A",
        config_sha256="a" * 64,
        motor_version="motor",
        rules_version="rules",
        source_results_sha256=(
            "b" * 64
        ),
        source_manifest_sha256=(
            "c" * 64
        ),
    )

    second = calculate_metrics(
        rows=[
            row(
                "2026-01-01",
                -100,
            )
        ],
        experiment_id="EXP-B",
        config_sha256="d" * 64,
        motor_version="motor",
        rules_version="rules",
        source_results_sha256=(
            "b" * 64
        ),
        source_manifest_sha256=(
            "c" * 64
        ),
    )

    assert (
        first[
            "total_weighted_points"
        ]
        == 100
    )

    assert (
        second[
            "total_weighted_points"
        ]
        == -100
    )