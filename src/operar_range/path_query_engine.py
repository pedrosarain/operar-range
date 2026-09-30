from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from operar_range.research_workspace import (
    load_research_definition,
    research_paths,
)


PATH_QUERY_VERSION = (
    "path-query-drilldown-v1"
)


@dataclass(frozen=True)
class PathQuery:
    research_id: str
    experiment_id: str | None = None
    trade: str | None = None
    direction: str | None = None

    target_points: int | None = None
    target_reached: bool | None = None
    target_before_first_zero: bool | None = None
    target_after_first_zero: bool | None = None
    target_then_zero: bool | None = None

    stop_points: int | None = None
    stop_reached: bool | None = None
    stop_before_target: bool | None = None
    stop_after_target: bool | None = None
    stop_before_any_target: bool | None = None

    trade2_eligible: bool | None = None
    trade2_occurred: bool | None = None
    trade2_executed: bool | None = None
    trade2_return_to_entry: bool | None = None

    trade2_target_points: int | None = None
    trade2_target_reached: bool | None = None
    trade2_stop_points: int | None = None
    trade2_stop_reached: bool | None = None

    session_date: str | None = None


def _require_research(
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

    if not root.exists():
        raise FileNotFoundError(
            f"Research not found: "
            f"{research_id}"
        )

    path_analysis_path = (
        root
        / "path_analysis.parquet"
    )

    distributed_path = Path(
        paths[
            "distributed_results"
        ]
    )

    trajectory_manifest_path = Path(
        paths[
            "trajectory_manifest"
        ]
    )

    if not path_analysis_path.exists():
        raise FileNotFoundError(
            "path_analysis.parquet not found "
            f"for Research {research_id}"
        )

    if not distributed_path.exists():
        raise FileNotFoundError(
            "distributed_experiment_results.parquet "
            "not found for Research "
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

    path_analysis = (
        pl.read_parquet(
            path_analysis_path
        )
    )

    distributed = (
        pl.read_parquet(
            distributed_path
        )
    )

    if trajectory_manifest_path.exists():
        trajectory_manifest = (
            pl.read_parquet(
                trajectory_manifest_path
            )
        )
    else:
        trajectory_manifest = (
            pl.DataFrame()
        )

    return {
        "paths": paths,
        "root": root,
        "dataset_id": str(
            dataset_id
        ),
        "path_analysis_path": (
            path_analysis_path
        ),
        "distributed_path": (
            distributed_path
        ),
        "trajectory_manifest_path": (
            trajectory_manifest_path
        ),
        "path_analysis": (
            path_analysis
        ),
        "distributed": (
            distributed
        ),
        "trajectory_manifest": (
            trajectory_manifest
        ),
    }


def _event_after_expr(
    *,
    later_timestamp: str,
    later_trade_number: str,
    earlier_timestamp: str,
    earlier_trade_number: str,
) -> pl.Expr:
    return (
        (
            pl.col(
                later_timestamp
            )
            > pl.col(
                earlier_timestamp
            )
        )
        | (
            (
                pl.col(
                    later_timestamp
                )
                == pl.col(
                    earlier_timestamp
                )
            )
            & (
                pl.col(
                    later_trade_number
                )
                > pl.col(
                    earlier_trade_number
                )
            )
        )
    )


def _apply_bool_filter(
    dataframe: pl.DataFrame,
    column: str,
    value: bool | None,
) -> pl.DataFrame:
    if value is None:
        return dataframe

    if column not in dataframe.columns:
        if value is False:
            return dataframe

        return dataframe.head(
            0
        )

    return (
        dataframe
        .filter(
            pl.col(
                column
            )
            .fill_null(
                False
            )
            == value
        )
    )


def _experiment_ids(
    distributed: pl.DataFrame,
) -> list[str]:
    if (
        distributed.is_empty()
        or "experiment_id"
        not in distributed.columns
    ):
        return []

    return sorted(
        {
            str(value)
            for value in (
                distributed[
                    "experiment_id"
                ]
                .drop_nulls()
                .to_list()
            )
        }
    )


def _filter_distributed_sessions(
    distributed: pl.DataFrame,
    query: PathQuery,
) -> set[str] | None:
    filter_requested = any(
        value is not None
        for value in (
            query.trade2_eligible,
            query.trade2_occurred,
            query.trade2_executed,
        )
    )

    if not filter_requested:
        return None

    frame = distributed

    if query.experiment_id is not None:
        frame = frame.filter(
            pl.col(
                "experiment_id"
            )
            == query.experiment_id
        )

    frame = _apply_bool_filter(
        frame,
        "trade2_eligible",
        query.trade2_eligible,
    )

    frame = _apply_bool_filter(
        frame,
        "trade2_occurred",
        query.trade2_occurred,
    )

    frame = _apply_bool_filter(
        frame,
        "trade2_executed",
        query.trade2_executed,
    )

    if frame.is_empty():
        return set()

    return {
        str(value)
        for value in (
            frame[
                "date"
            ]
            .cast(
                pl.String
            )
            .to_list()
        )
    }


def _stop_before_any_target_sessions(
    dataframe: pl.DataFrame,
    stop_points: int,
) -> set[str]:
    if dataframe.is_empty():
        return set()

    required = {
        "session_date",
        "stop_points",
        "stop_reached",
        "stop_before_target",
    }

    if not required.issubset(
        set(
            dataframe.columns
        )
    ):
        return set()

    grouped = (
        dataframe
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
                    "_stop_reached"
                ),
                pl.col(
                    "stop_before_target"
                )
                .fill_null(
                    False
                )
                .all()
                .alias(
                    "_stop_before_all_targets"
                ),
            ]
        )
        .filter(
            pl.col(
                "_stop_reached"
            )
            & pl.col(
                "_stop_before_all_targets"
            )
        )
    )

    return {
        str(value)
        for value in (
            grouped[
                "session_date"
            ]
            .cast(
                pl.String
            )
            .to_list()
        )
    }


def _apply_query_filters(
    *,
    path_analysis: pl.DataFrame,
    distributed: pl.DataFrame,
    query: PathQuery,
) -> pl.DataFrame:
    frame = path_analysis

    if frame.is_empty():
        return frame

    if query.experiment_id is not None:
        frame = frame.filter(
            pl.col(
                "experiment_id"
            )
            == query.experiment_id
        )

    if query.trade is not None:
        frame = frame.filter(
            pl.col(
                "trade"
            )
            == query.trade
        )

    if query.direction is not None:
        frame = frame.filter(
            pl.col(
                "direction"
            )
            == query.direction
        )

    if query.session_date is not None:
        frame = frame.filter(
            pl.col(
                "session_date"
            )
            .cast(
                pl.String
            )
            == str(
                query.session_date
            )
        )

    distributed_sessions = (
        _filter_distributed_sessions(
            distributed,
            query,
        )
    )

    if distributed_sessions is not None:
        if not distributed_sessions:
            return frame.head(
                0
            )

        frame = frame.filter(
            pl.col(
                "session_date"
            )
            .cast(
                pl.String
            )
            .is_in(
                sorted(
                    distributed_sessions
                )
            )
        )

    if query.target_points is not None:
        frame = frame.filter(
            pl.col(
                "target_points"
            )
            == query.target_points
        )

    frame = _apply_bool_filter(
        frame,
        "target_reached",
        query.target_reached,
    )

    if (
        query.target_before_first_zero
        is not None
    ):
        relation = (
            "TARGET_BEFORE_FIRST_ZERO_RETURN"
        )

        if query.target_before_first_zero:
            frame = frame.filter(
                pl.col(
                    "target_zero_relation"
                )
                == relation
            )
        else:
            frame = frame.filter(
                (
                    pl.col(
                        "target_zero_relation"
                    )
                    != relation
                )
                | pl.col(
                    "target_zero_relation"
                )
                .is_null()
            )

    if (
        query.target_after_first_zero
        is not None
    ):
        relation = (
            "TARGET_AFTER_FIRST_ZERO_RETURN"
        )

        if query.target_after_first_zero:
            frame = frame.filter(
                pl.col(
                    "target_zero_relation"
                )
                == relation
            )
        else:
            frame = frame.filter(
                (
                    pl.col(
                        "target_zero_relation"
                    )
                    != relation
                )
                | pl.col(
                    "target_zero_relation"
                )
                .is_null()
            )

    if query.target_then_zero is not None:
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
                frame.columns
            )
        ):
            if query.target_then_zero:
                return frame.head(
                    0
                )
        else:
            then_zero = (
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
                & _event_after_expr(
                    later_timestamp=(
                        "first_zero_return_timestamp"
                    ),
                    later_trade_number=(
                        "first_zero_return_trade_number"
                    ),
                    earlier_timestamp=(
                        "target_timestamp"
                    ),
                    earlier_trade_number=(
                        "target_trade_number"
                    ),
                )
            )

            frame = frame.filter(
                then_zero
                if query.target_then_zero
                else ~then_zero
            )

    if query.stop_points is not None:
        frame = frame.filter(
            pl.col(
                "stop_points"
            )
            == query.stop_points
        )

    frame = _apply_bool_filter(
        frame,
        "stop_reached",
        query.stop_reached,
    )

    frame = _apply_bool_filter(
        frame,
        "stop_before_target",
        query.stop_before_target,
    )

    frame = _apply_bool_filter(
        frame,
        "stop_after_target",
        query.stop_after_target,
    )

    if (
        query.stop_before_any_target
        is not None
    ):
        if query.stop_points is None:
            raise ValueError(
                "stop_before_any_target requires "
                "stop_points."
            )

        base = path_analysis

        if query.experiment_id is not None:
            base = base.filter(
                pl.col(
                    "experiment_id"
                )
                == query.experiment_id
            )

        if query.trade is not None:
            base = base.filter(
                pl.col(
                    "trade"
                )
                == query.trade
            )

        sessions = (
            _stop_before_any_target_sessions(
                base,
                query.stop_points,
            )
        )

        if query.stop_before_any_target:
            if not sessions:
                return frame.head(
                    0
                )

            frame = frame.filter(
                pl.col(
                    "session_date"
                )
                .cast(
                    pl.String
                )
                .is_in(
                    sorted(
                        sessions
                    )
                )
            )

        else:
            if sessions:
                frame = frame.filter(
                    ~pl.col(
                        "session_date"
                    )
                    .cast(
                        pl.String
                    )
                    .is_in(
                        sorted(
                            sessions
                        )
                    )
                )

    if query.trade2_return_to_entry is not None:
        if query.trade not in (
            None,
            "TRADE_2",
        ):
            if query.trade2_return_to_entry:
                return frame.head(
                    0
                )

        frame = _apply_bool_filter(
            frame,
            "first_zero_return_occurred",
            query.trade2_return_to_entry,
        )

    if (
        query.trade2_target_points
        is not None
    ):
        frame = frame.filter(
            pl.col(
                "trade"
            )
            == "TRADE_2"
        )

        frame = frame.filter(
            pl.col(
                "target_points"
            )
            == query.trade2_target_points
        )

    if (
        query.trade2_target_reached
        is not None
    ):
        frame = frame.filter(
            pl.col(
                "trade"
            )
            == "TRADE_2"
        )

        frame = _apply_bool_filter(
            frame,
            "target_reached",
            query.trade2_target_reached,
        )

    if (
        query.trade2_stop_points
        is not None
    ):
        frame = frame.filter(
            pl.col(
                "trade"
            )
            == "TRADE_2"
        )

        frame = frame.filter(
            pl.col(
                "stop_points"
            )
            == query.trade2_stop_points
        )

    if (
        query.trade2_stop_reached
        is not None
    ):
        frame = frame.filter(
            pl.col(
                "trade"
            )
            == "TRADE_2"
        )

        frame = _apply_bool_filter(
            frame,
            "stop_reached",
            query.trade2_stop_reached,
        )

    return (
        frame.sort(
            [
                "session_date",
                "trade",
                "target_points",
                "stop_points",
            ]
        )
    )


def _session_projection(
    frame: pl.DataFrame,
) -> pl.DataFrame:
    if frame.is_empty():
        return frame

    preferred = [
        "research_id",
        "dataset_id",
        "experiment_id",
        "session_date",
        "trade",
        "direction",
        "entry_price",
        "entry_timestamp",
        "entry_trade_number",
        "target_points",
        "target_reached",
        "target_timestamp",
        "target_trade_number",
        "first_zero_return_occurred",
        "first_zero_return_timestamp",
        "first_zero_return_trade_number",
        "target_zero_relation",
        "stop_points",
        "stop_reached",
        "stop_timestamp",
        "stop_trade_number",
        "stop_before_target",
        "stop_after_target",
        "trade2_eligible",
        "trade2_occurred",
        "trade2_executed",
    ]

    columns = [
        column
        for column in preferred
        if column in frame.columns
    ]

    return (
        frame.select(
            columns
        )
        .sort(
            [
                column
                for column in (
                    "session_date",
                    "trade",
                    "target_points",
                    "stop_points",
                )
                if column in columns
            ]
        )
    )


def execute_path_query(
    query: PathQuery,
) -> dict[str, Any]:
    inputs = _require_research(
        query.research_id
    )

    distributed = inputs[
        "distributed"
    ]

    if (
        query.experiment_id is not None
        and query.experiment_id
        not in _experiment_ids(
            distributed
        )
    ):
        raise ValueError(
            "Experiment not found in "
            "Research: "
            f"{query.experiment_id}"
        )

    filtered = _apply_query_filters(
        path_analysis=(
            inputs[
                "path_analysis"
            ]
        ),
        distributed=distributed,
        query=query,
    )

    rows = _session_projection(
        filtered
    )

    if rows.is_empty():
        sessions_found = 0
    else:
        sessions_found = int(
            rows.select(
                pl.col(
                    "session_date"
                )
                .n_unique()
                .alias(
                    "count"
                )
            )[
                "count"
            ][0]
        )

    records = (
        rows.to_dicts()
    )

    sessions = sorted(
        {
            str(
                record[
                    "session_date"
                ]
            )
            for record in records
            if record.get(
                "session_date"
            )
            is not None
        }
    )

    return {
        "path_query_version": (
            PATH_QUERY_VERSION
        ),
        "research_id": (
            query.research_id
        ),
        "dataset_id": (
            inputs[
                "dataset_id"
            ]
        ),
        "experiment_id": (
            query.experiment_id
        ),
        "sessions_found": (
            sessions_found
        ),
        "rows_found": int(
            rows.height
        ),
        "sessions": sessions,
        "records": records,
        "rows": records,
    }


def get_session_detail(
    *,
    research_id: str,
    experiment_id: str,
    session_date: str,
) -> dict[str, Any]:
    inputs = _require_research(
        research_id
    )

    path_analysis = inputs[
        "path_analysis"
    ]

    rows = (
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
                    "session_date"
                )
                .cast(
                    pl.String
                )
                == str(
                    session_date
                )
            )
        )
        .sort(
            [
                "trade",
                "target_points",
                "stop_points",
            ]
        )
    )

    if rows.is_empty():
        return {
            "path_query_version": (
                PATH_QUERY_VERSION
            ),
            "research_id": research_id,
            "dataset_id": (
                inputs[
                    "dataset_id"
                ]
            ),
            "experiment_id": (
                experiment_id
            ),
            "session_date": (
                session_date
            ),
            "found": False,
            "rows_found": 0,
            "trades": [],
            "records": [],
            "rows": [],
        }

    trades: list[
        dict[str, Any]
    ] = []

    for trade in sorted(
        {
            str(value)
            for value in (
                rows[
                    "trade"
                ]
                .drop_nulls()
                .to_list()
            )
        }
    ):
        trade_rows = (
            rows.filter(
                pl.col(
                    "trade"
                )
                == trade
            )
        )

        first = (
            trade_rows.row(
                0,
                named=True,
            )
        )

        target_rows = (
            trade_rows
            .unique(
                subset=[
                    "target_points",
                ],
                maintain_order=True,
            )
            .select(
                [
                    column
                    for column in (
                        "target_points",
                        "target_label",
                        "target_reached",
                        "target_timestamp",
                        "target_trade_number",
                        "target_zero_relation",
                    )
                    if column
                    in trade_rows.columns
                ]
            )
            .sort(
                "target_points"
            )
        )

        stop_rows = (
            trade_rows
            .unique(
                subset=[
                    "stop_points",
                ],
                maintain_order=True,
            )
            .select(
                [
                    column
                    for column in (
                        "stop_points",
                        "stop_reached",
                        "stop_timestamp",
                        "stop_trade_number",
                    )
                    if column
                    in trade_rows.columns
                ]
            )
            .sort(
                "stop_points"
            )
        )

        relations = (
            trade_rows.select(
                [
                    column
                    for column in (
                        "target_points",
                        "stop_points",
                        "stop_before_target",
                        "stop_after_target",
                        "target_zero_relation",
                    )
                    if column
                    in trade_rows.columns
                ]
            )
            .sort(
                [
                    column
                    for column in (
                        "target_points",
                        "stop_points",
                    )
                    if column
                    in trade_rows.columns
                ]
            )
        )

        trades.append(
            {
                "trade": trade,
                "direction": first.get(
                    "direction"
                ),
                "entry_price": first.get(
                    "entry_price"
                ),
                "entry_timestamp": (
                    first.get(
                        "entry_timestamp"
                    )
                ),
                "entry_trade_number": (
                    first.get(
                        "entry_trade_number"
                    )
                ),
                "first_zero_return_occurred": (
                    first.get(
                        "first_zero_return_occurred"
                    )
                ),
                "first_zero_return_timestamp": (
                    first.get(
                        "first_zero_return_timestamp"
                    )
                ),
                "first_zero_return_trade_number": (
                    first.get(
                        "first_zero_return_trade_number"
                    )
                ),
                "trade2_eligible": first.get(
                    "trade2_eligible"
                ),
                "trade2_occurred": first.get(
                    "trade2_occurred"
                ),
                "trade2_executed": first.get(
                    "trade2_executed"
                ),
                "targets": (
                    target_rows.to_dicts()
                ),
                "stops": (
                    stop_rows.to_dicts()
                ),
                "relations": (
                    relations.to_dicts()
                ),
            }
        )

    return {
        "path_query_version": (
            PATH_QUERY_VERSION
        ),
        "research_id": research_id,
        "dataset_id": (
            inputs[
                "dataset_id"
            ]
        ),
        "experiment_id": (
            experiment_id
        ),
        "session_date": (
            session_date
        ),
        "found": True,
        "rows_found": int(
            rows.height
        ),
        "trades": trades,
        "records": (
            rows.to_dicts()
        ),
        "rows": (
            rows.to_dicts()
        ),
    }


def resolve_trajectory(
    *,
    research_id: str,
    session_date: str,
) -> dict[str, Any]:
    inputs = _require_research(
        research_id
    )

    manifest = inputs[
        "trajectory_manifest"
    ]

    if manifest.is_empty():
        return {
            "path_query_version": (
                PATH_QUERY_VERSION
            ),
            "research_id": research_id,
            "dataset_id": (
                inputs[
                    "dataset_id"
                ]
            ),
            "session_date": (
                session_date
            ),
            "trajectory_exists": False,
            "file_exists": False,
            "trajectory_file_exists": False,
            "trajectory_path": None,
            "trajectory_sha256": None,
            "trajectory_rows": None,
        }

    row = (
        manifest
        .filter(
            pl.col(
                "date"
            )
            .cast(
                pl.String
            )
            == str(
                session_date
            )
        )
    )

    if row.is_empty():
        return {
            "path_query_version": (
                PATH_QUERY_VERSION
            ),
            "research_id": research_id,
            "dataset_id": (
                inputs[
                    "dataset_id"
                ]
            ),
            "session_date": (
                session_date
            ),
            "trajectory_exists": False,
            "file_exists": False,
            "trajectory_file_exists": False,
            "trajectory_path": None,
            "trajectory_sha256": None,
            "trajectory_rows": None,
        }

    value = row.row(
        0,
        named=True,
    )

    trajectory_exists = bool(
        value.get(
            "trajectory_exists",
            False,
        )
    )

    trajectory_path = value.get(
        "trajectory_path"
    )

    if (
        trajectory_exists
        and trajectory_path
    ):
        path = Path(
            str(
                trajectory_path
            )
        )

        if not path.is_absolute():
            project_root = (
                Path(__file__)
                .resolve()
                .parents[2]
            )

            path = (
                project_root
                / path
            ).resolve()

        resolved_path = str(
            path
        )

        file_exists = (
            path.exists()
        )

    else:
        resolved_path = None
        file_exists = False

    return {
        "path_query_version": (
            PATH_QUERY_VERSION
        ),
        "research_id": research_id,
        "dataset_id": (
            inputs[
                "dataset_id"
            ]
        ),
        "session_date": (
            session_date
        ),
        "trade_status": (
            value.get(
                "trade1_status"
            )
        ),
        "direction": (
            value.get(
                "direction"
            )
        ),
        "entry_price": (
            value.get(
                "entry_price"
            )
        ),
        "entry_timestamp": (
            value.get(
                "entry_timestamp"
            )
        ),
        "trajectory_exists": (
            trajectory_exists
        ),
        "file_exists": (
            file_exists
        ),
        "trajectory_file_exists": (
            file_exists
        ),
        "trajectory_path": (
            resolved_path
        ),
        "trajectory_sha256": (
            value.get(
                "sha256"
            )
        ),
        "trajectory_rows": (
            value.get(
                "trajectory_rows"
            )
        ),
    }
