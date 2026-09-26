from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


RANKING_ENGINE_VERSION = "ranking-engine-v1"


VALID_SCOPES = {
    "OVERALL",
    "YEARLY",
    "MONTHLY",
}


LEGACY_RULE_SET_STATUS = (
    "NOT_APPLICABLE_LEGACY_DATASET"
)


RANKING_METRICS = {
    "PROFIT_FACTOR": {
        "column": "profit_factor",
        "higher_is_better": True,
    },
    "EXPECTANCY": {
        "column": "expectancy_points_per_trade",
        "higher_is_better": True,
    },
    "NET_POINTS": {
        "column": "total_weighted_points",
        "higher_is_better": True,
    },
    "WIN_RATE": {
        "column": "win_rate_pct",
        "higher_is_better": True,
    },
    "AVERAGE_TRADE": {
        "column": "average_weighted_points",
        "higher_is_better": True,
    },
    "MAX_DRAWDOWN": {
        "column": "max_drawdown_points",
        "higher_is_better": False,
    },
    "RECOVERY_FACTOR": {
        "column": "recovery_factor",
        "higher_is_better": True,
    },
    "PAYOFF": {
        "column": "payoff_ratio",
        "higher_is_better": True,
    },
    "NUMBER_OF_TRADES": {
        "column": "trade1_count",
        "higher_is_better": True,
    },
    "FREQUENCY": {
        "column": "trade_frequency_pct",
        "higher_is_better": True,
    },
    "CAGR": {
        "column": "cagr",
        "higher_is_better": True,
    },
}


COMPOSITE_ALLOWED_METRICS = {
    "EXPECTANCY": {
        "column": "expectancy_points_per_trade",
        "higher_is_better": True,
    },
    "PROFIT_FACTOR": {
        "column": "profit_factor",
        "higher_is_better": True,
    },
    "MAX_DRAWDOWN": {
        "column": "max_drawdown_points",
        "higher_is_better": False,
    },
    "NUMBER_OF_TRADES": {
        "column": "trade1_count",
        "higher_is_better": True,
    },
    "WIN_RATE": {
        "column": "win_rate_pct",
        "higher_is_better": True,
    },
    "NET_POINTS": {
        "column": "total_weighted_points",
        "higher_is_better": True,
    },
    "AVERAGE_TRADE": {
        "column": "average_weighted_points",
        "higher_is_better": True,
    },
    "PAYOFF": {
        "column": "payoff_ratio",
        "higher_is_better": True,
    },
    "FREQUENCY": {
        "column": "trade_frequency_pct",
        "higher_is_better": True,
    },
    "RECOVERY_FACTOR": {
        "column": "recovery_factor",
        "higher_is_better": True,
    },
    "CAGR": {
        "column": "cagr",
        "higher_is_better": True,
    },
}


RANKING_SCHEMA = pa.schema(
    [
        ("ranking_id", pa.string()),
        ("ranking_type", pa.string()),
        ("scope", pa.string()),
        ("year", pa.int64()),
        ("month", pa.int64()),
        ("experiment_id", pa.string()),
        ("config_sha256", pa.string()),
        ("family", pa.string()),
        ("generation", pa.int64()),
        ("registry_status", pa.string()),
        ("ranking_status", pa.string()),
        ("rank_position", pa.int64()),
        ("metric_name", pa.string()),
        ("metric_value", pa.float64()),
        ("trade_count", pa.int64()),
        ("sessions_total", pa.int64()),
        ("max_drawdown_points", pa.float64()),
        ("composite_score", pa.float64()),
        ("metrics_available_count", pa.int64()),
        ("metrics_missing_count", pa.int64()),
        ("effective_weight_sum", pa.float64()),
        (
            "missing_metrics",
            pa.list_(pa.string()),
        ),
        ("source_dataset", pa.string()),
        ("source_hash", pa.string()),
        ("analytics_hash", pa.string()),
        ("registry_hash", pa.string()),
        ("rule_set_hash", pa.string()),
        ("rule_set_hash_status", pa.string()),
        ("ranking_config_sha256", pa.string()),
        ("logical_row_sha256", pa.string()),
        ("created_at", pa.string()),
        ("engine_version", pa.string()),
    ]
)


MANIFEST_SCHEMA = pa.schema(
    [
        ("ranking_id", pa.string()),
        ("ranking_type", pa.string()),
        ("scope", pa.string()),
        ("year", pa.int64()),
        ("month", pa.int64()),
        ("filters_json", pa.string()),
        ("weights_json", pa.string()),
        ("source_dataset", pa.string()),
        ("source_hash", pa.string()),
        ("analytics_hash", pa.string()),
        ("registry_hash", pa.string()),
        ("rule_set_hash", pa.string()),
        ("rule_set_hash_status", pa.string()),
        ("ranking_config_sha256", pa.string()),
        ("candidate_count", pa.int64()),
        ("rankable_count", pa.int64()),
        ("not_rankable_count", pa.int64()),
        ("ranking_status", pa.string()),
        ("logical_ranking_sha256", pa.string()),
        ("created_at", pa.string()),
        ("engine_version", pa.string()),
    ]
)


@dataclass(frozen=True)
class RankingRequest:
    scope: str = "OVERALL"
    year: int | None = None
    month: int | None = None
    family: str | None = None
    generation: int | None = None
    registry_status: str | None = None
    min_trades: int | None = None
    min_sessions: int | None = None
    min_profit_factor: float | None = None
    max_drawdown: float | None = None
    min_expectancy: float | None = None
    min_win_rate: float | None = None


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
            digest.update(chunk)

    return digest.hexdigest()


def _is_number(
    value: Any,
) -> bool:
    if isinstance(
        value,
        bool,
    ):
        return False

    if not isinstance(
        value,
        (int, float),
    ):
        return False

    return math.isfinite(
        float(value)
    )


def _optional_float(
    value: Any,
) -> float | None:
    if not _is_number(value):
        return None

    return float(value)


def _optional_int(
    value: Any,
) -> int | None:
    if value is None:
        return None

    return int(value)


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


def validate_request(
    request: RankingRequest,
) -> None:
    if request.scope not in VALID_SCOPES:
        raise ValueError(
            "Invalid ranking scope: "
            f"{request.scope}"
        )

    if request.scope == "OVERALL":
        if (
            request.year is not None
            or request.month is not None
        ):
            raise ValueError(
                "OVERALL cannot define "
                "year or month."
            )

    elif request.scope == "YEARLY":
        if request.year is None:
            raise ValueError(
                "YEARLY requires year."
            )

        if request.month is not None:
            raise ValueError(
                "YEARLY cannot define month."
            )

    elif request.scope == "MONTHLY":
        if (
            request.year is None
            or request.month is None
        ):
            raise ValueError(
                "MONTHLY requires "
                "year and month."
            )

        if not (
            1
            <= int(request.month)
            <= 12
        ):
            raise ValueError(
                "month must be between "
                "1 and 12."
            )


def source_path_for_scope(
    *,
    request: RankingRequest,
    overall_path: str | Path,
    yearly_path: str | Path,
    monthly_path: str | Path,
) -> Path:
    validate_request(
        request
    )

    if request.scope == "OVERALL":
        return Path(
            overall_path
        )

    if request.scope == "YEARLY":
        return Path(
            yearly_path
        )

    return Path(
        monthly_path
    )


def request_filters(
    request: RankingRequest,
) -> dict[str, Any]:
    return {
        "family": (
            request.family
        ),
        "generation": (
            request.generation
        ),
        "registry_status": (
            request.registry_status
        ),
        "min_trades": (
            request.min_trades
        ),
        "min_sessions": (
            request.min_sessions
        ),
        "min_profit_factor": (
            request.min_profit_factor
        ),
        "max_drawdown": (
            request.max_drawdown
        ),
        "min_expectancy": (
            request.min_expectancy
        ),
        "min_win_rate": (
            request.min_win_rate
        ),
    }


def validate_weights(
    weights: dict[str, float],
) -> None:
    if not weights:
        raise ValueError(
            "Composite weights "
            "cannot be empty."
        )

    total = 0.0

    for metric, weight in (
        weights.items()
    ):
        if (
            metric
            not in COMPOSITE_ALLOWED_METRICS
        ):
            raise ValueError(
                "Unsupported composite "
                f"metric: {metric}"
            )

        if (
            not _is_number(weight)
            or float(weight) <= 0
        ):
            raise ValueError(
                "Composite weights "
                "must be positive."
            )

        total += float(
            weight
        )

    if total <= 0:
        raise ValueError(
            "Composite weight sum "
            "must be positive."
        )


def normalized_weights(
    weights: dict[str, float],
) -> dict[str, float]:
    validate_weights(
        weights
    )

    total = sum(
        float(value)
        for value in weights.values()
    )

    return {
        key: (
            float(value)
            / total
        )
        for key, value in sorted(
            weights.items()
        )
    }


def _join_registry(
    *,
    metric_rows: list[
        dict[str, Any]
    ],
    registry_rows: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:
    registry_by_id = {
        row["experiment_id"]: row
        for row in registry_rows
    }

    joined = []

    for metric_row in metric_rows:
        experiment_id = (
            metric_row[
                "experiment_id"
            ]
        )

        registry_row = (
            registry_by_id.get(
                experiment_id
            )
        )

        if registry_row is None:
            raise RuntimeError(
                "Metric experiment "
                "missing from Registry: "
                f"{experiment_id}"
            )

        metric_hash = (
            metric_row.get(
                "config_sha256"
            )
        )

        registry_hash = (
            registry_row.get(
                "config_sha256"
            )
        )

        if (
            metric_hash
            and registry_hash
            and metric_hash
            != registry_hash
        ):
            raise RuntimeError(
                "Config hash mismatch "
                f"for {experiment_id}."
            )

        joined_row = dict(
            metric_row
        )

        joined_row[
            "family"
        ] = registry_row.get(
            "family"
        )

        joined_row[
            "generation"
        ] = registry_row.get(
            "generation"
        )

        joined_row[
            "registry_status"
        ] = registry_row.get(
            "status"
        )

        joined.append(
            joined_row
        )

    return joined


def _filter_temporal_scope(
    *,
    rows: list[
        dict[str, Any]
    ],
    request: RankingRequest,
) -> list[dict[str, Any]]:
    if request.scope == "OVERALL":
        return list(rows)

    if request.scope == "YEARLY":
        return [
            row
            for row in rows
            if row.get("year")
            == request.year
        ]

    return [
        row
        for row in rows
        if (
            row.get("year")
            == request.year
            and row.get("month")
            == request.month
        )
    ]


def _passes_numeric_min(
    row: dict[str, Any],
    field: str,
    minimum: float | int | None,
) -> bool:
    if minimum is None:
        return True

    value = row.get(
        field
    )

    if not _is_number(value):
        return False

    return (
        float(value)
        >= float(minimum)
    )


def _passes_numeric_max(
    row: dict[str, Any],
    field: str,
    maximum: float | int | None,
) -> bool:
    if maximum is None:
        return True

    value = row.get(
        field
    )

    if not _is_number(value):
        return False

    return (
        float(value)
        <= float(maximum)
    )


def apply_filters(
    *,
    rows: list[
        dict[str, Any]
    ],
    request: RankingRequest,
) -> list[dict[str, Any]]:
    filtered = []

    for row in rows:
        if (
            request.family is not None
            and row.get(
                "family"
            )
            != request.family
        ):
            continue

        if (
            request.generation
            is not None
            and row.get(
                "generation"
            )
            != request.generation
        ):
            continue

        if (
            request.registry_status
            is not None
            and row.get(
                "registry_status"
            )
            != request.registry_status
        ):
            continue

        if not _passes_numeric_min(
            row,
            "trade1_count",
            request.min_trades,
        ):
            continue

        if not _passes_numeric_min(
            row,
            "sessions_total",
            request.min_sessions,
        ):
            continue

        if not _passes_numeric_min(
            row,
            "profit_factor",
            request.min_profit_factor,
        ):
            continue

        if not _passes_numeric_max(
            row,
            "max_drawdown_points",
            request.max_drawdown,
        ):
            continue

        if not _passes_numeric_min(
            row,
            "expectancy_points_per_trade",
            request.min_expectancy,
        ):
            continue

        if not _passes_numeric_min(
            row,
            "win_rate_pct",
            request.min_win_rate,
        ):
            continue

        filtered.append(
            row
        )

    return sorted(
        filtered,
        key=lambda row: (
            row[
                "experiment_id"
            ]
        ),
    )


def ranking_config_payload(
    *,
    ranking_type: str,
    request: RankingRequest,
    weights: dict[
        str,
        float,
    ] | None,
    source_hash: str,
) -> dict[str, Any]:
    return {
        "engine_version": (
            RANKING_ENGINE_VERSION
        ),
        "ranking_type": (
            ranking_type
        ),
        "scope": (
            request.scope
        ),
        "year": (
            request.year
        ),
        "month": (
            request.month
        ),
        "filters": (
            request_filters(
                request
            )
        ),
        "weights": (
            normalized_weights(
                weights
            )
            if weights
            else None
        ),
        "source_hash": (
            source_hash
        ),
    }


def ranking_config_sha256(
    *,
    ranking_type: str,
    request: RankingRequest,
    weights: dict[
        str,
        float,
    ] | None,
    source_hash: str,
) -> str:
    return _sha256_text(
        _canonical_json(
            ranking_config_payload(
                ranking_type=(
                    ranking_type
                ),
                request=request,
                weights=weights,
                source_hash=(
                    source_hash
                ),
            )
        )
    )


def build_ranking_id(
    *,
    ranking_type: str,
    ranking_config_hash: str,
) -> str:
    prefix = (
        ranking_type
        .replace("_", "-")
    )

    return (
        "RANK-"
        f"{prefix}-"
        f"{ranking_config_hash[:20]}"
    )


def _tie_break_key(
    row: dict[str, Any],
) -> tuple[
    float,
    float,
    str,
]:
    trades = row.get(
        "trade1_count"
    )

    drawdown = row.get(
        "max_drawdown_points"
    )

    trade_value = (
        float(trades)
        if _is_number(trades)
        else -math.inf
    )

    drawdown_value = (
        float(drawdown)
        if _is_number(drawdown)
        else math.inf
    )

    return (
        -trade_value,
        drawdown_value,
        str(
            row[
                "experiment_id"
            ]
        ),
    )


def _individual_sort_key(
    *,
    row: dict[str, Any],
    metric_column: str,
    higher_is_better: bool,
) -> tuple[Any, ...]:
    value = float(
        row[
            metric_column
        ]
    )

    primary = (
        -value
        if higher_is_better
        else value
    )

    return (
        primary,
        *_tie_break_key(
            row
        ),
    )


def _logical_row_sha256(
    row: dict[str, Any],
) -> str:
    payload = {
        key: value
        for key, value in row.items()
        if key not in (
            "created_at",
            "logical_row_sha256",
        )
    }

    return _sha256_text(
        _canonical_json(
            payload
        )
    )


def _base_output_row(
    *,
    source_row: dict[str, Any],
    ranking_id: str,
    ranking_type: str,
    request: RankingRequest,
    source_dataset: str,
    source_hash: str,
    registry_hash: str,
    ranking_config_hash: str,
    created_at: str,
) -> dict[str, Any]:
    return {
        "ranking_id": (
            ranking_id
        ),
        "ranking_type": (
            ranking_type
        ),
        "scope": (
            request.scope
        ),
        "year": (
            request.year
        ),
        "month": (
            request.month
        ),
        "experiment_id": (
            source_row[
                "experiment_id"
            ]
        ),
        "config_sha256": (
            source_row.get(
                "config_sha256"
            )
        ),
        "family": (
            source_row.get(
                "family"
            )
        ),
        "generation": (
            _optional_int(
                source_row.get(
                    "generation"
                )
            )
        ),
        "registry_status": (
            source_row.get(
                "registry_status"
            )
        ),
        "ranking_status": None,
        "rank_position": None,
        "metric_name": None,
        "metric_value": None,
        "trade_count": (
            _optional_int(
                source_row.get(
                    "trade1_count"
                )
            )
        ),
        "sessions_total": (
            _optional_int(
                source_row.get(
                    "sessions_total"
                )
            )
        ),
        "max_drawdown_points": (
            _optional_float(
                source_row.get(
                    "max_drawdown_points"
                )
            )
        ),
        "composite_score": None,
        "metrics_available_count": None,
        "metrics_missing_count": None,
        "effective_weight_sum": None,
        "missing_metrics": [],
        "source_dataset": (
            source_dataset
        ),
        "source_hash": (
            source_hash
        ),
        "analytics_hash": (
            source_hash
        ),
        "registry_hash": (
            registry_hash
        ),
        "rule_set_hash": None,
        "rule_set_hash_status": (
            LEGACY_RULE_SET_STATUS
        ),
        "ranking_config_sha256": (
            ranking_config_hash
        ),
        "logical_row_sha256": None,
        "created_at": (
            created_at
        ),
        "engine_version": (
            RANKING_ENGINE_VERSION
        ),
    }


def build_individual_ranking(
    *,
    ranking_type: str,
    rows: list[
        dict[str, Any]
    ],
    request: RankingRequest,
    source_dataset: str,
    source_hash: str,
    registry_hash: str,
    created_at: str,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    definition = (
        RANKING_METRICS[
            ranking_type
        ]
    )

    metric_column = (
        definition[
            "column"
        ]
    )

    higher_is_better = bool(
        definition[
            "higher_is_better"
        ]
    )

    config_hash = (
        ranking_config_sha256(
            ranking_type=(
                ranking_type
            ),
            request=request,
            weights=None,
            source_hash=(
                source_hash
            ),
        )
    )

    ranking_id = (
        build_ranking_id(
            ranking_type=(
                ranking_type
            ),
            ranking_config_hash=(
                config_hash
            ),
        )
    )

    metric_available = (
        metric_column
        in (
            rows[0].keys()
            if rows
            else []
        )
    )

    if (
        ranking_type
        in (
            "CAGR",
            "RECOVERY_FACTOR",
        )
        and not metric_available
    ):
        manifest = {
            "ranking_id": ranking_id,
            "ranking_type": (
                ranking_type
            ),
            "scope": (
                request.scope
            ),
            "year": (
                request.year
            ),
            "month": (
                request.month
            ),
            "filters_json": (
                _canonical_json(
                    request_filters(
                        request
                    )
                )
            ),
            "weights_json": None,
            "source_dataset": (
                source_dataset
            ),
            "source_hash": (
                source_hash
            ),
            "analytics_hash": (
                source_hash
            ),
            "registry_hash": (
                registry_hash
            ),
            "rule_set_hash": None,
            "rule_set_hash_status": (
                LEGACY_RULE_SET_STATUS
            ),
            "ranking_config_sha256": (
                config_hash
            ),
            "candidate_count": (
                len(rows)
            ),
            "rankable_count": 0,
            "not_rankable_count": (
                len(rows)
            ),
            "ranking_status": (
                "UNAVAILABLE"
            ),
            "logical_ranking_sha256": (
                _sha256_text(
                    _canonical_json(
                        {
                            "ranking_id":
                                ranking_id,
                            "status":
                                "UNAVAILABLE",
                        }
                    )
                )
            ),
            "created_at": (
                created_at
            ),
            "engine_version": (
                RANKING_ENGINE_VERSION
            ),
        }

        return (
            [],
            manifest,
        )

    rankable = [
        row
        for row in rows
        if _is_number(
            row.get(
                metric_column
            )
        )
    ]

    not_rankable = [
        row
        for row in rows
        if not _is_number(
            row.get(
                metric_column
            )
        )
    ]

    ordered_rankable = sorted(
        rankable,
        key=lambda row: (
            _individual_sort_key(
                row=row,
                metric_column=(
                    metric_column
                ),
                higher_is_better=(
                    higher_is_better
                ),
            )
        ),
    )

    output_rows = []

    for position, source_row in enumerate(
        ordered_rankable,
        start=1,
    ):
        row = _base_output_row(
            source_row=source_row,
            ranking_id=ranking_id,
            ranking_type=(
                ranking_type
            ),
            request=request,
            source_dataset=(
                source_dataset
            ),
            source_hash=(
                source_hash
            ),
            registry_hash=(
                registry_hash
            ),
            ranking_config_hash=(
                config_hash
            ),
            created_at=(
                created_at
            ),
        )

        row[
            "ranking_status"
        ] = "RANKED"

        row[
            "rank_position"
        ] = position

        row[
            "metric_name"
        ] = metric_column

        row[
            "metric_value"
        ] = float(
            source_row[
                metric_column
            ]
        )

        row[
            "logical_row_sha256"
        ] = _logical_row_sha256(
            row
        )

        output_rows.append(
            row
        )

    for source_row in sorted(
        not_rankable,
        key=lambda row: (
            row[
                "experiment_id"
            ]
        ),
    ):
        row = _base_output_row(
            source_row=source_row,
            ranking_id=ranking_id,
            ranking_type=(
                ranking_type
            ),
            request=request,
            source_dataset=(
                source_dataset
            ),
            source_hash=(
                source_hash
            ),
            registry_hash=(
                registry_hash
            ),
            ranking_config_hash=(
                config_hash
            ),
            created_at=(
                created_at
            ),
        )

        row[
            "ranking_status"
        ] = "NOT_RANKABLE"

        row[
            "metric_name"
        ] = metric_column

        row[
            "logical_row_sha256"
        ] = _logical_row_sha256(
            row
        )

        output_rows.append(
            row
        )

    logical_payload = [
        {
            key: value
            for key, value
            in row.items()
            if key
            not in (
                "created_at",
            )
        }
        for row in output_rows
    ]

    logical_hash = (
        _sha256_text(
            _canonical_json(
                logical_payload
            )
        )
    )

    manifest = {
        "ranking_id": ranking_id,
        "ranking_type": (
            ranking_type
        ),
        "scope": (
            request.scope
        ),
        "year": (
            request.year
        ),
        "month": (
            request.month
        ),
        "filters_json": (
            _canonical_json(
                request_filters(
                    request
                )
            )
        ),
        "weights_json": None,
        "source_dataset": (
            source_dataset
        ),
        "source_hash": (
            source_hash
        ),
        "analytics_hash": (
            source_hash
        ),
        "registry_hash": (
            registry_hash
        ),
        "rule_set_hash": None,
        "rule_set_hash_status": (
            LEGACY_RULE_SET_STATUS
        ),
        "ranking_config_sha256": (
            config_hash
        ),
        "candidate_count": (
            len(rows)
        ),
        "rankable_count": (
            len(rankable)
        ),
        "not_rankable_count": (
            len(not_rankable)
        ),
        "ranking_status": (
            "AVAILABLE"
        ),
        "logical_ranking_sha256": (
            logical_hash
        ),
        "created_at": (
            created_at
        ),
        "engine_version": (
            RANKING_ENGINE_VERSION
        ),
    }

    return (
        output_rows,
        manifest,
    )


def _min_max_values(
    *,
    rows: list[
        dict[str, Any]
    ],
    column: str,
) -> tuple[
    float | None,
    float | None,
]:
    values = [
        float(
            row[column]
        )
        for row in rows
        if _is_number(
            row.get(column)
        )
    ]

    if not values:
        return (
            None,
            None,
        )

    return (
        min(values),
        max(values),
    )


def _normalize_metric(
    *,
    value: float,
    minimum: float,
    maximum: float,
    higher_is_better: bool,
) -> float:
    if math.isclose(
        minimum,
        maximum,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        return 0.5

    normalized = (
        (
            float(value)
            - minimum
        )
        / (
            maximum
            - minimum
        )
    )

    if not higher_is_better:
        normalized = (
            1.0
            - normalized
        )

    return normalized


def build_composite_ranking(
    *,
    rows: list[
        dict[str, Any]
    ],
    request: RankingRequest,
    weights: dict[
        str,
        float,
    ],
    source_dataset: str,
    source_hash: str,
    registry_hash: str,
    created_at: str,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    normalized_config_weights = (
        normalized_weights(
            weights
        )
    )

    config_hash = (
        ranking_config_sha256(
            ranking_type=(
                "COMPOSITE_SCORE"
            ),
            request=request,
            weights=weights,
            source_hash=(
                source_hash
            ),
        )
    )

    ranking_id = (
        build_ranking_id(
            ranking_type=(
                "COMPOSITE_SCORE"
            ),
            ranking_config_hash=(
                config_hash
            ),
        )
    )

    bounds = {}

    for metric in (
        normalized_config_weights
    ):
        definition = (
            COMPOSITE_ALLOWED_METRICS[
                metric
            ]
        )

        column = (
            definition[
                "column"
            ]
        )

        bounds[
            metric
        ] = _min_max_values(
            rows=rows,
            column=column,
        )

    scored = []

    for source_row in rows:
        available = []
        missing = []

        for metric, configured_weight in (
            normalized_config_weights.items()
        ):
            definition = (
                COMPOSITE_ALLOWED_METRICS[
                    metric
                ]
            )

            column = (
                definition[
                    "column"
                ]
            )

            value = (
                source_row.get(
                    column
                )
            )

            (
                minimum,
                maximum,
            ) = bounds[
                metric
            ]

            if (
                not _is_number(value)
                or minimum is None
                or maximum is None
            ):
                missing.append(
                    metric
                )
                continue

            available.append(
                (
                    metric,
                    float(
                        configured_weight
                    ),
                    float(value),
                    float(minimum),
                    float(maximum),
                    bool(
                        definition[
                            "higher_is_better"
                        ]
                    ),
                )
            )

        available_weight_sum = sum(
            item[1]
            for item in available
        )

        if (
            not available
            or available_weight_sum <= 0
        ):
            score = None
            effective_weight_sum = 0.0

        else:
            score = 0.0

            for (
                _metric,
                configured_weight,
                value,
                minimum,
                maximum,
                higher_is_better,
            ) in available:
                normalized_metric = (
                    _normalize_metric(
                        value=value,
                        minimum=minimum,
                        maximum=maximum,
                        higher_is_better=(
                            higher_is_better
                        ),
                    )
                )

                effective_metric_weight = (
                    configured_weight
                    / available_weight_sum
                )

                score += (
                    normalized_metric
                    * effective_metric_weight
                )

            #
            # Os pesos disponíveis foram
            # renormalizados entre si.
            #
            # Portanto a soma efetiva
            # utilizada no Composite Score
            # é sempre 100%.
            #
            effective_weight_sum = 1.0

        scored.append(
            {
                "source_row": (
                    source_row
                ),
                "score": score,
                "available_count": (
                    len(available)
                ),
                "missing_count": (
                    len(missing)
                ),
                "effective_weight_sum": (
                    effective_weight_sum
                ),
                "missing_metrics": (
                    sorted(
                        missing
                    )
                ),
            }
        )

    rankable = [
        item
        for item in scored
        if _is_number(
            item[
                "score"
            ]
        )
    ]

    not_rankable = [
        item
        for item in scored
        if not _is_number(
            item[
                "score"
            ]
        )
    ]

    rankable = sorted(
        rankable,
        key=lambda item: (
            -float(
                item["score"]
            ),
            *_tie_break_key(
                item[
                    "source_row"
                ]
            ),
        ),
    )

    output_rows = []

    for position, item in enumerate(
        rankable,
        start=1,
    ):
        source_row = item[
            "source_row"
        ]

        row = _base_output_row(
            source_row=source_row,
            ranking_id=ranking_id,
            ranking_type=(
                "COMPOSITE_SCORE"
            ),
            request=request,
            source_dataset=(
                source_dataset
            ),
            source_hash=(
                source_hash
            ),
            registry_hash=(
                registry_hash
            ),
            ranking_config_hash=(
                config_hash
            ),
            created_at=(
                created_at
            ),
        )

        row[
            "ranking_status"
        ] = "RANKED"

        row[
            "rank_position"
        ] = position

        row[
            "metric_name"
        ] = "composite_score"

        row[
            "metric_value"
        ] = float(
            item[
                "score"
            ]
        )

        row[
            "composite_score"
        ] = float(
            item[
                "score"
            ]
        )

        row[
            "metrics_available_count"
        ] = int(
            item[
                "available_count"
            ]
        )

        row[
            "metrics_missing_count"
        ] = int(
            item[
                "missing_count"
            ]
        )

        row[
            "effective_weight_sum"
        ] = float(
            item[
                "effective_weight_sum"
            ]
        )

        row[
            "missing_metrics"
        ] = item[
            "missing_metrics"
        ]

        row[
            "logical_row_sha256"
        ] = _logical_row_sha256(
            row
        )

        output_rows.append(
            row
        )

    for item in sorted(
        not_rankable,
        key=lambda current: (
            current[
                "source_row"
            ][
                "experiment_id"
            ]
        ),
    ):
        source_row = item[
            "source_row"
        ]

        row = _base_output_row(
            source_row=source_row,
            ranking_id=ranking_id,
            ranking_type=(
                "COMPOSITE_SCORE"
            ),
            request=request,
            source_dataset=(
                source_dataset
            ),
            source_hash=(
                source_hash
            ),
            registry_hash=(
                registry_hash
            ),
            ranking_config_hash=(
                config_hash
            ),
            created_at=(
                created_at
            ),
        )

        row[
            "ranking_status"
        ] = "NOT_RANKABLE"

        row[
            "metric_name"
        ] = "composite_score"

        row[
            "metrics_available_count"
        ] = int(
            item[
                "available_count"
            ]
        )

        row[
            "metrics_missing_count"
        ] = int(
            item[
                "missing_count"
            ]
        )

        row[
            "effective_weight_sum"
        ] = float(
            item[
                "effective_weight_sum"
            ]
        )

        row[
            "missing_metrics"
        ] = item[
            "missing_metrics"
        ]

        row[
            "logical_row_sha256"
        ] = _logical_row_sha256(
            row
        )

        output_rows.append(
            row
        )

    logical_payload = [
        {
            key: value
            for key, value
            in row.items()
            if key != "created_at"
        }
        for row in output_rows
    ]

    logical_hash = (
        _sha256_text(
            _canonical_json(
                logical_payload
            )
        )
    )

    manifest = {
        "ranking_id": (
            ranking_id
        ),
        "ranking_type": (
            "COMPOSITE_SCORE"
        ),
        "scope": (
            request.scope
        ),
        "year": (
            request.year
        ),
        "month": (
            request.month
        ),
        "filters_json": (
            _canonical_json(
                request_filters(
                    request
                )
            )
        ),
        "weights_json": (
            _canonical_json(
                normalized_config_weights
            )
        ),
        "source_dataset": (
            source_dataset
        ),
        "source_hash": (
            source_hash
        ),
        "analytics_hash": (
            source_hash
        ),
        "registry_hash": (
            registry_hash
        ),
        "rule_set_hash": None,
        "rule_set_hash_status": (
            LEGACY_RULE_SET_STATUS
        ),
        "ranking_config_sha256": (
            config_hash
        ),
        "candidate_count": (
            len(rows)
        ),
        "rankable_count": (
            len(rankable)
        ),
        "not_rankable_count": (
            len(not_rankable)
        ),
        "ranking_status": (
            "AVAILABLE"
            if rows
            else "EMPTY"
        ),
        "logical_ranking_sha256": (
            logical_hash
        ),
        "created_at": (
            created_at
        ),
        "engine_version": (
            RANKING_ENGINE_VERSION
        ),
    }

    return (
        output_rows,
        manifest,
    )


def _preserve_created_at(
    *,
    manifests: list[
        dict[str, Any]
    ],
    existing_manifest_path: (
        str | Path
    ),
) -> list[dict[str, Any]]:
    path = Path(
        existing_manifest_path
    )

    if not path.exists():
        return manifests

    existing_rows = (
        pq.read_table(
            path
        ).to_pylist()
    )

    existing_by_id = {
        row["ranking_id"]: row
        for row in existing_rows
    }

    for row in manifests:
        existing = (
            existing_by_id.get(
                row[
                    "ranking_id"
                ]
            )
        )

        if existing is None:
            continue

        if (
            existing.get(
                "ranking_config_sha256"
            )
            == row.get(
                "ranking_config_sha256"
            )
        ):
            row[
                "created_at"
            ] = existing.get(
                "created_at"
            )

    return manifests


def run_ranking_engine(
    *,
    request: RankingRequest,
    composite_weights: dict[
        str,
        float,
    ],
    overall_metrics_path: str | Path = (
        "data/research/"
        "experiment_metrics.parquet"
    ),
    yearly_metrics_path: str | Path = (
        "data/research/"
        "experiment_metrics_yearly.parquet"
    ),
    monthly_metrics_path: str | Path = (
        "data/research/"
        "experiment_metrics_monthly.parquet"
    ),
    registry_path: str | Path = (
        "data/research/"
        "experiment_registry.parquet"
    ),
    rankings_path: str | Path = (
        "data/research/"
        "experiment_rankings.parquet"
    ),
    manifest_path: str | Path = (
        "data/research/"
        "ranking_manifest.parquet"
    ),
    summary_path: str | Path = (
        "data/reports/"
        "ranking_summary.json"
    ),
    created_at: str | None = None,
) -> dict[str, Any]:
    validate_request(
        request
    )

    validate_weights(
        composite_weights
    )

    if created_at is None:
        created_at = utc_now()

    source_path = (
        source_path_for_scope(
            request=request,
            overall_path=(
                overall_metrics_path
            ),
            yearly_path=(
                yearly_metrics_path
            ),
            monthly_path=(
                monthly_metrics_path
            ),
        )
    )

    source_table = (
        _read_table(
            source_path
        )
    )

    registry_table = (
        _read_table(
            registry_path
        )
    )

    source_hash = (
        sha256_file(
            source_path
        )
    )

    registry_hash = (
        sha256_file(
            registry_path
        )
    )

    metric_rows = (
        source_table.to_pylist()
    )

    registry_rows = (
        registry_table.to_pylist()
    )

    temporal_rows = (
        _filter_temporal_scope(
            rows=metric_rows,
            request=request,
        )
    )

    joined_rows = (
        _join_registry(
            metric_rows=(
                temporal_rows
            ),
            registry_rows=(
                registry_rows
            ),
        )
    )

    candidate_rows = (
        apply_filters(
            rows=joined_rows,
            request=request,
        )
    )

    all_ranking_rows = []
    manifests = []

    for ranking_type in (
        RANKING_METRICS
    ):
        rows, manifest = (
            build_individual_ranking(
                ranking_type=(
                    ranking_type
                ),
                rows=(
                    candidate_rows
                ),
                request=request,
                source_dataset=(
                    str(
                        source_path
                    )
                ),
                source_hash=(
                    source_hash
                ),
                registry_hash=(
                    registry_hash
                ),
                created_at=(
                    created_at
                ),
            )
        )

        all_ranking_rows.extend(
            rows
        )

        manifests.append(
            manifest
        )

    (
        composite_rows,
        composite_manifest,
    ) = build_composite_ranking(
        rows=candidate_rows,
        request=request,
        weights=(
            composite_weights
        ),
        source_dataset=str(
            source_path
        ),
        source_hash=source_hash,
        registry_hash=(
            registry_hash
        ),
        created_at=created_at,
    )

    all_ranking_rows.extend(
        composite_rows
    )

    manifests.append(
        composite_manifest
    )

    manifests = (
        _preserve_created_at(
            manifests=manifests,
            existing_manifest_path=(
                manifest_path
            ),
        )
    )

    created_by_ranking_id = {
        row[
            "ranking_id"
        ]: row[
            "created_at"
        ]
        for row in manifests
    }

    for row in all_ranking_rows:
        row[
            "created_at"
        ] = (
            created_by_ranking_id[
                row[
                    "ranking_id"
                ]
            ]
        )

        row[
            "logical_row_sha256"
        ] = _logical_row_sha256(
            row
        )

    all_ranking_rows = sorted(
        all_ranking_rows,
        key=lambda row: (
            row[
                "ranking_type"
            ],
            row[
                "rank_position"
            ]
            is None,
            (
                row[
                    "rank_position"
                ]
                if row[
                    "rank_position"
                ]
                is not None
                else 10**18
            ),
            row[
                "experiment_id"
            ],
        ),
    )

    manifests = sorted(
        manifests,
        key=lambda row: (
            row[
                "ranking_type"
            ]
        ),
    )

    rankings_path = (
        _write_rows(
            rows=(
                all_ranking_rows
            ),
            schema=(
                RANKING_SCHEMA
            ),
            path=(
                rankings_path
            ),
        )
    )

    manifest_path = (
        _write_rows(
            rows=manifests,
            schema=(
                MANIFEST_SCHEMA
            ),
            path=(
                manifest_path
            ),
        )
    )

    overall_logical_hash = (
        _sha256_text(
            _canonical_json(
                [
                    {
                        key: value
                        for key, value
                        in row.items()
                        if key
                        != "created_at"
                    }
                    for row
                    in all_ranking_rows
                ]
            )
        )
    )

    cagr_manifest = next(
        row
        for row in manifests
        if row[
            "ranking_type"
        ]
        == "CAGR"
    )

    recovery_manifest = next(
        row
        for row in manifests
        if row[
            "ranking_type"
        ]
        == "RECOVERY_FACTOR"
    )

    composite_manifest_row = next(
        row
        for row in manifests
        if row[
            "ranking_type"
        ]
        == "COMPOSITE_SCORE"
    )

    not_rankable_total = sum(
        1
        for row
        in all_ranking_rows
        if row[
            "ranking_status"
        ]
        == "NOT_RANKABLE"
    )

    ranked_total = sum(
        1
        for row
        in all_ranking_rows
        if row[
            "ranking_status"
        ]
        == "RANKED"
    )

    summary = {
        "engine_version": (
            RANKING_ENGINE_VERSION
        ),
        "scope": (
            request.scope
        ),
        "year": (
            request.year
        ),
        "month": (
            request.month
        ),
        "source_dataset": (
            str(
                source_path
            )
        ),
        "source_hash": (
            source_hash
        ),
        "analytics_hash": (
            source_hash
        ),
        "registry_hash": (
            registry_hash
        ),
        "rule_set_hash": None,
        "rule_set_hash_status": (
            LEGACY_RULE_SET_STATUS
        ),
        "filters": (
            request_filters(
                request
            )
        ),
        "composite_weights": (
            normalized_weights(
                composite_weights
            )
        ),
        "experiments_classified": (
            len(
                candidate_rows
            )
        ),
        "ranking_types_total": (
            len(
                manifests
            )
        ),
        "ranked_rows_total": (
            ranked_total
        ),
        "not_rankable_rows_total": (
            not_rankable_total
        ),
        "cagr_status": (
            cagr_manifest[
                "ranking_status"
            ]
        ),
        "recovery_factor_status": (
            recovery_manifest[
                "ranking_status"
            ]
        ),
        "composite_ranking_id": (
            composite_manifest_row[
                "ranking_id"
            ]
        ),
        "logical_rankings_sha256": (
            overall_logical_hash
        ),
        "experiment_rankings_sha256": (
            sha256_file(
                rankings_path
            )
        ),
        "ranking_manifest_sha256": (
            sha256_file(
                manifest_path
            )
        ),
        "ranking_ids": [
            row[
                "ranking_id"
            ]
            for row in manifests
        ],
        "ranking_config_sha256": {
            row[
                "ranking_type"
            ]: row[
                "ranking_config_sha256"
            ]
            for row in manifests
        },
        "created_at": (
            created_at
        ),
    }

    summary_path = Path(
        summary_path
    )

    summary_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_path.write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        "summary": summary,
        "ranking_rows": (
            all_ranking_rows
        ),
        "manifest_rows": (
            manifests
        ),
        "candidate_rows": (
            candidate_rows
        ),
        "rankings_path": str(
            rankings_path
        ),
        "manifest_path": str(
            manifest_path
        ),
        "summary_path": str(
            summary_path
        ),
    }