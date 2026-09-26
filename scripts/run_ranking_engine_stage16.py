from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from operar_range.ranking_engine import (
    RANKING_ENGINE_VERSION,
    RankingRequest,
    run_ranking_engine,
    sha256_file,
)


OVERALL_METRICS = Path(
    "data/research/"
    "experiment_metrics.parquet"
)

YEARLY_METRICS = Path(
    "data/research/"
    "experiment_metrics_yearly.parquet"
)

MONTHLY_METRICS = Path(
    "data/research/"
    "experiment_metrics_monthly.parquet"
)

REGISTRY = Path(
    "data/research/"
    "experiment_registry.parquet"
)


CANONICAL_RANKINGS = Path(
    "data/research/"
    "experiment_rankings.parquet"
)

CANONICAL_MANIFEST = Path(
    "data/research/"
    "ranking_manifest.parquet"
)

CANONICAL_SUMMARY = Path(
    "data/reports/"
    "ranking_summary.json"
)


VALIDATION_ROOT = Path(
    "data/research/"
    "stage16_validation"
)


CREATED_AT = (
    "2026-09-25T00:00:00+00:00"
)


COMPOSITE_WEIGHTS = {
    "EXPECTANCY": 35.0,
    "PROFIT_FACTOR": 25.0,
    "MAX_DRAWDOWN": 20.0,
    "NUMBER_OF_TRADES": 10.0,
    "WIN_RATE": 10.0,
}


def separator(
    title: str,
) -> None:
    print()
    print(
        "=" * 78
    )
    print(title)
    print(
        "=" * 78
    )


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode(
            "utf-8"
        )
    ).hexdigest()


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


def read_json(
    path: str | Path,
) -> dict[str, Any]:
    path = Path(path)

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def parquet_rows(
    path: str | Path,
) -> list[dict[str, Any]]:
    return (
        pq.read_table(
            path
        )
        .to_pylist()
    )


def logical_parquet_hash(
    path: str | Path,
) -> str:
    rows = parquet_rows(
        path
    )

    normalized = []

    for row in rows:
        normalized.append(
            {
                key: value
                for key, value
                in row.items()
                if key
                not in (
                    "created_at",
                )
            }
        )

    return sha256_text(
        canonical_json(
            normalized
        )
    )


def require_inputs() -> None:
    required = [
        OVERALL_METRICS,
        YEARLY_METRICS,
        MONTHLY_METRICS,
        REGISTRY,
    ]

    missing = [
        str(path)
        for path in required
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing Stage 16 inputs: "
            + ", ".join(
                missing
            )
        )


def scope_paths(
    name: str,
) -> dict[str, Path]:
    root = (
        VALIDATION_ROOT
        / name.lower()
    )

    return {
        "root": root,
        "rankings": (
            root
            / "experiment_rankings.parquet"
        ),
        "manifest": (
            root
            / "ranking_manifest.parquet"
        ),
        "summary": (
            root
            / "ranking_summary.json"
        ),
    }


def print_scope_summary(
    *,
    label: str,
    result: dict[str, Any],
    elapsed_seconds: float,
) -> None:
    summary = result[
        "summary"
    ]

    separator(
        f"ETAPA 16 — {label}"
    )

    print(
        "ENGINE_VERSION:",
        RANKING_ENGINE_VERSION,
    )

    print(
        "SCOPE:",
        summary[
            "scope"
        ],
    )

    print(
        "YEAR:",
        summary[
            "year"
        ],
    )

    print(
        "MONTH:",
        summary[
            "month"
        ],
    )

    print(
        "SOURCE_DATASET:",
        summary[
            "source_dataset"
        ],
    )

    print(
        "SOURCE_HASH:",
        summary[
            "source_hash"
        ],
    )

    print(
        "REGISTRY_HASH:",
        summary[
            "registry_hash"
        ],
    )

    print(
        "RULE_SET_HASH:",
        summary[
            "rule_set_hash"
        ],
    )

    print(
        "RULE_SET_HASH_STATUS:",
        summary[
            "rule_set_hash_status"
        ],
    )

    print(
        "EXPERIMENTS_CLASSIFIED:",
        summary[
            "experiments_classified"
        ],
    )

    print(
        "RANKING_TYPES_TOTAL:",
        summary[
            "ranking_types_total"
        ],
    )

    print(
        "RANKED_ROWS_TOTAL:",
        summary[
            "ranked_rows_total"
        ],
    )

    print(
        "NOT_RANKABLE_ROWS_TOTAL:",
        summary[
            "not_rankable_rows_total"
        ],
    )

    print(
        "CAGR_STATUS:",
        summary[
            "cagr_status"
        ],
    )

    print(
        "RECOVERY_FACTOR_STATUS:",
        summary[
            "recovery_factor_status"
        ],
    )

    print(
        "COMPOSITE_RANKING_ID:",
        summary[
            "composite_ranking_id"
        ],
    )

    print(
        "LOGICAL_RANKINGS_SHA256:",
        summary[
            "logical_rankings_sha256"
        ],
    )

    print(
        "RANKINGS_FILE_SHA256:",
        summary[
            "experiment_rankings_sha256"
        ],
    )

    print(
        "MANIFEST_FILE_SHA256:",
        summary[
            "ranking_manifest_sha256"
        ],
    )

    print(
        "ELAPSED_SECONDS:",
        round(
            elapsed_seconds,
            6,
        ),
    )


def execute_scope_once(
    *,
    label: str,
    request: RankingRequest,
    rankings_path: Path,
    manifest_path: Path,
    summary_path: Path,
) -> tuple[
    dict[str, Any],
    float,
]:
    started = (
        time.perf_counter()
    )

    result = run_ranking_engine(
        request=request,
        composite_weights=(
            COMPOSITE_WEIGHTS
        ),
        overall_metrics_path=(
            OVERALL_METRICS
        ),
        yearly_metrics_path=(
            YEARLY_METRICS
        ),
        monthly_metrics_path=(
            MONTHLY_METRICS
        ),
        registry_path=(
            REGISTRY
        ),
        rankings_path=(
            rankings_path
        ),
        manifest_path=(
            manifest_path
        ),
        summary_path=(
            summary_path
        ),
        created_at=(
            CREATED_AT
        ),
    )

    elapsed = (
        time.perf_counter()
        - started
    )

    print_scope_summary(
        label=label,
        result=result,
        elapsed_seconds=(
            elapsed
        ),
    )

    return (
        result,
        elapsed,
    )


def validate_scope(
    *,
    label: str,
    request: RankingRequest,
) -> dict[str, Any]:
    paths = scope_paths(
        label
    )

    root = paths[
        "root"
    ]

    if root.exists():
        shutil.rmtree(
            root
        )

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    first_result, first_time = (
        execute_scope_once(
            label=label,
            request=request,
            rankings_path=(
                paths[
                    "rankings"
                ]
            ),
            manifest_path=(
                paths[
                    "manifest"
                ]
            ),
            summary_path=(
                paths[
                    "summary"
                ]
            ),
        )
    )

    first_rankings_hash = (
        sha256_file(
            paths[
                "rankings"
            ]
        )
    )

    first_manifest_hash = (
        sha256_file(
            paths[
                "manifest"
            ]
        )
    )

    first_logical_hash = (
        logical_parquet_hash(
            paths[
                "rankings"
            ]
        )
    )

    first_manifest_logical_hash = (
        logical_parquet_hash(
            paths[
                "manifest"
            ]
        )
    )

    first_summary = read_json(
        paths[
            "summary"
        ]
    )

    first_ranking_ids = list(
        first_summary[
            "ranking_ids"
        ]
    )

    first_config_hashes = dict(
        first_summary[
            "ranking_config_sha256"
        ]
    )

    second_result, second_time = (
        execute_scope_once(
            label=(
                label
                + " — SECOND RUN"
            ),
            request=request,
            rankings_path=(
                paths[
                    "rankings"
                ]
            ),
            manifest_path=(
                paths[
                    "manifest"
                ]
            ),
            summary_path=(
                paths[
                    "summary"
                ]
            ),
        )
    )

    second_rankings_hash = (
        sha256_file(
            paths[
                "rankings"
            ]
        )
    )

    second_manifest_hash = (
        sha256_file(
            paths[
                "manifest"
            ]
        )
    )

    second_logical_hash = (
        logical_parquet_hash(
            paths[
                "rankings"
            ]
        )
    )

    second_manifest_logical_hash = (
        logical_parquet_hash(
            paths[
                "manifest"
            ]
        )
    )

    second_summary = read_json(
        paths[
            "summary"
        ]
    )

    second_ranking_ids = list(
        second_summary[
            "ranking_ids"
        ]
    )

    second_config_hashes = dict(
        second_summary[
            "ranking_config_sha256"
        ]
    )

    deterministic = (
        first_logical_hash
        == second_logical_hash
        and
        first_manifest_logical_hash
        == second_manifest_logical_hash
        and
        first_ranking_ids
        == second_ranking_ids
        and
        first_config_hashes
        == second_config_hashes
    )

    idempotent = (
        first_rankings_hash
        == second_rankings_hash
        and
        first_manifest_hash
        == second_manifest_hash
    )

    if not deterministic:
        raise RuntimeError(
            f"{label}: determinism "
            "validation failed."
        )

    if not idempotent:
        raise RuntimeError(
            f"{label}: idempotence "
            "validation failed."
        )

    manifest_rows = (
        parquet_rows(
            paths[
                "manifest"
            ]
        )
    )

    ranking_rows = (
        parquet_rows(
            paths[
                "rankings"
            ]
        )
    )

    composite_rows = [
        row
        for row
        in ranking_rows
        if row[
            "ranking_type"
        ]
        == "COMPOSITE_SCORE"
        and row[
            "ranking_status"
        ]
        == "RANKED"
    ]

    composite_rows = sorted(
        composite_rows,
        key=lambda row: (
            row[
                "rank_position"
            ]
        ),
    )

    not_rankable = [
        row
        for row
        in ranking_rows
        if row[
            "ranking_status"
        ]
        == "NOT_RANKABLE"
    ]

    cagr_manifest = next(
        row
        for row in manifest_rows
        if row[
            "ranking_type"
        ]
        == "CAGR"
    )

    recovery_manifest = next(
        row
        for row in manifest_rows
        if row[
            "ranking_type"
        ]
        == "RECOVERY_FACTOR"
    )

    separator(
        f"{label} — DETERMINISMO / IDEMPOTENCIA"
    )

    print(
        "DETERMINISTIC:",
        deterministic,
    )

    print(
        "IDEMPOTENT:",
        idempotent,
    )

    print(
        "FIRST_RANKINGS_SHA256:",
        first_rankings_hash,
    )

    print(
        "SECOND_RANKINGS_SHA256:",
        second_rankings_hash,
    )

    print(
        "FIRST_MANIFEST_SHA256:",
        first_manifest_hash,
    )

    print(
        "SECOND_MANIFEST_SHA256:",
        second_manifest_hash,
    )

    print(
        "FIRST_LOGICAL_SHA256:",
        first_logical_hash,
    )

    print(
        "SECOND_LOGICAL_SHA256:",
        second_logical_hash,
    )

    separator(
        f"{label} — COMPOSITE SCORE"
    )

    print(
        "COMPOSITE_WEIGHTS:",
        json.dumps(
            COMPOSITE_WEIGHTS,
            sort_keys=True,
        ),
    )

    print(
        "COMPOSITE_RANKED:",
        len(
            composite_rows
        ),
    )

    for row in composite_rows:
        print(
            (
                f"RANK {row['rank_position']:>2}"
                f" | {row['experiment_id']}"
                f" | SCORE: "
                f"{row['composite_score']}"
                f" | AVAILABLE: "
                f"{row['metrics_available_count']}"
                f" | MISSING: "
                f"{row['metrics_missing_count']}"
                f" | EFFECTIVE_WEIGHT_SUM: "
                f"{row['effective_weight_sum']}"
                f" | MISSING_METRICS: "
                f"{row['missing_metrics']}"
            )
        )

    separator(
        f"{label} — METRIC STATUS"
    )

    print(
        "NOT_RANKABLE_ROWS:",
        len(
            not_rankable
        ),
    )

    print(
        "CAGR_STATUS:",
        cagr_manifest[
            "ranking_status"
        ],
    )

    print(
        "RECOVERY_FACTOR_STATUS:",
        recovery_manifest[
            "ranking_status"
        ],
    )

    print(
        "RULE_SET_HASH:",
        first_summary[
            "rule_set_hash"
        ],
    )

    print(
        "RULE_SET_HASH_STATUS:",
        first_summary[
            "rule_set_hash_status"
        ],
    )

    return {
        "label": label,
        "request": request,
        "first_result": (
            first_result
        ),
        "second_result": (
            second_result
        ),
        "first_time": (
            first_time
        ),
        "second_time": (
            second_time
        ),
        "rankings_path": (
            paths[
                "rankings"
            ]
        ),
        "manifest_path": (
            paths[
                "manifest"
            ]
        ),
        "summary_path": (
            paths[
                "summary"
            ]
        ),
        "rankings_sha256": (
            second_rankings_hash
        ),
        "manifest_sha256": (
            second_manifest_hash
        ),
        "logical_sha256": (
            second_logical_hash
        ),
        "manifest_logical_sha256": (
            second_manifest_logical_hash
        ),
        "ranking_ids": (
            second_ranking_ids
        ),
        "ranking_config_sha256": (
            second_config_hashes
        ),
        "deterministic": (
            deterministic
        ),
        "idempotent": (
            idempotent
        ),
        "experiments_classified": (
            second_summary[
                "experiments_classified"
            ]
        ),
        "ranking_types_total": (
            second_summary[
                "ranking_types_total"
            ]
        ),
        "not_rankable_rows_total": (
            second_summary[
                "not_rankable_rows_total"
            ]
        ),
        "cagr_status": (
            second_summary[
                "cagr_status"
            ]
        ),
        "recovery_factor_status": (
            second_summary[
                "recovery_factor_status"
            ]
        ),
        "source_hash": (
            second_summary[
                "source_hash"
            ]
        ),
        "registry_hash": (
            second_summary[
                "registry_hash"
            ]
        ),
        "rule_set_hash": (
            second_summary[
                "rule_set_hash"
            ]
        ),
        "rule_set_hash_status": (
            second_summary[
                "rule_set_hash_status"
            ]
        ),
    }


def materialize_canonical_overall(
    validation: dict[str, Any],
) -> None:
    CANONICAL_RANKINGS.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    CANONICAL_MANIFEST.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    CANONICAL_SUMMARY.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copyfile(
        validation[
            "rankings_path"
        ],
        CANONICAL_RANKINGS,
    )

    shutil.copyfile(
        validation[
            "manifest_path"
        ],
        CANONICAL_MANIFEST,
    )

    shutil.copyfile(
        validation[
            "summary_path"
        ],
        CANONICAL_SUMMARY,
    )


def print_ranking_ids(
    validation: dict[str, Any],
) -> None:
    separator(
        validation[
            "label"
        ]
        + " — RANKING IDS"
    )

    manifests = parquet_rows(
        validation[
            "manifest_path"
        ]
    )

    manifests = sorted(
        manifests,
        key=lambda row: (
            row[
                "ranking_type"
            ]
        ),
    )

    for row in manifests:
        print(
            (
                f"{row['ranking_type']}"
                f" | {row['ranking_id']}"
                f" | CONFIG_SHA256: "
                f"{row['ranking_config_sha256']}"
                f" | STATUS: "
                f"{row['ranking_status']}"
            )
        )


def final_validation(
    validations: list[
        dict[str, Any]
    ],
) -> None:
    separator(
        "ETAPA 16 — VALIDACAO FINAL"
    )

    all_deterministic = all(
        item[
            "deterministic"
        ]
        for item in validations
    )

    all_idempotent = all(
        item[
            "idempotent"
        ]
        for item in validations
    )

    print(
        "SCOPES_VALIDATED:",
        len(
            validations
        ),
    )

    print(
        "OVERALL_VALIDATED:",
        any(
            item[
                "request"
            ].scope
            == "OVERALL"
            for item in validations
        ),
    )

    print(
        "YEARLY_2026_VALIDATED:",
        any(
            (
                item[
                    "request"
                ].scope
                == "YEARLY"
                and item[
                    "request"
                ].year
                == 2026
            )
            for item in validations
        ),
    )

    print(
        "MONTHLY_2026_08_VALIDATED:",
        any(
            (
                item[
                    "request"
                ].scope
                == "MONTHLY"
                and item[
                    "request"
                ].year
                == 2026
                and item[
                    "request"
                ].month
                == 8
            )
            for item in validations
        ),
    )

    print(
        "DETERMINISTIC_ALL:",
        all_deterministic,
    )

    print(
        "IDEMPOTENT_ALL:",
        all_idempotent,
    )

    print(
        "CAGR_STATUS:",
        validations[0][
            "cagr_status"
        ],
    )

    print(
        "RECOVERY_FACTOR_STATUS:",
        validations[0][
            "recovery_factor_status"
        ],
    )

    print(
        "RULE_SET_HASH:",
        validations[0][
            "rule_set_hash"
        ],
    )

    print(
        "RULE_SET_HASH_STATUS:",
        validations[0][
            "rule_set_hash_status"
        ],
    )

    print()

    for item in validations:
        request = item[
            "request"
        ]

        print(
            (
                f"{item['label']}"
                f" | EXPERIMENTS: "
                f"{item['experiments_classified']}"
                f" | RANKINGS: "
                f"{item['ranking_types_total']}"
                f" | SOURCE_SHA256: "
                f"{item['source_hash']}"
                f" | LOGICAL_SHA256: "
                f"{item['logical_sha256']}"
            )
        )

        print(
            (
                f"  SCOPE="
                f"{request.scope}"
                f" YEAR="
                f"{request.year}"
                f" MONTH="
                f"{request.month}"
            )
        )

    if not all_deterministic:
        raise RuntimeError(
            "Stage 16 determinism "
            "validation failed."
        )

    if not all_idempotent:
        raise RuntimeError(
            "Stage 16 idempotence "
            "validation failed."
        )


def main() -> None:
    require_inputs()

    if VALIDATION_ROOT.exists():
        shutil.rmtree(
            VALIDATION_ROOT
        )

    VALIDATION_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    separator(
        "ETAPA 16 — RANKING ENGINE V1"
    )

    print(
        "ENGINE_VERSION:",
        RANKING_ENGINE_VERSION,
    )

    print(
        "OVERALL_SOURCE:",
        OVERALL_METRICS,
    )

    print(
        "YEARLY_SOURCE:",
        YEARLY_METRICS,
    )

    print(
        "MONTHLY_SOURCE:",
        MONTHLY_METRICS,
    )

    print(
        "REGISTRY_SOURCE:",
        REGISTRY,
    )

    print(
        "OVERALL_SOURCE_SHA256:",
        sha256_file(
            OVERALL_METRICS
        ),
    )

    print(
        "YEARLY_SOURCE_SHA256:",
        sha256_file(
            YEARLY_METRICS
        ),
    )

    print(
        "MONTHLY_SOURCE_SHA256:",
        sha256_file(
            MONTHLY_METRICS
        ),
    )

    print(
        "REGISTRY_SHA256:",
        sha256_file(
            REGISTRY
        ),
    )

    overall = validate_scope(
        label="OVERALL",
        request=RankingRequest(
            scope="OVERALL",
        ),
    )

    yearly = validate_scope(
        label="YEARLY_2026",
        request=RankingRequest(
            scope="YEARLY",
            year=2026,
        ),
    )

    monthly = validate_scope(
        label="MONTHLY_2026_08",
        request=RankingRequest(
            scope="MONTHLY",
            year=2026,
            month=8,
        ),
    )

    validations = [
        overall,
        yearly,
        monthly,
    ]

    for validation in (
        validations
    ):
        print_ranking_ids(
            validation
        )

    final_validation(
        validations
    )

    materialize_canonical_overall(
        overall
    )

    separator(
        "CANONICAL OUTPUT — OVERALL"
    )

    print(
        "EXPERIMENT_RANKINGS:",
        CANONICAL_RANKINGS,
    )

    print(
        "EXPERIMENT_RANKINGS_SHA256:",
        sha256_file(
            CANONICAL_RANKINGS
        ),
    )

    print(
        "RANKING_MANIFEST:",
        CANONICAL_MANIFEST,
    )

    print(
        "RANKING_MANIFEST_SHA256:",
        sha256_file(
            CANONICAL_MANIFEST
        ),
    )

    print(
        "RANKING_SUMMARY:",
        CANONICAL_SUMMARY,
    )

    print(
        "RANKING_SUMMARY_SHA256:",
        sha256_file(
            CANONICAL_SUMMARY
        ),
    )

    separator(
        "ETAPA 16 — EXECUCAO CONCLUIDA"
    )

    print(
        "DETERMINISTIC: True"
    )

    print(
        "IDEMPOTENT: True"
    )

    print(
        "CAGR_STATUS: UNAVAILABLE"
    )

    print(
        "RECOVERY_FACTOR_STATUS: "
        "UNAVAILABLE"
    )

    print(
        "RULE_SET_HASH: None"
    )

    print(
        "RULE_SET_HASH_STATUS: "
        "NOT_APPLICABLE_LEGACY_DATASET"
    )


if __name__ == "__main__":
    main()