from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.batch_execution import (
    BATCH_RESULT_SCHEMA,
    execute_batch,
)
from operar_range.research_engine import (
    MOTOR_VERSION,
    RULES_VERSION,
)


DISTRIBUTED_ENGINE_VERSION = (
    "distributed-executor-v1"
)

BATCH_PACKAGE_VERSION = (
    "distributed-batch-package-v1"
)

WORKER_CONTRACT_VERSION = (
    "distributed-worker-contract-v1"
)

BATCH_STATES = {
    "PENDING",
    "CLAIMED",
    "RUNNING",
    "COMPLETED",
    "FAILED",
}


ATTEMPT_SCHEMA = pa.schema(
    [
        ("run_id", pa.string()),
        ("batch_id", pa.string()),
        ("attempt_count", pa.int64()),
        ("worker_id", pa.string()),
        ("status", pa.string()),
        ("claimed_at", pa.string()),
        ("started_at", pa.string()),
        ("completed_at", pa.string()),
        ("heartbeat_at", pa.string()),
        ("lease_expires_at", pa.string()),
        ("exception_type", pa.string()),
        ("error_message", pa.string()),
        ("result_path", pa.string()),
        ("result_sha256", pa.string()),
        (
            "worker_manifest_path",
            pa.string(),
        ),
        (
            "worker_manifest_sha256",
            pa.string(),
        ),
    ]
)


DISTRIBUTED_RESULT_SCHEMA = (
    BATCH_RESULT_SCHEMA
)


@dataclass(frozen=True)
class DistributedSources:
    batch_plan_sha256: str
    registry_sha256: str
    trajectory_manifest_sha256: str
    rule_set_sha256: str
    valid_experiments_sha256: str
    motor_version: str
    rules_version: str


def utc_now() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
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
        value.encode(
            "utf-8"
        )
    ).hexdigest()


def sha256_file(
    path: str | Path,
) -> str:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as file:
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


def _write_rows(
    *,
    rows: list[dict[str, Any]],
    schema: pa.Schema,
    path: str | Path,
) -> Path:
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        rows,
        schema=schema,
    )

    pq.write_table(
        table,
        path,
        compression="zstd",
    )

    return path


def _read_json(
    path: str | Path,
) -> dict[str, Any]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def _write_json(
    *,
    value: dict[str, Any],
    path: str | Path,
) -> Path:
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return path


def _relative_path(
    *,
    path: str | Path,
    project_root: str | Path,
) -> str:
    path = Path(path)

    project_root = Path(
        project_root
    ).resolve()

    resolved = path.resolve()

    try:
        return str(
            resolved.relative_to(
                project_root
            )
        )

    except ValueError:
        raise RuntimeError(
            "Distributed execution "
            "requires paths inside "
            "project_root. "
            f"Invalid path: {resolved}"
        )


def _resolve_project_path(
    *,
    path: str | Path,
    project_root: str | Path,
) -> Path:
    path = Path(path)

    if path.is_absolute():
        raise RuntimeError(
            "Absolute paths are not "
            "allowed in distributed "
            "batch contracts."
        )

    return (
        Path(project_root)
        / path
    ).resolve()


def load_rule_set_sha256(
    constraint_summary_path: (
        str | Path
    ),
) -> str:
    summary = _read_json(
        constraint_summary_path
    )

    value = summary.get(
        "rule_set_sha256"
    )

    if not value:
        raise RuntimeError(
            "rule_set_sha256 missing "
            "from Constraint Engine "
            "summary."
        )

    return str(value)


def build_source_contract(
    *,
    batch_plan_path: str | Path,
    registry_path: str | Path,
    trajectory_manifest_path: (
        str | Path
    ),
    valid_experiments_path: (
        str | Path
    ),
    constraint_summary_path: (
        str | Path
    ),
) -> DistributedSources:
    return DistributedSources(
        batch_plan_sha256=(
            sha256_file(
                batch_plan_path
            )
        ),
        registry_sha256=(
            sha256_file(
                registry_path
            )
        ),
        trajectory_manifest_sha256=(
            sha256_file(
                trajectory_manifest_path
            )
        ),
        rule_set_sha256=(
            load_rule_set_sha256(
                constraint_summary_path
            )
        ),
        valid_experiments_sha256=(
            sha256_file(
                valid_experiments_path
            )
        ),
        motor_version=MOTOR_VERSION,
        rules_version=RULES_VERSION,
    )


def build_run_id(
    sources: DistributedSources,
) -> str:
    payload = {
        "batch_plan_sha256": (
            sources.batch_plan_sha256
        ),
        "registry_sha256": (
            sources.registry_sha256
        ),
        (
            "trajectory_manifest_sha256"
        ): (
            sources
            .trajectory_manifest_sha256
        ),
        "rule_set_sha256": (
            sources.rule_set_sha256
        ),
        (
            "valid_experiments_sha256"
        ): (
            sources
            .valid_experiments_sha256
        ),
        "motor_version": (
            sources.motor_version
        ),
        "rules_version": (
            sources.rules_version
        ),
        (
            "distributed_engine_version"
        ): (
            DISTRIBUTED_ENGINE_VERSION
        ),
    }

    digest = _sha256_text(
        _canonical_json(
            payload
        )
    )

    return (
        "DRUN-"
        + digest[:24]
    )


def _batch_package_dir(
    *,
    distributed_root: str | Path,
    run_id: str,
    batch_id: str,
) -> Path:
    return (
        Path(distributed_root)
        / run_id
        / "packages"
        / batch_id
    )


def _batch_runtime_dir(
    *,
    distributed_root: str | Path,
    run_id: str,
    batch_id: str,
) -> Path:
    return (
        Path(distributed_root)
        / run_id
        / batch_id
    )


def _attempt_dir(
    *,
    distributed_root: str | Path,
    run_id: str,
    batch_id: str,
    attempt_count: int,
) -> Path:
    return (
        _batch_runtime_dir(
            distributed_root=(
                distributed_root
            ),
            run_id=run_id,
            batch_id=batch_id,
        )
        / (
            f"attempt_"
            f"{attempt_count:04d}"
        )
    )


def serialize_batch(
    *,
    batch_id: str,
    run_id: str,
    project_root: str | Path,
    batch_plan_path: str | Path,
    registry_path: str | Path,
    trajectory_manifest_path: (
        str | Path
    ),
    valid_experiments_path: (
        str | Path
    ),
    constraint_summary_path: (
        str | Path
    ),
    distributed_root: str | Path = (
        "data/research/"
        "distributed_runs"
    ),
) -> dict[str, Any]:
    project_root = Path(
        project_root
    ).resolve()

    sources = (
        build_source_contract(
            batch_plan_path=(
                batch_plan_path
            ),
            registry_path=(
                registry_path
            ),
            trajectory_manifest_path=(
                trajectory_manifest_path
            ),
            valid_experiments_path=(
                valid_experiments_path
            ),
            constraint_summary_path=(
                constraint_summary_path
            ),
        )
    )

    expected_run_id = (
        build_run_id(
            sources
        )
    )

    if run_id != expected_run_id:
        raise RuntimeError(
            "run_id does not match "
            "source contract."
        )

    plan_table = pq.read_table(
        batch_plan_path
    )

    plan_rows = (
        plan_table.to_pylist()
    )

    batch_rows = [
        dict(row)
        for row in plan_rows
        if row["batch_id"]
        == batch_id
    ]

    if not batch_rows:
        raise ValueError(
            f"Unknown batch_id: "
            f"{batch_id}"
        )

    batch_rows = sorted(
        batch_rows,
        key=lambda row: (
            row[
                "execution_unit_id"
            ]
        ),
    )

    experiment_ids = sorted(
        {
            row[
                "experiment_id"
            ]
            for row in batch_rows
        }
    )

    dates = sorted(
        {
            row["date"]
            for row in batch_rows
        }
    )

    all_experiments = (
        _read_rows(
            valid_experiments_path
        )
    )

    experiment_rows = [
        row
        for row in all_experiments
        if row[
            "experiment_id"
        ]
        in experiment_ids
    ]

    found_experiment_ids = {
        row[
            "experiment_id"
        ]
        for row in experiment_rows
    }

    missing_experiments = (
        set(
            experiment_ids
        )
        - found_experiment_ids
    )

    if missing_experiments:
        raise RuntimeError(
            "Batch references missing "
            "valid experiments: "
            f"{sorted(missing_experiments)}"
        )

    trajectory_table = (
        pq.read_table(
            trajectory_manifest_path
        )
    )

    trajectory_rows = [
        row
        for row
        in trajectory_table.to_pylist()
        if row["date"] in dates
    ]

    found_dates = {
        row["date"]
        for row in trajectory_rows
    }

    missing_dates = (
        set(dates)
        - found_dates
    )

    if missing_dates:
        raise RuntimeError(
            "Batch references missing "
            "sessions: "
            f"{sorted(missing_dates)}"
        )

    package_dir = (
        _batch_package_dir(
            distributed_root=(
                distributed_root
            ),
            run_id=run_id,
            batch_id=batch_id,
        )
    )

    package_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    package_plan_path = (
        package_dir
        / "batch_plan.parquet"
    )

    package_experiments_path = (
        package_dir
        / "experiments.parquet"
    )

    package_trajectory_path = (
        package_dir
        / "trajectory_manifest.parquet"
    )

    package_manifest_path = (
        package_dir
        / "batch_manifest.json"
    )

    package_plan_rows = []

    for row in batch_rows:
        copied = dict(row)

        #
        # IMPORTANTE:
        #
        # O plano oficial da Etapa 15
        # pode estar totalmente
        # COMPLETED ou conter unidades
        # SKIPPED_NO_TRADE.
        #
        # Esses estados representam o
        # checkpoint da execução local
        # da Etapa 15.
        #
        # Eles NÃO podem controlar a
        # execução independente do
        # worker distribuído.
        #
        # O pacote distribuído representa
        # uma nova execução física do
        # mesmo plano lógico.
        #
        # Portanto TODAS as execution
        # units do pacote são
        # materializadas como PENDING.
        #
        # Isso NÃO modifica o plano
        # oficial e NÃO modifica a
        # identidade lógica da unidade.
        #
        copied[
            "execution_status"
        ] = "PENDING"

        #
        # attempt_count do Batch Executor
        # local também não deve vazar
        # para o contrato do worker.
        #
        # As tentativas distribuídas são
        # auditadas separadamente em
        # attempts.parquet.
        #
        if (
            "attempt_count"
            in copied
        ):
            copied[
                "attempt_count"
            ] = 0

        trajectory_path = (
            copied.get(
                "trajectory_path"
            )
        )

        if trajectory_path:
            copied[
                "trajectory_path"
            ] = _relative_path(
                path=trajectory_path,
                project_root=(
                    project_root
                ),
            )

        package_plan_rows.append(
            copied
        )

    _write_rows(
        rows=package_plan_rows,
        schema=plan_table.schema,
        path=package_plan_path,
    )

    experiment_schema = (
        pq.read_table(
            valid_experiments_path
        ).schema
    )

    _write_rows(
        rows=experiment_rows,
        schema=experiment_schema,
        path=(
            package_experiments_path
        ),
    )

    _write_rows(
        rows=trajectory_rows,
        schema=(
            trajectory_table.schema
        ),
        path=(
            package_trajectory_path
        ),
    )

    execution_unit_ids = [
        row[
            "execution_unit_id"
        ]
        for row in batch_rows
    ]

    package_manifest = {
        "package_version": (
            BATCH_PACKAGE_VERSION
        ),
        "worker_contract_version": (
            WORKER_CONTRACT_VERSION
        ),
        (
            "distributed_engine_version"
        ): (
            DISTRIBUTED_ENGINE_VERSION
        ),
        "run_id": run_id,
        "batch_id": batch_id,
        "execution_unit_count": (
            len(batch_rows)
        ),
        "execution_unit_ids": (
            execution_unit_ids
        ),
        "experiment_ids": (
            experiment_ids
        ),
        "session_dates": dates,
        "motor_version": (
            MOTOR_VERSION
        ),
        "rules_version": (
            RULES_VERSION
        ),
        "source_hashes": {
            "batch_plan_sha256": (
                sources.batch_plan_sha256
            ),
            "registry_sha256": (
                sources.registry_sha256
            ),
            (
                "trajectory_manifest_sha256"
            ): (
                sources
                .trajectory_manifest_sha256
            ),
            "rule_set_sha256": (
                sources.rule_set_sha256
            ),
            (
                "valid_experiments_sha256"
            ): (
                sources
                .valid_experiments_sha256
            ),
        },
        "package_files": {
            "batch_plan": (
                "batch_plan.parquet"
            ),
            "experiments": (
                "experiments.parquet"
            ),
            "trajectory_manifest": (
                "trajectory_manifest.parquet"
            ),
        },
        "package_hashes": {
            "batch_plan": (
                sha256_file(
                    package_plan_path
                )
            ),
            "experiments": (
                sha256_file(
                    package_experiments_path
                )
            ),
            "trajectory_manifest": (
                sha256_file(
                    package_trajectory_path
                )
            ),
        },
    }

    _write_json(
        value=package_manifest,
        path=package_manifest_path,
    )

    return {
        "run_id": run_id,
        "batch_id": batch_id,
        "package_dir": str(
            package_dir
        ),
        "package_manifest_path": str(
            package_manifest_path
        ),
        (
            "package_manifest_sha256"
        ): (
            sha256_file(
                package_manifest_path
            )
        ),
        "execution_units": len(
            batch_rows
        ),
    }


def serialize_all_batches(
    *,
    project_root: str | Path,
    batch_plan_path: str | Path,
    registry_path: str | Path,
    trajectory_manifest_path: (
        str | Path
    ),
    valid_experiments_path: (
        str | Path
    ),
    constraint_summary_path: (
        str | Path
    ),
    distributed_root: str | Path = (
        "data/research/"
        "distributed_runs"
    ),
) -> dict[str, Any]:
    sources = (
        build_source_contract(
            batch_plan_path=(
                batch_plan_path
            ),
            registry_path=(
                registry_path
            ),
            trajectory_manifest_path=(
                trajectory_manifest_path
            ),
            valid_experiments_path=(
                valid_experiments_path
            ),
            constraint_summary_path=(
                constraint_summary_path
            ),
        )
    )

    run_id = build_run_id(
        sources
    )

    plan_rows = _read_rows(
        batch_plan_path
    )

    batch_ids = sorted(
        {
            row["batch_id"]
            for row in plan_rows
        }
    )

    packages = []

    for batch_id in batch_ids:
        packages.append(
            serialize_batch(
                batch_id=batch_id,
                run_id=run_id,
                project_root=(
                    project_root
                ),
                batch_plan_path=(
                    batch_plan_path
                ),
                registry_path=(
                    registry_path
                ),
                trajectory_manifest_path=(
                    trajectory_manifest_path
                ),
                valid_experiments_path=(
                    valid_experiments_path
                ),
                constraint_summary_path=(
                    constraint_summary_path
                ),
                distributed_root=(
                    distributed_root
                ),
            )
        )

    run_root = (
        Path(distributed_root)
        / run_id
    )

    run_manifest_path = (
        run_root
        / "distributed_run_manifest.json"
    )

    run_manifest = {
        "run_id": run_id,
        (
            "distributed_engine_version"
        ): (
            DISTRIBUTED_ENGINE_VERSION
        ),
        "worker_contract_version": (
            WORKER_CONTRACT_VERSION
        ),
        "motor_version": (
            MOTOR_VERSION
        ),
        "rules_version": (
            RULES_VERSION
        ),
        "batches_total": len(
            batch_ids
        ),
        "execution_units_total": (
            len(
                plan_rows
            )
        ),
        "batch_ids": batch_ids,
        "source_hashes": {
            "batch_plan_sha256": (
                sources.batch_plan_sha256
            ),
            "registry_sha256": (
                sources.registry_sha256
            ),
            (
                "trajectory_manifest_sha256"
            ): (
                sources
                .trajectory_manifest_sha256
            ),
            "rule_set_sha256": (
                sources.rule_set_sha256
            ),
            (
                "valid_experiments_sha256"
            ): (
                sources
                .valid_experiments_sha256
            ),
        },
    }

    _write_json(
        value=run_manifest,
        path=run_manifest_path,
    )

    return {
        "run_id": run_id,
        "batches_total": len(
            batch_ids
        ),
        "execution_units_total": (
            len(
                plan_rows
            )
        ),
        "packages": packages,
        "run_manifest_path": str(
            run_manifest_path
        ),
        "run_manifest_sha256": (
            sha256_file(
                run_manifest_path
            )
        ),
    }


def _attempts_path(
    *,
    distributed_root: str | Path,
    run_id: str,
    batch_id: str,
) -> Path:
    return (
        _batch_runtime_dir(
            distributed_root=(
                distributed_root
            ),
            run_id=run_id,
            batch_id=batch_id,
        )
        / "attempts.parquet"
    )


def read_attempts(
    *,
    distributed_root: str | Path,
    run_id: str,
    batch_id: str,
) -> list[dict[str, Any]]:
    path = _attempts_path(
        distributed_root=(
            distributed_root
        ),
        run_id=run_id,
        batch_id=batch_id,
    )

    if not path.exists():
        return []

    return pq.read_table(
        path
    ).to_pylist()


def _write_attempts(
    *,
    distributed_root: str | Path,
    run_id: str,
    batch_id: str,
    rows: list[dict[str, Any]],
) -> Path:
    path = _attempts_path(
        distributed_root=(
            distributed_root
        ),
        run_id=run_id,
        batch_id=batch_id,
    )

    ordered = sorted(
        rows,
        key=lambda row: (
            int(
                row[
                    "attempt_count"
                ]
            )
        ),
    )

    return _write_rows(
        rows=ordered,
        schema=ATTEMPT_SCHEMA,
        path=path,
    )


def claim_batch(
    *,
    distributed_root: str | Path,
    run_id: str,
    batch_id: str,
    worker_id: str,
) -> dict[str, Any]:
    if not worker_id:
        raise ValueError(
            "worker_id is required."
        )

    attempts = read_attempts(
        distributed_root=(
            distributed_root
        ),
        run_id=run_id,
        batch_id=batch_id,
    )

    completed_attempts = [
        row
        for row in attempts
        if row["status"]
        == "COMPLETED"
    ]

    if completed_attempts:
        raise RuntimeError(
            "Batch already has a "
            "COMPLETED logical result."
        )

    active_attempts = [
        row
        for row in attempts
        if row["status"]
        in (
            "CLAIMED",
            "RUNNING",
        )
    ]

    if active_attempts:
        raise RuntimeError(
            "Batch is already claimed "
            "by an active worker."
        )

    attempt_count = (
        max(
            (
                int(
                    row[
                        "attempt_count"
                    ]
                )
                for row in attempts
            ),
            default=0,
        )
        + 1
    )

    claimed_at = utc_now()

    row = {
        "run_id": run_id,
        "batch_id": batch_id,
        "attempt_count": (
            attempt_count
        ),
        "worker_id": worker_id,
        "status": "CLAIMED",
        "claimed_at": (
            claimed_at
        ),
        "started_at": None,
        "completed_at": None,
        "heartbeat_at": None,
        "lease_expires_at": None,
        "exception_type": None,
        "error_message": None,
        "result_path": None,
        "result_sha256": None,
        "worker_manifest_path": None,
        "worker_manifest_sha256": (
            None
        ),
    }

    attempts.append(
        row
    )

    _write_attempts(
        distributed_root=(
            distributed_root
        ),
        run_id=run_id,
        batch_id=batch_id,
        rows=attempts,
    )

    return dict(row)


def _update_attempt(
    *,
    distributed_root: str | Path,
    run_id: str,
    batch_id: str,
    attempt_count: int,
    updates: dict[str, Any],
) -> dict[str, Any]:
    attempts = read_attempts(
        distributed_root=(
            distributed_root
        ),
        run_id=run_id,
        batch_id=batch_id,
    )

    found = False
    updated = None

    for row in attempts:
        if (
            int(
                row[
                    "attempt_count"
                ]
            )
            == int(
                attempt_count
            )
        ):
            found = True

            row.update(
                updates
            )

            updated = dict(
                row
            )

            break

    if not found:
        raise KeyError(
            (
                run_id,
                batch_id,
                attempt_count,
            )
        )

    _write_attempts(
        distributed_root=(
            distributed_root
        ),
        run_id=run_id,
        batch_id=batch_id,
        rows=attempts,
    )

    return updated


def validate_worker_sources(
    *,
    package_manifest: dict[str, Any],
    batch_plan_path: str | Path,
    registry_path: str | Path,
    trajectory_manifest_path: (
        str | Path
    ),
    valid_experiments_path: (
        str | Path
    ),
    constraint_summary_path: (
        str | Path
    ),
) -> tuple[
    bool,
    dict[str, dict[str, str]],
]:
    expected = package_manifest[
        "source_hashes"
    ]

    actual = {
        "batch_plan_sha256": (
            sha256_file(
                batch_plan_path
            )
        ),
        "registry_sha256": (
            sha256_file(
                registry_path
            )
        ),
        (
            "trajectory_manifest_sha256"
        ): (
            sha256_file(
                trajectory_manifest_path
            )
        ),
        "rule_set_sha256": (
            load_rule_set_sha256(
                constraint_summary_path
            )
        ),
        (
            "valid_experiments_sha256"
        ): (
            sha256_file(
                valid_experiments_path
            )
        ),
    }

    mismatches = {}

    for key, expected_value in (
        expected.items()
    ):
        actual_value = actual.get(
            key
        )

        if (
            actual_value
            != expected_value
        ):
            mismatches[key] = {
                "expected": (
                    expected_value
                ),
                "actual": (
                    actual_value
                ),
            }

    return (
        not bool(
            mismatches
        ),
        mismatches,
    )


def execute_worker(
    *,
    project_root: str | Path,
    distributed_root: str | Path,
    run_id: str,
    batch_id: str,
    worker_id: str,
    batch_plan_path: str | Path,
    registry_path: str | Path,
    trajectory_manifest_path: (
        str | Path
    ),
    valid_experiments_path: (
        str | Path
    ),
    constraint_summary_path: (
        str | Path
    ),
    normalized_dir: str | Path = (
        "data/normalized"
    ),
    force_failure: bool = False,
) -> dict[str, Any]:
    project_root = Path(
        project_root
    ).resolve()

    package_dir = (
        _batch_package_dir(
            distributed_root=(
                distributed_root
            ),
            run_id=run_id,
            batch_id=batch_id,
        )
    )

    package_manifest_path = (
        package_dir
        / "batch_manifest.json"
    )

    package_manifest = (
        _read_json(
            package_manifest_path
        )
    )

    if (
        package_manifest[
            "run_id"
        ]
        != run_id
    ):
        raise RuntimeError(
            "Package run_id mismatch."
        )

    if (
        package_manifest[
            "batch_id"
        ]
        != batch_id
    ):
        raise RuntimeError(
            "Package batch_id mismatch."
        )

    claim = claim_batch(
        distributed_root=(
            distributed_root
        ),
        run_id=run_id,
        batch_id=batch_id,
        worker_id=worker_id,
    )

    attempt_count = int(
        claim[
            "attempt_count"
        ]
    )

    attempt_dir = (
        _attempt_dir(
            distributed_root=(
                distributed_root
            ),
            run_id=run_id,
            batch_id=batch_id,
            attempt_count=(
                attempt_count
            ),
        )
    )

    attempt_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    started_at = utc_now()

    _update_attempt(
        distributed_root=(
            distributed_root
        ),
        run_id=run_id,
        batch_id=batch_id,
        attempt_count=(
            attempt_count
        ),
        updates={
            "status": "RUNNING",
            "started_at": (
                started_at
            ),
        },
    )

    try:
        source_ok, mismatches = (
            validate_worker_sources(
                package_manifest=(
                    package_manifest
                ),
                batch_plan_path=(
                    batch_plan_path
                ),
                registry_path=(
                    registry_path
                ),
                trajectory_manifest_path=(
                    trajectory_manifest_path
                ),
                valid_experiments_path=(
                    valid_experiments_path
                ),
                constraint_summary_path=(
                    constraint_summary_path
                ),
            )
        )

        if not source_ok:
            raise RuntimeError(
                "SOURCE_MISMATCH: "
                + _canonical_json(
                    mismatches
                )
            )

        if (
            package_manifest[
                "motor_version"
            ]
            != MOTOR_VERSION
        ):
            raise RuntimeError(
                "SOURCE_MISMATCH: "
                "motor_version"
            )

        if (
            package_manifest[
                "rules_version"
            ]
            != RULES_VERSION
        ):
            raise RuntimeError(
                "SOURCE_MISMATCH: "
                "rules_version"
            )

        if force_failure:
            raise RuntimeError(
                "CONTROLLED_FAILURE"
            )

        package_plan_path = (
            package_dir
            / package_manifest[
                "package_files"
            ]["batch_plan"]
        )

        package_experiments_path = (
            package_dir
            / package_manifest[
                "package_files"
            ]["experiments"]
        )

        package_trajectory_path = (
            package_dir
            / package_manifest[
                "package_files"
            ]["trajectory_manifest"]
        )

        package_hashes = (
            package_manifest[
                "package_hashes"
            ]
        )

        package_actual_hashes = {
            "batch_plan": (
                sha256_file(
                    package_plan_path
                )
            ),
            "experiments": (
                sha256_file(
                    package_experiments_path
                )
            ),
            "trajectory_manifest": (
                sha256_file(
                    package_trajectory_path
                )
            ),
        }

        if (
            package_actual_hashes
            != package_hashes
        ):
            raise RuntimeError(
                "SOURCE_MISMATCH: "
                "serialized batch package"
            )

        local_plan_table = (
            pq.read_table(
                package_plan_path
            )
        )

        local_plan_rows = (
            local_plan_table.to_pylist()
        )

        rewritten_rows = []

        for row in local_plan_rows:
            copied = dict(row)

            trajectory_path = (
                copied.get(
                    "trajectory_path"
                )
            )

            if trajectory_path:
                copied[
                    "trajectory_path"
                ] = str(
                    _resolve_project_path(
                        path=(
                            trajectory_path
                        ),
                        project_root=(
                            project_root
                        ),
                    )
                )

            rewritten_rows.append(
                copied
            )

        runtime_plan_path = (
            attempt_dir
            / "runtime_plan.parquet"
        )

        _write_rows(
            rows=rewritten_rows,
            schema=(
                local_plan_table.schema
            ),
            path=runtime_plan_path,
        )

        runtime_batches_dir = (
            attempt_dir
            / "runtime_batch"
        )

        normalized_path = (
            _resolve_project_path(
                path=normalized_dir,
                project_root=(
                    project_root
                ),
            )
        )

        execution_result = (
            execute_batch(
                batch_id=batch_id,
                plan_path=(
                    runtime_plan_path
                ),
                valid_experiments_path=(
                    package_experiments_path
                ),
                trajectory_manifest_path=(
                    package_trajectory_path
                ),
                normalized_dir=(
                    normalized_path
                ),
                batches_dir=(
                    runtime_batches_dir
                ),
            )
        )

        if execution_result[
            "failures"
        ]:
            raise RuntimeError(
                "Worker batch execution "
                "contains execution unit "
                "failures: "
                + _canonical_json(
                    execution_result[
                        "failures"
                    ]
                )
            )

        runtime_result_path = Path(
            execution_result[
                "output_path"
            ]
        )

        result_path = (
            attempt_dir
            / "result.parquet"
        )

        shutil.copyfile(
            runtime_result_path,
            result_path,
        )

        result_rows = _read_rows(
            result_path
        )

        expected_unit_ids = set(
            package_manifest[
                "execution_unit_ids"
            ]
        )

        actual_unit_ids = {
            row[
                "execution_unit_id"
            ]
            for row in result_rows
        }

        if (
            expected_unit_ids
            != actual_unit_ids
        ):
            raise RuntimeError(
                "Worker result execution "
                "unit set mismatch."
            )

        if (
            len(result_rows)
            != len(
                actual_unit_ids
            )
        ):
            raise RuntimeError(
                "Duplicate "
                "execution_unit_id inside "
                "worker result."
            )

        result_sha = (
            sha256_file(
                result_path
            )
        )

        completed_at = utc_now()

        worker_manifest = {
            "worker_contract_version": (
                WORKER_CONTRACT_VERSION
            ),
            (
                "distributed_engine_version"
            ): (
                DISTRIBUTED_ENGINE_VERSION
            ),
            "run_id": run_id,
            "batch_id": batch_id,
            "worker_id": worker_id,
            "attempt_count": (
                attempt_count
            ),
            "status": "COMPLETED",
            "claimed_at": (
                claim[
                    "claimed_at"
                ]
            ),
            "started_at": (
                started_at
            ),
            "completed_at": (
                completed_at
            ),
            "heartbeat_at": None,
            "lease_expires_at": None,
            "execution_units": (
                len(
                    result_rows
                )
            ),
            "result_path": (
                "result.parquet"
            ),
            "result_sha256": (
                result_sha
            ),
            "motor_version": (
                MOTOR_VERSION
            ),
            "rules_version": (
                RULES_VERSION
            ),
            "source_hashes": (
                package_manifest[
                    "source_hashes"
                ]
            ),
            (
                "package_manifest_sha256"
            ): (
                sha256_file(
                    package_manifest_path
                )
            ),
        }

        worker_manifest_path = (
            attempt_dir
            / "worker_manifest.json"
        )

        _write_json(
            value=worker_manifest,
            path=(
                worker_manifest_path
            ),
        )

        worker_manifest_sha = (
            sha256_file(
                worker_manifest_path
            )
        )

        _update_attempt(
            distributed_root=(
                distributed_root
            ),
            run_id=run_id,
            batch_id=batch_id,
            attempt_count=(
                attempt_count
            ),
            updates={
                "status": "COMPLETED",
                "completed_at": (
                    completed_at
                ),
                "result_path": str(
                    result_path
                ),
                "result_sha256": (
                    result_sha
                ),
                (
                    "worker_manifest_path"
                ): str(
                    worker_manifest_path
                ),
                (
                    "worker_manifest_sha256"
                ): (
                    worker_manifest_sha
                ),
            },
        )

        return {
            "run_id": run_id,
            "batch_id": batch_id,
            "worker_id": worker_id,
            "attempt_count": (
                attempt_count
            ),
            "status": "COMPLETED",
            "execution_units": (
                len(
                    result_rows
                )
            ),
            "result_path": str(
                result_path
            ),
            "result_sha256": (
                result_sha
            ),
            "worker_manifest_path": str(
                worker_manifest_path
            ),
            (
                "worker_manifest_sha256"
            ): (
                worker_manifest_sha
            ),
        }

    except Exception as exc:
        completed_at = utc_now()

        worker_manifest = {
            "worker_contract_version": (
                WORKER_CONTRACT_VERSION
            ),
            (
                "distributed_engine_version"
            ): (
                DISTRIBUTED_ENGINE_VERSION
            ),
            "run_id": run_id,
            "batch_id": batch_id,
            "worker_id": worker_id,
            "attempt_count": (
                attempt_count
            ),
            "status": "FAILED",
            "claimed_at": (
                claim[
                    "claimed_at"
                ]
            ),
            "started_at": (
                started_at
            ),
            "completed_at": (
                completed_at
            ),
            "heartbeat_at": None,
            "lease_expires_at": None,
            "exception_type": (
                type(exc).__name__
            ),
            "error_message": str(
                exc
            ),
            "motor_version": (
                MOTOR_VERSION
            ),
            "rules_version": (
                RULES_VERSION
            ),
        }

        worker_manifest_path = (
            attempt_dir
            / "worker_manifest.json"
        )

        _write_json(
            value=worker_manifest,
            path=(
                worker_manifest_path
            ),
        )

        worker_manifest_sha = (
            sha256_file(
                worker_manifest_path
            )
        )

        _update_attempt(
            distributed_root=(
                distributed_root
            ),
            run_id=run_id,
            batch_id=batch_id,
            attempt_count=(
                attempt_count
            ),
            updates={
                "status": "FAILED",
                "completed_at": (
                    completed_at
                ),
                "exception_type": (
                    type(exc).__name__
                ),
                "error_message": str(
                    exc
                ),
                (
                    "worker_manifest_path"
                ): str(
                    worker_manifest_path
                ),
                (
                    "worker_manifest_sha256"
                ): (
                    worker_manifest_sha
                ),
            },
        )

        return {
            "run_id": run_id,
            "batch_id": batch_id,
            "worker_id": worker_id,
            "attempt_count": (
                attempt_count
            ),
            "status": "FAILED",
            "exception_type": (
                type(exc).__name__
            ),
            "error_message": str(
                exc
            ),
            "worker_manifest_path": str(
                worker_manifest_path
            ),
            (
                "worker_manifest_sha256"
            ): (
                worker_manifest_sha
            ),
        }


def _logical_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row[
                "execution_unit_id"
            ]
        ),
    )


def logical_result_sha256(
    rows: list[dict[str, Any]],
) -> str:
    normalized = []

    fields = (
        "execution_unit_id",
        "experiment_id",
        "date",
        "trade_status",
        "direction",
        "stop_points",
        "partial_1_points",
        "partial_1_pct",
        "partial_2_points",
        "partial_2_pct",
        "partial_3_points",
        "partial_3_pct",
        "break_even",
        "break_even_after_partial",
        "runner",
        "runner_pct",
        "runner_rule",
        "final_target",
        "position_size",
        "total_weighted_points",
        "trade1_result_points",
        "trade2_eligible",
        "trade2_occurred",
        "trade2_executed",
        "trade2_winner",
        "trade2_loser",
        "trade2_breakeven",
        "trade2_result_points",
        "consolidated_result_points",
        "trade2_direction",
        "trade2_trigger_level",
        "trade2_entry_timestamp",
        "trade2_entry_trade_number",
        "trade2_first_traded_price",
        "trade2_jumped_entry_level",
        "trade2_final_reason",
        "trade2_final_timestamp",
        "trade2_final_price",
        "trade2_mfe",
        "trade2_mae",
        "trade2_management_json",
        "lifecycle_version",
        "final_reason",
        "final_timestamp",
        "final_price",
        "mfe",
        "mae",
        "trajectory_sha256",
        "config_sha256",
        "motor_version",
        "rules_version",
    )

    for row in _logical_rows(
        rows
    ):
        normalized.append(
            {
                key: row.get(
                    key
                )
                for key in fields
            }
        )

    return _sha256_text(
        _canonical_json(
            normalized
        )
    )


def merge_distributed_results(
    *,
    distributed_root: str | Path,
    run_id: str,
    output_path: str | Path,
) -> dict[str, Any]:
    run_root = (
        Path(distributed_root)
        / run_id
    )

    run_manifest_path = (
        run_root
        / (
            "distributed_run_manifest.json"
        )
    )

    run_manifest = (
        _read_json(
            run_manifest_path
        )
    )

    expected_batch_ids = (
        run_manifest[
            "batch_ids"
        ]
    )

    all_rows = []
    selected_attempts = []
    duplicate_attempts = 0

    for batch_id in (
        expected_batch_ids
    ):
        attempts = read_attempts(
            distributed_root=(
                distributed_root
            ),
            run_id=run_id,
            batch_id=batch_id,
        )

        completed = sorted(
            [
                row
                for row in attempts
                if row[
                    "status"
                ]
                == "COMPLETED"
            ],
            key=lambda row: (
                int(
                    row[
                        "attempt_count"
                    ]
                )
            ),
        )

        if not completed:
            raise RuntimeError(
                "Distributed merge "
                "requires COMPLETED batch: "
                f"{batch_id}"
            )

        selected = completed[0]

        if len(completed) > 1:
            duplicate_attempts += (
                len(completed)
                - 1
            )

            first_rows = _read_rows(
                selected[
                    "result_path"
                ]
            )

            first_hash = (
                logical_result_sha256(
                    first_rows
                )
            )

            for extra in (
                completed[1:]
            ):
                extra_rows = (
                    _read_rows(
                        extra[
                            "result_path"
                        ]
                    )
                )

                extra_hash = (
                    logical_result_sha256(
                        extra_rows
                    )
                )

                if (
                    extra_hash
                    != first_hash
                ):
                    raise RuntimeError(
                        "Multiple COMPLETED "
                        "attempts produced "
                        "different logical "
                        "results for "
                        f"{batch_id}."
                    )

        result_path = Path(
            selected[
                "result_path"
            ]
        )

        actual_sha = (
            sha256_file(
                result_path
            )
        )

        if (
            actual_sha
            != selected[
                "result_sha256"
            ]
        ):
            raise RuntimeError(
                "Worker result hash "
                "mismatch for "
                f"{batch_id}."
            )

        batch_rows = _read_rows(
            result_path
        )

        package_manifest = (
            _read_json(
                _batch_package_dir(
                    distributed_root=(
                        distributed_root
                    ),
                    run_id=run_id,
                    batch_id=batch_id,
                )
                / "batch_manifest.json"
            )
        )

        expected_unit_ids = set(
            package_manifest[
                "execution_unit_ids"
            ]
        )

        actual_unit_ids = {
            row[
                "execution_unit_id"
            ]
            for row in batch_rows
        }

        if (
            expected_unit_ids
            != actual_unit_ids
        ):
            raise RuntimeError(
                "Distributed merge "
                "execution_unit mismatch "
                f"for {batch_id}."
            )

        if (
            len(batch_rows)
            != len(
                actual_unit_ids
            )
        ):
            raise RuntimeError(
                "Duplicate "
                "execution_unit_id inside "
                f"{batch_id}."
            )

        all_rows.extend(
            batch_rows
        )

        selected_attempts.append(
            {
                "batch_id": (
                    batch_id
                ),
                "attempt_count": (
                    selected[
                        "attempt_count"
                    ]
                ),
                "worker_id": (
                    selected[
                        "worker_id"
                    ]
                ),
            }
        )

    all_execution_ids = [
        row[
            "execution_unit_id"
        ]
        for row in all_rows
    ]

    if (
        len(all_execution_ids)
        != len(
            set(
                all_execution_ids
            )
        )
    ):
        raise RuntimeError(
            "Duplicate logical "
            "execution_unit_id across "
            "distributed batches."
        )

    ordered = sorted(
        all_rows,
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

    _write_rows(
        rows=ordered,
        schema=(
            DISTRIBUTED_RESULT_SCHEMA
        ),
        path=output_path,
    )

    return {
        "run_id": run_id,
        "rows": len(
            ordered
        ),
        "batches": len(
            expected_batch_ids
        ),
        (
            "duplicate_completed_attempts"
        ): (
            duplicate_attempts
        ),
        "duplicate_logical_results": 0,
        "selected_attempts": (
            selected_attempts
        ),
        "output_path": str(
            output_path
        ),
        "output_sha256": (
            sha256_file(
                output_path
            )
        ),
        "logical_sha256": (
            logical_result_sha256(
                ordered
            )
        ),
    }


def compare_with_stage15(
    *,
    distributed_result_path: (
        str | Path
    ),
    stage15_result_path: str | Path,
) -> dict[str, Any]:
    distributed_rows = (
        _read_rows(
            distributed_result_path
        )
    )

    stage15_rows = (
        _read_rows(
            stage15_result_path
        )
    )

    distributed_by_id = {
        row[
            "execution_unit_id"
        ]: row
        for row in distributed_rows
    }

    stage15_by_id = {
        row[
            "execution_unit_id"
        ]: row
        for row in stage15_rows
    }

    same_ids = (
        set(
            distributed_by_id
        )
        == set(
            stage15_by_id
        )
    )

    if not same_ids:
        return {
            "match": False,
            "same_execution_unit_ids": (
                False
            ),
            (
                "distributed_logical_sha256"
            ): (
                logical_result_sha256(
                    distributed_rows
                )
            ),
            (
                "stage15_logical_sha256"
            ): (
                logical_result_sha256(
                    stage15_rows
                )
            ),
        }

    fields = (
        "execution_unit_id",
        "experiment_id",
        "date",
        "trade_status",
        "direction",
        "stop_points",
        "partial_1_points",
        "partial_1_pct",
        "partial_2_points",
        "partial_2_pct",
        "partial_3_points",
        "partial_3_pct",
        "break_even",
        "break_even_after_partial",
        "runner",
        "runner_pct",
        "runner_rule",
        "final_target",
        "position_size",
        "total_weighted_points",
        "trade1_result_points",
        "trade2_eligible",
        "trade2_occurred",
        "trade2_executed",
        "trade2_winner",
        "trade2_loser",
        "trade2_breakeven",
        "trade2_result_points",
        "consolidated_result_points",
        "trade2_direction",
        "trade2_trigger_level",
        "trade2_entry_timestamp",
        "trade2_entry_trade_number",
        "trade2_first_traded_price",
        "trade2_jumped_entry_level",
        "trade2_final_reason",
        "trade2_final_timestamp",
        "trade2_final_price",
        "trade2_mfe",
        "trade2_mae",
        "trade2_management_json",
        "lifecycle_version",
        "final_reason",
        "final_timestamp",
        "final_price",
        "mfe",
        "mae",
        "trajectory_sha256",
        "config_sha256",
        "motor_version",
        "rules_version",
    )

    mismatches = []

    for execution_unit_id in sorted(
        distributed_by_id
    ):
        left = distributed_by_id[
            execution_unit_id
        ]

        right = stage15_by_id[
            execution_unit_id
        ]

        for field in fields:
            if (
                left.get(field)
                != right.get(field)
            ):
                mismatches.append(
                    {
                        (
                            "execution_unit_id"
                        ): (
                            execution_unit_id
                        ),
                        "field": field,
                        "distributed": (
                            left.get(
                                field
                            )
                        ),
                        "stage15": (
                            right.get(
                                field
                            )
                        ),
                    }
                )

    distributed_hash = (
        logical_result_sha256(
            distributed_rows
        )
    )

    stage15_hash = (
        logical_result_sha256(
            stage15_rows
        )
    )

    return {
        "match": (
            len(
                mismatches
            )
            == 0
        ),
        "same_execution_unit_ids": (
            True
        ),
        "mismatch_count": len(
            mismatches
        ),
        "mismatches": (
            mismatches
        ),
        (
            "distributed_logical_sha256"
        ): distributed_hash,
        "stage15_logical_sha256": (
            stage15_hash
        ),
        "logical_hash_match": (
            distributed_hash
            == stage15_hash
        ),
    }


def distributed_status(
    *,
    distributed_root: str | Path,
    run_id: str,
) -> dict[str, Any]:
    run_manifest = _read_json(
        Path(
            distributed_root
        )
        / run_id
        / (
            "distributed_run_manifest.json"
        )
    )

    batches_total = int(
        run_manifest[
            "batches_total"
        ]
    )

    completed = 0
    failed_final = 0
    retries = 0
    attempts_total = 0

    workers = set()

    for batch_id in (
        run_manifest[
            "batch_ids"
        ]
    ):
        attempts = read_attempts(
            distributed_root=(
                distributed_root
            ),
            run_id=run_id,
            batch_id=batch_id,
        )

        attempts_total += len(
            attempts
        )

        retries += max(
            0,
            len(attempts) - 1,
        )

        workers.update(
            row["worker_id"]
            for row in attempts
            if row.get(
                "worker_id"
            )
        )

        if any(
            row["status"]
            == "COMPLETED"
            for row in attempts
        ):
            completed += 1

        elif attempts:
            failed_final += 1

    return {
        "run_id": run_id,
        "batches_total": (
            batches_total
        ),
        "workers_total": len(
            workers
        ),
        "workers": sorted(
            workers
        ),
        "execution_units_total": (
            int(
                run_manifest[
                    "execution_units_total"
                ]
            )
        ),
        "completed": completed,
        "failed_final": (
            failed_final
        ),
        "retries": retries,
        "attempts_total": (
            attempts_total
        ),
    }