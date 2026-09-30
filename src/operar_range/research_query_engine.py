from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from operar_range.research_workspace import (
    load_research_definition,
    load_research_manifest,
    research_paths,
)


QUERY_ENGINE_VERSION = (
    "research-query-engine-v1"
)


TRADE1_OUTCOMES = {
    "WIN",
    "LOSS",
    "BREAK_EVEN",
    "NO_TRADE",
}

RESULT_SIGNS = {
    "POSITIVE",
    "NEGATIVE",
    "ZERO",
}

DIRECTIONS = {
    "LONG",
    "SHORT",
}


@dataclass(frozen=True)
class ResearchQuery:
    research_id: str

    experiment_id: str | None = None

    date: str | None = None
    year: int | None = None
    month: int | None = None

    trade1_outcome: str | None = None

    trade2_enabled: bool | None = None
    trade2_eligible: bool | None = None
    trade2_executed: bool | None = None
    trade2_winner: bool | None = None
    trade2_loser: bool | None = None
    trade2_breakeven: bool | None = None

    direction: str | None = None

    result_sign: str | None = None

    runner_occurred: bool | None = None


def _validate_query(
    query: ResearchQuery,
) -> None:
    if not query.research_id:
        raise ValueError(
            "research_id is required."
        )

    if (
        query.trade1_outcome is not None
        and query.trade1_outcome
        not in TRADE1_OUTCOMES
    ):
        raise ValueError(
            "Unsupported trade1_outcome: "
            f"{query.trade1_outcome}"
        )

    if (
        query.result_sign is not None
        and query.result_sign
        not in RESULT_SIGNS
    ):
        raise ValueError(
            "Unsupported result_sign: "
            f"{query.result_sign}"
        )

    if (
        query.direction is not None
        and query.direction
        not in DIRECTIONS
    ):
        raise ValueError(
            "Unsupported direction: "
            f"{query.direction}"
        )

    if (
        query.year is not None
        and query.year < 1
    ):
        raise ValueError(
            "year must be positive."
        )

    if (
        query.month is not None
        and query.month
        not in range(
            1,
            13,
        )
    ):
        raise ValueError(
            "month must be between 1 and 12."
        )


def _require_research(
    research_id: str,
) -> tuple[
    dict[str, Path],
    dict[str, Any],
    dict[str, Any],
]:
    paths = research_paths(
        research_id
    )

    root = paths[
        "root"
    ]

    if not root.exists():
        raise FileNotFoundError(
            f"Research not found: "
            f"{research_id}"
        )

    distributed = paths[
        "distributed_results"
    ]

    if not distributed.exists():
        raise FileNotFoundError(
            "Research distributed results "
            "not found: "
            f"{research_id}"
        )

    definition = (
        load_research_definition(
            research_id
        )
    )

    manifest = (
        load_research_manifest(
            research_id
        )
    )

    return (
        paths,
        definition,
        manifest,
    )


def _scan_research_rows(
    paths: dict[str, Path],
) -> pl.LazyFrame:
    distributed = (
        pl.scan_parquet(
            paths[
                "distributed_results"
            ]
        )
    )

    valid_path = paths[
        "valid"
    ]

    if not valid_path.exists():
        return (
            distributed
            .with_columns(
                pl.lit(
                    None,
                    dtype=pl.Boolean,
                )
                .alias(
                    "query_trade2_enabled"
                )
            )
        )

    valid_schema = (
        pl.scan_parquet(
            valid_path
        )
        .collect_schema()
    )

    if (
        "trade2_enabled"
        not in valid_schema.names()
    ):
        return (
            distributed
            .with_columns(
                pl.lit(
                    None,
                    dtype=pl.Boolean,
                )
                .alias(
                    "query_trade2_enabled"
                )
            )
        )

    valid = (
        pl.scan_parquet(
            valid_path
        )
        .select(
            [
                pl.col(
                    "experiment_id"
                ),
                pl.col(
                    "trade2_enabled"
                )
                .alias(
                    "query_trade2_enabled"
                ),
            ]
        )
        .unique(
            subset=[
                "experiment_id",
            ]
        )
    )

    return distributed.join(
        valid,
        on="experiment_id",
        how="left",
    )


def _with_query_columns(
    lazy: pl.LazyFrame,
) -> pl.LazyFrame:
    return lazy.with_columns(
        [
            pl.col(
                "date"
            )
            .str.strptime(
                pl.Date,
                format="%Y-%m-%d",
                strict=False,
            )
            .alias(
                "_query_date"
            ),

            (
                pl.col(
                    "final_reason"
                )
                == "EXIT_RUNNER_CANDLE"
            )
            .fill_null(
                False
            )
            .alias(
                "query_runner_occurred"
            ),
        ]
    )


def _filter_trade1_outcome(
    lazy: pl.LazyFrame,
    outcome: str,
) -> pl.LazyFrame:
    if outcome == "NO_TRADE":
        return lazy.filter(
            pl.col(
                "trade_status"
            )
            == "NO_TRADE_1"
        )

    traded = (
        pl.col(
            "trade_status"
        )
        != "NO_TRADE_1"
    )

    points = pl.col(
        "trade1_result_points"
    )

    if outcome == "WIN":
        expression = (
            traded
            & points.is_not_null()
            & (
                points > 0
            )
        )

    elif outcome == "LOSS":
        expression = (
            traded
            & points.is_not_null()
            & (
                points < 0
            )
        )

    elif outcome == "BREAK_EVEN":
        expression = (
            traded
            & points.is_not_null()
            & (
                points == 0
            )
        )

    else:
        raise ValueError(
            f"Unsupported Trade 1 outcome: "
            f"{outcome}"
        )

    return lazy.filter(
        expression
    )


def _filter_result_sign(
    lazy: pl.LazyFrame,
    result_sign: str,
) -> pl.LazyFrame:
    points = pl.col(
        "consolidated_result_points"
    )

    if result_sign == "POSITIVE":
        expression = (
            points.is_not_null()
            & (
                points > 0
            )
        )

    elif result_sign == "NEGATIVE":
        expression = (
            points.is_not_null()
            & (
                points < 0
            )
        )

    elif result_sign == "ZERO":
        expression = (
            points.is_not_null()
            & (
                points == 0
            )
        )

    else:
        raise ValueError(
            "Unsupported result_sign: "
            f"{result_sign}"
        )

    return lazy.filter(
        expression
    )


def _apply_filters(
    lazy: pl.LazyFrame,
    query: ResearchQuery,
) -> pl.LazyFrame:
    if query.experiment_id is not None:
        lazy = lazy.filter(
            pl.col(
                "experiment_id"
            )
            == query.experiment_id
        )

    if query.date is not None:
        lazy = lazy.filter(
            pl.col(
                "date"
            )
            == query.date
        )

    if query.year is not None:
        lazy = lazy.filter(
            pl.col(
                "_query_date"
            )
            .dt.year()
            == query.year
        )

    if query.month is not None:
        lazy = lazy.filter(
            pl.col(
                "_query_date"
            )
            .dt.month()
            == query.month
        )

    if query.trade1_outcome is not None:
        lazy = _filter_trade1_outcome(
            lazy,
            query.trade1_outcome,
        )

    boolean_filters = (
        (
            "query_trade2_enabled",
            query.trade2_enabled,
        ),
        (
            "trade2_eligible",
            query.trade2_eligible,
        ),
        (
            "trade2_executed",
            query.trade2_executed,
        ),
        (
            "trade2_winner",
            query.trade2_winner,
        ),
        (
            "trade2_loser",
            query.trade2_loser,
        ),
        (
            "trade2_breakeven",
            query.trade2_breakeven,
        ),
        (
            "query_runner_occurred",
            query.runner_occurred,
        ),
    )

    for (
        column,
        expected,
    ) in boolean_filters:
        if expected is None:
            continue

        lazy = lazy.filter(
            pl.col(
                column
            )
            .fill_null(
                False
            )
            == expected
        )

    if query.direction is not None:
        lazy = lazy.filter(
            pl.col(
                "direction"
            )
            == query.direction
        )

    if query.result_sign is not None:
        lazy = _filter_result_sign(
            lazy,
            query.result_sign,
        )

    return lazy


def _experiment_exists(
    paths: dict[str, Path],
    experiment_id: str,
) -> bool:
    valid_path = paths[
        "valid"
    ]

    if valid_path.exists():
        result = (
            pl.scan_parquet(
                valid_path
            )
            .filter(
                pl.col(
                    "experiment_id"
                )
                == experiment_id
            )
            .select(
                pl.len()
                .alias(
                    "count"
                )
            )
            .collect(
                engine="streaming"
            )
        )

        if int(
            result[
                "count"
            ][0]
        ) > 0:
            return True

    distributed_path = paths[
        "distributed_results"
    ]

    result = (
        pl.scan_parquet(
            distributed_path
        )
        .filter(
            pl.col(
                "experiment_id"
            )
            == experiment_id
        )
        .select(
            pl.len()
            .alias(
                "count"
            )
        )
        .collect(
            engine="streaming"
        )
    )

    return (
        int(
            result[
                "count"
            ][0]
        )
        > 0
    )


def execute_query(
    query: ResearchQuery,
) -> dict[str, Any]:
    _validate_query(
        query
    )

    (
        paths,
        definition,
        manifest,
    ) = _require_research(
        query.research_id
    )

    if (
        query.experiment_id is not None
        and not _experiment_exists(
            paths,
            query.experiment_id,
        )
    ):
        raise ValueError(
            "Experiment not found in "
            "Research: "
            f"{query.experiment_id}"
        )

    lazy = _scan_research_rows(
        paths
    )

    lazy = _with_query_columns(
        lazy
    )

    lazy = _apply_filters(
        lazy,
        query,
    )

    result = (
        lazy
        .drop(
            [
                "_query_date",
            ]
        )
        .sort(
            [
                "date",
                "experiment_id",
                "execution_unit_id",
            ]
        )
        .collect(
            engine="streaming"
        )
    )

    if result.height:
        session_count = (
            result.select(
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

        experiment_count = (
            result.select(
                pl.col(
                    "experiment_id"
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
        session_count = 0
        experiment_count = 0

    dataset_id = (
        manifest.get(
            "dataset_id"
        )
        or definition.get(
            "dataset_id"
        )
        or definition.get(
            "dataset_key"
        )
    )

    return {
        "query_engine_version": (
            QUERY_ENGINE_VERSION
        ),
        "research_id": (
            query.research_id
        ),
        "dataset_id": (
            dataset_id
        ),
        "sessions": int(
            session_count
        ),
        "experiments": int(
            experiment_count
        ),
        "rows_found": int(
            result.height
        ),
        "rows": result,
    }
