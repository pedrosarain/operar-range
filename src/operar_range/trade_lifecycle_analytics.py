from __future__ import annotations

import hashlib
from pathlib import Path
from statistics import median
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


TRADE_LIFECYCLE_ANALYTICS_VERSION = (
    "trade-lifecycle-analytics-v1"
)


TRADE2_ANALYTICS_SCHEMA = pa.schema(
    [
        ("experiment_id", pa.string()),
        ("config_sha256", pa.string()),
        ("motor_version", pa.string()),
        ("rules_version", pa.string()),
        ("analytics_version", pa.string()),

        ("sessions_total", pa.int64()),
        ("trade2_eligible_count", pa.int64()),
        ("trade2_occurred_count", pa.int64()),
        ("trade2_executed_count", pa.int64()),
        ("trade2_winning_count", pa.int64()),
        ("trade2_losing_count", pa.int64()),
        ("trade2_breakeven_count", pa.int64()),
        ("trade2_runner_count", pa.int64()),

        (
            "trade2_weighted_result_points",
            pa.float64(),
        ),
        (
            "trade2_total_position_points",
            pa.float64(),
        ),

        ("source_results_sha256", pa.string()),
        ("source_manifest_sha256", pa.string()),
    ]
)


CONSOLIDATED_ANALYTICS_SCHEMA = pa.schema(
    [
        ("experiment_id", pa.string()),
        ("config_sha256", pa.string()),
        ("motor_version", pa.string()),
        ("rules_version", pa.string()),
        ("analytics_version", pa.string()),

        ("total_cycles", pa.int64()),
        ("cycles_with_trade2", pa.int64()),
        ("cycles_without_trade2", pa.int64()),
        ("trade2_pct", pa.float64()),

        ("recovered_cycle_count", pa.int64()),
        ("recovery_pct", pa.float64()),

        ("total_result_points", pa.float64()),
        ("expectancy_points_per_cycle", pa.float64()),
        ("average_cycle_points", pa.float64()),
        ("median_cycle_points", pa.float64()),
        ("best_cycle_points", pa.float64()),
        ("worst_cycle_points", pa.float64()),

        ("winning_cycles", pa.int64()),
        ("losing_cycles", pa.int64()),
        ("breakeven_cycles", pa.int64()),

        ("win_rate_pct", pa.float64()),
        ("loss_rate_pct", pa.float64()),
        ("breakeven_rate_pct", pa.float64()),

        ("gross_profit_points", pa.float64()),
        ("gross_loss_points", pa.float64()),
        ("average_win_points", pa.float64()),
        ("average_loss_points", pa.float64()),

        ("profit_factor", pa.float64()),
        ("profit_factor_status", pa.string()),

        ("payoff_ratio", pa.float64()),
        ("payoff_ratio_status", pa.string()),

        ("max_drawdown_points", pa.float64()),
        ("max_drawdown_start_date", pa.string()),
        ("max_drawdown_end_date", pa.string()),

        ("max_consecutive_losses", pa.int64()),
        ("max_consecutive_wins", pa.int64()),

        ("source_results_sha256", pa.string()),
        ("source_manifest_sha256", pa.string()),
    ]
)


COMPARISON_SCHEMA = pa.schema(
    [
        ("experiment_id", pa.string()),
        ("config_sha256", pa.string()),
        ("motor_version", pa.string()),
        ("rules_version", pa.string()),
        ("analytics_version", pa.string()),

        (
            "trade1_total_result_points",
            pa.float64(),
        ),
        (
            "consolidated_total_result_points",
            pa.float64(),
        ),
        (
            "difference_total_result_points",
            pa.float64(),
        ),

        (
            "trade1_expectancy_points",
            pa.float64(),
        ),
        (
            "consolidated_expectancy_points",
            pa.float64(),
        ),
        (
            "difference_expectancy_points",
            pa.float64(),
        ),

        (
            "trade1_profit_factor",
            pa.float64(),
        ),
        (
            "consolidated_profit_factor",
            pa.float64(),
        ),
        (
            "difference_profit_factor",
            pa.float64(),
        ),

        (
            "trade1_max_drawdown_points",
            pa.float64(),
        ),
        (
            "consolidated_max_drawdown_points",
            pa.float64(),
        ),
        (
            "difference_max_drawdown_points",
            pa.float64(),
        ),

        (
            "trade1_win_rate_pct",
            pa.float64(),
        ),
        (
            "consolidated_win_rate_pct",
            pa.float64(),
        ),
        (
            "difference_win_rate_pct",
            pa.float64(),
        ),

        ("source_results_sha256", pa.string()),
        ("source_manifest_sha256", pa.string()),
    ]
)


def sha256_file(
    path: str | Path,
) -> str:
    path = Path(
        path
    )

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def _max_sequences(
    values: list[float],
) -> tuple[int, int]:
    max_losses = 0
    max_wins = 0

    current_losses = 0
    current_wins = 0

    for value in values:
        if value < 0:
            current_losses += 1
            current_wins = 0

            max_losses = max(
                max_losses,
                current_losses,
            )

        elif value > 0:
            current_wins += 1
            current_losses = 0

            max_wins = max(
                max_wins,
                current_wins,
            )

        else:
            current_losses = 0
            current_wins = 0

    return (
        max_losses,
        max_wins,
    )


def _drawdown(
    rows: list[
        dict[str, Any]
    ],
    *,
    value_field: str,
) -> tuple[
    float,
    str | None,
    str | None,
]:
    if not rows:
        return 0.0, None, None

    ordered = sorted(
        rows,
        key=lambda row: (
            row["date"]
        ),
    )

    cumulative = 0.0
    peak_value = 0.0
    peak_date: str | None = None

    max_drawdown = 0.0
    max_start: str | None = None
    max_end: str | None = None

    for row in ordered:
        value = row.get(
            value_field
        )

        if value is None:
            continue

        cumulative += float(
            value
        )

        if cumulative > peak_value:
            peak_value = cumulative
            peak_date = row[
                "date"
            ]

        drawdown = (
            peak_value
            - cumulative
        )

        if (
            drawdown
            > max_drawdown
        ):
            max_drawdown = drawdown
            max_start = peak_date
            max_end = row[
                "date"
            ]

    return (
        float(
            max_drawdown
        ),
        max_start,
        max_end,
    )


def _statistical_metrics(
    *,
    rows: list[
        dict[str, Any]
    ],
    value_field: str,
) -> dict[str, Any]:
    usable_rows = [
        row
        for row in rows
        if row.get(
            value_field
        )
        is not None
    ]

    values = [
        float(
            row[
                value_field
            ]
        )
        for row in usable_rows
    ]

    wins = [
        value
        for value in values
        if value > 0
    ]

    losses = [
        value
        for value in values
        if value < 0
    ]

    breakevens = [
        value
        for value in values
        if value == 0
    ]

    total_count = len(
        values
    )

    total_points = (
        sum(
            values
        )
        if values
        else 0.0
    )

    average = (
        total_points
        / total_count
        if total_count
        else None
    )

    median_value = (
        float(
            median(
                values
            )
        )
        if values
        else None
    )

    best = (
        max(
            values
        )
        if values
        else None
    )

    worst = (
        min(
            values
        )
        if values
        else None
    )

    winning_count = len(
        wins
    )

    losing_count = len(
        losses
    )

    breakeven_count = len(
        breakevens
    )

    win_rate = (
        100.0
        * winning_count
        / total_count
        if total_count
        else None
    )

    loss_rate = (
        100.0
        * losing_count
        / total_count
        if total_count
        else None
    )

    breakeven_rate = (
        100.0
        * breakeven_count
        / total_count
        if total_count
        else None
    )

    gross_profit = sum(
        wins
    )

    gross_loss = sum(
        losses
    )

    average_win = (
        sum(
            wins
        )
        / len(
            wins
        )
        if wins
        else None
    )

    average_loss = (
        sum(
            losses
        )
        / len(
            losses
        )
        if losses
        else None
    )

    if not losses:
        profit_factor = None
        profit_factor_status = (
            "NO_LOSSES"
        )
    else:
        profit_factor = (
            gross_profit
            / abs(
                gross_loss
            )
        )
        profit_factor_status = (
            "OK"
        )

    if (
        not wins
        and not losses
    ):
        payoff_ratio = None
        payoff_ratio_status = (
            "NO_WINS_OR_LOSSES"
        )

    elif not wins:
        payoff_ratio = None
        payoff_ratio_status = (
            "NO_WINS"
        )

    elif not losses:
        payoff_ratio = None
        payoff_ratio_status = (
            "NO_LOSSES"
        )

    else:
        payoff_ratio = (
            average_win
            / abs(
                average_loss
            )
        )
        payoff_ratio_status = (
            "OK"
        )

    (
        max_drawdown,
        drawdown_start,
        drawdown_end,
    ) = _drawdown(
        usable_rows,
        value_field=(
            value_field
        ),
    )

    (
        max_consecutive_losses,
        max_consecutive_wins,
    ) = _max_sequences(
        values
    )

    return {
        "count": (
            total_count
        ),
        "total_result_points": (
            float(
                total_points
            )
        ),
        "expectancy_points": (
            float(
                average
            )
            if average
            is not None
            else None
        ),
        "average_points": (
            float(
                average
            )
            if average
            is not None
            else None
        ),
        "median_points": (
            median_value
        ),
        "best_points": (
            float(
                best
            )
            if best
            is not None
            else None
        ),
        "worst_points": (
            float(
                worst
            )
            if worst
            is not None
            else None
        ),
        "winning_count": (
            winning_count
        ),
        "losing_count": (
            losing_count
        ),
        "breakeven_count": (
            breakeven_count
        ),
        "win_rate_pct": (
            win_rate
        ),
        "loss_rate_pct": (
            loss_rate
        ),
        "breakeven_rate_pct": (
            breakeven_rate
        ),
        "gross_profit_points": (
            float(
                gross_profit
            )
        ),
        "gross_loss_points": (
            float(
                gross_loss
            )
        ),
        "average_win_points": (
            float(
                average_win
            )
            if average_win
            is not None
            else None
        ),
        "average_loss_points": (
            float(
                average_loss
            )
            if average_loss
            is not None
            else None
        ),
        "profit_factor": (
            float(
                profit_factor
            )
            if profit_factor
            is not None
            else None
        ),
        "profit_factor_status": (
            profit_factor_status
        ),
        "payoff_ratio": (
            float(
                payoff_ratio
            )
            if payoff_ratio
            is not None
            else None
        ),
        "payoff_ratio_status": (
            payoff_ratio_status
        ),
        "max_drawdown_points": (
            max_drawdown
        ),
        "max_drawdown_start_date": (
            drawdown_start
        ),
        "max_drawdown_end_date": (
            drawdown_end
        ),
        "max_consecutive_losses": (
            max_consecutive_losses
        ),
        "max_consecutive_wins": (
            max_consecutive_wins
        ),
    }


def _trade2_total_position_points(
    row: dict[str, Any],
) -> float | None:
    value = row.get(
        "trade2_total_position_points"
    )

    if value is not None:
        return float(
            value
        )

    management_json = row.get(
        "trade2_management_json"
    )

    if not management_json:
        return None

    import json

    try:
        payload = json.loads(
            management_json
        )
    except Exception:
        return None

    value = payload.get(
        "total_position_points"
    )

    if value is None:
        return None

    return float(
        value
    )


def calculate_trade2_analytics(
    *,
    rows: list[
        dict[str, Any]
    ],
    experiment_id: str,
    config_sha256: str,
    motor_version: str,
    rules_version: str,
    source_results_sha256: str,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    sessions_total = len(
        rows
    )

    eligible_count = sum(
        1
        for row in rows
        if row.get(
            "trade2_eligible"
        )
        is True
    )

    occurred_count = sum(
        1
        for row in rows
        if row.get(
            "trade2_occurred"
        )
        is True
    )

    executed_count = sum(
        1
        for row in rows
        if row.get(
            "trade2_executed"
        )
        is True
    )

    winning_count = sum(
        1
        for row in rows
        if row.get(
            "trade2_winner"
        )
        is True
    )

    losing_count = sum(
        1
        for row in rows
        if row.get(
            "trade2_loser"
        )
        is True
    )

    breakeven_count = sum(
        1
        for row in rows
        if row.get(
            "trade2_breakeven"
        )
        is True
    )

    runner_count = 0

    for row in rows:
        management_json = row.get(
            "trade2_management_json"
        )

        if not management_json:
            continue

        import json

        try:
            payload = json.loads(
                management_json
            )
        except Exception:
            continue

        runner_result = (
            payload.get(
                "runner_result"
            )
            or {}
        )

        if runner_result.get(
            "executed"
        ) is True:
            runner_count += 1

    weighted_total = sum(
        float(
            row[
                "trade2_result_points"
            ]
        )
        for row in rows
        if row.get(
            "trade2_result_points"
        )
        is not None
    )

    position_values = [
        value
        for value in (
            _trade2_total_position_points(
                row
            )
            for row in rows
        )
        if value is not None
    ]

    return {
        "experiment_id": (
            experiment_id
        ),
        "config_sha256": (
            config_sha256
        ),
        "motor_version": (
            motor_version
        ),
        "rules_version": (
            rules_version
        ),
        "analytics_version": (
            TRADE_LIFECYCLE_ANALYTICS_VERSION
        ),
        "sessions_total": (
            sessions_total
        ),
        "trade2_eligible_count": (
            eligible_count
        ),
        "trade2_occurred_count": (
            occurred_count
        ),
        "trade2_executed_count": (
            executed_count
        ),
        "trade2_winning_count": (
            winning_count
        ),
        "trade2_losing_count": (
            losing_count
        ),
        "trade2_breakeven_count": (
            breakeven_count
        ),
        "trade2_runner_count": (
            runner_count
        ),
        "trade2_weighted_result_points": (
            float(
                weighted_total
            )
        ),
        "trade2_total_position_points": (
            float(
                sum(
                    position_values
                )
            )
            if position_values
            else None
        ),
        "source_results_sha256": (
            source_results_sha256
        ),
        "source_manifest_sha256": (
            source_manifest_sha256
        ),
    }


def calculate_consolidated_analytics(
    *,
    rows: list[
        dict[str, Any]
    ],
    experiment_id: str,
    config_sha256: str,
    motor_version: str,
    rules_version: str,
    source_results_sha256: str,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    cycle_rows = [
        row
        for row in rows
        if row.get(
            "consolidated_result_points"
        )
        is not None
    ]

    total_cycles = len(
        cycle_rows
    )

    cycles_with_trade2 = sum(
        1
        for row in cycle_rows
        if row.get(
            "trade2_executed"
        )
        is True
    )

    cycles_without_trade2 = (
        total_cycles
        - cycles_with_trade2
    )

    trade2_pct = (
        100.0
        * cycles_with_trade2
        / total_cycles
        if total_cycles
        else None
    )

    recovered_cycle_count = sum(
        1
        for row in cycle_rows
        if (
            row.get(
                "trade1_result_points"
            )
            is not None
            and float(
                row[
                    "trade1_result_points"
                ]
            )
            < 0
            and row.get(
                "trade2_executed"
            )
            is True
            and float(
                row[
                    "consolidated_result_points"
                ]
            )
            >= 0
        )
    )

    recovery_pct = (
        100.0
        * recovered_cycle_count
        / cycles_with_trade2
        if cycles_with_trade2
        else None
    )

    stats = _statistical_metrics(
        rows=cycle_rows,
        value_field=(
            "consolidated_result_points"
        ),
    )

    return {
        "experiment_id": (
            experiment_id
        ),
        "config_sha256": (
            config_sha256
        ),
        "motor_version": (
            motor_version
        ),
        "rules_version": (
            rules_version
        ),
        "analytics_version": (
            TRADE_LIFECYCLE_ANALYTICS_VERSION
        ),
        "total_cycles": (
            total_cycles
        ),
        "cycles_with_trade2": (
            cycles_with_trade2
        ),
        "cycles_without_trade2": (
            cycles_without_trade2
        ),
        "trade2_pct": (
            trade2_pct
        ),
        "recovered_cycle_count": (
            recovered_cycle_count
        ),
        "recovery_pct": (
            recovery_pct
        ),
        "total_result_points": (
            stats[
                "total_result_points"
            ]
        ),
        "expectancy_points_per_cycle": (
            stats[
                "expectancy_points"
            ]
        ),
        "average_cycle_points": (
            stats[
                "average_points"
            ]
        ),
        "median_cycle_points": (
            stats[
                "median_points"
            ]
        ),
        "best_cycle_points": (
            stats[
                "best_points"
            ]
        ),
        "worst_cycle_points": (
            stats[
                "worst_points"
            ]
        ),
        "winning_cycles": (
            stats[
                "winning_count"
            ]
        ),
        "losing_cycles": (
            stats[
                "losing_count"
            ]
        ),
        "breakeven_cycles": (
            stats[
                "breakeven_count"
            ]
        ),
        "win_rate_pct": (
            stats[
                "win_rate_pct"
            ]
        ),
        "loss_rate_pct": (
            stats[
                "loss_rate_pct"
            ]
        ),
        "breakeven_rate_pct": (
            stats[
                "breakeven_rate_pct"
            ]
        ),
        "gross_profit_points": (
            stats[
                "gross_profit_points"
            ]
        ),
        "gross_loss_points": (
            stats[
                "gross_loss_points"
            ]
        ),
        "average_win_points": (
            stats[
                "average_win_points"
            ]
        ),
        "average_loss_points": (
            stats[
                "average_loss_points"
            ]
        ),
        "profit_factor": (
            stats[
                "profit_factor"
            ]
        ),
        "profit_factor_status": (
            stats[
                "profit_factor_status"
            ]
        ),
        "payoff_ratio": (
            stats[
                "payoff_ratio"
            ]
        ),
        "payoff_ratio_status": (
            stats[
                "payoff_ratio_status"
            ]
        ),
        "max_drawdown_points": (
            stats[
                "max_drawdown_points"
            ]
        ),
        "max_drawdown_start_date": (
            stats[
                "max_drawdown_start_date"
            ]
        ),
        "max_drawdown_end_date": (
            stats[
                "max_drawdown_end_date"
            ]
        ),
        "max_consecutive_losses": (
            stats[
                "max_consecutive_losses"
            ]
        ),
        "max_consecutive_wins": (
            stats[
                "max_consecutive_wins"
            ]
        ),
        "source_results_sha256": (
            source_results_sha256
        ),
        "source_manifest_sha256": (
            source_manifest_sha256
        ),
    }


def _difference(
    left: Any,
    right: Any,
) -> float | None:
    if (
        left is None
        or right is None
    ):
        return None

    return float(
        right
    ) - float(
        left
    )


def calculate_comparison(
    *,
    trade1_metrics: dict[str, Any],
    consolidated_metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "experiment_id": (
            trade1_metrics[
                "experiment_id"
            ]
        ),
        "config_sha256": (
            trade1_metrics[
                "config_sha256"
            ]
        ),
        "motor_version": (
            trade1_metrics[
                "motor_version"
            ]
        ),
        "rules_version": (
            trade1_metrics[
                "rules_version"
            ]
        ),
        "analytics_version": (
            TRADE_LIFECYCLE_ANALYTICS_VERSION
        ),

        "trade1_total_result_points": (
            trade1_metrics.get(
                "total_weighted_points"
            )
        ),
        "consolidated_total_result_points": (
            consolidated_metrics.get(
                "total_result_points"
            )
        ),
        "difference_total_result_points": (
            _difference(
                trade1_metrics.get(
                    "total_weighted_points"
                ),
                consolidated_metrics.get(
                    "total_result_points"
                ),
            )
        ),

        "trade1_expectancy_points": (
            trade1_metrics.get(
                "expectancy_points_per_trade"
            )
        ),
        "consolidated_expectancy_points": (
            consolidated_metrics.get(
                "expectancy_points_per_cycle"
            )
        ),
        "difference_expectancy_points": (
            _difference(
                trade1_metrics.get(
                    "expectancy_points_per_trade"
                ),
                consolidated_metrics.get(
                    "expectancy_points_per_cycle"
                ),
            )
        ),

        "trade1_profit_factor": (
            trade1_metrics.get(
                "profit_factor"
            )
        ),
        "consolidated_profit_factor": (
            consolidated_metrics.get(
                "profit_factor"
            )
        ),
        "difference_profit_factor": (
            _difference(
                trade1_metrics.get(
                    "profit_factor"
                ),
                consolidated_metrics.get(
                    "profit_factor"
                ),
            )
        ),

        "trade1_max_drawdown_points": (
            trade1_metrics.get(
                "max_drawdown_points"
            )
        ),
        "consolidated_max_drawdown_points": (
            consolidated_metrics.get(
                "max_drawdown_points"
            )
        ),
        "difference_max_drawdown_points": (
            _difference(
                trade1_metrics.get(
                    "max_drawdown_points"
                ),
                consolidated_metrics.get(
                    "max_drawdown_points"
                ),
            )
        ),

        "trade1_win_rate_pct": (
            trade1_metrics.get(
                "win_rate_pct"
            )
        ),
        "consolidated_win_rate_pct": (
            consolidated_metrics.get(
                "win_rate_pct"
            )
        ),
        "difference_win_rate_pct": (
            _difference(
                trade1_metrics.get(
                    "win_rate_pct"
                ),
                consolidated_metrics.get(
                    "win_rate_pct"
                ),
            )
        ),

        "source_results_sha256": (
            consolidated_metrics[
                "source_results_sha256"
            ]
        ),
        "source_manifest_sha256": (
            consolidated_metrics[
                "source_manifest_sha256"
            ]
        ),
    }


def _write_rows(
    *,
    rows: list[
        dict[str, Any]
    ],
    schema: pa.Schema,
    output_path: str | Path,
) -> Path:
    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ordered = sorted(
        rows,
        key=lambda row: (
            row[
                "experiment_id"
            ]
        ),
    )

    table = pa.Table.from_pylist(
        ordered,
        schema=schema,
    )

    pq.write_table(
        table,
        output_path,
        compression="zstd",
    )

    return output_path


def run_trade_lifecycle_analytics(
    *,
    results_path: str | Path,
    manifest_path: str | Path,
    trade1_metrics_path: str | Path,
    trade2_analytics_path: str | Path,
    consolidated_analytics_path: str | Path,
    comparison_path: str | Path,
) -> dict[str, Any]:
    results_path = Path(
        results_path
    )

    manifest_path = Path(
        manifest_path
    )

    trade1_metrics_path = Path(
        trade1_metrics_path
    )

    for required in (
        results_path,
        manifest_path,
        trade1_metrics_path,
    ):
        if not required.exists():
            raise FileNotFoundError(
                required
            )

    results_sha256 = (
        sha256_file(
            results_path
        )
    )

    manifest_sha256 = (
        sha256_file(
            manifest_path
        )
    )

    results = pq.read_table(
        results_path
    ).to_pylist()

    manifest = pq.read_table(
        manifest_path
    ).to_pylist()

    trade1_metrics = pq.read_table(
        trade1_metrics_path
    ).to_pylist()

    manifest_by_id = {
        row[
            "experiment_id"
        ]: row
        for row in manifest
    }

    trade1_by_id = {
        row[
            "experiment_id"
        ]: row
        for row in trade1_metrics
    }

    experiment_ids = sorted(
        {
            row[
                "experiment_id"
            ]
            for row in results
        }
    )

    trade2_rows = []
    consolidated_rows = []
    comparison_rows = []

    for experiment_id in (
        experiment_ids
    ):
        if (
            experiment_id
            not in manifest_by_id
        ):
            raise ValueError(
                (
                    "Experiment missing "
                    "from manifest: "
                    f"{experiment_id}"
                )
            )

        if (
            experiment_id
            not in trade1_by_id
        ):
            raise ValueError(
                (
                    "Experiment missing "
                    "from Trade 1 metrics: "
                    f"{experiment_id}"
                )
            )

        manifest_row = (
            manifest_by_id[
                experiment_id
            ]
        )

        config_sha256 = (
            manifest_row[
                "config_sha256"
            ]
        )

        motor_version = (
            manifest_row[
                "motor_version"
            ]
        )

        rules_version = (
            manifest_row[
                "rules_version"
            ]
        )

        experiment_rows = sorted(
            [
                row
                for row in results
                if row[
                    "experiment_id"
                ]
                == experiment_id
            ],
            key=lambda row: (
                row[
                    "date"
                ]
            ),
        )

        for row in experiment_rows:
            if (
                row[
                    "config_sha256"
                ]
                != config_sha256
            ):
                raise ValueError(
                    (
                        "Configuration hash "
                        "mismatch for "
                        f"{experiment_id}."
                    )
                )

        trade2 = (
            calculate_trade2_analytics(
                rows=(
                    experiment_rows
                ),
                experiment_id=(
                    experiment_id
                ),
                config_sha256=(
                    config_sha256
                ),
                motor_version=(
                    motor_version
                ),
                rules_version=(
                    rules_version
                ),
                source_results_sha256=(
                    results_sha256
                ),
                source_manifest_sha256=(
                    manifest_sha256
                ),
            )
        )

        consolidated = (
            calculate_consolidated_analytics(
                rows=(
                    experiment_rows
                ),
                experiment_id=(
                    experiment_id
                ),
                config_sha256=(
                    config_sha256
                ),
                motor_version=(
                    motor_version
                ),
                rules_version=(
                    rules_version
                ),
                source_results_sha256=(
                    results_sha256
                ),
                source_manifest_sha256=(
                    manifest_sha256
                ),
            )
        )

        comparison = (
            calculate_comparison(
                trade1_metrics=(
                    trade1_by_id[
                        experiment_id
                    ]
                ),
                consolidated_metrics=(
                    consolidated
                ),
            )
        )

        trade2_rows.append(
            trade2
        )

        consolidated_rows.append(
            consolidated
        )

        comparison_rows.append(
            comparison
        )

    trade2_path = _write_rows(
        rows=(
            trade2_rows
        ),
        schema=(
            TRADE2_ANALYTICS_SCHEMA
        ),
        output_path=(
            trade2_analytics_path
        ),
    )

    consolidated_path = _write_rows(
        rows=(
            consolidated_rows
        ),
        schema=(
            CONSOLIDATED_ANALYTICS_SCHEMA
        ),
        output_path=(
            consolidated_analytics_path
        ),
    )

    comparison_written_path = (
        _write_rows(
            rows=(
                comparison_rows
            ),
            schema=(
                COMPARISON_SCHEMA
            ),
            output_path=(
                comparison_path
            ),
        )
    )

    return {
        "trade2": (
            trade2_rows
        ),
        "consolidated": (
            consolidated_rows
        ),
        "comparison": (
            comparison_rows
        ),
        "trade2_analytics_path": str(
            trade2_path
        ),
        "consolidated_analytics_path": str(
            consolidated_path
        ),
        "comparison_path": str(
            comparison_written_path
        ),
        "source_results_sha256": (
            results_sha256
        ),
        "source_manifest_sha256": (
            manifest_sha256
        ),
    }
