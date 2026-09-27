from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


LINEAGE_ADAPTER_VERSION = (
    "research-lineage-adapter-v1"
)


CONFIG_FIELDS = (
    "stop_points",
    "partial_1_points",
    "partial_1_pct",
    "partial_2_points",
    "partial_2_pct",
    "partial_3_points",
    "partial_3_pct",
    "break_even_enabled",
    "break_even_after_partial",
    "runner_enabled",
    "runner_pct",
    "runner_rule",
    "final_target_points",
)


EXPERIMENT_MANIFEST_SCHEMA = pa.schema(
    [
        ("experiment_id", pa.string()),
        ("name", pa.string()),
        ("config_json", pa.string()),
        ("created_at", pa.string()),
        ("motor_version", pa.string()),
        ("rules_version", pa.string()),
        (
            "sessions_executed",
            pa.int64(),
        ),
        ("config_sha256", pa.string()),
    ]
)


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
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


def read_parquet_rows(
    path: str | Path,
) -> list[dict[str, Any]]:
    path = Path(path)

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


def read_json(
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


def _required_value(
    row: dict[str, Any],
    field: str,
    *,
    context: str,
) -> Any:
    if field not in row:
        raise RuntimeError(
            f"Missing required field "
            f"{field!r} in {context}."
        )

    value = row.get(
        field
    )

    if value is None:
        raise RuntimeError(
            f"Required field "
            f"{field!r} is null in "
            f"{context}."
        )

    if (
        isinstance(
            value,
            str,
        )
        and not value.strip()
    ):
        raise RuntimeError(
            f"Required field "
            f"{field!r} is empty in "
            f"{context}."
        )

    return value


def _unique_by_experiment_id(
    rows: list[dict[str, Any]],
    *,
    source_name: str,
) -> dict[
    str,
    dict[str, Any],
]:
    result: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in rows:
        experiment_id = str(
            _required_value(
                row,
                "experiment_id",
                context=source_name,
            )
        )

        if experiment_id in result:
            raise RuntimeError(
                "Duplicate experiment_id "
                f"in {source_name}: "
                f"{experiment_id}"
            )

        result[
            experiment_id
        ] = row

    return result


def _registry_by_id(
    rows: list[dict[str, Any]],
) -> dict[
    str,
    dict[str, Any],
]:
    return _unique_by_experiment_id(
        rows,
        source_name=(
            "experiment_registry"
        ),
    )


def _valid_by_id(
    rows: list[dict[str, Any]],
) -> dict[
    str,
    dict[str, Any],
]:
    return _unique_by_experiment_id(
        rows,
        source_name=(
            "valid_experiments"
        ),
    )


def _results_by_experiment(
    rows: list[dict[str, Any]],
) -> dict[
    str,
    list[dict[str, Any]],
]:
    result: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    seen_execution_units = set()

    for row in rows:
        experiment_id = str(
            _required_value(
                row,
                "experiment_id",
                context=(
                    "distributed_results"
                ),
            )
        )

        execution_unit_id = (
            row.get(
                "execution_unit_id"
            )
        )

        if execution_unit_id:
            if (
                execution_unit_id
                in seen_execution_units
            ):
                raise RuntimeError(
                    "Duplicate "
                    "execution_unit_id in "
                    "distributed results: "
                    f"{execution_unit_id}"
                )

            seen_execution_units.add(
                execution_unit_id
            )

        result.setdefault(
            experiment_id,
            [],
        ).append(
            row
        )

    return result


def _config_payload(
    row: dict[str, Any],
) -> dict[str, Any]:
    payload = {}

    for field in CONFIG_FIELDS:
        if field not in row:
            raise RuntimeError(
                "Valid experiment is "
                "missing configuration "
                f"field: {field}"
            )

        payload[
            field
        ] = row.get(
            field
        )

    return payload


def _single_value(
    rows: list[dict[str, Any]],
    field: str,
    *,
    experiment_id: str,
) -> Any:
    values = {
        row.get(
            field
        )
        for row in rows
        if row.get(
            field
        )
        is not None
    }

    if not values:
        raise RuntimeError(
            f"No {field} found in "
            "distributed results for "
            f"{experiment_id}."
        )

    if len(values) != 1:
        raise RuntimeError(
            f"Inconsistent {field} in "
            "distributed results for "
            f"{experiment_id}: "
            f"{sorted(values)}"
        )

    return next(
        iter(values)
    )


def _sessions_executed(
    rows: list[dict[str, Any]],
    *,
    experiment_id: str,
) -> int:
    dates = []

    for row in rows:
        date_value = (
            row.get(
                "date"
            )
        )

        if not date_value:
            raise RuntimeError(
                "Distributed result is "
                "missing date for "
                f"{experiment_id}."
            )

        dates.append(
            str(
                date_value
            )
        )

    unique_dates = set(
        dates
    )

    if (
        len(unique_dates)
        != len(dates)
    ):
        raise RuntimeError(
            "Duplicate session result "
            "for experiment "
            f"{experiment_id}."
        )

    return len(
        unique_dates
    )


def _validate_trajectory_sessions(
    *,
    results_by_experiment: dict[
        str,
        list[dict[str, Any]],
    ],
    trajectory_rows: list[
        dict[str, Any]
    ],
) -> None:
    trajectory_dates = {
        str(
            _required_value(
                row,
                "date",
                context=(
                    "trajectory_manifest"
                ),
            )
        )
        for row in trajectory_rows
    }

    if not trajectory_dates:
        raise RuntimeError(
            "Trajectory manifest "
            "contains no sessions."
        )

    for (
        experiment_id,
        rows,
    ) in results_by_experiment.items():
        result_dates = {
            str(
                row[
                    "date"
                ]
            )
            for row in rows
        }

        unknown_dates = (
            result_dates
            - trajectory_dates
        )

        if unknown_dates:
            raise RuntimeError(
                "Distributed results "
                "contain sessions absent "
                "from trajectory manifest "
                f"for {experiment_id}: "
                f"{sorted(unknown_dates)}"
            )


def build_manifest_rows(
    *,
    distributed_results_rows: list[
        dict[str, Any]
    ],
    valid_experiment_rows: list[
        dict[str, Any]
    ],
    registry_rows: list[
        dict[str, Any]
    ],
    trajectory_rows: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:
    if not distributed_results_rows:
        raise RuntimeError(
            "Distributed results are empty."
        )

    if not valid_experiment_rows:
        raise RuntimeError(
            "Valid experiments are empty."
        )

    if not registry_rows:
        raise RuntimeError(
            "Experiment Registry is empty."
        )

    results_by_experiment = (
        _results_by_experiment(
            distributed_results_rows
        )
    )

    valid_by_id = _valid_by_id(
        valid_experiment_rows
    )

    registry_by_id = (
        _registry_by_id(
            registry_rows
        )
    )

    result_ids = set(
        results_by_experiment
    )

    valid_ids = set(
        valid_by_id
    )

    missing_valid = (
        result_ids
        - valid_ids
    )

    if missing_valid:
        raise RuntimeError(
            "Distributed result "
            "experiment missing from "
            "valid_experiments: "
            f"{sorted(missing_valid)}"
        )

    extra_valid = (
        valid_ids
        - result_ids
    )

    if extra_valid:
        raise RuntimeError(
            "valid_experiments contains "
            "experiment absent from "
            "distributed results: "
            f"{sorted(extra_valid)}"
        )

    missing_registry = (
        result_ids
        - set(
            registry_by_id
        )
    )

    if missing_registry:
        raise RuntimeError(
            "Distributed result "
            "experiment missing from "
            "Registry: "
            f"{sorted(missing_registry)}"
        )

    _validate_trajectory_sessions(
        results_by_experiment=(
            results_by_experiment
        ),
        trajectory_rows=(
            trajectory_rows
        ),
    )

    manifest_rows = []

    for experiment_id in sorted(
        result_ids
    ):
        experiment = (
            valid_by_id[
                experiment_id
            ]
        )

        registry = (
            registry_by_id[
                experiment_id
            ]
        )

        result_rows = (
            results_by_experiment[
                experiment_id
            ]
        )

        valid_config_hash = str(
            _required_value(
                experiment,
                "config_sha256",
                context=(
                    "valid_experiments "
                    f"{experiment_id}"
                ),
            )
        )

        registry_config_hash = str(
            _required_value(
                registry,
                "config_sha256",
                context=(
                    "experiment_registry "
                    f"{experiment_id}"
                ),
            )
        )

        if (
            valid_config_hash
            != registry_config_hash
        ):
            raise RuntimeError(
                "Config hash mismatch "
                "between valid_experiments "
                "and Registry for "
                f"{experiment_id}."
            )

        result_config_hash = str(
            _single_value(
                result_rows,
                "config_sha256",
                experiment_id=(
                    experiment_id
                ),
            )
        )

        if (
            result_config_hash
            != valid_config_hash
        ):
            raise RuntimeError(
                "Config hash mismatch "
                "between distributed "
                "results and "
                "valid_experiments for "
                f"{experiment_id}."
            )

        motor_version = str(
            _single_value(
                result_rows,
                "motor_version",
                experiment_id=(
                    experiment_id
                ),
            )
        )

        rules_version = str(
            _single_value(
                result_rows,
                "rules_version",
                experiment_id=(
                    experiment_id
                ),
            )
        )

        valid_motor_version = (
            experiment.get(
                "motor_version"
            )
            or experiment.get(
                "engine_version"
            )
        )

        if (
            experiment.get(
                "motor_version"
            )
            is not None
            and str(
                experiment[
                    "motor_version"
                ]
            )
            != motor_version
        ):
            raise RuntimeError(
                "Motor version mismatch "
                "between distributed "
                "results and experiment "
                f"metadata for "
                f"{experiment_id}."
            )

        valid_rules_version = (
            experiment.get(
                "rules_version"
            )
        )

        if (
            valid_rules_version
            is not None
            and str(
                valid_rules_version
            )
            != rules_version
        ):
            raise RuntimeError(
                "Rules version mismatch "
                "between distributed "
                "results and experiment "
                f"metadata for "
                f"{experiment_id}."
            )

        registry_rules_version = (
            registry.get(
                "rules_version"
            )
        )

        if (
            registry_rules_version
            is not None
            and str(
                registry_rules_version
            )
            != rules_version
        ):
            raise RuntimeError(
                "Rules version mismatch "
                "between distributed "
                "results and Registry "
                f"for {experiment_id}."
            )

        name = (
            experiment.get(
                "experiment_name"
            )
            or registry.get(
                "experiment_name"
            )
        )

        if not name:
            raise RuntimeError(
                "Experiment name is "
                "missing for "
                f"{experiment_id}."
            )

        created_at = (
            experiment.get(
                "created_at"
            )
            or registry.get(
                "created_at"
            )
        )

        if not created_at:
            raise RuntimeError(
                "created_at is missing "
                "for "
                f"{experiment_id}."
            )

        config_payload = (
            _config_payload(
                experiment
            )
        )

        sessions_executed = (
            _sessions_executed(
                result_rows,
                experiment_id=(
                    experiment_id
                ),
            )
        )

        manifest_rows.append(
            {
                "experiment_id": (
                    experiment_id
                ),
                "name": str(
                    name
                ),
                "config_json": (
                    canonical_json(
                        config_payload
                    )
                ),
                "created_at": str(
                    created_at
                ),
                "motor_version": (
                    motor_version
                ),
                "rules_version": (
                    rules_version
                ),
                "sessions_executed": (
                    sessions_executed
                ),
                "config_sha256": (
                    valid_config_hash
                ),
            }
        )

    return manifest_rows


def write_experiment_manifest(
    *,
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
            row[
                "experiment_id"
            ]
        ),
    )

    table = pa.Table.from_pylist(
        ordered,
        schema=(
            EXPERIMENT_MANIFEST_SCHEMA
        ),
    )

    pq.write_table(
        table,
        output_path,
        compression="zstd",
    )

    return output_path


def validate_manifest_correspondence(
    *,
    distributed_results_rows: list[
        dict[str, Any]
    ],
    manifest_rows: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    results_by_experiment = (
        _results_by_experiment(
            distributed_results_rows
        )
    )

    manifest_by_id = (
        _unique_by_experiment_id(
            manifest_rows,
            source_name=(
                "research_local_manifest"
            ),
        )
    )

    result_ids = set(
        results_by_experiment
    )

    manifest_ids = set(
        manifest_by_id
    )

    missing_manifest = (
        result_ids
        - manifest_ids
    )

    extra_manifest = (
        manifest_ids
        - result_ids
    )

    mismatches = []

    for experiment_id in sorted(
        result_ids
        & manifest_ids
    ):
        result_rows = (
            results_by_experiment[
                experiment_id
            ]
        )

        manifest_row = (
            manifest_by_id[
                experiment_id
            ]
        )

        result_config_hash = str(
            _single_value(
                result_rows,
                "config_sha256",
                experiment_id=(
                    experiment_id
                ),
            )
        )

        if (
            result_config_hash
            != manifest_row.get(
                "config_sha256"
            )
        ):
            mismatches.append(
                {
                    "experiment_id": (
                        experiment_id
                    ),
                    "field": (
                        "config_sha256"
                    ),
                    "results": (
                        result_config_hash
                    ),
                    "manifest": (
                        manifest_row.get(
                            "config_sha256"
                        )
                    ),
                }
            )

        result_motor_version = str(
            _single_value(
                result_rows,
                "motor_version",
                experiment_id=(
                    experiment_id
                ),
            )
        )

        if (
            result_motor_version
            != manifest_row.get(
                "motor_version"
            )
        ):
            mismatches.append(
                {
                    "experiment_id": (
                        experiment_id
                    ),
                    "field": (
                        "motor_version"
                    ),
                    "results": (
                        result_motor_version
                    ),
                    "manifest": (
                        manifest_row.get(
                            "motor_version"
                        )
                    ),
                }
            )

        result_rules_version = str(
            _single_value(
                result_rows,
                "rules_version",
                experiment_id=(
                    experiment_id
                ),
            )
        )

        if (
            result_rules_version
            != manifest_row.get(
                "rules_version"
            )
        ):
            mismatches.append(
                {
                    "experiment_id": (
                        experiment_id
                    ),
                    "field": (
                        "rules_version"
                    ),
                    "results": (
                        result_rules_version
                    ),
                    "manifest": (
                        manifest_row.get(
                            "rules_version"
                        )
                    ),
                }
            )

        sessions_executed = (
            _sessions_executed(
                result_rows,
                experiment_id=(
                    experiment_id
                ),
            )
        )

        if (
            sessions_executed
            != manifest_row.get(
                "sessions_executed"
            )
        ):
            mismatches.append(
                {
                    "experiment_id": (
                        experiment_id
                    ),
                    "field": (
                        "sessions_executed"
                    ),
                    "results": (
                        sessions_executed
                    ),
                    "manifest": (
                        manifest_row.get(
                            "sessions_executed"
                        )
                    ),
                }
            )

    match = (
        not missing_manifest
        and not extra_manifest
        and not mismatches
    )

    return {
        "match": match,
        "results_experiment_count": (
            len(
                result_ids
            )
        ),
        "manifest_experiment_count": (
            len(
                manifest_ids
            )
        ),
        "missing_manifest": (
            sorted(
                missing_manifest
            )
        ),
        "extra_manifest": (
            sorted(
                extra_manifest
            )
        ),
        "mismatches": (
            mismatches
        ),
    }


def build_research_manifest(
    *,
    distributed_results_path: (
        str | Path
    ),
    valid_experiments_path: (
        str | Path
    ),
    registry_path: str | Path,
    trajectory_manifest_path: (
        str | Path
    ),
    output_path: str | Path,
) -> dict[str, Any]:
    distributed_results_path = (
        Path(
            distributed_results_path
        )
    )

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

    distributed_results_rows = (
        read_parquet_rows(
            distributed_results_path
        )
    )

    valid_experiment_rows = (
        read_parquet_rows(
            valid_experiments_path
        )
    )

    registry_rows = (
        read_parquet_rows(
            registry_path
        )
    )

    trajectory_rows = (
        read_parquet_rows(
            trajectory_manifest_path
        )
    )

    manifest_rows = (
        build_manifest_rows(
            distributed_results_rows=(
                distributed_results_rows
            ),
            valid_experiment_rows=(
                valid_experiment_rows
            ),
            registry_rows=(
                registry_rows
            ),
            trajectory_rows=(
                trajectory_rows
            ),
        )
    )

    write_experiment_manifest(
        rows=manifest_rows,
        output_path=output_path,
    )

    persisted_rows = (
        read_parquet_rows(
            output_path
        )
    )

    lineage = (
        validate_manifest_correspondence(
            distributed_results_rows=(
                distributed_results_rows
            ),
            manifest_rows=(
                persisted_rows
            ),
        )
    )

    if not lineage[
        "match"
    ]:
        raise RuntimeError(
            "Research lineage "
            "correspondence failed: "
            + canonical_json(
                lineage
            )
        )

    return {
        "adapter_version": (
            LINEAGE_ADAPTER_VERSION
        ),
        "manifest_path": str(
            output_path
        ),
        "experiment_manifest_sha256": (
            sha256_file(
                output_path
            )
        ),
        "distributed_results_sha256": (
            sha256_file(
                distributed_results_path
            )
        ),
        (
            "source_valid_experiments_sha256"
        ): (
            sha256_file(
                valid_experiments_path
            )
        ),
        "registry_sha256": (
            sha256_file(
                registry_path
            )
        ),
        "trajectory_manifest_sha256": (
            sha256_file(
                trajectory_manifest_path
            )
        ),
        "manifest_experiment_count": (
            lineage[
                "manifest_experiment_count"
            ]
        ),
        "results_experiment_count": (
            lineage[
                "results_experiment_count"
            ]
        ),
        "lineage_match": (
            lineage[
                "match"
            ]
        ),
        "lineage": lineage,
        (
            "quantitative_execution_repeated"
        ): False,
    }