from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


BATCH_EXECUTOR_VERSION = "batch-executor-v1"


PLAN_SCHEMA = pa.schema(
    [
        ("execution_unit_id", pa.string()),
        ("batch_id", pa.string()),
        ("experiment_id", pa.string()),
        ("config_sha256", pa.string()),
        ("date", pa.string()),
        ("trade_status", pa.string()),
        ("trajectory_path", pa.string()),
        ("trajectory_sha256", pa.string()),
        ("requires_runner_candles", pa.bool_()),
        ("execution_status", pa.string()),
        ("attempt_count", pa.int64()),
        ("engine_version", pa.string()),
        ("rules_version", pa.string()),
    ]
)


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


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


def execution_unit_id(
    *,
    experiment_id: str,
    date: str,
    config_sha256: str,
    trajectory_sha256: str | None,
    motor_version: str | None,
    rules_version: str | None,
) -> str:
    payload = {
        "experiment_id": (
            experiment_id
        ),
        "date": date,
        "config_sha256": (
            config_sha256
        ),
        "trajectory_sha256": (
            trajectory_sha256
        ),
        "motor_version": (
            motor_version
        ),
        "rules_version": (
            rules_version
        ),
    }

    digest = _sha256_text(
        _canonical_json(
            payload
        )
    )

    return (
        "EU-"
        + digest
    )


def deterministic_batch_id(
    *,
    batch_number: int,
    execution_unit_ids: list[str],
) -> str:
    payload = {
        "batch_number": (
            batch_number
        ),
        "execution_unit_ids": (
            execution_unit_ids
        ),
    }

    digest = _sha256_text(
        _canonical_json(
            payload
        )
    )

    return (
        f"BATCH-{batch_number:06d}-"
        f"{digest[:16]}"
    )


def _read_rows(
    path: str | Path,
) -> list[dict[str, Any]]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    return pq.read_table(
        path
    ).to_pylist()


def _validate_registry(
    *,
    experiments: list[
        dict[str, Any]
    ],
    registry_rows: list[
        dict[str, Any]
    ],
) -> None:
    registry_by_id = {
        row["experiment_id"]: row
        for row in registry_rows
    }

    for experiment in experiments:
        experiment_id = (
            experiment[
                "experiment_id"
            ]
        )

        if (
            experiment_id
            not in registry_by_id
        ):
            raise RuntimeError(
                "Experiment missing from "
                "Registry: "
                f"{experiment_id}"
            )

        registered = (
            registry_by_id[
                experiment_id
            ]
        )

        if (
            registered.get(
                "config_sha256"
            )
            != experiment.get(
                "config_sha256"
            )
        ):
            raise RuntimeError(
                "Registry config hash "
                "mismatch for "
                f"{experiment_id}."
            )

        status = registered.get(
            "status"
        )

        if status not in (
            "ACTIVE",
            "FROZEN",
            "SUPERSEDED",
        ):
            raise RuntimeError(
                "Unsupported Registry status "
                f"for {experiment_id}: "
                f"{status}"
            )


def _requires_runner_candles(
    experiment: dict[str, Any],
) -> bool:
    return (
        experiment.get(
            "runner_enabled"
        )
        is True
        and experiment.get(
            "runner_rule"
        )
        == "CANDLE_BREAK_M5"
    )


def _motor_version_for_session(
    session: dict[str, Any],
) -> str | None:
    return (
        session.get(
            "motor_version"
        )
    )


def build_execution_units(
    *,
    experiments: list[
        dict[str, Any]
    ],
    sessions: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:
    ordered_experiments = sorted(
        experiments,
        key=lambda row: (
            row["experiment_id"],
            row["config_sha256"],
        ),
    )

    ordered_sessions = sorted(
        sessions,
        key=lambda row: (
            row["date"],
            row.get(
                "source_parquet"
            )
            or "",
        ),
    )

    units: list[
        dict[str, Any]
    ] = []

    seen_ids: set[str] = set()

    for experiment in (
        ordered_experiments
    ):
        for session in (
            ordered_sessions
        ):
            trade_status = (
                session.get(
                    "trade1_status"
                )
            )

            if trade_status not in (
                "TRADE_1",
                "NO_TRADE_1",
            ):
                raise RuntimeError(
                    "Unsupported trade status "
                    f"for {session.get('date')}: "
                    f"{trade_status}"
                )

            trajectory_exists = bool(
                session.get(
                    "trajectory_exists"
                )
            )

            if (
                trade_status == "TRADE_1"
                and not trajectory_exists
            ):
                raise RuntimeError(
                    "TRADE_1 session without "
                    "trajectory: "
                    f"{session['date']}"
                )

            if (
                trade_status
                == "NO_TRADE_1"
            ):
                trajectory_path = None
                trajectory_hash = None
                initial_status = (
                    "SKIPPED_NO_TRADE"
                )

            else:
                trajectory_path = (
                    session.get(
                        "trajectory_path"
                    )
                )

                trajectory_hash = (
                    session.get(
                        "sha256"
                    )
                )

                if not trajectory_path:
                    raise RuntimeError(
                        "Missing trajectory_path "
                        f"for {session['date']}."
                    )

                if not trajectory_hash:
                    raise RuntimeError(
                        "Missing trajectory SHA256 "
                        f"for {session['date']}."
                    )

                initial_status = (
                    "PENDING"
                )

            rules_version = (
                experiment.get(
                    "rules_version"
                )
            )

            motor_version = (
                _motor_version_for_session(
                    session
                )
            )

            unit_id = execution_unit_id(
                experiment_id=(
                    experiment[
                        "experiment_id"
                    ]
                ),
                date=session[
                    "date"
                ],
                config_sha256=(
                    experiment[
                        "config_sha256"
                    ]
                ),
                trajectory_sha256=(
                    trajectory_hash
                ),
                motor_version=(
                    motor_version
                ),
                rules_version=(
                    rules_version
                ),
            )

            if unit_id in seen_ids:
                raise RuntimeError(
                    "Duplicate "
                    "execution_unit_id: "
                    f"{unit_id}"
                )

            seen_ids.add(
                unit_id
            )

            units.append(
                {
                    "execution_unit_id": (
                        unit_id
                    ),
                    "batch_id": None,
                    "experiment_id": (
                        experiment[
                            "experiment_id"
                        ]
                    ),
                    "config_sha256": (
                        experiment[
                            "config_sha256"
                        ]
                    ),
                    "date": (
                        session[
                            "date"
                        ]
                    ),
                    "trade_status": (
                        trade_status
                    ),
                    "trajectory_path": (
                        trajectory_path
                    ),
                    "trajectory_sha256": (
                        trajectory_hash
                    ),
                    "requires_runner_candles": (
                        _requires_runner_candles(
                            experiment
                        )
                    ),
                    "execution_status": (
                        initial_status
                    ),
                    "attempt_count": 0,
                    "engine_version": (
                        BATCH_EXECUTOR_VERSION
                    ),
                    "rules_version": (
                        rules_version
                    ),
                }
            )

    return units


def assign_batches(
    *,
    units: list[
        dict[str, Any]
    ],
    batch_size: int,
) -> list[dict[str, Any]]:
    if (
        not isinstance(
            batch_size,
            int,
        )
        or batch_size <= 0
    ):
        raise ValueError(
            "batch_size must be a "
            "positive integer."
        )

    ordered = sorted(
        (
            dict(row)
            for row in units
        ),
        key=lambda row: (
            row["experiment_id"],
            row["date"],
            row[
                "execution_unit_id"
            ],
        ),
    )

    for index in range(
        0,
        len(ordered),
        batch_size,
    ):
        batch_number = (
            index // batch_size
            + 1
        )

        batch_rows = ordered[
            index:
            index + batch_size
        ]

        ids = [
            row[
                "execution_unit_id"
            ]
            for row in batch_rows
        ]

        batch_id = (
            deterministic_batch_id(
                batch_number=(
                    batch_number
                ),
                execution_unit_ids=ids,
            )
        )

        for row in batch_rows:
            row[
                "batch_id"
            ] = batch_id

    return ordered


def write_execution_plan(
    *,
    rows: list[
        dict[str, Any]
    ],
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
            row["date"],
            row[
                "execution_unit_id"
            ],
        ),
    )

    table = pa.Table.from_pylist(
        ordered,
        schema=PLAN_SCHEMA,
    )

    pq.write_table(
        table,
        output_path,
        compression="zstd",
    )

    return output_path


def build_execution_plan(
    *,
    valid_experiments_path: (
        str | Path
    ) = (
        "data/research/"
        "valid_experiments.parquet"
    ),
    registry_path: (
        str | Path
    ) = (
        "data/research/"
        "experiment_registry.parquet"
    ),
    trajectory_manifest_path: (
        str | Path
    ) = (
        "data/research/"
        "trade1_trajectory_manifest.parquet"
    ),
    output_path: (
        str | Path
    ) = (
        "data/research/"
        "batch_execution_plan.parquet"
    ),
    batch_size: int = 1000,
) -> dict[str, Any]:
    valid_experiments_path = Path(
        valid_experiments_path
    )

    registry_path = Path(
        registry_path
    )

    trajectory_manifest_path = Path(
        trajectory_manifest_path
    )

    output_path = Path(
        output_path
    )

    experiments = _read_rows(
        valid_experiments_path
    )

    registry_rows = _read_rows(
        registry_path
    )

    sessions = _read_rows(
        trajectory_manifest_path
    )

    _validate_registry(
        experiments=experiments,
        registry_rows=registry_rows,
    )

    units = build_execution_units(
        experiments=experiments,
        sessions=sessions,
    )

    planned = assign_batches(
        units=units,
        batch_size=batch_size,
    )

    write_execution_plan(
        rows=planned,
        output_path=output_path,
    )

    batch_ids = sorted(
        {
            row["batch_id"]
            for row in planned
        }
    )

    pending_total = sum(
        1
        for row in planned
        if row[
            "execution_status"
        ]
        == "PENDING"
    )

    skipped_total = sum(
        1
        for row in planned
        if row[
            "execution_status"
        ]
        == "SKIPPED_NO_TRADE"
    )

    expected_batches = (
        math.ceil(
            len(planned)
            / batch_size
        )
        if planned
        else 0
    )

    if (
        len(batch_ids)
        != expected_batches
    ):
        raise RuntimeError(
            "Batch count mismatch."
        )

    return {
        "rows": planned,
        "execution_units_total": (
            len(planned)
        ),
        "pending_total": (
            pending_total
        ),
        "skipped_total": (
            skipped_total
        ),
        "batches_total": (
            len(batch_ids)
        ),
        "batch_ids": (
            batch_ids
        ),
        "batch_size": (
            batch_size
        ),
        "output_path": str(
            output_path
        ),
        "output_sha256": (
            sha256_file(
                output_path
            )
        ),
        (
            "source_valid_experiments_sha256"
        ): sha256_file(
            valid_experiments_path
        ),
        "source_registry_sha256": (
            sha256_file(
                registry_path
            )
        ),
        (
            "source_trajectory_manifest_sha256"
        ): sha256_file(
            trajectory_manifest_path
        ),
    }