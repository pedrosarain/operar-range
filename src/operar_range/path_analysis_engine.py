from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.research_workspace import (
    load_research_definition,
    load_research_manifest,
    research_paths,
)


PATH_ANALYSIS_ENGINE_VERSION = (
    "quantitative-path-analysis-v1"
)

PATH_ANALYSIS_ARTIFACT_NAME = (
    "path_analysis.parquet"
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


PATH_ANALYSIS_SCHEMA = pa.schema(
    [
        (
            "research_id",
            pa.string(),
        ),
        (
            "dataset_id",
            pa.string(),
        ),
        (
            "experiment_id",
            pa.string(),
        ),
        (
            "config_sha256",
            pa.string(),
        ),
        (
            "motor_version",
            pa.string(),
        ),
        (
            "rules_version",
            pa.string(),
        ),
        (
            "trajectory_sha256",
            pa.string(),
        ),
        (
            "path_analysis_version",
            pa.string(),
        ),

        (
            "session_date",
            pa.string(),
        ),
        (
            "trade",
            pa.string(),
        ),
        (
            "direction",
            pa.string(),
        ),
        (
            "entry_price",
            pa.float64(),
        ),
        (
            "entry_timestamp",
            pa.string(),
        ),
        (
            "entry_trade_number",
            pa.int64(),
        ),

        (
            "trade2_eligible",
            pa.bool_(),
        ),
        (
            "trade2_occurred",
            pa.bool_(),
        ),
        (
            "trade2_executed",
            pa.bool_(),
        ),

        (
            "first_zero_return_occurred",
            pa.bool_(),
        ),
        (
            "first_zero_return_timestamp",
            pa.string(),
        ),
        (
            "first_zero_return_trade_number",
            pa.int64(),
        ),

        (
            "target_points",
            pa.int64(),
        ),
        (
            "target_label",
            pa.string(),
        ),
        (
            "target_reached",
            pa.bool_(),
        ),
        (
            "target_timestamp",
            pa.string(),
        ),
        (
            "target_trade_number",
            pa.int64(),
        ),
        (
            "target_zero_relation",
            pa.string(),
        ),

        (
            "stop_points",
            pa.int64(),
        ),
        (
            "stop_reached",
            pa.bool_(),
        ),
        (
            "stop_timestamp",
            pa.string(),
        ),
        (
            "stop_trade_number",
            pa.int64(),
        ),
        (
            "stop_before_target",
            pa.bool_(),
        ),
        (
            "stop_after_target",
            pa.bool_(),
        ),
    ]
)


@dataclass(frozen=True)
class PathEvent:
    timestamp: str
    trade_number: int
    price: float


def path_analysis_artifact_path(
    research_id: str,
) -> Path:
    return (
        research_paths(
            research_id
        )["root"]
        / PATH_ANALYSIS_ARTIFACT_NAME
    )


def _event_key(
    event: PathEvent,
) -> tuple[
    str,
    int,
]:
    return (
        event.timestamp,
        event.trade_number,
    )


def _row_key(
    row: dict[str, Any],
) -> tuple[
    str,
    int,
]:
    timestamp = row[
        "timestamp"
    ]

    if hasattr(
        timestamp,
        "isoformat",
    ):
        timestamp_text = (
            timestamp.isoformat()
        )

    else:
        timestamp_text = str(
            timestamp
        )

    return (
        timestamp_text,
        int(
            row[
                "trade_number"
            ]
        ),
    )


def _signed_points(
    *,
    direction: str,
    entry_price: float,
    price: float,
) -> float:
    if direction == "LONG":
        return (
            float(price)
            - float(entry_price)
        )

    if direction == "SHORT":
        return (
            float(entry_price)
            - float(price)
        )

    raise ValueError(
        f"Unsupported direction: "
        f"{direction}"
    )


def _validate_chronology(
    trajectory: pl.DataFrame,
) -> None:
    previous: tuple[
        str,
        int,
    ] | None = None

    for row in trajectory.iter_rows(
        named=True
    ):
        current = _row_key(
            row
        )

        if (
            previous is not None
            and current < previous
        ):
            raise ValueError(
                "Trajectory is not ordered "
                "chronologically by timestamp "
                "and trade_number."
            )

        previous = current


def _slice_from_entry(
    *,
    trajectory: pl.DataFrame,
    entry_timestamp: str,
    entry_trade_number: int,
) -> pl.DataFrame:
    entry_key = (
        str(
            entry_timestamp
        ),
        int(
            entry_trade_number
        ),
    )

    start_index: int | None = None

    for index, row in enumerate(
        trajectory.iter_rows(
            named=True
        )
    ):
        if (
            _row_key(
                row
            )
            == entry_key
        ):
            start_index = index
            break

    if start_index is None:
        raise ValueError(
            "Exact entry event not found "
            "inside trajectory chronology."
        )

    return trajectory.slice(
        start_index
    )


def _scan_trade_path(
    *,
    trajectory: pl.DataFrame,
    direction: str,
    entry_price: float,
) -> dict[str, Any]:
    first_zero_return: (
        PathEvent | None
    ) = None

    target_events: dict[
        int,
        PathEvent | None,
    ] = {
        target: None
        for target
        in TARGET_LEVELS
    }

    stop_events: dict[
        int,
        PathEvent | None,
    ] = {
        stop: None
        for stop
        in STOP_LEVELS
    }

    moved_away_from_zero = False

    first_row = True

    for row in trajectory.iter_rows(
        named=True
    ):
        (
            timestamp,
            trade_number,
        ) = _row_key(
            row
        )

        price = float(
            row[
                "price"
            ]
        )

        points = _signed_points(
            direction=direction,
            entry_price=entry_price,
            price=price,
        )

        event = PathEvent(
            timestamp=timestamp,
            trade_number=trade_number,
            price=price,
        )

        #
        # O próprio tick da entrada não conta
        # como retorno ao zero.
        #
        if first_row:
            first_row = False

        else:
            if points != 0:
                moved_away_from_zero = True

            elif (
                moved_away_from_zero
                and first_zero_return
                is None
            ):
                first_zero_return = (
                    event
                )

        for target in TARGET_LEVELS:
            if (
                target_events[
                    target
                ]
                is None
                and points
                >= target
            ):
                target_events[
                    target
                ] = event

        for stop in STOP_LEVELS:
            if (
                stop_events[
                    stop
                ]
                is None
                and points
                <= -stop
            ):
                stop_events[
                    stop
                ] = event

        all_targets_found = all(
            event is not None
            for event
            in target_events.values()
        )

        all_stops_found = all(
            event is not None
            for event
            in stop_events.values()
        )

        if (
            first_zero_return
            is not None
            and all_targets_found
            and all_stops_found
        ):
            break

    return {
        "first_zero_return": (
            first_zero_return
        ),
        "targets": (
            target_events
        ),
        "stops": (
            stop_events
        ),
    }


def _target_zero_relation(
    *,
    target_event: PathEvent | None,
    zero_event: PathEvent | None,
) -> str | None:
    if (
        target_event is None
        or zero_event is None
    ):
        return None

    if (
        _event_key(
            target_event
        )
        < _event_key(
            zero_event
        )
    ):
        return (
            "TARGET_BEFORE_FIRST_ZERO_RETURN"
        )

    return (
        "TARGET_AFTER_FIRST_ZERO_RETURN"
    )


def _event_before(
    *,
    first: PathEvent | None,
    second: PathEvent | None,
) -> bool | None:
    if (
        first is None
        or second is None
    ):
        return None

    return (
        _event_key(
            first
        )
        < _event_key(
            second
        )
    )


def _event_after(
    *,
    first: PathEvent | None,
    second: PathEvent | None,
) -> bool | None:
    if (
        first is None
        or second is None
    ):
        return None

    return (
        _event_key(
            first
        )
        > _event_key(
            second
        )
    )


def _target_label(
    target: int,
) -> str:
    if target == 1000:
        return "1000+"

    return str(
        target
    )


def analyze_trade_path(
    *,
    research_id: str,
    dataset_id: str,
    experiment_id: str,
    config_sha256: str | None,
    motor_version: str | None,
    rules_version: str | None,
    trajectory_sha256: str | None,
    session_date: str,
    trade: str,
    direction: str,
    entry_price: float,
    entry_timestamp: str,
    entry_trade_number: int,
    trajectory: pl.DataFrame,
    trade2_eligible: bool,
    trade2_occurred: bool,
    trade2_executed: bool,
) -> list[
    dict[str, Any]
]:
    _validate_chronology(
        trajectory
    )

    sliced = _slice_from_entry(
        trajectory=trajectory,
        entry_timestamp=entry_timestamp,
        entry_trade_number=(
            entry_trade_number
        ),
    )

    scan = _scan_trade_path(
        trajectory=sliced,
        direction=direction,
        entry_price=entry_price,
    )

    zero_event = scan[
        "first_zero_return"
    ]

    target_events = scan[
        "targets"
    ]

    stop_events = scan[
        "stops"
    ]

    rows: list[
        dict[str, Any]
    ] = []

    for target in TARGET_LEVELS:
        target_event = (
            target_events[
                target
            ]
        )

        relation = (
            _target_zero_relation(
                target_event=(
                    target_event
                ),
                zero_event=(
                    zero_event
                ),
            )
        )

        for stop in STOP_LEVELS:
            stop_event = (
                stop_events[
                    stop
                ]
            )

            rows.append(
                {
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
                    "motor_version": (
                        motor_version
                    ),
                    "rules_version": (
                        rules_version
                    ),
                    "trajectory_sha256": (
                        trajectory_sha256
                    ),
                    "path_analysis_version": (
                        PATH_ANALYSIS_ENGINE_VERSION
                    ),

                    "session_date": (
                        session_date
                    ),
                    "trade": trade,
                    "direction": (
                        direction
                    ),
                    "entry_price": float(
                        entry_price
                    ),
                    "entry_timestamp": (
                        str(
                            entry_timestamp
                        )
                    ),
                    "entry_trade_number": int(
                        entry_trade_number
                    ),

                    "trade2_eligible": bool(
                        trade2_eligible
                    ),
                    "trade2_occurred": bool(
                        trade2_occurred
                    ),
                    "trade2_executed": bool(
                        trade2_executed
                    ),

                    "first_zero_return_occurred": (
                        zero_event
                        is not None
                    ),
                    "first_zero_return_timestamp": (
                        zero_event.timestamp
                        if zero_event
                        is not None
                        else None
                    ),
                    "first_zero_return_trade_number": (
                        zero_event.trade_number
                        if zero_event
                        is not None
                        else None
                    ),

                    "target_points": int(
                        target
                    ),
                    "target_label": (
                        _target_label(
                            target
                        )
                    ),
                    "target_reached": (
                        target_event
                        is not None
                    ),
                    "target_timestamp": (
                        target_event.timestamp
                        if target_event
                        is not None
                        else None
                    ),
                    "target_trade_number": (
                        target_event.trade_number
                        if target_event
                        is not None
                        else None
                    ),
                    "target_zero_relation": (
                        relation
                    ),

                    "stop_points": int(
                        stop
                    ),
                    "stop_reached": (
                        stop_event
                        is not None
                    ),
                    "stop_timestamp": (
                        stop_event.timestamp
                        if stop_event
                        is not None
                        else None
                    ),
                    "stop_trade_number": (
                        stop_event.trade_number
                        if stop_event
                        is not None
                        else None
                    ),
                    "stop_before_target": (
                        _event_before(
                            first=(
                                stop_event
                            ),
                            second=(
                                target_event
                            ),
                        )
                    ),
                    "stop_after_target": (
                        _event_after(
                            first=(
                                stop_event
                            ),
                            second=(
                                target_event
                            ),
                        )
                    ),
                }
            )

    return rows


def _load_trajectory(
    path: str | Path,
) -> pl.DataFrame:
    trajectory = (
        pl.read_parquet(
            path
        )
        .select(
            [
                "timestamp",
                "trade_number",
                "price",
            ]
        )
    )

    if trajectory.is_empty():
        raise ValueError(
            "Trajectory artifact is empty."
        )

    return trajectory


def _dataset_id(
    *,
    definition: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    value = (
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

    if not value:
        raise ValueError(
            "Dataset ID unavailable for "
            "Research."
        )

    return str(
        value
    )


def build_research_path_analysis(
    research_id: str,
) -> pl.DataFrame:
    paths = research_paths(
        research_id
    )

    if not paths[
        "root"
    ].exists():
        raise FileNotFoundError(
            f"Research not found: "
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

    dataset_id = _dataset_id(
        definition=definition,
        manifest=manifest,
    )

    trajectory_manifest_path = (
        paths[
            "trajectory_manifest"
        ]
    )

    distributed_path = (
        paths[
            "distributed_results"
        ]
    )

    if not trajectory_manifest_path.exists():
        raise FileNotFoundError(
            "Trajectory manifest not found "
            f"for Research: {research_id}"
        )

    if not distributed_path.exists():
        raise FileNotFoundError(
            "Distributed experiment results "
            "not found for Research: "
            f"{research_id}"
        )

    trajectory_manifest = (
        pl.read_parquet(
            trajectory_manifest_path
        )
    )

    distributed = (
        pl.read_parquet(
            distributed_path
        )
    )

    manifest_by_date = {
        str(
            row[
                "date"
            ]
        ): row
        for row
        in trajectory_manifest.iter_rows(
            named=True
        )
    }

    trajectory_cache: dict[
        str,
        pl.DataFrame,
    ] = {}

    output_rows: list[
        dict[str, Any]
    ] = []

    ordered_results = distributed.sort(
        [
            "date",
            "experiment_id",
            "execution_unit_id",
        ]
    )

    for result in ordered_results.iter_rows(
        named=True
    ):
        if (
            result.get(
                "trade_status"
            )
            == "NO_TRADE_1"
        ):
            continue

        session_date = str(
            result[
                "date"
            ]
        )

        manifest_row = (
            manifest_by_date.get(
                session_date
            )
        )

        if manifest_row is None:
            raise ValueError(
                "Trajectory manifest row "
                "missing for session: "
                f"{session_date}"
            )

        if not bool(
            manifest_row.get(
                "trajectory_exists"
            )
        ):
            raise ValueError(
                "Trade 1 exists without "
                "trajectory artifact for "
                f"{session_date}"
            )

        trajectory_path = str(
            manifest_row[
                "trajectory_path"
            ]
        )

        if trajectory_path not in trajectory_cache:
            trajectory_cache[
                trajectory_path
            ] = _load_trajectory(
                trajectory_path
            )

        trajectory = (
            trajectory_cache[
                trajectory_path
            ]
        )

        first_row = (
            trajectory.row(
                0,
                named=True,
            )
        )

        first_timestamp = (
            first_row[
                "timestamp"
            ]
        )

        if hasattr(
            first_timestamp,
            "isoformat",
        ):
            entry_timestamp = (
                first_timestamp.isoformat()
            )

        else:
            entry_timestamp = str(
                first_timestamp
            )

        entry_trade_number = int(
            first_row[
                "trade_number"
            ]
        )

        trade2_eligible = bool(
            result.get(
                "trade2_eligible"
            )
            or False
        )

        trade2_occurred = bool(
            result.get(
                "trade2_occurred"
            )
            or False
        )

        trade2_executed = bool(
            result.get(
                "trade2_executed"
            )
            or False
        )

        output_rows.extend(
            analyze_trade_path(
                research_id=(
                    research_id
                ),
                dataset_id=(
                    dataset_id
                ),
                experiment_id=str(
                    result[
                        "experiment_id"
                    ]
                ),
                config_sha256=(
                    result.get(
                        "config_sha256"
                    )
                ),
                motor_version=(
                    result.get(
                        "motor_version"
                    )
                ),
                rules_version=(
                    result.get(
                        "rules_version"
                    )
                ),
                trajectory_sha256=(
                    result.get(
                        "trajectory_sha256"
                    )
                    or manifest_row.get(
                        "sha256"
                    )
                ),
                session_date=(
                    session_date
                ),
                trade="TRADE_1",
                direction=str(
                    result[
                        "direction"
                    ]
                ),
                entry_price=float(
                    manifest_row[
                        "entry_price"
                    ]
                ),
                entry_timestamp=(
                    entry_timestamp
                ),
                entry_trade_number=(
                    entry_trade_number
                ),
                trajectory=(
                    trajectory
                ),
                trade2_eligible=(
                    trade2_eligible
                ),
                trade2_occurred=(
                    trade2_occurred
                ),
                trade2_executed=(
                    trade2_executed
                ),
            )
        )

        if not trade2_executed:
            continue

        trade2_entry_timestamp = (
            result.get(
                "trade2_entry_timestamp"
            )
        )

        trade2_entry_trade_number = (
            result.get(
                "trade2_entry_trade_number"
            )
        )

        trade2_entry_price = (
            result.get(
                "trade2_trigger_level"
            )
        )

        trade2_direction = (
            result.get(
                "trade2_direction"
            )
        )

        if (
            trade2_entry_timestamp is None
            or trade2_entry_trade_number
            is None
            or trade2_entry_price is None
            or trade2_direction is None
        ):
            raise ValueError(
                "Executed Trade 2 is missing "
                "entry lineage."
            )

        output_rows.extend(
            analyze_trade_path(
                research_id=(
                    research_id
                ),
                dataset_id=(
                    dataset_id
                ),
                experiment_id=str(
                    result[
                        "experiment_id"
                    ]
                ),
                config_sha256=(
                    result.get(
                        "config_sha256"
                    )
                ),
                motor_version=(
                    result.get(
                        "motor_version"
                    )
                ),
                rules_version=(
                    result.get(
                        "rules_version"
                    )
                ),
                trajectory_sha256=(
                    result.get(
                        "trajectory_sha256"
                    )
                    or manifest_row.get(
                        "sha256"
                    )
                ),
                session_date=(
                    session_date
                ),
                trade="TRADE_2",
                direction=str(
                    trade2_direction
                ),
                entry_price=float(
                    trade2_entry_price
                ),
                entry_timestamp=str(
                    trade2_entry_timestamp
                ),
                entry_trade_number=int(
                    trade2_entry_trade_number
                ),
                trajectory=(
                    trajectory
                ),
                trade2_eligible=(
                    trade2_eligible
                ),
                trade2_occurred=(
                    trade2_occurred
                ),
                trade2_executed=(
                    trade2_executed
                ),
            )
        )

    if not output_rows:
        return pl.DataFrame(
            schema={
                field.name: (
                    pl.String
                    if pa.types.is_string(
                        field.type
                    )
                    else pl.Boolean
                    if pa.types.is_boolean(
                        field.type
                    )
                    else pl.Int64
                    if pa.types.is_int64(
                        field.type
                    )
                    else pl.Float64
                )
                for field
                in PATH_ANALYSIS_SCHEMA
            }
        )

    return (
        pl.DataFrame(
            output_rows
        )
        .sort(
            [
                "session_date",
                "experiment_id",
                "trade",
                "target_points",
                "stop_points",
            ]
        )
    )


def _to_arrow_table(
    dataframe: pl.DataFrame,
) -> pa.Table:
    rows = dataframe.to_dicts()

    return pa.Table.from_pylist(
        rows,
        schema=PATH_ANALYSIS_SCHEMA,
    )


def write_research_path_analysis(
    research_id: str,
) -> dict[str, Any]:
    dataframe = (
        build_research_path_analysis(
            research_id
        )
    )

    output_path = (
        path_analysis_artifact_path(
            research_id
        )
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = _to_arrow_table(
        dataframe
    )

    pq.write_table(
        table,
        output_path,
        compression="zstd",
    )

    return {
        "research_id": research_id,
        "artifact_path": str(
            output_path
        ),
        "rows": int(
            dataframe.height
        ),
        "path_analysis_version": (
            PATH_ANALYSIS_ENGINE_VERSION
        ),
    }


def load_research_path_analysis(
    research_id: str,
) -> pl.DataFrame:
    path = path_analysis_artifact_path(
        research_id
    )

    if not path.exists():
        raise FileNotFoundError(
            "Path Analysis artifact not "
            f"found: {research_id}"
        )

    return pl.read_parquet(
        path
    )
