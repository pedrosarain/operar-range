from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.batch_execution import (
    BATCH_RESULT_SCHEMA,
    FAILURE_SCHEMA,
    execute_batch,
)


MERGED_RESULTS_SCHEMA = (
    BATCH_RESULT_SCHEMA
)


def sha256_file(
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
            digest.update(chunk)

    return digest.hexdigest()


def _read_table(
    path: str | Path,
) -> pa.Table:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    return pq.read_table(
        path
    )


def _read_rows(
    path: str | Path,
) -> list[dict[str, Any]]:
    return _read_table(
        path
    ).to_pylist()


def _write_plan(
    *,
    rows: list[dict[str, Any]],
    path: str | Path,
    schema: pa.Schema,
) -> None:
    path = Path(path)

    ordered = sorted(
        rows,
        key=lambda row: (
            row["batch_id"],
            row[
                "execution_unit_id"
            ],
        ),
    )

    table = pa.Table.from_pylist(
        ordered,
        schema=schema,
    )

    pq.write_table(
        table,
        path,
        compression="zstd",
    )


def update_plan_after_batch(
    *,
    plan_path: str | Path,
    completed_unit_ids: list[str],
    skipped_unit_ids: list[str],
    failures: list[
        dict[str, Any]
    ],
) -> dict[str, int]:
    plan_path = Path(
        plan_path
    )

    plan_table = _read_table(
        plan_path
    )

    rows = plan_table.to_pylist()

    completed = set(
        completed_unit_ids
    )

    skipped = set(
        skipped_unit_ids
    )

    failures_by_id = {
        row[
            "execution_unit_id"
        ]: row
        for row in failures
    }

    changed = 0

    for row in rows:
        execution_unit_id = (
            row[
                "execution_unit_id"
            ]
        )

        if (
            execution_unit_id
            in completed
        ):
            row[
                "execution_status"
            ] = "COMPLETED"

            row[
                "attempt_count"
            ] = (
                int(
                    row.get(
                        "attempt_count"
                    )
                    or 0
                )
                + 1
            )

            changed += 1
            continue

        if (
            execution_unit_id
            in skipped
        ):
            row[
                "execution_status"
            ] = (
                "SKIPPED_NO_TRADE"
            )

            changed += 1
            continue

        if (
            execution_unit_id
            in failures_by_id
        ):
            failure = (
                failures_by_id[
                    execution_unit_id
                ]
            )

            row[
                "execution_status"
            ] = "FAILED"

            row[
                "attempt_count"
            ] = int(
                failure[
                    "attempt_count"
                ]
            )

            changed += 1

    _write_plan(
        rows=rows,
        path=plan_path,
        schema=plan_table.schema,
    )

    return {
        "changed": changed,
        "completed": len(
            completed
        ),
        "skipped": len(
            skipped
        ),
        "failed": len(
            failures
        ),
    }


def write_failures(
    *,
    failures: list[
        dict[str, Any]
    ],
    failure_path: str | Path,
) -> Path:
    failure_path = Path(
        failure_path
    )

    failure_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    existing = []

    if failure_path.exists():
        existing = (
            pq.read_table(
                failure_path
            ).to_pylist()
        )

    combined = (
        existing
        + failures
    )

    combined = sorted(
        combined,
        key=lambda row: (
            row[
                "execution_unit_id"
            ],
            int(
                row[
                    "attempt_count"
                ]
            ),
        ),
    )

    table = pa.Table.from_pylist(
        combined,
        schema=FAILURE_SCHEMA,
    )

    pq.write_table(
        table,
        failure_path,
        compression="zstd",
    )

    return failure_path


def pending_batches(
    plan_path: str | Path,
) -> list[str]:
    rows = _read_rows(
        plan_path
    )

    return sorted(
        {
            row["batch_id"]
            for row in rows
            if row[
                "execution_status"
            ]
            in (
                "PENDING",
                "FAILED",
            )
        }
    )


def plan_status_counts(
    plan_path: str | Path,
) -> dict[str, int]:
    rows = _read_rows(
        plan_path
    )

    counts = {
        "PENDING": 0,
        "RUNNING": 0,
        "COMPLETED": 0,
        "FAILED": 0,
        "SKIPPED_NO_TRADE": 0,
    }

    for row in rows:
        status = row[
            "execution_status"
        ]

        if status not in counts:
            counts[
                status
            ] = 0

        counts[
            status
        ] += 1

    return counts


def execute_pending_batches(
    *,
    plan_path: str | Path = (
        "data/research/"
        "batch_execution_plan.parquet"
    ),
    valid_experiments_path: str | Path = (
        "data/research/"
        "valid_experiments.parquet"
    ),
    trajectory_manifest_path: str | Path = (
        "data/research/"
        "trade1_trajectory_manifest.parquet"
    ),
    normalized_dir: str | Path = (
        "data/normalized"
    ),
    batches_dir: str | Path = (
        "data/research/batches"
    ),
    failure_path: str | Path = (
        "data/research/"
        "batch_failures.parquet"
    ),
    max_batches: int | None = None,
) -> dict[str, Any]:
    batch_ids = pending_batches(
        plan_path
    )

    if (
        max_batches is not None
    ):
        batch_ids = batch_ids[
            :max_batches
        ]

    batches_executed = 0
    new_results = 0
    failures_total = 0

    trajectory_loads = 0
    runner_candle_builds = 0

    for batch_id in batch_ids:
        result = execute_batch(
            batch_id=batch_id,
            plan_path=plan_path,
            valid_experiments_path=(
                valid_experiments_path
            ),
            trajectory_manifest_path=(
                trajectory_manifest_path
            ),
            normalized_dir=(
                normalized_dir
            ),
            batches_dir=batches_dir,
        )

        update_plan_after_batch(
            plan_path=plan_path,
            completed_unit_ids=(
                result[
                    "completed_unit_ids"
                ]
            ),
            skipped_unit_ids=(
                result[
                    "skipped_unit_ids"
                ]
            ),
            failures=(
                result[
                    "failures"
                ]
            ),
        )

        write_failures(
            failures=result[
                "failures"
            ],
            failure_path=failure_path,
        )

        batches_executed += 1

        new_results += int(
            result[
                "new_results"
            ]
        )

        failures_total += len(
            result[
                "failures"
            ]
        )

        trajectory_loads += int(
            result[
                "trajectory_loads"
            ]
        )

        runner_candle_builds += int(
            result[
                "runner_candle_builds"
            ]
        )

    return {
        "batches_executed": (
            batches_executed
        ),
        "new_results": (
            new_results
        ),
        "failures": (
            failures_total
        ),
        "trajectory_loads": (
            trajectory_loads
        ),
        "runner_candle_builds": (
            runner_candle_builds
        ),
        "status_counts": (
            plan_status_counts(
                plan_path
            )
        ),
    }


def merge_batch_results(
    *,
    plan_path: str | Path = (
        "data/research/"
        "batch_execution_plan.parquet"
    ),
    batches_dir: str | Path = (
        "data/research/batches"
    ),
    output_path: str | Path = (
        "data/research/"
        "batch_experiment_results.parquet"
    ),
) -> dict[str, Any]:
    plan_rows = _read_rows(
        plan_path
    )

    expected_unit_ids = {
        row[
            "execution_unit_id"
        ]
        for row in plan_rows
        if row[
            "execution_status"
        ]
        in (
            "COMPLETED",
            "SKIPPED_NO_TRADE",
        )
    }

    batches_dir = Path(
        batches_dir
    )

    rows: list[
        dict[str, Any]
    ] = []

    for path in sorted(
        batches_dir.glob(
            "*.parquet"
        )
    ):
        rows.extend(
            pq.read_table(
                path
            ).to_pylist()
        )

    ids = [
        row[
            "execution_unit_id"
        ]
        for row in rows
    ]

    if len(ids) != len(set(ids)):
        raise RuntimeError(
            "Duplicate execution_unit_id "
            "found during merge."
        )

    actual_unit_ids = set(ids)

    missing = (
        expected_unit_ids
        - actual_unit_ids
    )

    unexpected = (
        actual_unit_ids
        - expected_unit_ids
    )

    if missing:
        raise RuntimeError(
            "Missing batch results for "
            f"{len(missing)} execution units."
        )

    if unexpected:
        raise RuntimeError(
            "Unexpected batch results for "
            f"{len(unexpected)} execution units."
        )

    ordered = sorted(
        rows,
        key=lambda row: (
            row[
                "experiment_id"
            ],
            row["date"],
            row[
                "execution_unit_id"
            ],
        ),
    )

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        ordered,
        schema=(
            MERGED_RESULTS_SCHEMA
        ),
    )

    pq.write_table(
        table,
        output_path,
        compression="zstd",
    )

    return {
        "rows": len(
            ordered
        ),
        "output_path": str(
            output_path
        ),
        "sha256": sha256_file(
            output_path
        ),
    }