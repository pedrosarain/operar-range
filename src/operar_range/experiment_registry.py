from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


REGISTRY_VERSION = "experiment-registry-v1"

VALID_STATUSES = {
    "ACTIVE",
    "FROZEN",
    "SUPERSEDED",
}


REGISTRY_SCHEMA = pa.schema(
    [
        ("experiment_id", pa.string()),
        ("config_sha256", pa.string()),
        (
            "config_identity_version",
            pa.string(),
        ),
        (
            "canonical_config_json",
            pa.string(),
        ),
        (
            "trade1_config_sha256",
            pa.string(),
        ),
        (
            "trade2_override_sha256",
            pa.string(),
        ),
        (
            "trade2_effective_config_sha256",
            pa.string(),
        ),
        ("family", pa.string()),
        ("generation", pa.int64()),
        ("experiment_name", pa.string()),
        ("status", pa.string()),
        ("created_at", pa.string()),
        ("engine_version", pa.string()),
        ("rules_version", pa.string()),
        ("parent_experiment_id", pa.string()),
        ("supersedes_experiment_id", pa.string()),
        ("definition_sha256", pa.string()),
        ("source_path", pa.string()),
        ("source_sha256", pa.string()),
        ("registry_version", pa.string()),
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


def experiment_number(
    experiment_id: str,
) -> int:
    match = re.fullmatch(
        r"EXP-(\d{6})",
        experiment_id,
    )

    if match is None:
        raise ValueError(
            f"Invalid experiment_id: "
            f"{experiment_id}"
        )

    return int(match.group(1))


def next_available_id(
    rows: list[dict[str, Any]],
) -> str:
    if not rows:
        return "EXP-000001"

    highest = max(
        experiment_number(
            row["experiment_id"]
        )
        for row in rows
    )

    return f"EXP-{highest + 1:06d}"


def _read_parquet_rows(
    path: str | Path,
) -> list[dict[str, Any]]:
    path = Path(path)

    if not path.exists():
        return []

    return pq.read_table(
        path
    ).to_pylist()


def read_registry(
    path: str | Path,
) -> list[dict[str, Any]]:
    return _read_parquet_rows(path)


def _value(
    row: dict[str, Any],
    *names: str,
    default: Any = None,
) -> Any:
    for name in names:
        if name in row:
            value = row.get(name)

            if value is not None:
                return value

    return default


def _registry_row_from_source(
    *,
    row: dict[str, Any],
    source_path: Path,
) -> dict[str, Any]:
    experiment_id = row.get(
        "experiment_id"
    )

    config_hash = row.get(
        "config_sha256"
    )

    if not experiment_id:
        raise ValueError(
            f"Missing experiment_id in "
            f"{source_path}"
        )

    if not config_hash:
        raise ValueError(
            f"Missing config_sha256 for "
            f"{experiment_id}"
        )

    family = _value(
        row,
        "family",
        default="TRADE1_BASE",
    )

    generation = int(
        _value(
            row,
            "generation",
            default=1,
        )
    )

    experiment_name = _value(
        row,
        "experiment_name",
        "name",
        "management_name",
        default=experiment_id,
    )

    created_at = _value(
        row,
        "created_at",
        default=None,
    )

    engine_version = _value(
        row,
        "engine_version",
        "motor_version",
        default=None,
    )

    rules_version = _value(
        row,
        "rules_version",
        default=None,
    )

    definition_hash = _value(
        row,
        "definition_sha256",
        default=None,
    )

    return {
        "experiment_id": experiment_id,
        "config_sha256": config_hash,
        "config_identity_version": (
            row.get(
                "config_identity_version"
            )
        ),
        "canonical_config_json": (
            row.get(
                "canonical_config_json"
            )
        ),
        "trade1_config_sha256": (
            row.get(
                "trade1_config_sha256"
            )
        ),
        "trade2_override_sha256": (
            row.get(
                "trade2_override_sha256"
            )
        ),
        (
            "trade2_effective_config_sha256"
        ): (
            row.get(
                "trade2_effective_config_sha256"
            )
        ),
        "family": family,
        "generation": generation,
        "experiment_name": (
            experiment_name
        ),
        "status": "ACTIVE",
        "created_at": created_at,
        "engine_version": (
            engine_version
        ),
        "rules_version": (
            rules_version
        ),
        "parent_experiment_id": None,
        "supersedes_experiment_id": None,
        "definition_sha256": (
            definition_hash
        ),
        "source_path": str(
            source_path
        ),
        "source_sha256": (
            sha256_file(source_path)
        ),
        "registry_version": (
            REGISTRY_VERSION
        ),
    }


IMMUTABLE_FIELDS = (
    "experiment_id",
    "config_sha256",
    "config_identity_version",
    "canonical_config_json",
    "trade1_config_sha256",
    "trade2_override_sha256",
    "trade2_effective_config_sha256",
    "family",
    "generation",
    "experiment_name",
    "created_at",
    "engine_version",
    "rules_version",
    "definition_sha256",
)


def _assert_same_identity(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> None:
    for field in IMMUTABLE_FIELDS:
        old = existing.get(field)
        new = incoming.get(field)

        if (
            old is not None
            and new is not None
            and old != new
        ):
            raise RuntimeError(
                "Historical experiment mutation "
                f"detected for "
                f"{existing['experiment_id']}: "
                f"{field}: {old!r} != {new!r}"
            )


IDENTITY_ENRICHMENT_FIELDS = (
    "config_identity_version",
    "canonical_config_json",
    "trade1_config_sha256",
    "trade2_override_sha256",
    "trade2_effective_config_sha256",
)


def _enrich_missing_identity_metadata(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> bool:
    changed = False

    for field in (
        IDENTITY_ENRICHMENT_FIELDS
    ):
        old = existing.get(
            field
        )

        new = incoming.get(
            field
        )

        if (
            old is None
            and new is not None
        ):
            existing[
                field
            ] = new

            changed = True

        elif (
            old is not None
            and new is not None
            and old != new
        ):
            raise RuntimeError(
                "Historical experiment "
                "identity metadata mutation "
                f"detected for "
                f"{existing['experiment_id']}: "
                f"{field}."
            )

    return changed


def _validate_unique_registry(
    rows: list[dict[str, Any]],
) -> None:
    ids: dict[
        str,
        dict[str, Any],
    ] = {}

    hashes: dict[
        str,
        str,
    ] = {}

    for row in rows:
        experiment_id = row[
            "experiment_id"
        ]

        config_hash = row[
            "config_sha256"
        ]

        status = row["status"]

        if status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status: {status}"
            )

        if experiment_id in ids:
            raise RuntimeError(
                "Duplicate experiment_id: "
                f"{experiment_id}"
            )

        ids[experiment_id] = row

        existing_id = hashes.get(
            config_hash
        )

        if (
            existing_id is not None
            and existing_id
            != experiment_id
        ):
            raise RuntimeError(
                "Same config_sha256 assigned "
                "to different experiment IDs: "
                f"{config_hash}: "
                f"{existing_id}, "
                f"{experiment_id}"
            )

        hashes[
            config_hash
        ] = experiment_id


def write_registry(
    rows: list[dict[str, Any]],
    path: str | Path,
) -> Path:
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _validate_unique_registry(
        rows
    )

    ordered = sorted(
        rows,
        key=lambda row: (
            experiment_number(
                row["experiment_id"]
            )
        ),
    )

    table = pa.Table.from_pylist(
        ordered,
        schema=REGISTRY_SCHEMA,
    )

    pq.write_table(
        table,
        path,
        compression="zstd",
    )

    return path


def migrate_registry(
    *,
    registry_path: str | Path,
    source_paths: list[
        str | Path
    ],
) -> dict[str, Any]:
    registry_path = Path(
        registry_path
    )

    existing = read_registry(
        registry_path
    )

    by_id = {
        row["experiment_id"]: row
        for row in existing
    }

    by_hash = {
        row["config_sha256"]: row
        for row in existing
    }

    new_experiments = 0

    for raw_path in source_paths:
        source_path = Path(
            raw_path
        )

        if not source_path.exists():
            continue

        for source_row in (
            _read_parquet_rows(
                source_path
            )
        ):
            incoming = (
                _registry_row_from_source(
                    row=source_row,
                    source_path=(
                        source_path
                    ),
                )
            )

            experiment_id = (
                incoming[
                    "experiment_id"
                ]
            )

            config_hash = (
                incoming[
                    "config_sha256"
                ]
            )

            existing_id_row = (
                by_id.get(
                    experiment_id
                )
            )

            if (
                existing_id_row
                is not None
            ):
                _assert_same_identity(
                    existing_id_row,
                    incoming,
                )

                _enrich_missing_identity_metadata(
                    existing_id_row,
                    incoming,
                )

                continue

            existing_hash_row = (
                by_hash.get(
                    config_hash
                )
            )

            if (
                existing_hash_row
                is not None
            ):
                if (
                    existing_hash_row[
                        "experiment_id"
                    ]
                    != experiment_id
                ):
                    raise RuntimeError(
                        "Configuration already "
                        "registered under another "
                        "experiment_id: "
                        f"{config_hash}"
                    )

                continue

            by_id[
                experiment_id
            ] = incoming

            by_hash[
                config_hash
            ] = incoming

            new_experiments += 1

    rows = list(
        by_id.values()
    )

    write_registry(
        rows,
        registry_path,
    )

    return {
        "rows": sorted(
            rows,
            key=lambda row: (
                experiment_number(
                    row[
                        "experiment_id"
                    ]
                )
            ),
        ),
        "new_experiments": (
            new_experiments
        ),
        "next_available_id": (
            next_available_id(
                rows
            )
        ),
        "registry_path": str(
            registry_path
        ),
        "registry_sha256": (
            sha256_file(
                registry_path
            )
        ),
    }


def freeze_experiment(
    *,
    registry_path: str | Path,
    experiment_id: str,
) -> None:
    rows = read_registry(
        registry_path
    )

    found = False

    for row in rows:
        if (
            row["experiment_id"]
            == experiment_id
        ):
            found = True

            if (
                row["status"]
                == "SUPERSEDED"
            ):
                raise RuntimeError(
                    "SUPERSEDED experiment "
                    "cannot be frozen."
                )

            row["status"] = "FROZEN"
            break

    if not found:
        raise KeyError(
            experiment_id
        )

    write_registry(
        rows,
        registry_path,
    )


def supersede_experiment(
    *,
    registry_path: str | Path,
    old_experiment_id: str,
    new_experiment_id: str,
) -> None:
    rows = read_registry(
        registry_path
    )

    by_id = {
        row["experiment_id"]: row
        for row in rows
    }

    if old_experiment_id not in by_id:
        raise KeyError(
            old_experiment_id
        )

    if new_experiment_id not in by_id:
        raise KeyError(
            new_experiment_id
        )

    if (
        old_experiment_id
        == new_experiment_id
    ):
        raise ValueError(
            "Experiment cannot "
            "supersede itself."
        )

    by_id[
        old_experiment_id
    ]["status"] = "SUPERSEDED"

    by_id[
        new_experiment_id
    ][
        "supersedes_experiment_id"
    ] = old_experiment_id

    write_registry(
        list(by_id.values()),
        registry_path,
    )


def set_parent(
    *,
    registry_path: str | Path,
    experiment_id: str,
    parent_experiment_id: str,
) -> None:
    rows = read_registry(
        registry_path
    )

    by_id = {
        row["experiment_id"]: row
        for row in rows
    }

    if experiment_id not in by_id:
        raise KeyError(
            experiment_id
        )

    if parent_experiment_id not in by_id:
        raise KeyError(
            parent_experiment_id
        )

    if (
        experiment_id
        == parent_experiment_id
    ):
        raise ValueError(
            "Experiment cannot "
            "be its own parent."
        )

    by_id[
        experiment_id
    ][
        "parent_experiment_id"
    ] = parent_experiment_id

    write_registry(
        list(by_id.values()),
        registry_path,
    )