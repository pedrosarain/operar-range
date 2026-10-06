from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


MANUAL_BASELINE_REGISTRY_VERSION = (
    "manual-baseline-registry-v1"
)

MANUAL_BASELINE_SCHEMA_VERSION = 1

MANUAL_BASELINE_RESULTS_SCHEMA_VERSION = 1

MANUAL_BASELINE_ROOT = (
    Path("data")
    / "manual"
    / "baselines"
)


MANUAL_BASELINE_REQUIRED_FIELDS = (
    "baseline_id",
    "name",
    "description",
    "strategy",
    "market",
    "asset",
    "source_dataset_id",
    "universe",
    "session_count",
    "author",
    "created_at",
    "status",
    "notes",
    "version",
    "baseline_sha256",
    "registry_version",
    "schema_version",
    "results_schema_version",
    "results",
)


MANUAL_BASELINE_RESULT_FIELDS = (
    "question_key",
    "question_label",
    "category",
    "value_type",
    "value",
    "unit",
    "dimensions",
    "notes",
)


MANUAL_BASELINE_RESULT_CATEGORIES = (
    "TARGET",
    "ZERO_RELATION",
    "TARGET_STOP",
    "STOP_TARGET",
    "TRADE_2",
    "EXPECTANCY",
    "WIN_RATE",
    "DRAWDOWN",
    "OTHER",
)


MANUAL_BASELINE_COMPARISON_CONTRACT_FIELDS = (
    "research_id",
    "manual_baseline_id",
    "manual_baseline_version",
    "manual_baseline_sha256",
    "question_key",
    "research_value",
    "manual_baseline_value",
    "status",
)


MANUAL_BASELINE_COMPARISON_STATUSES = (
    "MATCH",
    "DIVERGENT",
)


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode(
            "utf-8"
        )
    ).hexdigest()


def _clean_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(
        value
    ).strip()


def _validate_baseline_id(
    baseline_id: str,
) -> str:
    value = _clean_text(
        baseline_id
    )

    if not value:
        raise ValueError(
            "baseline_id is required."
        )

    if (
        "/" in value
        or "\\" in value
        or ".." in value
    ):
        raise ValueError(
            "Invalid baseline_id."
        )

    if not value.startswith(
        "MBL-"
    ):
        raise ValueError(
            "baseline_id must start with MBL-."
        )

    return value


def baseline_identity_payload(
    *,
    name: str,
    strategy: str,
    market: str,
    asset: str,
    author: str,
) -> dict[str, str]:
    payload = {
        "name": _clean_text(
            name
        ),
        "strategy": _clean_text(
            strategy
        ),
        "market": _clean_text(
            market
        ),
        "asset": _clean_text(
            asset
        ),
        "author": _clean_text(
            author
        ),
    }

    for key, value in payload.items():
        if not value:
            raise ValueError(
                f"{key} is required."
            )

    return payload


def new_manual_baseline_id(
    *,
    name: str,
    strategy: str,
    market: str,
    asset: str,
    author: str,
) -> str:
    payload = baseline_identity_payload(
        name=name,
        strategy=strategy,
        market=market,
        asset=asset,
        author=author,
    )

    digest = sha256_text(
        canonical_json(
            payload
        )
    )

    return (
        "MBL-"
        + digest[
            :16
        ].upper()
    )


def baseline_root(
    baseline_id: str,
    *,
    root: str | Path = (
        MANUAL_BASELINE_ROOT
    ),
) -> Path:
    identifier = (
        _validate_baseline_id(
            baseline_id
        )
    )

    return (
        Path(
            root
        )
        / identifier
    )


def baseline_versions_root(
    baseline_id: str,
    *,
    root: str | Path = (
        MANUAL_BASELINE_ROOT
    ),
) -> Path:
    return (
        baseline_root(
            baseline_id,
            root=root,
        )
        / "versions"
    )


def baseline_version_path(
    baseline_id: str,
    version: int,
    *,
    root: str | Path = (
        MANUAL_BASELINE_ROOT
    ),
) -> Path:
    if (
        isinstance(
            version,
            bool,
        )
        or not isinstance(
            version,
            int,
        )
        or version < 1
    ):
        raise ValueError(
            "version must be an integer >= 1."
        )

    return (
        baseline_versions_root(
            baseline_id,
            root=root,
        )
        / (
            f"{version:06d}.json"
        )
    )


def _validate_result_contract(
    result: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        result,
        dict,
    ):
        raise TypeError(
            "Manual Baseline result "
            "must be a dictionary."
        )

    normalized = {
        field: result.get(
            field
        )
        for field
        in MANUAL_BASELINE_RESULT_FIELDS
    }

    question_key = _clean_text(
        normalized[
            "question_key"
        ]
    )

    question_label = _clean_text(
        normalized[
            "question_label"
        ]
    )

    category = _clean_text(
        normalized[
            "category"
        ]
    ).upper()

    value_type = _clean_text(
        normalized[
            "value_type"
        ]
    )

    if not question_key:
        raise ValueError(
            "question_key is required."
        )

    if not question_label:
        raise ValueError(
            "question_label is required."
        )

    if (
        category
        not in
        MANUAL_BASELINE_RESULT_CATEGORIES
    ):
        raise ValueError(
            "Unsupported Manual Baseline "
            f"result category: {category}"
        )

    if not value_type:
        raise ValueError(
            "value_type is required."
        )

    dimensions = normalized.get(
        "dimensions"
    )

    if dimensions is None:
        dimensions = {}

    if not isinstance(
        dimensions,
        dict,
    ):
        raise TypeError(
            "dimensions must be "
            "a dictionary."
        )

    return {
        "question_key": (
            question_key
        ),
        "question_label": (
            question_label
        ),
        "category": category,
        "value_type": (
            value_type
        ),
        "value": normalized.get(
            "value"
        ),
        "unit": _clean_text(
            normalized.get(
                "unit"
            )
        ),
        "dimensions": (
            dimensions
        ),
        "notes": _clean_text(
            normalized.get(
                "notes"
            )
        ),
    }


def normalize_results(
    results: list[
        dict[str, Any]
    ] | None,
) -> list[dict[str, Any]]:
    if results is None:
        return []

    if not isinstance(
        results,
        list,
    ):
        raise TypeError(
            "results must be a list."
        )

    normalized = [
        _validate_result_contract(
            result
        )
        for result
        in results
    ]

    question_keys = [
        row[
            "question_key"
        ]
        for row
        in normalized
    ]

    if (
        len(
            question_keys
        )
        != len(
            set(
                question_keys
            )
        )
    ):
        raise ValueError(
            "Duplicate question_key "
            "within Manual Baseline version."
        )

    return normalized


def baseline_hash_payload(
    definition: dict[
        str,
        Any,
    ],
) -> dict[str, Any]:
    excluded = {
        "baseline_sha256",
    }

    return {
        key: value
        for key, value
        in definition.items()
        if key not in excluded
    }


def manual_baseline_sha256(
    definition: dict[
        str,
        Any,
    ],
) -> str:
    return sha256_text(
        canonical_json(
            baseline_hash_payload(
                definition
            )
        )
    )


def build_manual_baseline_definition(
    *,
    baseline_id: str,
    name: str,
    description: str,
    strategy: str,
    market: str,
    asset: str,
    source_dataset_id: str | None,
    universe: str,
    session_count: int,
    author: str,
    created_at: str,
    status: str,
    notes: str,
    version: int,
    results: list[
        dict[str, Any]
    ] | None = None,
) -> dict[str, Any]:
    identifier = (
        _validate_baseline_id(
            baseline_id
        )
    )

    if (
        isinstance(
            session_count,
            bool,
        )
        or not isinstance(
            session_count,
            int,
        )
        or session_count < 0
    ):
        raise ValueError(
            "session_count must be "
            "an integer >= 0."
        )

    if (
        isinstance(
            version,
            bool,
        )
        or not isinstance(
            version,
            int,
        )
        or version < 1
    ):
        raise ValueError(
            "version must be "
            "an integer >= 1."
        )

    required_text = {
        "name": name,
        "description": description,
        "strategy": strategy,
        "market": market,
        "asset": asset,
        "universe": universe,
        "author": author,
        "created_at": created_at,
        "status": status,
    }

    cleaned = {
        key: _clean_text(
            value
        )
        for key, value
        in required_text.items()
    }

    for key, value in cleaned.items():
        if not value:
            raise ValueError(
                f"{key} is required."
            )

    definition: dict[
        str,
        Any,
    ] = {
        "baseline_id": (
            identifier
        ),
        "name": cleaned[
            "name"
        ],
        "description": cleaned[
            "description"
        ],
        "strategy": cleaned[
            "strategy"
        ],
        "market": cleaned[
            "market"
        ],
        "asset": cleaned[
            "asset"
        ],
        "source_dataset_id": (
            _clean_text(
                source_dataset_id
            )
            or None
        ),
        "universe": cleaned[
            "universe"
        ],
        "session_count": (
            int(
                session_count
            )
        ),
        "author": cleaned[
            "author"
        ],
        "created_at": cleaned[
            "created_at"
        ],
        "status": cleaned[
            "status"
        ],
        "notes": _clean_text(
            notes
        ),
        "version": int(
            version
        ),
        "registry_version": (
            MANUAL_BASELINE_REGISTRY_VERSION
        ),
        "schema_version": (
            MANUAL_BASELINE_SCHEMA_VERSION
        ),
        "results_schema_version": (
            MANUAL_BASELINE_RESULTS_SCHEMA_VERSION
        ),
        "results": (
            normalize_results(
                results
            )
        ),
    }

    definition[
        "baseline_sha256"
    ] = manual_baseline_sha256(
        definition
    )

    return definition


def validate_manual_baseline_definition(
    definition: dict[
        str,
        Any,
    ],
) -> None:
    if not isinstance(
        definition,
        dict,
    ):
        raise TypeError(
            "Manual Baseline definition "
            "must be a dictionary."
        )

    missing = [
        field
        for field
        in MANUAL_BASELINE_REQUIRED_FIELDS
        if field not in definition
    ]

    if missing:
        raise ValueError(
            "Manual Baseline missing fields: "
            + ", ".join(
                missing
            )
        )

    _validate_baseline_id(
        str(
            definition[
                "baseline_id"
            ]
        )
    )

    if (
        definition.get(
            "registry_version"
        )
        != MANUAL_BASELINE_REGISTRY_VERSION
    ):
        raise ValueError(
            "Unsupported registry_version."
        )

    if (
        definition.get(
            "schema_version"
        )
        != MANUAL_BASELINE_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported schema_version."
        )

    if (
        definition.get(
            "results_schema_version"
        )
        != MANUAL_BASELINE_RESULTS_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported results_schema_version."
        )

    normalize_results(
        definition.get(
            "results"
        )
    )

    expected = (
        manual_baseline_sha256(
            definition
        )
    )

    actual = str(
        definition.get(
            "baseline_sha256"
        )
        or ""
    )

    if expected != actual:
        raise ValueError(
            "Manual Baseline SHA256 mismatch."
        )


def write_manual_baseline_version(
    definition: dict[
        str,
        Any,
    ],
    *,
    root: str | Path = (
        MANUAL_BASELINE_ROOT
    ),
) -> Path:
    validate_manual_baseline_definition(
        definition
    )

    baseline_id = str(
        definition[
            "baseline_id"
        ]
    )

    version = int(
        definition[
            "version"
        ]
    )

    path = baseline_version_path(
        baseline_id,
        version,
        root=root,
    )

    if path.exists():
        raise FileExistsError(
            "Manual Baseline versions "
            "are immutable: "
            f"{baseline_id} v{version}"
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = (
        json.dumps(
            definition,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    path.write_text(
        payload,
        encoding="utf-8",
    )

    return path


def load_manual_baseline(
    baseline_id: str,
    version: int,
    *,
    root: str | Path = (
        MANUAL_BASELINE_ROOT
    ),
) -> dict[str, Any]:
    path = baseline_version_path(
        baseline_id,
        version,
        root=root,
    )

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    definition = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    validate_manual_baseline_definition(
        definition
    )

    return definition


def list_manual_baseline_versions(
    baseline_id: str,
    *,
    root: str | Path = (
        MANUAL_BASELINE_ROOT
    ),
) -> list[int]:
    versions_root = (
        baseline_versions_root(
            baseline_id,
            root=root,
        )
    )

    if not versions_root.exists():
        return []

    versions: list[int] = []

    for path in sorted(
        versions_root.glob(
            "*.json"
        )
    ):
        try:
            version = int(
                path.stem
            )
        except ValueError:
            continue

        if version >= 1:
            versions.append(
                version
            )

    return sorted(
        set(
            versions
        )
    )


def load_latest_manual_baseline(
    baseline_id: str,
    *,
    root: str | Path = (
        MANUAL_BASELINE_ROOT
    ),
) -> dict[str, Any]:
    versions = (
        list_manual_baseline_versions(
            baseline_id,
            root=root,
        )
    )

    if not versions:
        raise FileNotFoundError(
            "Manual Baseline has "
            "no registered versions: "
            f"{baseline_id}"
        )

    return load_manual_baseline(
        baseline_id,
        versions[
            -1
        ],
        root=root,
    )


def list_manual_baselines(
    *,
    root: str | Path = (
        MANUAL_BASELINE_ROOT
    ),
) -> list[dict[str, Any]]:
    root_path = Path(
        root
    )

    if not root_path.exists():
        return []

    rows: list[
        dict[str, Any]
    ] = []

    for path in sorted(
        item
        for item
        in root_path.iterdir()
        if item.is_dir()
    ):
        baseline_id = path.name

        try:
            latest = (
                load_latest_manual_baseline(
                    baseline_id,
                    root=root_path,
                )
            )
        except (
            FileNotFoundError,
            ValueError,
            TypeError,
        ):
            continue

        rows.append(
            latest
        )

    return sorted(
        rows,
        key=lambda row: (
            str(
                row.get(
                    "name"
                )
                or ""
            ).lower(),
            str(
                row.get(
                    "baseline_id"
                )
                or ""
            ),
        ),
    )


def comparison_contract_definition() -> dict[
    str,
    Any,
]:
    return {
        "fields": list(
            MANUAL_BASELINE_COMPARISON_CONTRACT_FIELDS
        ),
        "statuses": list(
            MANUAL_BASELINE_COMPARISON_STATUSES
        ),
        "implementation_status": (
            "CONTRACT_ONLY"
        ),
        "comparison_implemented": False,
    }
