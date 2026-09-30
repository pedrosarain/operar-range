from __future__ import annotations

import json
from numbers import Real
from pathlib import Path
from typing import Any

import polars as pl

from operar_range.research_query_engine import (
    QUERY_ENGINE_VERSION,
)
from operar_range.research_workspace import (
    load_research_definition,
    load_research_manifest,
    research_paths,
)


COMPARISON_ENGINE_VERSION = (
    "research-comparison-engine-v1"
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
    "trade2_enabled",
    "trade2_management_mode",
    "trade2_stop_mode",
    "trade2_stop_points",
    "trade2_partial_1_mode",
    "trade2_partial_1_points",
    "trade2_partial_1_pct",
    "trade2_partial_2_mode",
    "trade2_partial_2_points",
    "trade2_partial_2_pct",
    "trade2_partial_3_mode",
    "trade2_partial_3_points",
    "trade2_partial_3_pct",
    "trade2_break_even_mode",
    "trade2_break_even_after_partial",
    "trade2_runner_mode",
    "trade2_runner_pct",
    "trade2_runner_rule",
    "trade2_final_target_mode",
    "trade2_final_target_points",
)


TRADE1_METRIC_FIELDS = (
    "sessions_total",
    "trade1_count",
    "no_trade1_count",
    "total_weighted_points",
    "consolidated_total_result_points",
    "winning_trades",
    "losing_trades",
    "breakeven_trades",
    "win_rate_pct",
    "loss_rate_pct",
    "profit_factor",
    "profit_factor_status",
    "payoff_ratio",
    "payoff_ratio_status",
    "expectancy_points_per_trade",
    "max_drawdown_points",
    "max_drawdown_start_date",
    "max_drawdown_end_date",
)


TRADE2_METRIC_FIELDS = (
    "sessions_total",
    "trade2_eligible_count",
    "trade2_occurred_count",
    "trade2_executed_count",
    "trade2_winning_count",
    "trade2_losing_count",
    "trade2_breakeven_count",
    "trade2_runner_count",
    "trade2_weighted_result_points",
    "trade2_total_position_points",
)


LIFECYCLE_METRIC_FIELDS = (
    "total_cycles",
    "cycles_with_trade2",
    "cycles_without_trade2",
    "trade2_pct",
    "recovered_cycle_count",
    "recovery_pct",
    "total_result_points",
    "expectancy_points_per_cycle",
    "winning_cycles",
    "losing_cycles",
    "breakeven_cycles",
    "win_rate_pct",
    "loss_rate_pct",
    "breakeven_rate_pct",
    "profit_factor",
    "profit_factor_status",
    "payoff_ratio",
    "payoff_ratio_status",
    "max_drawdown_points",
    "max_drawdown_start_date",
    "max_drawdown_end_date",
)


LIFECYCLE_COMPARISON_FIELDS = (
    "trade1_total_result_points",
    "consolidated_total_result_points",
    "difference_total_result_points",
    "trade1_expectancy_points",
    "consolidated_expectancy_points",
    "difference_expectancy_points",
    "trade1_profit_factor",
    "consolidated_profit_factor",
    "difference_profit_factor",
    "trade1_max_drawdown_points",
    "consolidated_max_drawdown_points",
    "difference_max_drawdown_points",
    "trade1_win_rate_pct",
    "consolidated_win_rate_pct",
    "difference_win_rate_pct",
)


def _read_rows(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    return (
        pl.scan_parquet(
            path
        )
        .collect(
            engine="streaming"
        )
        .to_dicts()
    )


def _safe_manifest(
    research_id: str,
) -> dict[str, Any]:
    try:
        return load_research_manifest(
            research_id
        )
    except FileNotFoundError:
        return {}


def _require_research(
    research_id: str,
) -> dict[str, Any]:
    paths = research_paths(
        research_id
    )

    if not paths[
        "root"
    ].exists():
        raise FileNotFoundError(
            f"Research not found: "
            f"{research_id}"
        )

    definition = (
        load_research_definition(
            research_id
        )
    )

    manifest = (
        _safe_manifest(
            research_id
        )
    )

    return {
        "research_id": research_id,
        "paths": paths,
        "definition": definition,
        "manifest": manifest,
    }


def _parse_config_json(
    value: Any,
) -> dict[str, Any]:
    if not value:
        return {}

    try:
        parsed = json.loads(
            str(value)
        )
    except Exception:
        return {}

    if not isinstance(
        parsed,
        dict,
    ):
        return {}

    return parsed


def _experiment_rows(
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    paths = context[
        "paths"
    ]

    valid = _read_rows(
        paths[
            "valid"
        ]
    )

    if valid:
        rows = [
            dict(
                row
            )
            for row in valid
        ]

    else:
        manifest_rows = (
            _read_rows(
                paths[
                    "experiment_manifest"
                ]
            )
        )

        rows = []

        for source in manifest_rows:
            row = dict(
                source
            )

            config = (
                _parse_config_json(
                    source.get(
                        "config_json"
                    )
                )
            )

            for field in CONFIG_FIELDS:
                if field not in row:
                    row[
                        field
                    ] = config.get(
                        field
                    )

            rows.append(
                row
            )

    rows.sort(
        key=lambda row: (
            str(
                row.get(
                    "experiment_id"
                )
                or ""
            ),
            str(
                row.get(
                    "config_sha256"
                )
                or ""
            ),
        )
    )

    return rows


def _research_metadata(
    context: dict[str, Any],
) -> dict[str, Any]:
    definition = context[
        "definition"
    ]

    manifest = context[
        "manifest"
    ]

    dataset_id = (
        manifest.get(
            "dataset_id"
        )
        or definition.get(
            "dataset_id"
        )
        or definition.get(
            "dataset_key"
        )
    )

    dataset_version = (
        manifest.get(
            "dataset_version"
        )
        or definition.get(
            "dataset_version"
        )
    )

    period_start = (
        definition.get(
            "period_start"
        )
    )

    period_end = (
        definition.get(
            "period_end"
        )
    )

    return {
        "research_id": (
            context[
                "research_id"
            ]
        ),
        "dataset_id": dataset_id,
        "dataset_version": (
            dataset_version
        ),
        "period_start": (
            period_start
        ),
        "period_end": (
            period_end
        ),
        "market": (
            definition.get(
                "market"
            )
            or manifest.get(
                "market"
            )
        ),
        "asset": (
            definition.get(
                "asset"
            )
            or manifest.get(
                "asset"
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
        "rules_version": (
            definition.get(
                "rules_version"
            )
            or manifest.get(
                "rules_version"
            )
        ),
        "status": (
            manifest.get(
                "status"
            )
            or definition.get(
                "status"
            )
            or definition.get(
                "definition_status"
            )
        ),
    }


def _rows_by_experiment(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in rows:
        experiment_id = row.get(
            "experiment_id"
        )

        if experiment_id is None:
            continue

        result[
            str(
                experiment_id
            )
        ] = row

    return result


def _rows_by_config(
    rows: list[dict[str, Any]],
) -> dict[
    str,
    list[dict[str, Any]],
]:
    result: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for row in rows:
        config_hash = row.get(
            "config_sha256"
        )

        if not config_hash:
            continue

        result.setdefault(
            str(
                config_hash
            ),
            [],
        ).append(
            row
        )

    for config_hash in result:
        result[
            config_hash
        ].sort(
            key=lambda row: str(
                row.get(
                    "experiment_id"
                )
                or ""
            )
        )

    return result


def _artifact_maps(
    context: dict[str, Any],
) -> dict[
    str,
    dict[str, dict[str, Any]],
]:
    paths = context[
        "paths"
    ]

    artifact_keys = (
        "metrics",
        "trade2_analytics",
        "consolidated_analytics",
        "lifecycle_comparison",
        "experiment_manifest",
    )

    result: dict[
        str,
        dict[str, dict[str, Any]],
    ] = {}

    for key in artifact_keys:
        rows = _read_rows(
            paths[
                key
            ]
        )

        result[
            key
        ] = _rows_by_experiment(
            rows
        )

    return result


def _selected(
    row: dict[str, Any] | None,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    if row is None:
        return {}

    return {
        field: row.get(
            field
        )
        for field in fields
    }


def _is_numeric(
    value: Any,
) -> bool:
    return (
        isinstance(
            value,
            Real,
        )
        and not isinstance(
            value,
            bool,
        )
    )


def _numeric_deltas(
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, float | None]:
    fields = sorted(
        set(
            left
        )
        | set(
            right
        )
    )

    result: dict[
        str,
        float | None,
    ] = {}

    for field in fields:
        left_value = left.get(
            field
        )

        right_value = right.get(
            field
        )

        if (
            _is_numeric(
                left_value
            )
            and _is_numeric(
                right_value
            )
        ):
            result[
                field
            ] = (
                float(
                    left_value
                )
                - float(
                    right_value
                )
            )

        else:
            result[
                field
            ] = None

    return result


def _experiment_summary(
    row: dict[str, Any],
) -> dict[str, Any]:
    return {
        "experiment_id": (
            row.get(
                "experiment_id"
            )
        ),
        "config_sha256": (
            row.get(
                "config_sha256"
            )
        ),
        "config_identity_version": (
            row.get(
                "config_identity_version"
            )
        ),
        "family": (
            row.get(
                "family"
            )
        ),
        "generation": (
            row.get(
                "generation"
            )
        ),
        "experiment_name": (
            row.get(
                "experiment_name"
            )
            or row.get(
                "name"
            )
        ),
    }


def _experiment_snapshot(
    *,
    context: dict[str, Any],
    artifact_maps: dict[
        str,
        dict[str, dict[str, Any]],
    ],
    experiment: dict[str, Any],
) -> dict[str, Any]:
    experiment_id = str(
        experiment[
            "experiment_id"
        ]
    )

    metrics = (
        artifact_maps[
            "metrics"
        ].get(
            experiment_id
        )
    )

    trade2 = (
        artifact_maps[
            "trade2_analytics"
        ].get(
            experiment_id
        )
    )

    consolidated = (
        artifact_maps[
            "consolidated_analytics"
        ].get(
            experiment_id
        )
    )

    lifecycle = (
        artifact_maps[
            "lifecycle_comparison"
        ].get(
            experiment_id
        )
    )

    experiment_manifest = (
        artifact_maps[
            "experiment_manifest"
        ].get(
            experiment_id
        )
    )

    analytics_version = None

    for row in (
        lifecycle,
        consolidated,
        trade2,
    ):
        if (
            row is not None
            and row.get(
                "analytics_version"
            )
        ):
            analytics_version = (
                row[
                    "analytics_version"
                ]
            )
            break

    motor_version = None
    rules_version = None

    for row in (
        metrics,
        consolidated,
        trade2,
        lifecycle,
        experiment_manifest,
        experiment,
    ):
        if row is None:
            continue

        if (
            motor_version is None
            and row.get(
                "motor_version"
            )
        ):
            motor_version = (
                row[
                    "motor_version"
                ]
            )

        if (
            rules_version is None
            and row.get(
                "rules_version"
            )
        ):
            rules_version = (
                row[
                    "rules_version"
                ]
            )

    config = {
        field: experiment.get(
            field
        )
        for field in CONFIG_FIELDS
        if field in experiment
    }

    return {
        "research": (
            _research_metadata(
                context
            )
        ),
        "identity": {
            "experiment_id": (
                experiment.get(
                    "experiment_id"
                )
            ),
            "config_sha256": (
                experiment.get(
                    "config_sha256"
                )
            ),
            "config_identity_version": (
                experiment.get(
                    "config_identity_version"
                )
            ),
            "motor_version": (
                motor_version
            ),
            "rules_version": (
                rules_version
            ),
            "analytics_version": (
                analytics_version
            ),
        },
        "configuration": config,
        "metrics": (
            _selected(
                metrics,
                TRADE1_METRIC_FIELDS,
            )
        ),
        "trade2_metrics": (
            _selected(
                trade2,
                TRADE2_METRIC_FIELDS,
            )
        ),
        "lifecycle_metrics": (
            _selected(
                consolidated,
                LIFECYCLE_METRIC_FIELDS,
            )
        ),
        "lifecycle_comparison": (
            _selected(
                lifecycle,
                LIFECYCLE_COMPARISON_FIELDS,
            )
        ),
    }


def _compare_snapshots(
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any]:
    return {
        "experiment_a": left,
        "experiment_b": right,
        "configuration_delta": (
            _numeric_deltas(
                left[
                    "configuration"
                ],
                right[
                    "configuration"
                ],
            )
        ),
        "metrics_delta": (
            _numeric_deltas(
                left[
                    "metrics"
                ],
                right[
                    "metrics"
                ],
            )
        ),
        "trade2_metrics_delta": (
            _numeric_deltas(
                left[
                    "trade2_metrics"
                ],
                right[
                    "trade2_metrics"
                ],
            )
        ),
        "lifecycle_metrics_delta": (
            _numeric_deltas(
                left[
                    "lifecycle_metrics"
                ],
                right[
                    "lifecycle_metrics"
                ],
            )
        ),
        "lifecycle_comparison_delta": (
            _numeric_deltas(
                left[
                    "lifecycle_comparison"
                ],
                right[
                    "lifecycle_comparison"
                ],
            )
        ),
    }


def compare_experiments(
    *,
    research_a_id: str,
    experiment_a_id: str,
    research_b_id: str,
    experiment_b_id: str,
) -> dict[str, Any]:
    context_a = _require_research(
        research_a_id
    )

    context_b = _require_research(
        research_b_id
    )

    experiments_a = _experiment_rows(
        context_a
    )

    experiments_b = _experiment_rows(
        context_b
    )

    by_id_a = _rows_by_experiment(
        experiments_a
    )

    by_id_b = _rows_by_experiment(
        experiments_b
    )

    if experiment_a_id not in by_id_a:
        raise ValueError(
            "Experiment not found in "
            "Research A: "
            f"{experiment_a_id}"
        )

    if experiment_b_id not in by_id_b:
        raise ValueError(
            "Experiment not found in "
            "Research B: "
            f"{experiment_b_id}"
        )

    metadata_a = (
        _research_metadata(
            context_a
        )
    )

    metadata_b = (
        _research_metadata(
            context_b
        )
    )

    artifacts_a = (
        _artifact_maps(
            context_a
        )
    )

    artifacts_b = (
        _artifact_maps(
            context_b
        )
    )

    snapshot_a = (
        _experiment_snapshot(
            context=context_a,
            artifact_maps=artifacts_a,
            experiment=(
                by_id_a[
                    experiment_a_id
                ]
            ),
        )
    )

    snapshot_b = (
        _experiment_snapshot(
            context=context_b,
            artifact_maps=artifacts_b,
            experiment=(
                by_id_b[
                    experiment_b_id
                ]
            ),
        )
    )

    config_a = (
        snapshot_a[
            "identity"
        ].get(
            "config_sha256"
        )
    )

    config_b = (
        snapshot_b[
            "identity"
        ].get(
            "config_sha256"
        )
    )

    return {
        "comparison_engine_version": (
            COMPARISON_ENGINE_VERSION
        ),
        "query_engine_version": (
            QUERY_ENGINE_VERSION
        ),
        "mode": (
            "EXPERIMENT_X_EXPERIMENT"
        ),
        "status": (
            "EXPLICIT_COMPARISON"
        ),
        "research_a": metadata_a,
        "research_b": metadata_b,
        "same_dataset": (
            metadata_a.get(
                "dataset_id"
            )
            == metadata_b.get(
                "dataset_id"
            )
        ),
        "same_period": (
            (
                metadata_a.get(
                    "period_start"
                ),
                metadata_a.get(
                    "period_end"
                ),
            )
            == (
                metadata_b.get(
                    "period_start"
                ),
                metadata_b.get(
                    "period_end"
                ),
            )
        ),
        "same_config": (
            config_a == config_b
        ),
        "comparison": (
            _compare_snapshots(
                snapshot_a,
                snapshot_b,
            )
        ),
    }


def compare_researches(
    *,
    research_a_id: str,
    research_b_id: str,
) -> dict[str, Any]:
    context_a = _require_research(
        research_a_id
    )

    context_b = _require_research(
        research_b_id
    )

    rows_a = _experiment_rows(
        context_a
    )

    rows_b = _experiment_rows(
        context_b
    )

    metadata_a = (
        _research_metadata(
            context_a
        )
    )

    metadata_b = (
        _research_metadata(
            context_b
        )
    )

    by_id_a = _rows_by_experiment(
        rows_a
    )

    by_id_b = _rows_by_experiment(
        rows_b
    )

    identity_conflicts: list[
        dict[str, Any]
    ] = []

    conflicted_ids: set[str] = set()

    for experiment_id in sorted(
        set(
            by_id_a
        )
        & set(
            by_id_b
        )
    ):
        config_a = (
            by_id_a[
                experiment_id
            ].get(
                "config_sha256"
            )
        )

        config_b = (
            by_id_b[
                experiment_id
            ].get(
                "config_sha256"
            )
        )

        if (
            config_a
            and config_b
            and config_a
            != config_b
        ):
            conflicted_ids.add(
                experiment_id
            )

            identity_conflicts.append(
                {
                    "status": (
                        "IDENTITY_CONFLICT"
                    ),
                    "experiment_id": (
                        experiment_id
                    ),
                    "config_sha256_a": (
                        config_a
                    ),
                    "config_sha256_b": (
                        config_b
                    ),
                    (
                        "config_identity_version_a"
                    ): (
                        by_id_a[
                            experiment_id
                        ].get(
                            "config_identity_version"
                        )
                    ),
                    (
                        "config_identity_version_b"
                    ): (
                        by_id_b[
                            experiment_id
                        ].get(
                            "config_identity_version"
                        )
                    ),
                }
            )

    eligible_a = [
        row
        for row in rows_a
        if str(
            row.get(
                "experiment_id"
            )
        )
        not in conflicted_ids
    ]

    eligible_b = [
        row
        for row in rows_b
        if str(
            row.get(
                "experiment_id"
            )
        )
        not in conflicted_ids
    ]

    by_config_a = _rows_by_config(
        eligible_a
    )

    by_config_b = _rows_by_config(
        eligible_b
    )

    configs_a = set(
        by_config_a
    )

    configs_b = set(
        by_config_b
    )

    shared_configs = sorted(
        configs_a
        & configs_b
    )

    only_configs_a = sorted(
        configs_a
        - configs_b
    )

    only_configs_b = sorted(
        configs_b
        - configs_a
    )

    artifacts_a = (
        _artifact_maps(
            context_a
        )
    )

    artifacts_b = (
        _artifact_maps(
            context_b
        )
    )

    matched: list[
        dict[str, Any]
    ] = []

    for config_hash in shared_configs:
        for experiment_a in (
            by_config_a[
                config_hash
            ]
        ):
            for experiment_b in (
                by_config_b[
                    config_hash
                ]
            ):
                snapshot_a = (
                    _experiment_snapshot(
                        context=(
                            context_a
                        ),
                        artifact_maps=(
                            artifacts_a
                        ),
                        experiment=(
                            experiment_a
                        ),
                    )
                )

                snapshot_b = (
                    _experiment_snapshot(
                        context=(
                            context_b
                        ),
                        artifact_maps=(
                            artifacts_b
                        ),
                        experiment=(
                            experiment_b
                        ),
                    )
                )

                matched.append(
                    {
                        "status": (
                            "MATCHED"
                        ),
                        "config_sha256": (
                            config_hash
                        ),
                        "experiment_a_id": (
                            experiment_a.get(
                                "experiment_id"
                            )
                        ),
                        "experiment_b_id": (
                            experiment_b.get(
                                "experiment_id"
                            )
                        ),
                        (
                            "config_identity_version_a"
                        ): (
                            experiment_a.get(
                                "config_identity_version"
                            )
                        ),
                        (
                            "config_identity_version_b"
                        ): (
                            experiment_b.get(
                                "config_identity_version"
                            )
                        ),
                        "comparison": (
                            _compare_snapshots(
                                snapshot_a,
                                snapshot_b,
                            )
                        ),
                    }
                )

    only_in_a: list[
        dict[str, Any]
    ] = []

    for config_hash in only_configs_a:
        for row in by_config_a[
            config_hash
        ]:
            item = (
                _experiment_summary(
                    row
                )
            )

            item[
                "status"
            ] = "ONLY_IN_RESEARCH_A"

            only_in_a.append(
                item
            )

    only_in_b: list[
        dict[str, Any]
    ] = []

    for config_hash in only_configs_b:
        for row in by_config_b[
            config_hash
        ]:
            item = (
                _experiment_summary(
                    row
                )
            )

            item[
                "status"
            ] = "ONLY_IN_RESEARCH_B"

            only_in_b.append(
                item
            )

    overall_status = (
        "MATCHED_EXPERIMENTS"
        if matched
        else "NO_MATCHED_EXPERIMENTS"
    )

    return {
        "comparison_engine_version": (
            COMPARISON_ENGINE_VERSION
        ),
        "query_engine_version": (
            QUERY_ENGINE_VERSION
        ),
        "mode": (
            "RESEARCH_X_RESEARCH"
        ),
        "status": (
            overall_status
        ),
        "research_a": metadata_a,
        "research_b": metadata_b,
        "same_dataset": (
            metadata_a.get(
                "dataset_id"
            )
            == metadata_b.get(
                "dataset_id"
            )
        ),
        "same_period": (
            (
                metadata_a.get(
                    "period_start"
                ),
                metadata_a.get(
                    "period_end"
                ),
            )
            == (
                metadata_b.get(
                    "period_start"
                ),
                metadata_b.get(
                    "period_end"
                ),
            )
        ),
        "experiments_a": [
            _experiment_summary(
                row
            )
            for row in rows_a
        ],
        "experiments_b": [
            _experiment_summary(
                row
            )
            for row in rows_b
        ],
        "matched_experiments": (
            matched
        ),
        "only_in_a": (
            only_in_a
        ),
        "only_in_b": (
            only_in_b
        ),
        "identity_conflicts": (
            identity_conflicts
        ),
        "counts": {
            "experiments_a": (
                len(
                    rows_a
                )
            ),
            "experiments_b": (
                len(
                    rows_b
                )
            ),
            "matched_experiments": (
                len(
                    matched
                )
            ),
            "only_in_a": (
                len(
                    only_in_a
                )
            ),
            "only_in_b": (
                len(
                    only_in_b
                )
            ),
            "identity_conflicts": (
                len(
                    identity_conflicts
                )
            ),
        },
    }
