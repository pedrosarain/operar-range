from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.management import (
    ManagementConfig,
    simulate_management,
)
from operar_range.runner import (
    build_m5_candles_from_parquet,
)
from operar_range.scanner import MOTOR_VERSION
from operar_range.trajectory import (
    read_trajectory_parquet,
)


RULES_VERSION = "ADR-004+STAGE10"
CREATED_AT = "2026-09-25"


RESULT_SCHEMA = pa.schema(
    [
        ("experiment_id", pa.string()),
        ("management_name", pa.string()),
        ("date", pa.string()),
        ("trade_status", pa.string()),
        ("direction", pa.string()),
        ("stop_points", pa.float64()),
        ("partial_1_points", pa.float64()),
        ("partial_1_pct", pa.float64()),
        ("partial_2_points", pa.float64()),
        ("partial_2_pct", pa.float64()),
        ("partial_3_points", pa.float64()),
        ("partial_3_pct", pa.float64()),
        ("break_even", pa.bool_()),
        ("break_even_after_partial", pa.int64()),
        ("runner", pa.bool_()),
        ("runner_pct", pa.float64()),
        ("runner_rule", pa.string()),
        ("final_target", pa.float64()),
        ("position_size", pa.float64()),
        ("total_weighted_points", pa.float64()),
        ("final_reason", pa.string()),
        ("final_timestamp", pa.string()),
        ("final_price", pa.float64()),
        ("mfe", pa.float64()),
        ("mae", pa.float64()),
        ("trajectory_sha256", pa.string()),
        ("config_sha256", pa.string()),
        ("motor_version", pa.string()),
        ("rules_version", pa.string()),
    ]
)


MANIFEST_SCHEMA = pa.schema(
    [
        ("experiment_id", pa.string()),
        ("name", pa.string()),
        ("config_json", pa.string()),
        ("created_at", pa.string()),
        ("motor_version", pa.string()),
        ("rules_version", pa.string()),
        ("sessions_executed", pa.int64()),
        ("config_sha256", pa.string()),
    ]
)


@dataclass(frozen=True)
class ExperimentDefinition:
    experiment_id: str
    name: str
    config: ManagementConfig


def canonical_config_json(
    config: ManagementConfig,
) -> str:
    return json.dumps(
        asdict(config),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def config_sha256(
    config: ManagementConfig,
) -> str:
    payload = canonical_config_json(
        config
    ).encode("utf-8")

    return hashlib.sha256(
        payload
    ).hexdigest()


def validate_experiments(
    experiments: list[
        ExperimentDefinition
    ],
) -> None:
    if not experiments:
        raise ValueError(
            "At least one experiment is required."
        )

    ids = [
        experiment.experiment_id
        for experiment in experiments
    ]

    if len(ids) != len(set(ids)):
        raise ValueError(
            "Experiment IDs must be unique."
        )

    names = [
        experiment.name
        for experiment in experiments
    ]

    if len(names) != len(set(names)):
        raise ValueError(
            "Experiment names must be unique."
        )


def _result_base(
    *,
    experiment: ExperimentDefinition,
    day: dict[str, Any],
) -> dict[str, Any]:
    config = experiment.config

    return {
        "experiment_id": (
            experiment.experiment_id
        ),
        "management_name": (
            experiment.name
        ),
        "date": day["date"],
        "trade_status": (
            day["trade1_status"]
        ),
        "direction": day["direction"],
        "stop_points": float(
            config.stop_points
        ),
        "partial_1_points": (
            float(
                config.partial_1_points
            )
            if config.partial_1_points
            is not None
            else None
        ),
        "partial_1_pct": (
            float(
                config.partial_1_pct
            )
            if config.partial_1_pct
            is not None
            else None
        ),
        "partial_2_points": (
            float(
                config.partial_2_points
            )
            if config.partial_2_points
            is not None
            else None
        ),
        "partial_2_pct": (
            float(
                config.partial_2_pct
            )
            if config.partial_2_pct
            is not None
            else None
        ),
        "partial_3_points": (
            float(
                config.partial_3_points
            )
            if config.partial_3_points
            is not None
            else None
        ),
        "partial_3_pct": (
            float(
                config.partial_3_pct
            )
            if config.partial_3_pct
            is not None
            else None
        ),
        "break_even": bool(
            config.break_even_enabled
        ),
        "break_even_after_partial": (
            int(
                config.break_even_after_partial
            )
            if config.break_even_after_partial
            is not None
            else None
        ),
        "runner": bool(
            config.runner_enabled
        ),
        "runner_pct": (
            float(config.runner_pct)
            if config.runner_pct
            is not None
            else None
        ),
        "runner_rule": (
            config.runner_exit_rule
        ),
        "final_target": (
            float(
                config.final_target_points
            )
            if config.final_target_points
            is not None
            else None
        ),
        "position_size": float(
            config.position_size
        ),
        "total_weighted_points": None,
        "final_reason": None,
        "final_timestamp": None,
        "final_price": None,
        "mfe": (
            float(day["mfe_points"])
            if day["mfe_points"]
            is not None
            else None
        ),
        "mae": (
            float(day["mae_points"])
            if day["mae_points"]
            is not None
            else None
        ),
        "trajectory_sha256": (
            day["sha256"]
        ),
        "config_sha256": (
            config_sha256(config)
        ),
        "motor_version": MOTOR_VERSION,
        "rules_version": RULES_VERSION,
    }


def _write_parquet(
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


def run_experiments(
    *,
    experiments: list[
        ExperimentDefinition
    ],
    trajectory_manifest_path: (
        str | Path
    ) = (
        "data/research/"
        "trade1_trajectory_manifest.parquet"
    ),
    normalized_dir: str | Path = (
        "data/normalized"
    ),
    results_path: str | Path = (
        "data/research/"
        "experiment_results.parquet"
    ),
    experiment_manifest_path: (
        str | Path
    ) = (
        "data/research/"
        "experiment_manifest.parquet"
    ),
) -> dict[str, Any]:
    validate_experiments(
        experiments
    )

    trajectory_manifest_path = Path(
        trajectory_manifest_path
    )

    normalized_dir = Path(
        normalized_dir
    )

    if not (
        trajectory_manifest_path.exists()
    ):
        raise FileNotFoundError(
            trajectory_manifest_path
        )

    days = pq.read_table(
        trajectory_manifest_path
    ).to_pylist()

    days = sorted(
        days,
        key=lambda row: (
            row["date"],
            row["source_parquet"],
        ),
    )

    ordered_experiments = sorted(
        experiments,
        key=lambda item: (
            item.experiment_id
        ),
    )

    results: list[
        dict[str, Any]
    ] = []

    for day in days:
        trade_exists = (
            day["trade1_status"]
            == "TRADE_1"
            and bool(
                day["trajectory_exists"]
            )
        )

        if not trade_exists:
            for experiment in (
                ordered_experiments
            ):
                results.append(
                    _result_base(
                        experiment=experiment,
                        day=day,
                    )
                )

            continue

        trajectory_path = Path(
            day["trajectory_path"]
        )

        trajectory = (
            read_trajectory_parquet(
                trajectory_path
            )
        )

        runner_required = any(
            experiment.config.runner_enabled
            for experiment
            in ordered_experiments
        )

        runner_candles = None

        if runner_required:
            source_path = (
                normalized_dir
                / day["source_parquet"]
            )

            runner_candles = (
                build_m5_candles_from_parquet(
                    source_path
                )
            )

        for experiment in (
            ordered_experiments
        ):
            base = _result_base(
                experiment=experiment,
                day=day,
            )

            config = experiment.config

            management_result = (
                simulate_management(
                    trajectory=trajectory,
                    date=day["date"],
                    direction=day[
                        "direction"
                    ],
                    entry_price=float(
                        day["entry_price"]
                    ),
                    config=config,
                    runner_candles=(
                        runner_candles
                        if config.runner_enabled
                        else None
                    ),
                )
            )

            base[
                "total_weighted_points"
            ] = float(
                management_result[
                    "total_weighted_points"
                ]
            )

            base[
                "final_reason"
            ] = management_result[
                "final_reason"
            ]

            base[
                "final_timestamp"
            ] = management_result[
                "final_timestamp"
            ]

            base[
                "final_price"
            ] = (
                float(
                    management_result[
                        "final_price"
                    ]
                )
                if management_result[
                    "final_price"
                ]
                is not None
                else None
            )

            results.append(
                base
            )

    results = sorted(
        results,
        key=lambda row: (
            row["experiment_id"],
            row["date"],
        ),
    )

    manifest_rows = []

    for experiment in (
        ordered_experiments
    ):
        manifest_rows.append(
            {
                "experiment_id": (
                    experiment.experiment_id
                ),
                "name": (
                    experiment.name
                ),
                "config_json": (
                    canonical_config_json(
                        experiment.config
                    )
                ),
                "created_at": CREATED_AT,
                "motor_version": (
                    MOTOR_VERSION
                ),
                "rules_version": (
                    RULES_VERSION
                ),
                "sessions_executed": (
                    len(days)
                ),
                "config_sha256": (
                    config_sha256(
                        experiment.config
                    )
                ),
            }
        )

    results_path = _write_parquet(
        rows=results,
        schema=RESULT_SCHEMA,
        path=results_path,
    )

    experiment_manifest_path = (
        _write_parquet(
            rows=manifest_rows,
            schema=MANIFEST_SCHEMA,
            path=(
                experiment_manifest_path
            ),
        )
    )

    return {
        "results": results,
        "manifest": manifest_rows,
        "results_path": str(
            results_path
        ),
        "experiment_manifest_path": str(
            experiment_manifest_path
        ),
        "sessions": len(days),
        "experiments": len(
            ordered_experiments
        ),
    }