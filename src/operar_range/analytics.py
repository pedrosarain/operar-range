from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


METRICS_SCHEMA = pa.schema(
    [
        ("experiment_id", pa.string()),
        ("config_sha256", pa.string()),
        ("motor_version", pa.string()),
        ("rules_version", pa.string()),
        ("year", pa.int32()),
        ("month", pa.int32()),
        ("period_start", pa.string()),
        ("period_end", pa.string()),
        ("sessions_total", pa.int64()),
        ("trade1_count", pa.int64()),
        ("no_trade1_count", pa.int64()),
        ("trade_frequency_pct", pa.float64()),
        ("total_weighted_points", pa.float64()),
        ("average_weighted_points", pa.float64()),
        ("median_weighted_points", pa.float64()),
        ("best_trade_points", pa.float64()),
        ("worst_trade_points", pa.float64()),
        ("winning_trades", pa.int64()),
        ("losing_trades", pa.int64()),
        ("breakeven_trades", pa.int64()),
        ("win_rate_pct", pa.float64()),
        ("loss_rate_pct", pa.float64()),
        ("gross_profit_points", pa.float64()),
        ("gross_loss_points", pa.float64()),
        ("average_win_points", pa.float64()),
        ("average_loss_points", pa.float64()),
        ("payoff_ratio", pa.float64()),
        ("payoff_ratio_status", pa.string()),
        ("profit_factor", pa.float64()),
        ("profit_factor_status", pa.string()),
        ("expectancy_points_per_trade", pa.float64()),
        ("max_drawdown_points", pa.float64()),
        ("max_drawdown_start_date", pa.string()),
        ("max_drawdown_end_date", pa.string()),
        ("max_consecutive_losses", pa.int64()),
        ("max_consecutive_wins", pa.int64()),
        ("negative_days", pa.int64()),
        ("positive_days", pa.int64()),
        ("zero_result_days", pa.int64()),
        ("source_results_sha256", pa.string()),
        ("source_manifest_sha256", pa.string()),
    ]
)


def sha256_file(
    path: str | Path,
) -> str:
    path = Path(path)

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _trade_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if (
            row.get("trade_status")
            == "TRADE_1"
            and row.get(
                "total_weighted_points"
            )
            is not None
        )
    ]


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
    trade_rows: list[
        dict[str, Any]
    ],
) -> tuple[
    float,
    str | None,
    str | None,
]:
    if not trade_rows:
        return 0.0, None, None

    ordered = sorted(
        trade_rows,
        key=lambda row: row["date"],
    )

    cumulative = 0.0
    peak_value = 0.0
    peak_date: str | None = None

    max_drawdown = 0.0
    max_start: str | None = None
    max_end: str | None = None

    for row in ordered:
        result = float(
            row[
                "total_weighted_points"
            ]
        )

        cumulative += result

        if cumulative > peak_value:
            peak_value = cumulative
            peak_date = row["date"]

        drawdown = (
            peak_value - cumulative
        )

        if drawdown > max_drawdown:
            max_drawdown = drawdown
            max_start = peak_date
            max_end = row["date"]

    return (
        float(max_drawdown),
        max_start,
        max_end,
    )


def calculate_metrics(
    *,
    rows: list[dict[str, Any]],
    experiment_id: str,
    config_sha256: str,
    motor_version: str,
    rules_version: str,
    source_results_sha256: str,
    source_manifest_sha256: str,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    if not rows:
        raise ValueError(
            "Metrics require at least one session."
        )

    ordered = sorted(
        rows,
        key=lambda row: row["date"],
    )

    sessions_total = len(ordered)

    trades = _trade_rows(
        ordered
    )

    trade1_count = len(trades)

    no_trade1_count = sum(
        1
        for row in ordered
        if row.get("trade_status")
        == "NO_TRADE_1"
    )

    trade_frequency_pct = (
        100.0
        * trade1_count
        / sessions_total
    )

    values = [
        float(
            row[
                "total_weighted_points"
            ]
        )
        for row in trades
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

    winning_trades = len(wins)
    losing_trades = len(losses)
    breakeven_trades = len(
        breakevens
    )

    total_points = (
        sum(values)
        if values
        else 0.0
    )

    average_points = (
        total_points / len(values)
        if values
        else None
    )

    median_points = (
        float(median(values))
        if values
        else None
    )

    best_trade = (
        max(values)
        if values
        else None
    )

    worst_trade = (
        min(values)
        if values
        else None
    )

    win_rate_pct = (
        100.0
        * winning_trades
        / trade1_count
        if trade1_count
        else None
    )

    loss_rate_pct = (
        100.0
        * losing_trades
        / trade1_count
        if trade1_count
        else None
    )

    gross_profit = sum(wins)

    gross_loss = sum(losses)

    average_win = (
        sum(wins) / len(wins)
        if wins
        else None
    )

    average_loss = (
        sum(losses) / len(losses)
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
            / abs(gross_loss)
        )
        profit_factor_status = "OK"

    if not wins and not losses:
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
            / abs(average_loss)
        )
        payoff_ratio_status = "OK"

    expectancy = (
        average_points
    )

    (
        max_drawdown,
        drawdown_start,
        drawdown_end,
    ) = _drawdown(
        trades
    )

    (
        max_consecutive_losses,
        max_consecutive_wins,
    ) = _max_sequences(
        values
    )

    positive_days = len(wins)
    negative_days = len(losses)
    zero_result_days = len(
        breakevens
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
        "year": year,
        "month": month,
        "period_start": (
            ordered[0]["date"]
        ),
        "period_end": (
            ordered[-1]["date"]
        ),
        "sessions_total": (
            sessions_total
        ),
        "trade1_count": (
            trade1_count
        ),
        "no_trade1_count": (
            no_trade1_count
        ),
        "trade_frequency_pct": (
            trade_frequency_pct
        ),
        "total_weighted_points": (
            float(total_points)
        ),
        "average_weighted_points": (
            float(average_points)
            if average_points
            is not None
            else None
        ),
        "median_weighted_points": (
            median_points
        ),
        "best_trade_points": (
            float(best_trade)
            if best_trade
            is not None
            else None
        ),
        "worst_trade_points": (
            float(worst_trade)
            if worst_trade
            is not None
            else None
        ),
        "winning_trades": (
            winning_trades
        ),
        "losing_trades": (
            losing_trades
        ),
        "breakeven_trades": (
            breakeven_trades
        ),
        "win_rate_pct": (
            win_rate_pct
        ),
        "loss_rate_pct": (
            loss_rate_pct
        ),
        "gross_profit_points": (
            float(gross_profit)
        ),
        "gross_loss_points": (
            float(gross_loss)
        ),
        "average_win_points": (
            float(average_win)
            if average_win
            is not None
            else None
        ),
        "average_loss_points": (
            float(average_loss)
            if average_loss
            is not None
            else None
        ),
        "payoff_ratio": (
            float(payoff_ratio)
            if payoff_ratio
            is not None
            else None
        ),
        "payoff_ratio_status": (
            payoff_ratio_status
        ),
        "profit_factor": (
            float(profit_factor)
            if profit_factor
            is not None
            else None
        ),
        "profit_factor_status": (
            profit_factor_status
        ),
        "expectancy_points_per_trade": (
            float(expectancy)
            if expectancy
            is not None
            else None
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
        "negative_days": (
            negative_days
        ),
        "positive_days": (
            positive_days
        ),
        "zero_result_days": (
            zero_result_days
        ),
        "source_results_sha256": (
            source_results_sha256
        ),
        "source_manifest_sha256": (
            source_manifest_sha256
        ),
    }


def _write_metrics(
    rows: list[dict[str, Any]],
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
            row["experiment_id"],
            row["year"]
            if row["year"]
            is not None
            else -1,
            row["month"]
            if row["month"]
            is not None
            else -1,
        ),
    )

    table = pa.Table.from_pylist(
        ordered,
        schema=METRICS_SCHEMA,
    )

    pq.write_table(
        table,
        output_path,
        compression="zstd",
    )

    return output_path


def run_analytics(
    *,
    results_path: str | Path = (
        "data/research/"
        "experiment_results.parquet"
    ),
    manifest_path: str | Path = (
        "data/research/"
        "experiment_manifest.parquet"
    ),
    metrics_path: str | Path = (
        "data/research/"
        "experiment_metrics.parquet"
    ),
    yearly_path: str | Path = (
        "data/research/"
        "experiment_metrics_yearly.parquet"
    ),
    monthly_path: str | Path = (
        "data/research/"
        "experiment_metrics_monthly.parquet"
    ),
) -> dict[str, Any]:
    results_path = Path(
        results_path
    )

    manifest_path = Path(
        manifest_path
    )

    if not results_path.exists():
        raise FileNotFoundError(
            results_path
        )

    if not manifest_path.exists():
        raise FileNotFoundError(
            manifest_path
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

    manifest_by_id = {
        row["experiment_id"]: row
        for row in manifest
    }

    experiment_ids = sorted(
        {
            row["experiment_id"]
            for row in results
        }
    )

    overall_rows = []
    yearly_rows = []
    monthly_rows = []

    for experiment_id in (
        experiment_ids
    ):
        if (
            experiment_id
            not in manifest_by_id
        ):
            raise ValueError(
                "Experiment missing from "
                f"manifest: {experiment_id}"
            )

        experiment_rows = [
            row
            for row in results
            if row["experiment_id"]
            == experiment_id
        ]

        experiment_rows = sorted(
            experiment_rows,
            key=lambda row: row["date"],
        )

        manifest_row = (
            manifest_by_id[
                experiment_id
            ]
        )

        config_hash = (
            manifest_row[
                "config_sha256"
            ]
        )

        for row in experiment_rows:
            if (
                row["config_sha256"]
                != config_hash
            ):
                raise ValueError(
                    "Configuration hash mismatch "
                    f"for {experiment_id}."
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

        overall_rows.append(
            calculate_metrics(
                rows=experiment_rows,
                experiment_id=(
                    experiment_id
                ),
                config_sha256=(
                    config_hash
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

        by_year: dict[
            int,
            list[dict[str, Any]],
        ] = {}

        by_month: dict[
            tuple[int, int],
            list[dict[str, Any]],
        ] = {}

        for row in experiment_rows:
            date_value = (
                row["date"]
            )

            year = int(
                date_value[0:4]
            )

            month = int(
                date_value[5:7]
            )

            by_year.setdefault(
                year,
                [],
            ).append(row)

            by_month.setdefault(
                (year, month),
                [],
            ).append(row)

        for year in sorted(
            by_year
        ):
            yearly_rows.append(
                calculate_metrics(
                    rows=by_year[year],
                    experiment_id=(
                        experiment_id
                    ),
                    config_sha256=(
                        config_hash
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
                    year=year,
                    month=None,
                )
            )

        for (
            year,
            month,
        ) in sorted(by_month):
            monthly_rows.append(
                calculate_metrics(
                    rows=by_month[
                        (
                            year,
                            month,
                        )
                    ],
                    experiment_id=(
                        experiment_id
                    ),
                    config_sha256=(
                        config_hash
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
                    year=year,
                    month=month,
                )
            )

    metrics_path = _write_metrics(
        overall_rows,
        metrics_path,
    )

    yearly_path = _write_metrics(
        yearly_rows,
        yearly_path,
    )

    monthly_path = _write_metrics(
        monthly_rows,
        monthly_path,
    )

    return {
        "metrics": overall_rows,
        "yearly": yearly_rows,
        "monthly": monthly_rows,
        "metrics_path": str(
            metrics_path
        ),
        "yearly_path": str(
            yearly_path
        ),
        "monthly_path": str(
            monthly_path
        ),
        "source_results_sha256": (
            results_sha256
        ),
        "source_manifest_sha256": (
            manifest_sha256
        ),
    }