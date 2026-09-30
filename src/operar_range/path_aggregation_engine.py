from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.research_workspace import (
    load_research_definition,
    research_paths,
)


PATH_AGGREGATION_VERSION = (
    "path-aggregation-v1"
)

TARGET_LEVELS = (
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

STOP_LEVELS = (
    100,
    125,
    150,
    175,
    200,
)

TARGET_ANALYTICS_ARTIFACT = (
    "path_target_analytics.parquet"
)

TARGET_STOP_MATRIX_ARTIFACT = (
    "path_target_stop_matrix.parquet"
)

STOP_ANALYTICS_ARTIFACT = (
    "path_stop_analytics.parquet"
)

TRADE2_ANALYTICS_ARTIFACT = (
    "path_trade2_analytics.parquet"
)


def _sha256_file(
    path: str | Path,
) -> str:
    path = Path(path)

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


def _percentage(
    numerator: int,
    denominator: int,
) -> tuple[
    float | None,
    str,
]:
    if denominator == 0:
        return (
            None,
            "NO_DENOMINATOR",
        )

    return (
        float(
            numerator
            / denominator
            * 100.0
        ),
        "OK",
    )


def _require_inputs(
    research_id: str,
) -> dict[str, Any]:
    paths = research_paths(
        research_id
    )

    root = Path(
        paths[
            "root"
        ]
    )

    distributed_path = Path(
        paths[
            "distributed_results"
        ]
    )

    path_analysis_path = (
        root
        / "path_analysis.parquet"
    )

    if not root.exists():
        raise FileNotFoundError(
            f"Research not found: "
            f"{research_id}"
        )

    if not distributed_path.exists():
        raise FileNotFoundError(
            "distributed_experiment_results.parquet "
            "not found for Research: "
            f"{research_id}"
        )

    if not path_analysis_path.exists():
        raise FileNotFoundError(
            "path_analysis.parquet not found "
            "for Research: "
            f"{research_id}"
        )

    definition = (
        load_research_definition(
            research_id
        )
    )

    dataset_id = (
        definition.get(
            "dataset_id"
        )
        or definition.get(
            "dataset_key"
        )
    )

    if not dataset_id:
        raise ValueError(
            "dataset_id unavailable "
            f"for Research {research_id}"
        )

    distributed = (
        pl.read_parquet(
            distributed_path
        )
    )

    path_analysis = (
        pl.read_parquet(
            path_analysis_path
        )
    )

    return {
        "paths": paths,
        "root": root,
        "definition": definition,
        "dataset_id": str(
            dataset_id
        ),
        "distributed_path": (
            distributed_path
        ),
        "path_analysis_path": (
            path_analysis_path
        ),
        "distributed": distributed,
        "path_analysis": path_analysis,
        "source_distributed_results_sha256": (
            _sha256_file(
                distributed_path
            )
        ),
        "source_path_analysis_sha256": (
            _sha256_file(
                path_analysis_path
            )
        ),
    }


def _experiment_ids(
    distributed: pl.DataFrame,
) -> list[str]:
    if (
        distributed.is_empty()
        or "experiment_id"
        not in distributed.columns
    ):
        return []

    return (
        distributed
        .select(
            pl.col(
                "experiment_id"
            )
            .cast(
                pl.String
            )
            .unique()
            .sort()
        )
        .to_series()
        .to_list()
    )


def _single_string_value(
    dataframe: pl.DataFrame,
    column: str,
) -> str | None:
    if (
        dataframe.is_empty()
        or column
        not in dataframe.columns
    ):
        return None

    values = (
        dataframe
        .select(
            pl.col(
                column
            )
            .drop_nulls()
            .cast(
                pl.String
            )
            .unique()
        )
        .to_series()
        .to_list()
    )

    if not values:
        return None

    if len(values) > 1:
        raise ValueError(
            f"Multiple values for "
            f"{column}: {values}"
        )

    return str(
        values[0]
    )


def _universe_for_experiment(
    distributed: pl.DataFrame,
    experiment_id: str,
) -> dict[str, Any]:
    experiment = (
        distributed
        .filter(
            pl.col(
                "experiment_id"
            )
            == experiment_id
        )
    )

    if experiment.is_empty():
        raise ValueError(
            "Experiment absent from "
            "distributed results: "
            f"{experiment_id}"
        )

    if "date" not in experiment.columns:
        raise ValueError(
            "distributed results missing "
            "date column."
        )

    if (
        "trade_status"
        not in experiment.columns
    ):
        raise ValueError(
            "distributed results missing "
            "trade_status column."
        )

    sessions = (
        experiment
        .select(
            [
                pl.col(
                    "date"
                )
                .cast(
                    pl.String
                ),
                pl.col(
                    "trade_status"
                )
                .cast(
                    pl.String
                ),
            ]
        )
        .unique(
            subset=[
                "date",
            ],
            maintain_order=True,
        )
    )

    sessions_total = (
        sessions.height
    )

    valid_trade_sessions = (
        sessions
        .filter(
            pl.col(
                "trade_status"
            )
            == "TRADE_1"
        )
        .height
    )

    no_trade_sessions = (
        sessions
        .filter(
            pl.col(
                "trade_status"
            )
            == "NO_TRADE_1"
        )
        .height
    )

    return {
        "experiment": experiment,
        "sessions": sessions,
        "sessions_total": int(
            sessions_total
        ),
        "valid_trade_sessions": int(
            valid_trade_sessions
        ),
        "no_trade_sessions": int(
            no_trade_sessions
        ),
        "config_sha256": (
            _single_string_value(
                experiment,
                "config_sha256",
            )
        ),
        "motor_version": (
            _single_string_value(
                experiment,
                "motor_version",
            )
        ),
        "rules_version": (
            _single_string_value(
                experiment,
                "rules_version",
            )
        ),
    }


def _path_for_experiment_trade(
    path_analysis: pl.DataFrame,
    experiment_id: str,
    trade: str,
) -> pl.DataFrame:
    if path_analysis.is_empty():
        return path_analysis

    return (
        path_analysis
        .filter(
            (
                pl.col(
                    "experiment_id"
                )
                == experiment_id
            )
            & (
                pl.col(
                    "trade"
                )
                == trade
            )
        )
        .sort(
            [
                "session_date",
                "target_points",
                "stop_points",
            ]
        )
    )


def _distinct_target_sessions(
    trade_path: pl.DataFrame,
    target_points: int,
) -> pl.DataFrame:
    if trade_path.is_empty():
        return trade_path

    return (
        trade_path
        .filter(
            pl.col(
                "target_points"
            )
            == target_points
        )
        .unique(
            subset=[
                "session_date",
                "trade",
                "target_points",
            ],
            maintain_order=True,
        )
        .sort(
            "session_date"
        )
    )


def _distinct_stop_sessions(
    trade_path: pl.DataFrame,
    stop_points: int,
) -> pl.DataFrame:
    if trade_path.is_empty():
        return trade_path

    return (
        trade_path
        .filter(
            pl.col(
                "stop_points"
            )
            == stop_points
        )
        .unique(
            subset=[
                "session_date",
                "trade",
                "stop_points",
            ],
            maintain_order=True,
        )
        .sort(
            "session_date"
        )
    )


def _count_true(
    dataframe: pl.DataFrame,
    column: str,
) -> int:
    if (
        dataframe.is_empty()
        or column
        not in dataframe.columns
    ):
        return 0

    value = (
        dataframe
        .select(
            pl.col(
                column
            )
            .fill_null(
                False
            )
            .cast(
                pl.Int64
            )
            .sum()
            .alias(
                "count"
            )
        )[
            "count"
        ][0]
    )

    if value is None:
        return 0

    return int(
        value
    )


def _count_relation(
    dataframe: pl.DataFrame,
    relation: str,
) -> int:
    if (
        dataframe.is_empty()
        or "target_zero_relation"
        not in dataframe.columns
    ):
        return 0

    return int(
        dataframe
        .filter(
            pl.col(
                "target_zero_relation"
            )
            == relation
        )
        .height
    )


def _event_key_expr(
    timestamp_column: str,
    trade_number_column: str,
) -> pl.Expr:
    return pl.struct(
        [
            pl.col(
                timestamp_column
            ),
            pl.col(
                trade_number_column
            ),
        ]
    )


def _target_then_zero_count(
    target_sessions: pl.DataFrame,
) -> int:
    if target_sessions.is_empty():
        return 0

    required = {
        "target_reached",
        "target_timestamp",
        "target_trade_number",
        "first_zero_return_occurred",
        "first_zero_return_timestamp",
        "first_zero_return_trade_number",
    }

    if not required.issubset(
        set(
            target_sessions.columns
        )
    ):
        return 0

    filtered = (
        target_sessions
        .filter(
            pl.col(
                "target_reached"
            )
            .fill_null(
                False
            )
            & pl.col(
                "first_zero_return_occurred"
            )
            .fill_null(
                False
            )
            & pl.col(
                "target_timestamp"
            )
            .is_not_null()
            & pl.col(
                "target_trade_number"
            )
            .is_not_null()
            & pl.col(
                "first_zero_return_timestamp"
            )
            .is_not_null()
            & pl.col(
                "first_zero_return_trade_number"
            )
            .is_not_null()
        )
    )

    if filtered.is_empty():
        return 0

    result = (
        filtered
        .filter(
            (
                pl.col(
                    "first_zero_return_timestamp"
                )
                > pl.col(
                    "target_timestamp"
                )
            )
            | (
                (
                    pl.col(
                        "first_zero_return_timestamp"
                    )
                    == pl.col(
                        "target_timestamp"
                    )
                )
                & (
                    pl.col(
                        "first_zero_return_trade_number"
                    )
                    > pl.col(
                        "target_trade_number"
                    )
                )
            )
        )
    )

    return int(
        result.height
    )


def _lineage_base(
    *,
    research_id: str,
    dataset_id: str,
    experiment_id: str,
    config_sha256: str | None,
    path_analysis_version: str | None,
    source_path_analysis_sha256: str,
    source_distributed_results_sha256: str,
) -> dict[str, Any]:
    return {
        "research_id": (
            research_id
        ),
        "dataset_id": (
            dataset_id
        ),
        "experiment_id": (
            experiment_id
        ),
        "config_sha256": (
            config_sha256
        ),
        "path_analysis_version": (
            path_analysis_version
        ),
        "source_path_analysis_sha256": (
            source_path_analysis_sha256
        ),
        "source_distributed_results_sha256": (
            source_distributed_results_sha256
        ),
        "aggregation_version": (
            PATH_AGGREGATION_VERSION
        ),
    }


def _build_target_analytics(
    *,
    research_id: str,
    dataset_id: str,
    experiment_id: str,
    universe: dict[str, Any],
    trade_path: pl.DataFrame,
    source_path_analysis_sha256: str,
    source_distributed_results_sha256: str,
    trade: str,
) -> list[dict[str, Any]]:
    rows: list[
        dict[str, Any]
    ] = []

    path_analysis_version = (
        _single_string_value(
            trade_path,
            "path_analysis_version",
        )
        if not trade_path.is_empty()
        else None
    )

    if (
        trade == "TRADE_1"
    ):
        valid_trade_sessions = int(
            universe[
                "valid_trade_sessions"
            ]
        )

    else:
        experiment = universe[
            "experiment"
        ]

        if (
            "trade2_executed"
            in experiment.columns
        ):
            valid_trade_sessions = int(
                experiment
                .filter(
                    pl.col(
                        "trade2_executed"
                    )
                    .fill_null(
                        False
                    )
                )
                .select(
                    pl.col(
                        "date"
                    )
                    .n_unique()
                    .alias(
                        "count"
                    )
                )[
                    "count"
                ][0]
            )
        else:
            valid_trade_sessions = 0

    sessions_total = int(
        universe[
            "sessions_total"
        ]
    )

    no_trade_sessions = int(
        universe[
            "no_trade_sessions"
        ]
    )

    lineage = _lineage_base(
        research_id=research_id,
        dataset_id=dataset_id,
        experiment_id=experiment_id,
        config_sha256=(
            universe[
                "config_sha256"
            ]
        ),
        path_analysis_version=(
            path_analysis_version
        ),
        source_path_analysis_sha256=(
            source_path_analysis_sha256
        ),
        source_distributed_results_sha256=(
            source_distributed_results_sha256
        ),
    )

    for target_points in TARGET_LEVELS:
        target_sessions = (
            _distinct_target_sessions(
                trade_path,
                target_points,
            )
        )

        target_reached_count = (
            _count_true(
                target_sessions,
                "target_reached",
            )
        )

        before_count = (
            _count_relation(
                target_sessions,
                (
                    "TARGET_BEFORE_"
                    "FIRST_ZERO_RETURN"
                ),
            )
        )

        after_count = (
            _count_relation(
                target_sessions,
                (
                    "TARGET_AFTER_"
                    "FIRST_ZERO_RETURN"
                ),
            )
        )

        target_never_reached_count = (
            max(
                valid_trade_sessions
                - target_reached_count,
                0,
            )
        )

        then_zero_count = (
            _target_then_zero_count(
                target_sessions
            )
        )

        (
            target_reached_pct,
            target_reached_pct_status,
        ) = _percentage(
            target_reached_count,
            valid_trade_sessions,
        )

        (
            before_pct,
            before_pct_status,
        ) = _percentage(
            before_count,
            valid_trade_sessions,
        )

        (
            after_pct,
            after_pct_status,
        ) = _percentage(
            after_count,
            valid_trade_sessions,
        )

        (
            then_zero_pct,
            then_zero_pct_status,
        ) = _percentage(
            then_zero_count,
            target_reached_count,
        )

        row = {
            **lineage,
            "trade": trade,
            "target_points": int(
                target_points
            ),
            "target_label": (
                "1000+"
                if target_points
                == 1000
                else str(
                    target_points
                )
            ),
            "sessions_total": (
                sessions_total
            ),
            "valid_trade_sessions": (
                valid_trade_sessions
            ),
            "no_trade_sessions": (
                no_trade_sessions
            ),

            "target_reached_count": (
                target_reached_count
            ),
            "target_reached_denominator": (
                valid_trade_sessions
            ),
            "target_reached_pct": (
                target_reached_pct
            ),
            "target_reached_pct_status": (
                target_reached_pct_status
            ),

            "target_before_first_zero_count": (
                before_count
            ),
            "target_before_first_zero_denominator": (
                valid_trade_sessions
            ),
            "target_before_first_zero_pct": (
                before_pct
            ),
            "target_before_first_zero_pct_status": (
                before_pct_status
            ),

            "target_after_first_zero_count": (
                after_count
            ),
            "target_after_first_zero_denominator": (
                valid_trade_sessions
            ),
            "target_after_first_zero_pct": (
                after_pct
            ),
            "target_after_first_zero_pct_status": (
                after_pct_status
            ),

            "target_never_reached_count": (
                target_never_reached_count
            ),

            "target_then_zero_count": (
                then_zero_count
            ),
            "target_then_zero_denominator": (
                target_reached_count
            ),
            "target_then_zero_pct": (
                then_zero_pct
            ),
            "target_then_zero_pct_status": (
                then_zero_pct_status
            ),
        }

        rows.append(
            row
        )

    return rows


def _build_target_stop_matrix(
    *,
    research_id: str,
    dataset_id: str,
    experiment_id: str,
    universe: dict[str, Any],
    trade_path: pl.DataFrame,
    source_path_analysis_sha256: str,
    source_distributed_results_sha256: str,
    trade: str,
) -> list[dict[str, Any]]:
    rows: list[
        dict[str, Any]
    ] = []

    path_analysis_version = (
        _single_string_value(
            trade_path,
            "path_analysis_version",
        )
        if not trade_path.is_empty()
        else None
    )

    if trade == "TRADE_1":
        valid_trade_sessions = int(
            universe[
                "valid_trade_sessions"
            ]
        )
    else:
        experiment = universe[
            "experiment"
        ]

        if (
            "trade2_executed"
            in experiment.columns
        ):
            valid_trade_sessions = int(
                experiment
                .filter(
                    pl.col(
                        "trade2_executed"
                    )
                    .fill_null(
                        False
                    )
                )
                .select(
                    pl.col(
                        "date"
                    )
                    .n_unique()
                    .alias(
                        "count"
                    )
                )[
                    "count"
                ][0]
            )
        else:
            valid_trade_sessions = 0

    lineage = _lineage_base(
        research_id=research_id,
        dataset_id=dataset_id,
        experiment_id=experiment_id,
        config_sha256=(
            universe[
                "config_sha256"
            ]
        ),
        path_analysis_version=(
            path_analysis_version
        ),
        source_path_analysis_sha256=(
            source_path_analysis_sha256
        ),
        source_distributed_results_sha256=(
            source_distributed_results_sha256
        ),
    )

    for target_points in TARGET_LEVELS:
        for stop_points in STOP_LEVELS:
            pair = (
                trade_path
                .filter(
                    (
                        pl.col(
                            "target_points"
                        )
                        == target_points
                    )
                    & (
                        pl.col(
                            "stop_points"
                        )
                        == stop_points
                    )
                )
                if not trade_path.is_empty()
                else trade_path
            )

            target_reached_count = (
                _count_true(
                    pair,
                    "target_reached",
                )
            )

            stop_after_target_count = (
                _count_true(
                    pair,
                    "stop_after_target",
                )
            )

            stop_before_target_count = (
                _count_true(
                    pair,
                    "stop_before_target",
                )
            )

            (
                stop_after_target_pct,
                stop_after_target_status,
            ) = _percentage(
                stop_after_target_count,
                target_reached_count,
            )

            (
                stop_before_target_pct,
                stop_before_target_status,
            ) = _percentage(
                stop_before_target_count,
                valid_trade_sessions,
            )

            rows.append(
                {
                    **lineage,
                    "trade": trade,
                    "target_points": int(
                        target_points
                    ),
                    "stop_points": int(
                        stop_points
                    ),
                    "sessions_total": int(
                        universe[
                            "sessions_total"
                        ]
                    ),
                    "valid_trade_sessions": (
                        valid_trade_sessions
                    ),

                    "target_reached_count": (
                        target_reached_count
                    ),

                    "stop_after_target_count": (
                        stop_after_target_count
                    ),
                    "stop_after_target_denominator": (
                        target_reached_count
                    ),
                    "stop_after_target_pct": (
                        stop_after_target_pct
                    ),
                    "stop_after_target_pct_status": (
                        stop_after_target_status
                    ),

                    "stop_before_target_count": (
                        stop_before_target_count
                    ),
                    "stop_before_target_denominator": (
                        valid_trade_sessions
                    ),
                    "stop_before_target_pct": (
                        stop_before_target_pct
                    ),
                    "stop_before_target_pct_status": (
                        stop_before_target_status
                    ),
                }
            )

    return rows


def _build_stop_analytics(
    *,
    research_id: str,
    dataset_id: str,
    experiment_id: str,
    universe: dict[str, Any],
    trade_path: pl.DataFrame,
    source_path_analysis_sha256: str,
    source_distributed_results_sha256: str,
    trade: str,
) -> list[dict[str, Any]]:
    rows: list[
        dict[str, Any]
    ] = []

    path_analysis_version = (
        _single_string_value(
            trade_path,
            "path_analysis_version",
        )
        if not trade_path.is_empty()
        else None
    )

    if trade == "TRADE_1":
        valid_trade_sessions = int(
            universe[
                "valid_trade_sessions"
            ]
        )
    else:
        experiment = universe[
            "experiment"
        ]

        if (
            "trade2_executed"
            in experiment.columns
        ):
            valid_trade_sessions = int(
                experiment
                .filter(
                    pl.col(
                        "trade2_executed"
                    )
                    .fill_null(
                        False
                    )
                )
                .select(
                    pl.col(
                        "date"
                    )
                    .n_unique()
                    .alias(
                        "count"
                    )
                )[
                    "count"
                ][0]
            )
        else:
            valid_trade_sessions = 0

    lineage = _lineage_base(
        research_id=research_id,
        dataset_id=dataset_id,
        experiment_id=experiment_id,
        config_sha256=(
            universe[
                "config_sha256"
            ]
        ),
        path_analysis_version=(
            path_analysis_version
        ),
        source_path_analysis_sha256=(
            source_path_analysis_sha256
        ),
        source_distributed_results_sha256=(
            source_distributed_results_sha256
        ),
    )

    for stop_points in STOP_LEVELS:
        stop_sessions = (
            _distinct_stop_sessions(
                trade_path,
                stop_points,
            )
        )

        stop_reached_count = (
            _count_true(
                stop_sessions,
                "stop_reached",
            )
        )

        if trade_path.is_empty():
            stop_before_any_target_count = 0

        else:
            stop_pairs = (
                trade_path
                .filter(
                    pl.col(
                        "stop_points"
                    )
                    == stop_points
                )
                .group_by(
                    "session_date"
                )
                .agg(
                    [
                        pl.col(
                            "stop_reached"
                        )
                        .fill_null(
                            False
                        )
                        .any()
                        .alias(
                            "stop_reached"
                        ),
                        pl.col(
                            "stop_before_target"
                        )
                        .fill_null(
                            False
                        )
                        .all()
                        .alias(
                            "stop_before_all_targets"
                        ),
                    ]
                )
            )

            stop_before_any_target_count = int(
                stop_pairs
                .filter(
                    pl.col(
                        "stop_reached"
                    )
                    & pl.col(
                        "stop_before_all_targets"
                    )
                )
                .height
            )

        (
            stop_reached_pct,
            stop_reached_status,
        ) = _percentage(
            stop_reached_count,
            valid_trade_sessions,
        )

        (
            stop_before_any_target_pct,
            stop_before_any_target_status,
        ) = _percentage(
            stop_before_any_target_count,
            valid_trade_sessions,
        )

        rows.append(
            {
                **lineage,
                "trade": trade,
                "stop_points": int(
                    stop_points
                ),
                "sessions_total": int(
                    universe[
                        "sessions_total"
                    ]
                ),
                "valid_trade_sessions": (
                    valid_trade_sessions
                ),

                "stop_reached_count": (
                    stop_reached_count
                ),
                "stop_reached_denominator": (
                    valid_trade_sessions
                ),
                "stop_reached_pct": (
                    stop_reached_pct
                ),
                "stop_reached_pct_status": (
                    stop_reached_status
                ),

                "stop_before_any_target_count": (
                    stop_before_any_target_count
                ),
                "stop_before_any_target_denominator": (
                    valid_trade_sessions
                ),
                "stop_before_any_target_pct": (
                    stop_before_any_target_pct
                ),
                "stop_before_any_target_pct_status": (
                    stop_before_any_target_status
                ),
            }
        )

    return rows


def _trade2_universe_counts(
    experiment: pl.DataFrame,
) -> dict[str, int]:
    def unique_dates_true(
        column: str,
    ) -> int:
        if column not in experiment.columns:
            return 0

        result = (
            experiment
            .filter(
                pl.col(
                    column
                )
                .fill_null(
                    False
                )
            )
            .select(
                pl.col(
                    "date"
                )
                .n_unique()
                .alias(
                    "count"
                )
            )[
                "count"
            ][0]
        )

        return int(
            result
            or 0
        )

    return {
        "trade2_eligible_count": (
            unique_dates_true(
                "trade2_eligible"
            )
        ),
        "trade2_occurred_count": (
            unique_dates_true(
                "trade2_occurred"
            )
        ),
        "trade2_executed_count": (
            unique_dates_true(
                "trade2_executed"
            )
        ),
    }


def _trade2_return_to_entry_count(
    trade2_path: pl.DataFrame,
) -> int:
    if trade2_path.is_empty():
        return 0

    sessions = (
        trade2_path
        .unique(
            subset=[
                "session_date",
                "trade",
            ],
            maintain_order=True,
        )
    )

    return _count_true(
        sessions,
        "first_zero_return_occurred",
    )


def _build_trade2_analytics(
    *,
    research_id: str,
    dataset_id: str,
    experiment_id: str,
    universe: dict[str, Any],
    trade1_path: pl.DataFrame,
    trade2_path: pl.DataFrame,
    source_path_analysis_sha256: str,
    source_distributed_results_sha256: str,
) -> list[dict[str, Any]]:
    rows: list[
        dict[str, Any]
    ] = []

    experiment = universe[
        "experiment"
    ]

    trade2_counts = (
        _trade2_universe_counts(
            experiment
        )
    )

    trade2_executed_count = int(
        trade2_counts[
            "trade2_executed_count"
        ]
    )

    valid_trade_sessions = int(
        universe[
            "valid_trade_sessions"
        ]
    )

    (
        trade2_occurrence_pct,
        trade2_occurrence_status,
    ) = _percentage(
        trade2_executed_count,
        valid_trade_sessions,
    )

    trade2_return_count = (
        _trade2_return_to_entry_count(
            trade2_path
        )
    )

    (
        trade2_return_pct,
        trade2_return_status,
    ) = _percentage(
        trade2_return_count,
        trade2_executed_count,
    )

    path_analysis_version = (
        _single_string_value(
            (
                trade2_path
                if not trade2_path.is_empty()
                else trade1_path
            ),
            "path_analysis_version",
        )
        if (
            not trade2_path.is_empty()
            or not trade1_path.is_empty()
        )
        else None
    )

    lineage = _lineage_base(
        research_id=research_id,
        dataset_id=dataset_id,
        experiment_id=experiment_id,
        config_sha256=(
            universe[
                "config_sha256"
            ]
        ),
        path_analysis_version=(
            path_analysis_version
        ),
        source_path_analysis_sha256=(
            source_path_analysis_sha256
        ),
        source_distributed_results_sha256=(
            source_distributed_results_sha256
        ),
    )

    for (
        trade1_stop_points
    ) in STOP_LEVELS:
        trade1_stop_sessions = (
            _distinct_stop_sessions(
                trade1_path,
                trade1_stop_points,
            )
        )

        trade1_stopped_count = (
            _count_true(
                trade1_stop_sessions,
                "stop_reached",
            )
        )

        for target_points in TARGET_LEVELS:
            target_sessions = (
                _distinct_target_sessions(
                    trade2_path,
                    target_points,
                )
            )

            trade2_target_reached_count = (
                _count_true(
                    target_sessions,
                    "target_reached",
                )
            )

            (
                target_pct,
                target_pct_status,
            ) = _percentage(
                trade2_target_reached_count,
                trade2_executed_count,
            )

            for stop_points in STOP_LEVELS:
                stop_sessions = (
                    _distinct_stop_sessions(
                        trade2_path,
                        stop_points,
                    )
                )

                trade2_stop_reached_count = (
                    _count_true(
                        stop_sessions,
                        "stop_reached",
                    )
                )

                (
                    stop_pct,
                    stop_pct_status,
                ) = _percentage(
                    trade2_stop_reached_count,
                    trade2_executed_count,
                )

                rows.append(
                    {
                        **lineage,

                        "sessions_total": int(
                            universe[
                                "sessions_total"
                            ]
                        ),
                        "valid_trade_sessions": (
                            valid_trade_sessions
                        ),

                        "trade1_stop_points": int(
                            trade1_stop_points
                        ),
                        "trade1_stopped_count": (
                            trade1_stopped_count
                        ),

                        "trade2_eligible_count": int(
                            trade2_counts[
                                "trade2_eligible_count"
                            ]
                        ),
                        "trade2_occurred_count": int(
                            trade2_counts[
                                "trade2_occurred_count"
                            ]
                        ),
                        "trade2_executed_count": (
                            trade2_executed_count
                        ),

                        "trade2_occurrence_numerator": (
                            trade2_executed_count
                        ),
                        "trade2_occurrence_denominator": (
                            valid_trade_sessions
                        ),
                        "trade2_occurrence_pct": (
                            trade2_occurrence_pct
                        ),
                        "trade2_occurrence_pct_status": (
                            trade2_occurrence_status
                        ),

                        "trade2_return_to_entry_count": (
                            trade2_return_count
                        ),
                        "trade2_return_to_entry_denominator": (
                            trade2_executed_count
                        ),
                        "trade2_return_to_entry_pct": (
                            trade2_return_pct
                        ),
                        "trade2_return_to_entry_pct_status": (
                            trade2_return_status
                        ),

                        "trade2_target_points": int(
                            target_points
                        ),
                        "trade2_target_reached_count": (
                            trade2_target_reached_count
                        ),
                        "trade2_target_reached_denominator": (
                            trade2_executed_count
                        ),
                        "trade2_target_reached_pct": (
                            target_pct
                        ),
                        "trade2_target_reached_pct_status": (
                            target_pct_status
                        ),

                        "trade2_stop_points": int(
                            stop_points
                        ),
                        "trade2_stop_reached_count": (
                            trade2_stop_reached_count
                        ),
                        "trade2_stop_reached_denominator": (
                            trade2_executed_count
                        ),
                        "trade2_stop_reached_pct": (
                            stop_pct
                        ),
                        "trade2_stop_reached_pct_status": (
                            stop_pct_status
                        ),
                    }
                )

    return rows


def _rows_to_frame(
    rows: list[
        dict[str, Any]
    ],
    sort_columns: list[str],
) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame()

    dataframe = (
        pl.DataFrame(
            rows,
            infer_schema_length=None,
        )
    )

    existing_sort = [
        column
        for column in sort_columns
        if column
        in dataframe.columns
    ]

    if existing_sort:
        dataframe = (
            dataframe.sort(
                existing_sort
            )
        )

    return dataframe


def build_path_aggregation(
    research_id: str,
) -> dict[str, pl.DataFrame]:
    inputs = _require_inputs(
        research_id
    )

    distributed = inputs[
        "distributed"
    ]

    path_analysis = inputs[
        "path_analysis"
    ]

    dataset_id = inputs[
        "dataset_id"
    ]

    experiment_ids = (
        _experiment_ids(
            distributed
        )
    )

    target_rows: list[
        dict[str, Any]
    ] = []

    matrix_rows: list[
        dict[str, Any]
    ] = []

    stop_rows: list[
        dict[str, Any]
    ] = []

    trade2_rows: list[
        dict[str, Any]
    ] = []

    for experiment_id in experiment_ids:
        universe = (
            _universe_for_experiment(
                distributed,
                experiment_id,
            )
        )

        trade1_path = (
            _path_for_experiment_trade(
                path_analysis,
                experiment_id,
                "TRADE_1",
            )
        )

        trade2_path = (
            _path_for_experiment_trade(
                path_analysis,
                experiment_id,
                "TRADE_2",
            )
        )

        target_rows.extend(
            _build_target_analytics(
                research_id=research_id,
                dataset_id=dataset_id,
                experiment_id=experiment_id,
                universe=universe,
                trade_path=trade1_path,
                source_path_analysis_sha256=(
                    inputs[
                        "source_path_analysis_sha256"
                    ]
                ),
                source_distributed_results_sha256=(
                    inputs[
                        "source_distributed_results_sha256"
                    ]
                ),
                trade="TRADE_1",
            )
        )

        matrix_rows.extend(
            _build_target_stop_matrix(
                research_id=research_id,
                dataset_id=dataset_id,
                experiment_id=experiment_id,
                universe=universe,
                trade_path=trade1_path,
                source_path_analysis_sha256=(
                    inputs[
                        "source_path_analysis_sha256"
                    ]
                ),
                source_distributed_results_sha256=(
                    inputs[
                        "source_distributed_results_sha256"
                    ]
                ),
                trade="TRADE_1",
            )
        )

        stop_rows.extend(
            _build_stop_analytics(
                research_id=research_id,
                dataset_id=dataset_id,
                experiment_id=experiment_id,
                universe=universe,
                trade_path=trade1_path,
                source_path_analysis_sha256=(
                    inputs[
                        "source_path_analysis_sha256"
                    ]
                ),
                source_distributed_results_sha256=(
                    inputs[
                        "source_distributed_results_sha256"
                    ]
                ),
                trade="TRADE_1",
            )
        )

        trade2_rows.extend(
            _build_trade2_analytics(
                research_id=research_id,
                dataset_id=dataset_id,
                experiment_id=experiment_id,
                universe=universe,
                trade1_path=trade1_path,
                trade2_path=trade2_path,
                source_path_analysis_sha256=(
                    inputs[
                        "source_path_analysis_sha256"
                    ]
                ),
                source_distributed_results_sha256=(
                    inputs[
                        "source_distributed_results_sha256"
                    ]
                ),
            )
        )

    return {
        "target_analytics": (
            _rows_to_frame(
                target_rows,
                [
                    "experiment_id",
                    "trade",
                    "target_points",
                ],
            )
        ),
        "target_stop_matrix": (
            _rows_to_frame(
                matrix_rows,
                [
                    "experiment_id",
                    "trade",
                    "target_points",
                    "stop_points",
                ],
            )
        ),
        "stop_analytics": (
            _rows_to_frame(
                stop_rows,
                [
                    "experiment_id",
                    "trade",
                    "stop_points",
                ],
            )
        ),
        "trade2_analytics": (
            _rows_to_frame(
                trade2_rows,
                [
                    "experiment_id",
                    "trade1_stop_points",
                    "trade2_target_points",
                    "trade2_stop_points",
                ],
            )
        ),
    }


def _write_parquet_deterministic(
    dataframe: pl.DataFrame,
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = dataframe.to_arrow()

    pq.write_table(
        table,
        path,
        compression="zstd",
        use_dictionary=False,
        write_statistics=True,
    )


def write_path_aggregation(
    research_id: str,
) -> dict[str, Any]:
    inputs = _require_inputs(
        research_id
    )

    root = inputs[
        "root"
    ]

    frames = (
        build_path_aggregation(
            research_id
        )
    )

    outputs = {
        "target_analytics": (
            root
            / TARGET_ANALYTICS_ARTIFACT
        ),
        "target_stop_matrix": (
            root
            / TARGET_STOP_MATRIX_ARTIFACT
        ),
        "stop_analytics": (
            root
            / STOP_ANALYTICS_ARTIFACT
        ),
        "trade2_analytics": (
            root
            / TRADE2_ANALYTICS_ARTIFACT
        ),
    }

    result: dict[
        str,
        Any
    ] = {
        "research_id": (
            research_id
        ),
        "aggregation_version": (
            PATH_AGGREGATION_VERSION
        ),
        "source_path_analysis_sha256": (
            inputs[
                "source_path_analysis_sha256"
            ]
        ),
        "source_distributed_results_sha256": (
            inputs[
                "source_distributed_results_sha256"
            ]
        ),
        "artifacts": {},
    }

    for name, path in outputs.items():
        dataframe = frames[
            name
        ]

        _write_parquet_deterministic(
            dataframe,
            path,
        )

        result[
            "artifacts"
        ][
            name
        ] = {
            "path": str(
                path.resolve()
            ),
            "rows": int(
                dataframe.height
            ),
            "sha256": (
                _sha256_file(
                    path
                )
            ),
        }

    return result


def load_path_target_analytics(
    research_id: str,
) -> pl.DataFrame:
    path = (
        Path(
            research_paths(
                research_id
            )[
                "root"
            ]
        )
        / TARGET_ANALYTICS_ARTIFACT
    )

    if not path.exists():
        return pl.DataFrame()

    return pl.read_parquet(
        path
    )


def load_path_target_stop_matrix(
    research_id: str,
) -> pl.DataFrame:
    path = (
        Path(
            research_paths(
                research_id
            )[
                "root"
            ]
        )
        / TARGET_STOP_MATRIX_ARTIFACT
    )

    if not path.exists():
        return pl.DataFrame()

    return pl.read_parquet(
        path
    )


def load_path_stop_analytics(
    research_id: str,
) -> pl.DataFrame:
    path = (
        Path(
            research_paths(
                research_id
            )[
                "root"
            ]
        )
        / STOP_ANALYTICS_ARTIFACT
    )

    if not path.exists():
        return pl.DataFrame()

    return pl.read_parquet(
        path
    )


def load_path_trade2_analytics(
    research_id: str,
) -> pl.DataFrame:
    path = (
        Path(
            research_paths(
                research_id
            )[
                "root"
            ]
        )
        / TRADE2_ANALYTICS_ARTIFACT
    )

    if not path.exists():
        return pl.DataFrame()

    return pl.read_parquet(
        path
    )
