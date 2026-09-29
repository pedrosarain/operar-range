from __future__ import annotations

import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any

from operar_range.dataset_store import (
    DATASET_STORE_VERSION,
    dataset_paths,
    ensure_dataset_directories,
)
from operar_range.ingest import (
    INGEST_VERSION,
    NORMALIZATION_VERSION,
    normalize_vendor_csv,
    sha256_file,
    utc_now,
)
from operar_range.scanner import (
    run_scanner,
)
from operar_range.trajectory_cache import (
    run_trajectory_cache,
)


DATASET_PIPELINE_VERSION = (
    "dataset-pipeline-v1"
)


class DatasetMaterializationError(
    RuntimeError
):
    pass


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


def _safe_name(
    value: str,
) -> str:
    normalized = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        str(
            value
        ),
    )

    normalized = normalized.strip(
        "._"
    )

    if not normalized:
        raise DatasetMaterializationError(
            "DATASET_MATERIALIZATION_ERROR: "
            "invalid source filename."
        )

    return normalized


def _write_json(
    *,
    path: Path,
    value: dict[str, Any],
) -> None:
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


def _read_json(
    path: Path,
) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def _quality_is_valid(
    report: dict[str, Any],
) -> bool:
    return bool(
        report.get(
            "is_sorted_by_timestamp_trade_number"
        )
    ) and (
        int(
            report.get(
                "duplicate_timestamp_trade_number"
            )
            or 0
        )
        == 0
    ) and bool(
        report.get(
            "original_columns_preserved"
        )
    )


def _source_inventory(
    selected_files: list[
        str | Path
    ],
) -> dict[
    str,
    Path
]:
    inventory: dict[
        str,
        Path
    ] = {}

    for value in selected_files:
        path = Path(
            value
        )

        if not path.exists():
            raise DatasetMaterializationError(
                "DATASET_MATERIALIZATION_ERROR: "
                "source file not found: "
                f"{path}"
            )

        if (
            path.suffix.lower()
            != ".zip"
        ):
            raise DatasetMaterializationError(
                "DATASET_MATERIALIZATION_ERROR: "
                "unsupported source format: "
                f"{path.name}"
            )

        if path.name in inventory:
            existing = inventory[
                path.name
            ]

            if (
                sha256_file(
                    existing
                )
                != sha256_file(
                    path
                )
            ):
                raise DatasetMaterializationError(
                    "DATASET_MATERIALIZATION_ERROR: "
                    "duplicate source filename "
                    "with different content: "
                    f"{path.name}"
                )

        inventory[
            path.name
        ] = path

    return inventory


def _validate_discovery_sources(
    *,
    discovery: dict[str, Any],
    inventory: dict[
        str,
        Path
    ],
) -> None:
    expected_sources = {
        str(
            row[
                "name"
            ]
        ): str(
            row[
                "source_sha256"
            ]
        )
        for row in discovery.get(
            "sources",
            []
        )
    }

    if (
        set(
            expected_sources
        )
        != set(
            inventory
        )
    ):
        raise DatasetMaterializationError(
            "DATASET_MATERIALIZATION_ERROR: "
            "selected source files do not "
            "match Dataset Discovery."
        )

    for name, expected_hash in (
        expected_sources.items()
    ):
        actual_hash = sha256_file(
            inventory[
                name
            ]
        )

        if (
            actual_hash
            != expected_hash
        ):
            raise DatasetMaterializationError(
                "DATASET_MATERIALIZATION_ERROR: "
                "source SHA256 mismatch for "
                f"{name}."
            )


def _existing_dataset_result(
    *,
    paths: dict[str, Path],
    discovery: dict[str, Any],
) -> dict[str, Any] | None:
    manifest_path = paths[
        "manifest"
    ]

    if not manifest_path.exists():
        return None

    existing = _read_json(
        manifest_path
    )

    if (
        str(
            existing.get(
                "dataset_id"
            )
        )
        != str(
            discovery.get(
                "dataset_id"
            )
        )
    ):
        raise DatasetMaterializationError(
            "DATASET_MATERIALIZATION_ERROR: "
            "existing Dataset manifest "
            "identity mismatch."
        )

    identity_fields = (
        "dataset_version",
        "market",
        "asset",
        "period_start",
        "period_end",
        "source_sha256",
    )

    for field in identity_fields:
        if (
            existing.get(
                field
            )
            != discovery.get(
                field
            )
        ):
            raise DatasetMaterializationError(
                "DATASET_MATERIALIZATION_ERROR: "
                "existing Dataset manifest "
                "does not match discovery "
                f"field {field}."
            )

    required_paths = (
        "source_zip",
        "source_csv",
        "normalized",
        "quality",
    )

    for key in required_paths:
        if not paths[
            key
        ].exists():
            raise DatasetMaterializationError(
                "DATASET_MATERIALIZATION_ERROR: "
                "existing Dataset is "
                "physically incomplete."
            )

    return {
        "dataset_id": (
            existing[
                "dataset_id"
            ]
        ),
        "status": (
            "ALREADY_MATERIALIZED"
        ),
        "manifest": existing,
        "manifest_path": str(
            manifest_path
        ),
        "paths": {
            key: str(
                value
            )
            for key, value
            in paths.items()
        },
    }


def materialize_dataset(
    *,
    discovery: dict[str, Any],
    selected_files: list[
        str | Path
    ],
    data_root: str | Path = "data",
) -> dict[str, Any]:
    dataset_id_value = str(
        discovery.get(
            "dataset_id"
        )
        or ""
    ).strip()

    if not dataset_id_value:
        raise DatasetMaterializationError(
            "DATASET_MATERIALIZATION_ERROR: "
            "dataset_id is required."
        )

    market = str(
        discovery.get(
            "market"
        )
        or ""
    ).strip()

    asset = str(
        discovery.get(
            "asset"
        )
        or ""
    ).strip()

    if not market:
        raise DatasetMaterializationError(
            "DATASET_MATERIALIZATION_ERROR: "
            "market is required."
        )

    if not asset:
        raise DatasetMaterializationError(
            "DATASET_MATERIALIZATION_ERROR: "
            "asset is required."
        )

    inventory = (
        _source_inventory(
            selected_files
        )
    )

    _validate_discovery_sources(
        discovery=discovery,
        inventory=inventory,
    )

    paths = dataset_paths(
        data_root=data_root,
        dataset_id_value=(
            dataset_id_value
        ),
    )

    existing = (
        _existing_dataset_result(
            paths=paths,
            discovery=discovery,
        )
    )

    if existing is not None:
        return existing

    paths = ensure_dataset_directories(
        data_root=data_root,
        dataset_id_value=(
            dataset_id_value
        ),
    )

    imported_at = utc_now()

    source_artifacts = []
    normalized_artifacts = []
    quality_artifacts = []

    reports = []

    for source in sorted(
        discovery[
            "sources"
        ],
        key=lambda row: (
            str(
                row[
                    "name"
                ]
            ),
            str(
                row[
                    "source_sha256"
                ]
            ),
        ),
    ):
        source_name = str(
            source[
                "name"
            ]
        )

        source_path = inventory[
            source_name
        ]

        expected_hash = str(
            source[
                "source_sha256"
            ]
        )

        safe_zip_name = _safe_name(
            source_name
        )

        preserved_zip = (
            paths[
                "source_zip"
            ]
            / safe_zip_name
        )

        if preserved_zip.exists():
            if (
                sha256_file(
                    preserved_zip
                )
                != expected_hash
            ):
                raise DatasetMaterializationError(
                    "DATASET_MATERIALIZATION_ERROR: "
                    "isolated source already "
                    "exists with different "
                    f"content: {source_name}"
                )
        else:
            shutil.copy2(
                source_path,
                preserved_zip,
            )

        if (
            sha256_file(
                preserved_zip
            )
            != expected_hash
        ):
            raise DatasetMaterializationError(
                "DATASET_MATERIALIZATION_ERROR: "
                "preserved source hash "
                f"mismatch: {source_name}"
            )

        source_artifacts.append(
            {
                "name": (
                    source_name
                ),
                "path": str(
                    preserved_zip
                ),
                "sha256": (
                    expected_hash
                ),
            }
        )

        try:
            archive = zipfile.ZipFile(
                preserved_zip,
                "r",
            )
        except zipfile.BadZipFile as exc:
            raise DatasetMaterializationError(
                "DATASET_MATERIALIZATION_ERROR: "
                "invalid preserved ZIP: "
                f"{source_name}"
            ) from exc

        with archive:
            members = sorted(
                [
                    member
                    for member
                    in archive.namelist()
                    if (
                        member.lower()
                        .endswith(
                            ".csv"
                        )
                        and not member.endswith(
                            "/"
                        )
                    )
                ]
            )

            if not members:
                raise DatasetMaterializationError(
                    "DATASET_MATERIALIZATION_ERROR: "
                    f"{source_name} contains "
                    "no CSV files."
                )

            source_stem = _safe_name(
                Path(
                    source_name
                ).stem
            )

            for index, member in enumerate(
                members,
                start=1,
            ):
                original_csv_name = (
                    Path(
                        member
                    ).name
                )

                safe_csv_name = (
                    _safe_name(
                        original_csv_name
                    )
                )

                component_stem = (
                    f"{source_stem}"
                    f"__{index:06d}"
                    f"__{Path(safe_csv_name).stem}"
                )

                raw_csv = (
                    paths[
                        "source_csv"
                    ]
                    / (
                        component_stem
                        + ".csv"
                    )
                )

                if not raw_csv.exists():
                    with archive.open(
                        member
                    ) as source_stream:
                        with raw_csv.open(
                            "wb"
                        ) as target:
                            shutil.copyfileobj(
                                source_stream,
                                target,
                            )

                normalized_path = (
                    paths[
                        "normalized"
                    ]
                    / (
                        component_stem
                        + ".parquet"
                    )
                )

                report_path = (
                    paths[
                        "quality"
                    ]
                    / (
                        component_stem
                        + ".quality.json"
                    )
                )

                report = (
                    normalize_vendor_csv(
                        raw_csv=raw_csv,
                        output_parquet=(
                            normalized_path
                        ),
                        report_path=(
                            report_path
                        ),
                        raw_zip=(
                            preserved_zip
                        ),
                        imported_at=(
                            imported_at
                        ),
                    )
                )

                #
                # normalize_vendor_csv é
                # reutilizado integralmente.
                #
                # A identidade por arquivo
                # produzida pelo legado não é
                # a identidade oficial Stage 22.
                # O quality report é vinculado
                # ao Dataset agregado descoberto.
                #
                report[
                    "dataset_id"
                ] = dataset_id_value

                report[
                    "dataset_version"
                ] = discovery[
                    "dataset_version"
                ]

                report[
                    "market"
                ] = market

                report[
                    "asset"
                ] = asset

                report[
                    "source_provider"
                ] = discovery.get(
                    "provider"
                )

                report[
                    "dataset_discovery_version"
                ] = discovery.get(
                    "discovery_version"
                )

                report[
                    "dataset_pipeline_version"
                ] = (
                    DATASET_PIPELINE_VERSION
                )

                report[
                    "original_source_zip"
                ] = source_name

                report[
                    "original_source_csv"
                ] = original_csv_name

                _write_json(
                    path=report_path,
                    value=report,
                )

                normalized_hash = (
                    sha256_file(
                        normalized_path
                    )
                )

                quality_hash = (
                    sha256_file(
                        report_path
                    )
                )

                reports.append(
                    report
                )

                normalized_artifacts.append(
                    {
                        "source_zip": (
                            source_name
                        ),
                        "source_csv": (
                            original_csv_name
                        ),
                        "path": str(
                            normalized_path
                        ),
                        "sha256": (
                            normalized_hash
                        ),
                        "rows": int(
                            report[
                                "row_count"
                            ]
                        ),
                    }
                )

                quality_artifacts.append(
                    {
                        "source_zip": (
                            source_name
                        ),
                        "source_csv": (
                            original_csv_name
                        ),
                        "path": str(
                            report_path
                        ),
                        "sha256": (
                            quality_hash
                        ),
                        "quality_valid": (
                            _quality_is_valid(
                                report
                            )
                        ),
                    }
                )

    if not reports:
        raise DatasetMaterializationError(
            "DATASET_MATERIALIZATION_ERROR: "
            "no normalized components "
            "were produced."
        )

    quality_ok = all(
        _quality_is_valid(
            report
        )
        for report in reports
    )

    normalized_records = sum(
        int(
            report.get(
                "row_count"
            )
            or 0
        )
        for report in reports
    )

    dates = {
        str(
            date
        )
        for component
        in discovery.get(
            "components",
            []
        )
        for date
        in component.get(
            "dates",
            []
        )
    }

    manifest = {
        "dataset_id": (
            dataset_id_value
        ),
        "dataset_version": (
            discovery[
                "dataset_version"
            ]
        ),
        "market": market,
        "asset": asset,
        "provider": (
            discovery.get(
                "provider"
            )
        ),
        "imported_at": (
            imported_at
        ),
        "ingest_version": (
            INGEST_VERSION
        ),
        "normalization_version": (
            NORMALIZATION_VERSION
        ),
        "dataset_store_version": (
            DATASET_STORE_VERSION
        ),
        "dataset_discovery_version": (
            discovery.get(
                "discovery_version"
            )
        ),
        "dataset_pipeline_version": (
            DATASET_PIPELINE_VERSION
        ),
        "period_start": (
            discovery[
                "period_start"
            ]
        ),
        "period_end": (
            discovery[
                "period_end"
            ]
        ),
        "files_total": (
            discovery[
                "files_total"
            ]
        ),
        "components_total": (
            discovery[
                "components_total"
            ]
        ),
        "sessions_total": (
            len(
                dates
            )
        ),
        "records_total": (
            normalized_records
        ),
        "source_files": (
            discovery[
                "source_files"
            ]
        ),
        "source_sha256": (
            discovery[
                "source_sha256"
            ]
        ),
        "sources": (
            source_artifacts
        ),
        "normalized_artifacts": (
            normalized_artifacts
        ),
        "quality_artifacts": (
            quality_artifacts
        ),
        "quality_status": (
            "READY"
            if quality_ok
            else "ERROR"
        ),
        "research_ready": False,
        "derived_artifacts": {
            "trade1_database": None,
            "trajectory_manifest": None,
            "trajectories": [],
        },
    }

    _write_json(
        path=(
            paths[
                "manifest"
            ]
        ),
        value=manifest,
    )

    return {
        "dataset_id": (
            dataset_id_value
        ),
        "status": (
            "MATERIALIZED"
        ),
        "manifest": manifest,
        "manifest_path": str(
            paths[
                "manifest"
            ]
        ),
        "paths": {
            key: str(
                value
            )
            for key, value
            in paths.items()
        },
    }


def _derived_artifact(
    path: Path,
) -> dict[str, Any]:
    if not path.exists():
        raise DatasetMaterializationError(
            "DATASET_PREPARATION_ERROR: "
            "expected derived artifact "
            f"does not exist: {path}"
        )

    return {
        "path": str(
            path
        ),
        "sha256": (
            sha256_file(
                path
            )
        ),
    }


def _trajectory_artifacts(
    trajectory_dir: Path,
    manifest_path: Path,
) -> list[dict[str, Any]]:
    if not trajectory_dir.exists():
        return []

    artifacts = []

    for path in sorted(
        trajectory_dir.glob(
            "*.parquet"
        )
    ):
        if (
            path.resolve()
            == manifest_path.resolve()
        ):
            continue

        artifacts.append(
            {
                "path": str(
                    path
                ),
                "sha256": (
                    sha256_file(
                        path
                    )
                ),
            }
        )

    return artifacts


def _prepared_dataset_is_complete(
    *,
    manifest: dict[str, Any],
    paths: dict[str, Path],
) -> bool:
    if (
        manifest.get(
            "research_ready"
        )
        is not True
    ):
        return False

    required = (
        paths[
            "trade1_database"
        ],
        paths[
            "trajectory_manifest"
        ],
        paths[
            "scanner_summary"
        ],
    )

    if not all(
        path.exists()
        for path in required
    ):
        return False

    derived = (
        manifest.get(
            "derived_artifacts"
        )
        or {}
    )

    trade1 = (
        derived.get(
            "trade1_database"
        )
        or {}
    )

    trajectory_manifest = (
        derived.get(
            "trajectory_manifest"
        )
        or {}
    )

    scanner_summary = (
        derived.get(
            "scanner_summary"
        )
        or {}
    )

    expected = (
        (
            paths[
                "trade1_database"
            ],
            trade1.get(
                "sha256"
            ),
        ),
        (
            paths[
                "trajectory_manifest"
            ],
            trajectory_manifest.get(
                "sha256"
            ),
        ),
        (
            paths[
                "scanner_summary"
            ],
            scanner_summary.get(
                "sha256"
            ),
        ),
    )

    for (
        artifact_path,
        expected_hash,
    ) in expected:
        if not expected_hash:
            return False

        if (
            sha256_file(
                artifact_path
            )
            != expected_hash
        ):
            return False

    for artifact in (
        derived.get(
            "trajectories"
        )
        or []
    ):
        artifact_path = Path(
            artifact[
                "path"
            ]
        )

        if not artifact_path.exists():
            return False

        if (
            sha256_file(
                artifact_path
            )
            != artifact.get(
                "sha256"
            )
        ):
            return False

    return True


def prepare_dataset_for_research(
    *,
    dataset_id_value: str,
    data_root: str | Path = "data",
) -> dict[str, Any]:
    paths = dataset_paths(
        data_root=data_root,
        dataset_id_value=(
            dataset_id_value
        ),
    )

    manifest_path = paths[
        "manifest"
    ]

    if not manifest_path.exists():
        raise DatasetMaterializationError(
            "DATASET_PREPARATION_ERROR: "
            "Dataset manifest does not "
            f"exist for {dataset_id_value}."
        )

    manifest = _read_json(
        manifest_path
    )

    if (
        str(
            manifest.get(
                "dataset_id"
            )
        )
        != str(
            dataset_id_value
        )
    ):
        raise DatasetMaterializationError(
            "DATASET_PREPARATION_ERROR: "
            "Dataset manifest identity "
            "mismatch."
        )

    if (
        manifest.get(
            "quality_status"
        )
        != "READY"
    ):
        raise DatasetMaterializationError(
            "DATASET_PREPARATION_ERROR: "
            "Dataset quality status is "
            "not READY."
        )

    if (
        _prepared_dataset_is_complete(
            manifest=manifest,
            paths=paths,
        )
    ):
        return {
            "dataset_id": (
                dataset_id_value
            ),
            "status": (
                "ALREADY_PREPARED"
            ),
            "manifest": manifest,
            "manifest_path": str(
                manifest_path
            ),
            "paths": {
                key: str(
                    value
                )
                for key, value
                in paths.items()
            },
        }

    normalized_dir = paths[
        "normalized"
    ]

    if not normalized_dir.exists():
        raise DatasetMaterializationError(
            "DATASET_PREPARATION_ERROR: "
            "Dataset normalized directory "
            "does not exist."
        )

    normalized_files = sorted(
        normalized_dir.glob(
            "*.parquet"
        )
    )

    if not normalized_files:
        raise DatasetMaterializationError(
            "DATASET_PREPARATION_ERROR: "
            "Dataset contains no normalized "
            "Parquet files."
        )

    #
    # Scanner homologado.
    #
    # IMPORTANTE:
    # recebe somente o normalized deste
    # Dataset ID.
    #
    scanner = run_scanner(
        normalized_dir=(
            normalized_dir
        ),
        database_path=(
            paths[
                "trade1_database"
            ]
        ),
        summary_path=(
            paths[
                "scanner_summary"
            ]
        ),
    )

    #
    # Trajectory Cache homologado.
    #
    # Também recebe somente o espaço
    # físico deste Dataset ID.
    #
    trajectory_cache = (
        run_trajectory_cache(
            normalized_dir=(
                normalized_dir
            ),
            trajectory_dir=(
                paths[
                    "trajectories"
                ]
            ),
            manifest_path=(
                paths[
                    "trajectory_manifest"
                ]
            ),
        )
    )

    trade1_artifact = (
        _derived_artifact(
            paths[
                "trade1_database"
            ]
        )
    )

    scanner_summary_artifact = (
        _derived_artifact(
            paths[
                "scanner_summary"
            ]
        )
    )

    trajectory_manifest_artifact = (
        _derived_artifact(
            paths[
                "trajectory_manifest"
            ]
        )
    )

    trajectories = (
        _trajectory_artifacts(
            paths[
                "trajectories"
            ],
            paths[
                "trajectory_manifest"
            ],
        )
    )

    manifest[
        "derived_artifacts"
    ] = {
        "trade1_database": (
            trade1_artifact
        ),
        "scanner_summary": (
            scanner_summary_artifact
        ),
        "trajectory_manifest": (
            trajectory_manifest_artifact
        ),
        "trajectories": (
            trajectories
        ),
    }

    manifest[
        "research_ready"
    ] = True

    manifest[
        "research_prepared_at"
    ] = utc_now()

    _write_json(
        path=manifest_path,
        value=manifest,
    )

    return {
        "dataset_id": (
            dataset_id_value
        ),
        "status": "READY",
        "manifest": manifest,
        "manifest_path": str(
            manifest_path
        ),
        "paths": {
            key: str(
                value
            )
            for key, value
            in paths.items()
        },
        "scanner": scanner,
        "trajectory_cache": (
            trajectory_cache
        ),
    }

