from __future__ import annotations

import hashlib
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.analytics import (
    run_analytics,
)
from operar_range.batch_executor import (
    build_execution_plan,
)
from operar_range.constraint_engine import (
    evaluate_config,
    run_constraint_engine,
)
from operar_range.distributed_executor import (
    distributed_status,
    execute_worker,
    merge_distributed_results,
    read_attempts,
    serialize_all_batches,
)
from operar_range.experiment_generator import (
    generate_configurations,
    generate_experiment_database,
)
from operar_range.ingest import (
    import_tick_zip,
)
from operar_range.ranking_engine import (
    RankingRequest,
    run_ranking_engine,
)
from operar_range.research_lineage_adapter import (
    build_research_manifest,
    canonical_json,
)
from operar_range.scanner import (
    run_scanner,
)
from operar_range.trajectory_cache import (
    run_trajectory_cache,
)


WORKSPACE_VERSION = (
    "research-workspace-v1"
)

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

DATA_ROOT = (
    PROJECT_ROOT
    / "data"
)

INBOX_ROOT = (
    DATA_ROOT
    / "inbox"
)

NORMALIZED_ROOT = (
    DATA_ROOT
    / "normalized"
)

RESEARCH_ROOT = (
    DATA_ROOT
    / "research"
)

REPORTS_ROOT = (
    DATA_ROOT
    / "reports"
)

WORKSPACE_ROOT = (
    RESEARCH_ROOT
    / "workspace"
)

REGISTRY_PATH = (
    RESEARCH_ROOT
    / "experiment_registry.parquet"
)

TRAJECTORY_MANIFEST_PATH = (
    RESEARCH_ROOT
    / "trade1_trajectory_manifest.parquet"
)

TRADE1_DATABASE_PATH = (
    RESEARCH_ROOT
    / "trade1_database.parquet"
)


DEFAULT_COMPOSITE_WEIGHTS = {
    "EXPECTANCY": 35.0,
    "PROFIT_FACTOR": 25.0,
    "MAX_DRAWDOWN": 20.0,
    "NUMBER_OF_TRADES": 10.0,
    "WIN_RATE": 10.0,
}


WORKERS = [
    "WORKER-001",
    "WORKER-002",
    "WORKER-003",
]


ProgressCallback = Callable[
    [
        str,
        float,
        dict[str, Any],
    ],
    None,
]


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


def sha256_file(
    path: str | Path,
) -> str:
    path = Path(
        path
    )

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


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode(
            "utf-8"
        )
    ).hexdigest()


def read_json(
    path: str | Path,
) -> dict[str, Any]:
    path = Path(
        path
    )

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def write_json(
    *,
    path: str | Path,
    value: dict[str, Any],
    overwrite: bool = False,
) -> Path:
    path = Path(
        path
    )

    if (
        path.exists()
        and not overwrite
    ):
        raise FileExistsError(
            path
        )

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


def read_parquet_rows(
    path: str | Path,
) -> list[dict[str, Any]]:
    path = Path(
        path
    )

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    return (
        pq.read_table(
            path
        )
        .to_pylist()
    )


def _write_rows_like(
    *,
    source_path: str | Path,
    rows: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    source_path = Path(
        source_path
    )

    output_path = Path(
        output_path
    )

    if not source_path.exists():
        raise FileNotFoundError(
            source_path
        )

    source_schema = (
        pq.read_table(
            source_path
        ).schema
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        rows,
        schema=source_schema,
    )

    pq.write_table(
        table,
        output_path,
        compression="zstd",
    )

    return output_path


def _progress(
    callback: (
        ProgressCallback
        | None
    ),
    stage: str,
    fraction: float,
    **details: Any,
) -> None:
    if callback is None:
        return

    callback(
        stage,
        max(
            0.0,
            min(
                1.0,
                float(
                    fraction
                ),
            ),
        ),
        details,
    )


def research_dir(
    research_id: str,
) -> Path:
    if not research_id:
        raise ValueError(
            "research_id is required."
        )

    if (
        "/" in research_id
        or "\\" in research_id
        or ".." in research_id
    ):
        raise ValueError(
            "Invalid research_id."
        )

    return (
        WORKSPACE_ROOT
        / research_id
    )


def research_paths(
    research_id: str,
) -> dict[str, Path]:
    root = research_dir(
        research_id
    )

    distributed_root = (
        root
        / "distributed_runs"
    )

    return {
        "root": root,
        "definition": (
            root
            / "research_definition.json"
        ),
        "run_manifest": (
            root
            / "research_run_manifest.json"
        ),
        "generated": (
            root
            / "generated_experiments.parquet"
        ),
        "valid": (
            root
            / "valid_experiments.parquet"
        ),
        "rejected": (
            root
            / "rejected_experiments.parquet"
        ),
        "constraint_rules": (
            root
            / "constraint_rules.parquet"
        ),
        "constraint_summary": (
            root
            / "constraint_engine_summary.json"
        ),
        "trajectory_manifest": (
            root
            / "trajectory_manifest.parquet"
        ),
        "batch_plan": (
            root
            / "batch_execution_plan.parquet"
        ),
        "distributed_root": (
            distributed_root
        ),
        "distributed_results": (
            root
            / "distributed_experiment_results.parquet"
        ),
        "experiment_manifest": (
            root
            / "experiment_manifest.parquet"
        ),
        "metrics": (
            root
            / "experiment_metrics.parquet"
        ),
        "metrics_yearly": (
            root
            / "experiment_metrics_yearly.parquet"
        ),
        "metrics_monthly": (
            root
            / "experiment_metrics_monthly.parquet"
        ),
        "rankings": (
            root
            / "experiment_rankings.parquet"
        ),
        "ranking_manifest": (
            root
            / "ranking_manifest.parquet"
        ),
        "ranking_summary": (
            root
            / "ranking_summary.json"
        ),
    }


def _definition_identity(
    definition: dict[str, Any],
) -> dict[str, Any]:
    excluded = {
        "research_id",
        "created_at",
        "status",
    }

    return {
        key: value
        for key, value
        in definition.items()
        if key not in excluded
    }


def research_definition_sha256(
    definition: dict[str, Any],
) -> str:
    return sha256_text(
        canonical_json(
            _definition_identity(
                definition
            )
        )
    )


def new_research_id(
    definition: dict[str, Any],
) -> str:
    definition_hash = (
        research_definition_sha256(
            definition
        )
    )

    timestamp = (
        datetime.now(
            timezone.utc
        )
        .strftime(
            "%Y%m%dT%H%M%SZ"
        )
    )

    base = (
        "RES-"
        + timestamp
        + "-"
        + definition_hash[:12]
    )

    candidate = base
    counter = 1

    while research_dir(
        candidate
    ).exists():
        counter += 1

        candidate = (
            base
            + "-"
            + f"{counter:02d}"
        )

    return candidate


def create_research(
    definition: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(
        definition
    )

    payload.setdefault(
        "strategy",
        "TRADE_1",
    )

    if (
        payload[
            "strategy"
        ]
        != "TRADE_1"
    ):
        raise ValueError(
            "Stage 18 supports "
            "TRADE_1 only."
        )

    definition_hash = (
        research_definition_sha256(
            payload
        )
    )

    research_id = (
        new_research_id(
            payload
        )
    )

    created_at = utc_now()

    payload[
        "research_id"
    ] = research_id

    payload[
        "created_at"
    ] = created_at

    payload[
        "status"
    ] = "CREATED"

    payload[
        "research_definition_sha256"
    ] = definition_hash

    paths = research_paths(
        research_id
    )

    paths[
        "root"
    ].mkdir(
        parents=True,
        exist_ok=False,
    )

    write_json(
        path=(
            paths[
                "definition"
            ]
        ),
        value=payload,
        overwrite=False,
    )

    manifest = {
        "workspace_version": (
            WORKSPACE_VERSION
        ),
        "research_id": (
            research_id
        ),
        "status": "CREATED",
        "created_at": (
            created_at
        ),
        "started_at": None,
        "completed_at": None,
        "failed_at": None,
        "current_stage": (
            "CREATED"
        ),
        "error_type": None,
        "error_message": None,
        "research_definition_sha256": (
            definition_hash
        ),
        "experiment_manifest_sha256": None,
        "distributed_results_sha256": None,
        "source_valid_experiments_sha256": None,
        "trajectory_manifest_sha256": None,
        "rule_set_sha256": None,
        "motor_version": None,
        "rules_version": None,
        "experiments_generated": None,
        "experiments_valid": None,
        "experiments_invalid": None,
        "execution_units_total": None,
        "batches_total": None,
        "distributed_run_id": None,
        "duration_seconds": None,
        "lineage_match": None,
        "quantitative_execution_repeated": (
            False
        ),
    }

    write_json(
        path=(
            paths[
                "run_manifest"
            ]
        ),
        value=manifest,
        overwrite=False,
    )

    return {
        "research_id": (
            research_id
        ),
        "research_dir": str(
            paths[
                "root"
            ]
        ),
        "definition_path": str(
            paths[
                "definition"
            ]
        ),
        "run_manifest_path": str(
            paths[
                "run_manifest"
            ]
        ),
        "research_definition_sha256": (
            definition_hash
        ),
    }


def load_research_definition(
    research_id: str,
) -> dict[str, Any]:
    return read_json(
        research_paths(
            research_id
        )[
            "definition"
        ]
    )


def load_research_manifest(
    research_id: str,
) -> dict[str, Any]:
    return read_json(
        research_paths(
            research_id
        )[
            "run_manifest"
        ]
    )


def update_run_manifest(
    research_id: str,
    **updates: Any,
) -> dict[str, Any]:
    paths = research_paths(
        research_id
    )

    current = (
        load_research_manifest(
            research_id
        )
    )

    current.update(
        updates
    )

    write_json(
        path=(
            paths[
                "run_manifest"
            ]
        ),
        value=current,
        overwrite=True,
    )

    return current


def list_researches() -> list[
    dict[str, Any]
]:
    if not WORKSPACE_ROOT.exists():
        return []

    rows = []

    for path in sorted(
        WORKSPACE_ROOT.iterdir()
    ):
        if not path.is_dir():
            continue

        manifest_path = (
            path
            / "research_run_manifest.json"
        )

        definition_path = (
            path
            / "research_definition.json"
        )

        if not manifest_path.exists():
            continue

        try:
            manifest = read_json(
                manifest_path
            )

            definition = (
                read_json(
                    definition_path
                )
                if definition_path.exists()
                else {}
            )

        except Exception:
            continue

        rows.append(
            {
                **manifest,
                "period_start": (
                    definition.get(
                        "period_start"
                    )
                ),
                "period_end": (
                    definition.get(
                        "period_end"
                    )
                ),
                "strategy": (
                    definition.get(
                        "strategy"
                    )
                ),
                "family": (
                    definition.get(
                        "family"
                    )
                ),
                "generation": (
                    definition.get(
                        "generation"
                    )
                ),
                "research_dir": str(
                    path
                ),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            row.get(
                "created_at"
            )
            or ""
        ),
        reverse=True,
    )


def _inbox_status(
    path: Path,
) -> tuple[
    str,
    str | None,
]:
    if (
        path.suffix.lower()
        != ".zip"
    ):
        return (
            "ERROR",
            "UNSUPPORTED_EXTENSION",
        )

    raw_copy = (
        DATA_ROOT
        / "raw"
        / "zip"
        / path.name
    )

    if not raw_copy.exists():
        return (
            "NEW",
            None,
        )

    try:
        source_hash = (
            sha256_file(
                path
            )
        )

        raw_hash = (
            sha256_file(
                raw_copy
            )
        )

    except Exception:
        return (
            "ERROR",
            "HASH_ERROR",
        )

    if (
        source_hash
        == raw_hash
    ):
        return (
            "PROCESSED",
            None,
        )

    return (
        "ERROR",
        "DUPLICATE_NAME_DIFFERENT_CONTENT",
    )


def list_inbox_files() -> list[
    dict[str, Any]
]:
    INBOX_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = []

    for path in sorted(
        INBOX_ROOT.iterdir()
    ):
        if not path.is_file():
            continue

        status, error = (
            _inbox_status(
                path
            )
        )

        stat = path.stat()

        rows.append(
            {
                "name": path.name,
                "path": str(
                    path
                ),
                "extension": (
                    path.suffix.lower()
                ),
                "size_bytes": int(
                    stat.st_size
                ),
                "modified_at": (
                    datetime.fromtimestamp(
                        stat.st_mtime,
                        tz=timezone.utc,
                    )
                    .replace(
                        microsecond=0
                    )
                    .isoformat()
                ),
                "sha256": (
                    sha256_file(
                        path
                    )
                    if status
                    != "ERROR"
                    else None
                ),
                "status": status,
                "error": error,
            }
        )

    return rows


def validate_inbox_selection(
    filenames: list[str],
) -> dict[str, Any]:
    if not filenames:
        return {
            "valid": False,
            "files": [],
            "errors": [
                "No dataset selected."
            ],
        }

    inventory = {
        row[
            "name"
        ]: row
        for row in list_inbox_files()
    }

    selected = []
    errors = []

    for filename in filenames:
        row = inventory.get(
            filename
        )

        if row is None:
            errors.append(
                (
                    "File not found in "
                    f"inbox: {filename}"
                )
            )
            continue

        selected.append(
            row
        )

        if (
            row[
                "status"
            ]
            == "ERROR"
        ):
            errors.append(
                (
                    f"{filename}: "
                    f"{row['error']}"
                )
            )

        if (
            row[
                "extension"
            ]
            != ".zip"
        ):
            errors.append(
                (
                    f"{filename}: "
                    "unsupported format."
                )
            )

        if (
            row[
                "size_bytes"
            ]
            <= 0
        ):
            errors.append(
                (
                    f"{filename}: "
                    "empty file."
                )
            )

    hashes = [
        row.get(
            "sha256"
        )
        for row in selected
        if row.get(
            "sha256"
        )
    ]

    if (
        len(
            hashes
        )
        != len(
            set(
                hashes
            )
        )
    ):
        errors.append(
            (
                "Duplicate dataset "
                "content selected."
            )
        )

    return {
        "valid": (
            len(
                errors
            )
            == 0
        ),
        "files": selected,
        "errors": errors,
    }


def process_datasets(
    filenames: list[str],
    *,
    progress_callback: (
        ProgressCallback
        | None
    ) = None,
) -> dict[str, Any]:
    validation = (
        validate_inbox_selection(
            filenames
        )
    )

    if not validation[
        "valid"
    ]:
        raise RuntimeError(
            "Dataset validation failed: "
            + canonical_json(
                validation[
                    "errors"
                ]
            )
        )

    _progress(
        progress_callback,
        "VALIDATION",
        0.05,
        status="COMPLETED",
    )

    imported = []

    files = validation[
        "files"
    ]

    for index, row in enumerate(
        files,
        start=1,
    ):
        imported.extend(
            import_tick_zip(
                row[
                    "path"
                ],
                data_root=(
                    DATA_ROOT
                ),
            )
        )

        _progress(
            progress_callback,
            "NORMALIZATION",
            (
                0.05
                + 0.35
                * (
                    index
                    / len(
                        files
                    )
                )
            ),
            file=row[
                "name"
            ],
            imported_reports=(
                len(
                    imported
                )
            ),
        )

    scanner = run_scanner(
        normalized_dir=(
            NORMALIZED_ROOT
        ),
        database_path=(
            TRADE1_DATABASE_PATH
        ),
        summary_path=(
            REPORTS_ROOT
            / "trade1_database_summary.json"
        ),
    )

    _progress(
        progress_callback,
        "SCANNER",
        0.55,
        status="COMPLETED",
    )

    trajectories = (
        run_trajectory_cache(
            normalized_dir=(
                NORMALIZED_ROOT
            ),
            trajectory_dir=(
                DATA_ROOT
                / "trajectories"
            ),
            manifest_path=(
                TRAJECTORY_MANIFEST_PATH
            ),
        )
    )

    _progress(
        progress_callback,
        "TRAJECTORY_CACHE",
        0.8,
        status="COMPLETED",
    )

    #
    # Analytics de pesquisa depende de
    # uma execução de experimentos.
    #
    # Neste ponto o Data Manager apenas
    # deixa a camada de dados pronta.
    #
    _progress(
        progress_callback,
        "ANALYTICS",
        1.0,
        status=(
            "DEFERRED_UNTIL_RESEARCH"
        ),
    )

    return {
        "validation": validation,
        "imports": imported,
        "scanner": scanner,
        "trajectory_cache": (
            trajectories
        ),
        "trade1_database_path": str(
            TRADE1_DATABASE_PATH
        ),
        "trajectory_manifest_path": str(
            TRAJECTORY_MANIFEST_PATH
        ),
        "analytics_status": (
            "DEFERRED_UNTIL_RESEARCH"
        ),
    }


def available_dataset_period() -> dict[
    str,
    Any
]:
    if not TRADE1_DATABASE_PATH.exists():
        return {
            "available": False,
            "period_start": None,
            "period_end": None,
            "sessions_total": 0,
        }

    rows = read_parquet_rows(
        TRADE1_DATABASE_PATH
    )

    dates = sorted(
        {
            str(
                row[
                    "date"
                ]
            )
            for row in rows
            if row.get(
                "date"
            )
        }
    )

    if not dates:
        return {
            "available": False,
            "period_start": None,
            "period_end": None,
            "sessions_total": 0,
        }

    return {
        "available": True,
        "period_start": (
            dates[0]
        ),
        "period_end": (
            dates[-1]
        ),
        "sessions_total": (
            len(
                dates
            )
        ),
    }


def _sessions_for_period(
    *,
    period_start: str,
    period_end: str,
) -> list[dict[str, Any]]:
    if (
        period_start
        > period_end
    ):
        raise ValueError(
            "period_start cannot "
            "be after period_end."
        )

    rows = read_parquet_rows(
        TRAJECTORY_MANIFEST_PATH
    )

    filtered = [
        row
        for row in rows
        if (
            period_start
            <= str(
                row[
                    "date"
                ]
            )
            <= period_end
        )
    ]

    return sorted(
        filtered,
        key=lambda row: (
            str(
                row[
                    "date"
                ]
            )
        ),
    )


def validate_research_period(
    *,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    available = (
        available_dataset_period()
    )

    errors = []

    if not available[
        "available"
    ]:
        errors.append(
            "No processed dataset available."
        )

    else:
        if (
            period_start
            < available[
                "period_start"
            ]
        ):
            errors.append(
                "period_start is before "
                "available dataset."
            )

        if (
            period_end
            > available[
                "period_end"
            ]
        ):
            errors.append(
                "period_end is after "
                "available dataset."
            )

    if (
        period_start
        > period_end
    ):
        errors.append(
            "period_start is after "
            "period_end."
        )

    sessions = []

    if not errors:
        sessions = (
            _sessions_for_period(
                period_start=(
                    period_start
                ),
                period_end=(
                    period_end
                ),
            )
        )

        if not sessions:
            errors.append(
                "Selected period contains "
                "no sessions."
            )

    return {
        "valid": (
            not errors
        ),
        "errors": errors,
        "sessions_total": (
            len(
                sessions
            )
        ),
        "available_period_start": (
            available[
                "period_start"
            ]
        ),
        "available_period_end": (
            available[
                "period_end"
            ]
        ),
    }


def estimate_research(
    definition: dict[str, Any],
) -> dict[str, Any]:
    period_start = str(
        definition[
            "period_start"
        ]
    )

    period_end = str(
        definition[
            "period_end"
        ]
    )

    period_validation = (
        validate_research_period(
            period_start=(
                period_start
            ),
            period_end=(
                period_end
            ),
        )
    )

    if not period_validation[
        "valid"
    ]:
        raise RuntimeError(
            "Invalid research period: "
            + canonical_json(
                period_validation[
                    "errors"
                ]
            )
        )

    base_config = (
        definition[
            "base_config"
        ]
    )

    parameter_definition = (
        definition[
            "parameter_definition"
        ]
    )

    configurations = (
        generate_configurations(
            base_config=(
                base_config
            ),
            parameter_definition=(
                parameter_definition
            ),
        )
    )

    #
    # A estimativa não registra
    # experimentos e não executa trades.
    #
    # Ela reutiliza somente o avaliador
    # homologado do Constraint Engine
    # para informar, antes da execução,
    # quantas configurações são válidas
    # e inválidas.
    #
    generated_total = len(
        configurations
    )

    valid_total = 0
    invalid_total = 0

    for config in configurations:
        errors, _warnings = (
            evaluate_config(
                config
            )
        )

        if errors:
            invalid_total += 1
        else:
            valid_total += 1

    sessions_total = int(
        period_validation[
            "sessions_total"
        ]
    )

    batch_size = int(
        definition.get(
            "batch_size",
            1000,
        )
    )

    if batch_size <= 0:
        raise ValueError(
            "batch_size must be positive."
        )

    execution_units_estimated = (
        generated_total
        * sessions_total
    )

    batches_estimated = (
        (
            execution_units_estimated
            + batch_size
            - 1
        )
        // batch_size
        if execution_units_estimated
        else 0
    )

    return {
        "sessions_total": (
            sessions_total
        ),
        "generated_configurations": (
            generated_total
        ),
        "valid_configurations": (
            valid_total
        ),
        "invalid_configurations": (
            invalid_total
        ),
        "execution_units_estimated": (
            execution_units_estimated
        ),
        "batches_estimated": (
            batches_estimated
        ),
        "batch_size": (
            batch_size
        ),
        "period_start": (
            period_start
        ),
        "period_end": (
            period_end
        ),
        "constraint_status": (
            "PREVALIDATED_WITH_RULE_ENGINE"
        ),
    }


def _materialize_period_manifest(
    *,
    research_id: str,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    paths = research_paths(
        research_id
    )

    rows = _sessions_for_period(
        period_start=(
            period_start
        ),
        period_end=(
            period_end
        ),
    )

    if not rows:
        raise RuntimeError(
            "Research period contains "
            "no trajectory sessions."
        )

    _write_rows_like(
        source_path=(
            TRAJECTORY_MANIFEST_PATH
        ),
        rows=rows,
        output_path=(
            paths[
                "trajectory_manifest"
            ]
        ),
    )

    return {
        "rows": len(
            rows
        ),
        "path": str(
            paths[
                "trajectory_manifest"
            ]
        ),
        "sha256": (
            sha256_file(
                paths[
                    "trajectory_manifest"
                ]
            )
        ),
    }


def _execute_distributed(
    *,
    research_id: str,
    progress_callback: (
        ProgressCallback
        | None
    ),
) -> dict[str, Any]:
    paths = research_paths(
        research_id
    )

    serialization = (
        serialize_all_batches(
            project_root=(
                PROJECT_ROOT
            ),
            batch_plan_path=(
                paths[
                    "batch_plan"
                ]
            ),
            registry_path=(
                REGISTRY_PATH
            ),
            trajectory_manifest_path=(
                paths[
                    "trajectory_manifest"
                ]
            ),
            valid_experiments_path=(
                paths[
                    "valid"
                ]
            ),
            constraint_summary_path=(
                paths[
                    "constraint_summary"
                ]
            ),
            distributed_root=(
                paths[
                    "distributed_root"
                ]
            ),
        )
    )

    run_id = (
        serialization[
            "run_id"
        ]
    )

    packages = (
        serialization[
            "packages"
        ]
    )

    batch_ids = [
        package[
            "batch_id"
        ]
        for package in packages
    ]

    total_batches = len(
        batch_ids
    )

    if not batch_ids:
        raise RuntimeError(
            "Distributed execution "
            "contains no batches."
        )

    for index, batch_id in enumerate(
        batch_ids,
        start=1,
    ):
        attempts = read_attempts(
            distributed_root=(
                paths[
                    "distributed_root"
                ]
            ),
            run_id=run_id,
            batch_id=batch_id,
        )

        completed = any(
            row[
                "status"
            ]
            == "COMPLETED"
            for row in attempts
        )

        if completed:
            continue

        worker_id = WORKERS[
            (
                index
                - 1
            )
            % len(
                WORKERS
            )
        ]

        result = execute_worker(
            project_root=(
                PROJECT_ROOT
            ),
            distributed_root=(
                paths[
                    "distributed_root"
                ]
            ),
            run_id=run_id,
            batch_id=batch_id,
            worker_id=(
                worker_id
            ),
            batch_plan_path=(
                paths[
                    "batch_plan"
                ]
            ),
            registry_path=(
                REGISTRY_PATH
            ),
            trajectory_manifest_path=(
                paths[
                    "trajectory_manifest"
                ]
            ),
            valid_experiments_path=(
                paths[
                    "valid"
                ]
            ),
            constraint_summary_path=(
                paths[
                    "constraint_summary"
                ]
            ),
            normalized_dir=(
                "data/normalized"
            ),
        )

        if (
            result[
                "status"
            ]
            != "COMPLETED"
        ):
            raise RuntimeError(
                "Distributed worker "
                "failed: "
                + canonical_json(
                    result
                )
            )

        _progress(
            progress_callback,
            "DISTRIBUTED_EXECUTOR",
            (
                0.35
                + 0.35
                * (
                    index
                    / total_batches
                )
            ),
            completed_batches=(
                index
            ),
            total_batches=(
                total_batches
            ),
            remaining_batches=(
                total_batches
                - index
            ),
            worker_id=(
                worker_id
            ),
            batch_id=(
                batch_id
            ),
        )

    status = distributed_status(
        distributed_root=(
            paths[
                "distributed_root"
            ]
        ),
        run_id=run_id,
    )

    if (
        status[
            "completed"
        ]
        != status[
            "batches_total"
        ]
    ):
        raise RuntimeError(
            "Distributed execution "
            "did not complete all batches."
        )

    if (
        status[
            "failed_final"
        ]
        != 0
    ):
        raise RuntimeError(
            "Distributed execution "
            "finished with failed batches."
        )

    merged = (
        merge_distributed_results(
            distributed_root=(
                paths[
                    "distributed_root"
                ]
            ),
            run_id=run_id,
            output_path=(
                paths[
                    "distributed_results"
                ]
            ),
        )
    )

    return {
        "run_id": (
            run_id
        ),
        "serialization": (
            serialization
        ),
        "status": status,
        "merged": merged,
    }


def execute_research(
    research_id: str,
    *,
    progress_callback: (
        ProgressCallback
        | None
    ) = None,
) -> dict[str, Any]:
    paths = research_paths(
        research_id
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

    if (
        manifest[
            "status"
        ]
        == "COMPLETED"
    ):
        raise RuntimeError(
            "Completed research is immutable."
        )

    if (
        paths[
            "distributed_results"
        ].exists()
        or paths[
            "metrics"
        ].exists()
        or paths[
            "rankings"
        ].exists()
    ):
        raise RuntimeError(
            "Research artifacts already "
            "exist. A new Research ID "
            "is required."
        )

    started_perf = (
        time.perf_counter()
    )

    started_at = utc_now()

    update_run_manifest(
        research_id,
        status="RUNNING",
        started_at=(
            started_at
        ),
        current_stage=(
            "PREPARING"
        ),
        error_type=None,
        error_message=None,
    )

    try:
        _progress(
            progress_callback,
            "PREPARING",
            0.02,
            research_id=(
                research_id
            ),
        )

        period_start = str(
            definition[
                "period_start"
            ]
        )

        period_end = str(
            definition[
                "period_end"
            ]
        )

        period_validation = (
            validate_research_period(
                period_start=(
                    period_start
                ),
                period_end=(
                    period_end
                ),
            )
        )

        if not period_validation[
            "valid"
        ]:
            raise RuntimeError(
                "Invalid research period: "
                + canonical_json(
                    period_validation[
                        "errors"
                    ]
                )
            )

        local_trajectory = (
            _materialize_period_manifest(
                research_id=(
                    research_id
                ),
                period_start=(
                    period_start
                ),
                period_end=(
                    period_end
                ),
            )
        )

        update_run_manifest(
            research_id,
            current_stage=(
                "EXPERIMENT_GENERATOR"
            ),
            trajectory_manifest_sha256=(
                local_trajectory[
                    "sha256"
                ]
            ),
        )

        _progress(
            progress_callback,
            "EXPERIMENT_GENERATOR",
            0.08,
        )

        generator = (
            generate_experiment_database(
                output_path=(
                    paths[
                        "generated"
                    ]
                ),
                family=str(
                    definition[
                        "family"
                    ]
                ),
                generation=int(
                    definition[
                        "generation"
                    ]
                ),
                created_at=(
                    definition[
                        "created_at"
                    ]
                ),
                rules_version=str(
                    definition[
                        "rules_version"
                    ]
                ),
                base_config=(
                    definition[
                        "base_config"
                    ]
                ),
                parameter_definition=(
                    definition[
                        "parameter_definition"
                    ]
                ),
                existing_generated_path=None,
                registry_path=(
                    REGISTRY_PATH
                ),
                reserved_paths=[],
                register_generated=True,
            )
        )

        update_run_manifest(
            research_id,
            experiments_generated=(
                generator[
                    "experiment_count"
                ]
            ),
            current_stage=(
                "CONSTRAINT_ENGINE"
            ),
        )

        _progress(
            progress_callback,
            "CONSTRAINT_ENGINE",
            0.15,
        )

        constraints = (
            run_constraint_engine(
                generated_path=(
                    paths[
                        "generated"
                    ]
                ),
                registry_path=(
                    REGISTRY_PATH
                ),
                valid_path=(
                    paths[
                        "valid"
                    ]
                ),
                rejected_path=(
                    paths[
                        "rejected"
                    ]
                ),
                rules_path=(
                    paths[
                        "constraint_rules"
                    ]
                ),
                summary_path=(
                    paths[
                        "constraint_summary"
                    ]
                ),
            )
        )

        constraint_summary = (
            constraints[
                "summary"
            ]
        )

        valid_total = int(
            constraint_summary[
                "valid_total"
            ]
        )

        invalid_total = int(
            constraint_summary[
                "invalid_total"
            ]
        )

        if valid_total <= 0:
            raise RuntimeError(
                "Constraint Engine produced "
                "zero valid experiments."
            )

        update_run_manifest(
            research_id,
            experiments_valid=(
                valid_total
            ),
            experiments_invalid=(
                invalid_total
            ),
            rule_set_sha256=(
                constraint_summary[
                    "rule_set_sha256"
                ]
            ),
            source_valid_experiments_sha256=(
                constraint_summary[
                    "valid_experiments_sha256"
                ]
            ),
            current_stage=(
                "BATCH_PLANNER"
            ),
        )

        _progress(
            progress_callback,
            "BATCH_PLANNER",
            0.22,
        )

        planner = (
            build_execution_plan(
                valid_experiments_path=(
                    paths[
                        "valid"
                    ]
                ),
                registry_path=(
                    REGISTRY_PATH
                ),
                trajectory_manifest_path=(
                    paths[
                        "trajectory_manifest"
                    ]
                ),
                output_path=(
                    paths[
                        "batch_plan"
                    ]
                ),
                batch_size=int(
                    definition.get(
                        "batch_size",
                        1000,
                    )
                ),
            )
        )

        update_run_manifest(
            research_id,
            execution_units_total=(
                planner[
                    "execution_units_total"
                ]
            ),
            batches_total=(
                planner[
                    "batches_total"
                ]
            ),
            current_stage=(
                "DISTRIBUTED_EXECUTOR"
            ),
        )

        _progress(
            progress_callback,
            "DISTRIBUTED_EXECUTOR",
            0.30,
            total_batches=(
                planner[
                    "batches_total"
                ]
            ),
            execution_units_total=(
                planner[
                    "execution_units_total"
                ]
            ),
        )

        distributed = (
            _execute_distributed(
                research_id=(
                    research_id
                ),
                progress_callback=(
                    progress_callback
                ),
            )
        )

        update_run_manifest(
            research_id,
            distributed_run_id=(
                distributed[
                    "run_id"
                ]
            ),
            distributed_results_sha256=(
                distributed[
                    "merged"
                ][
                    "output_sha256"
                ]
            ),
            current_stage=(
                "LINEAGE_ADAPTER"
            ),
        )

        _progress(
            progress_callback,
            "LINEAGE_ADAPTER",
            0.74,
        )

        lineage = (
            build_research_manifest(
                distributed_results_path=(
                    paths[
                        "distributed_results"
                    ]
                ),
                valid_experiments_path=(
                    paths[
                        "valid"
                    ]
                ),
                registry_path=(
                    REGISTRY_PATH
                ),
                trajectory_manifest_path=(
                    paths[
                        "trajectory_manifest"
                    ]
                ),
                output_path=(
                    paths[
                        "experiment_manifest"
                    ]
                ),
            )
        )

        if not lineage[
            "lineage_match"
        ]:
            raise RuntimeError(
                "LINEAGE_MATCH = False"
            )

        manifest_rows = (
            read_parquet_rows(
                paths[
                    "experiment_manifest"
                ]
            )
        )

        motor_versions = {
            row[
                "motor_version"
            ]
            for row in manifest_rows
        }

        rules_versions = {
            row[
                "rules_version"
            ]
            for row in manifest_rows
        }

        if len(
            motor_versions
        ) != 1:
            raise RuntimeError(
                "Research manifest contains "
                "multiple motor versions."
            )

        if len(
            rules_versions
        ) != 1:
            raise RuntimeError(
                "Research manifest contains "
                "multiple rules versions."
            )

        motor_version = next(
            iter(
                motor_versions
            )
        )

        rules_version = next(
            iter(
                rules_versions
            )
        )

        update_run_manifest(
            research_id,
            experiment_manifest_sha256=(
                lineage[
                    "experiment_manifest_sha256"
                ]
            ),
            distributed_results_sha256=(
                lineage[
                    "distributed_results_sha256"
                ]
            ),
            source_valid_experiments_sha256=(
                lineage[
                    "source_valid_experiments_sha256"
                ]
            ),
            trajectory_manifest_sha256=(
                lineage[
                    "trajectory_manifest_sha256"
                ]
            ),
            motor_version=(
                motor_version
            ),
            rules_version=(
                rules_version
            ),
            lineage_match=True,
            quantitative_execution_repeated=(
                False
            ),
            current_stage=(
                "ANALYTICS"
            ),
        )

        _progress(
            progress_callback,
            "ANALYTICS",
            0.82,
        )

        analytics = run_analytics(
            results_path=(
                paths[
                    "distributed_results"
                ]
            ),
            manifest_path=(
                paths[
                    "experiment_manifest"
                ]
            ),
            metrics_path=(
                paths[
                    "metrics"
                ]
            ),
            yearly_path=(
                paths[
                    "metrics_yearly"
                ]
            ),
            monthly_path=(
                paths[
                    "metrics_monthly"
                ]
            ),
        )

        update_run_manifest(
            research_id,
            current_stage=(
                "RANKING"
            ),
        )

        _progress(
            progress_callback,
            "RANKING",
            0.92,
        )

        ranking = (
            run_ranking_engine(
                request=(
                    RankingRequest(
                        scope="OVERALL"
                    )
                ),
                composite_weights=(
                    definition.get(
                        "composite_weights",
                        DEFAULT_COMPOSITE_WEIGHTS,
                    )
                ),
                overall_metrics_path=(
                    paths[
                        "metrics"
                    ]
                ),
                yearly_metrics_path=(
                    paths[
                        "metrics_yearly"
                    ]
                ),
                monthly_metrics_path=(
                    paths[
                        "metrics_monthly"
                    ]
                ),
                registry_path=(
                    REGISTRY_PATH
                ),
                rankings_path=(
                    paths[
                        "rankings"
                    ]
                ),
                manifest_path=(
                    paths[
                        "ranking_manifest"
                    ]
                ),
                summary_path=(
                    paths[
                        "ranking_summary"
                    ]
                ),
            )
        )

        elapsed = (
            time.perf_counter()
            - started_perf
        )

        completed_at = (
            utc_now()
        )

        final_manifest = (
            update_run_manifest(
                research_id,
                status="COMPLETED",
                current_stage=(
                    "COMPLETED"
                ),
                completed_at=(
                    completed_at
                ),
                duration_seconds=(
                    elapsed
                ),
                experiment_manifest_sha256=(
                    sha256_file(
                        paths[
                            "experiment_manifest"
                        ]
                    )
                ),
                distributed_results_sha256=(
                    sha256_file(
                        paths[
                            "distributed_results"
                        ]
                    )
                ),
                quantitative_execution_repeated=(
                    False
                ),
            )
        )

        _progress(
            progress_callback,
            "COMPLETED",
            1.0,
            research_id=(
                research_id
            ),
            duration_seconds=(
                elapsed
            ),
        )

        return {
            "research_id": (
                research_id
            ),
            "research_dir": str(
                paths[
                    "root"
                ]
            ),
            "generator": (
                generator
            ),
            "constraints": (
                constraints
            ),
            "planner": (
                planner
            ),
            "distributed": (
                distributed
            ),
            "lineage": (
                lineage
            ),
            "analytics": (
                analytics
            ),
            "ranking": (
                ranking
            ),
            "run_manifest": (
                final_manifest
            ),
            "lineage_match": True,
            "quantitative_execution_repeated": (
                False
            ),
        }

    except Exception as exc:
        elapsed = (
            time.perf_counter()
            - started_perf
        )

        update_run_manifest(
            research_id,
            status="FAILED",
            current_stage="FAILED",
            failed_at=(
                utc_now()
            ),
            duration_seconds=(
                elapsed
            ),
            error_type=(
                type(
                    exc
                ).__name__
            ),
            error_message=str(
                exc
            ),
        )

        _progress(
            progress_callback,
            "FAILED",
            1.0,
            error_type=(
                type(
                    exc
                ).__name__
            ),
            error_message=str(
                exc
            ),
        )

        raise


def research_result_paths(
    research_id: str,
) -> dict[str, str]:
    paths = research_paths(
        research_id
    )

    return {
        key: str(
            value
        )
        for key, value
        in paths.items()
        if key
        in {
            "root",
            "definition",
            "run_manifest",
            "experiment_manifest",
            "distributed_results",
            "metrics",
            "metrics_yearly",
            "metrics_monthly",
            "rankings",
            "ranking_manifest",
            "ranking_summary",
        }
    }


def delete_incomplete_research_for_test(
    research_id: str,
) -> None:
    """
    Utilitário restrito a testes.

    Pesquisas concluídas nunca devem ser
    apagadas silenciosamente pela aplicação.
    """
    paths = research_paths(
        research_id
    )

    if not paths[
        "root"
    ].exists():
        return

    manifest_path = (
        paths[
            "run_manifest"
        ]
    )

    if manifest_path.exists():
        manifest = read_json(
            manifest_path
        )

        if (
            manifest.get(
                "status"
            )
            == "COMPLETED"
        ):
            raise RuntimeError(
                "Cannot delete completed research."
            )

    shutil.rmtree(
        paths[
            "root"
        ]
    )