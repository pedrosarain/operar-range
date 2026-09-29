from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


DATASET_STORE_VERSION = "dataset-store-v1"
DATASET_VERSION = 1


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
        value.encode(
            "utf-8"
        )
    ).hexdigest()


def normalize_source_hashes(
    source_sha256: list[str],
) -> list[str]:
    if not source_sha256:
        raise ValueError(
            "Dataset requires at least "
            "one source SHA256."
        )

    normalized = sorted(
        {
            str(value).strip().lower()
            for value in source_sha256
            if str(value).strip()
        }
    )

    if not normalized:
        raise ValueError(
            "Dataset requires at least "
            "one valid source SHA256."
        )

    for value in normalized:
        if (
            len(value) != 64
            or any(
                character
                not in "0123456789abcdef"
                for character in value
            )
        ):
            raise ValueError(
                "Invalid source SHA256: "
                f"{value}"
            )

    return normalized


def dataset_identity_payload(
    *,
    market: str,
    asset: str,
    source_sha256: list[str],
    period_start: str,
    period_end: str,
    dataset_version: int = (
        DATASET_VERSION
    ),
) -> dict[str, Any]:
    market = str(
        market
    ).strip()

    asset = str(
        asset
    ).strip()

    period_start = str(
        period_start
    ).strip()

    period_end = str(
        period_end
    ).strip()

    if not market:
        raise ValueError(
            "market is required."
        )

    if not asset:
        raise ValueError(
            "asset is required."
        )

    if not period_start:
        raise ValueError(
            "period_start is required."
        )

    if not period_end:
        raise ValueError(
            "period_end is required."
        )

    if period_start > period_end:
        raise ValueError(
            "period_start cannot be "
            "after period_end."
        )

    if int(
        dataset_version
    ) <= 0:
        raise ValueError(
            "dataset_version must be "
            "positive."
        )

    return {
        "market": market,
        "asset": asset,
        "source_sha256": (
            normalize_source_hashes(
                source_sha256
            )
        ),
        "period_start": (
            period_start
        ),
        "period_end": (
            period_end
        ),
        "dataset_version": int(
            dataset_version
        ),
    }


def dataset_id(
    *,
    market: str,
    asset: str,
    source_sha256: list[str],
    period_start: str,
    period_end: str,
    dataset_version: int = (
        DATASET_VERSION
    ),
) -> str:
    payload = (
        dataset_identity_payload(
            market=market,
            asset=asset,
            source_sha256=(
                source_sha256
            ),
            period_start=(
                period_start
            ),
            period_end=(
                period_end
            ),
            dataset_version=(
                dataset_version
            ),
        )
    )

    digest = sha256_text(
        canonical_json(
            payload
        )
    )

    return (
        "DS-"
        + digest[:16].upper()
    )


def dataset_root(
    *,
    data_root: str | Path,
    dataset_id_value: str,
) -> Path:
    dataset_id_value = str(
        dataset_id_value
    ).strip()

    if not dataset_id_value:
        raise ValueError(
            "dataset_id is required."
        )

    if (
        "/" in dataset_id_value
        or "\\" in dataset_id_value
        or ".." in dataset_id_value
    ):
        raise ValueError(
            "Invalid dataset_id."
        )

    return (
        Path(
            data_root
        )
        / "datasets"
        / dataset_id_value
    )


def dataset_paths(
    *,
    data_root: str | Path,
    dataset_id_value: str,
) -> dict[str, Path]:
    root = dataset_root(
        data_root=data_root,
        dataset_id_value=(
            dataset_id_value
        ),
    )

    return {
        "root": root,
        "manifest": (
            root
            / "dataset_manifest.json"
        ),
        "source": (
            root
            / "source"
        ),
        "source_zip": (
            root
            / "source"
            / "zip"
        ),
        "source_csv": (
            root
            / "source"
            / "csv"
        ),
        "normalized": (
            root
            / "normalized"
        ),
        "quality": (
            root
            / "quality"
        ),
        "research": (
            root
            / "research"
        ),
        "trade1_database": (
            root
            / "research"
            / "trade1_database.parquet"
        ),
        "trajectories": (
            root
            / "trajectories"
        ),
        "trajectory_manifest": (
            root
            / "trajectories"
            / "trajectory_manifest.parquet"
        ),
        "reports": (
            root
            / "reports"
        ),
        "scanner_summary": (
            root
            / "reports"
            / "trade1_database_summary.json"
        ),
    }


def ensure_dataset_directories(
    *,
    data_root: str | Path,
    dataset_id_value: str,
) -> dict[str, Path]:
    paths = dataset_paths(
        data_root=data_root,
        dataset_id_value=(
            dataset_id_value
        ),
    )

    for key in (
        "root",
        "source",
        "source_zip",
        "source_csv",
        "normalized",
        "quality",
        "research",
        "trajectories",
        "reports",
    ):
        paths[
            key
        ].mkdir(
            parents=True,
            exist_ok=True,
        )

    return paths
