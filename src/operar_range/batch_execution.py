from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.management import (
    ManagementConfig,
    simulate_management,
)
from operar_range.research_engine import (
    MOTOR_VERSION,
    RULES_VERSION,
)
from operar_range.runner import (
    build_m5_candles_from_parquet,
)
from operar_range.trajectory import (
    read_trajectory_parquet,
)
from operar_range.trade_lifecycle import (
    TradeLifecycleConfig,
    simulate_trade_lifecycle,
)


BATCH_RESULT_SCHEMA = pa.schema(
    [
        ("execution_unit_id", pa.string()),
        ("batch_id", pa.string()),
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
        (
            "break_even_after_partial",
            pa.int64(),
        ),

        ("runner", pa.bool_()),
        ("runner_pct", pa.float64()),
        ("runner_rule", pa.string()),

        ("final_target", pa.float64()),
        ("position_size", pa.float64()),

        (
            "total_weighted_points",
            pa.float64(),
        ),

        # Trade Lifecycle V1.
        #
        # Compatibilidade obrigatória:
        # total_weighted_points continua
        # representando exclusivamente
        # o Trade 1.
        (
            "trade1_result_points",
            pa.float64(),
        ),
        (
            "trade2_eligible",
            pa.bool_(),
        ),
        (
            "trade2_occurred",
            pa.bool_(),
        ),
        (
            "trade2_executed",
            pa.bool_(),
        ),
        (
            "trade2_winner",
            pa.bool_(),
        ),
        (
            "trade2_loser",
            pa.bool_(),
        ),
        (
            "trade2_breakeven",
            pa.bool_(),
        ),
        (
            "trade2_result_points",
            pa.float64(),
        ),
        (
            "consolidated_result_points",
            pa.float64(),
        ),

        (
            "trade2_direction",
            pa.string(),
        ),
        (
            "trade2_trigger_level",
            pa.float64(),
        ),
        (
            "trade2_entry_timestamp",
            pa.string(),
        ),
        (
            "trade2_entry_trade_number",
            pa.int64(),
        ),
        (
            "trade2_first_traded_price",
            pa.float64(),
        ),
        (
            "trade2_jumped_entry_level",
            pa.bool_(),
        ),
        (
            "trade2_final_reason",
            pa.string(),
        ),
        (
            "trade2_final_timestamp",
            pa.string(),
        ),
        (
            "trade2_final_price",
            pa.float64(),
        ),
        (
            "trade2_mfe",
            pa.float64(),
        ),
        (
            "trade2_mae",
            pa.float64(),
        ),
        (
            "trade2_management_json",
            pa.string(),
        ),
        (
            "lifecycle_version",
            pa.string(),
        ),

        ("final_reason", pa.string()),
        ("final_timestamp", pa.string()),
        ("final_price", pa.float64()),

        ("mfe", pa.float64()),
        ("mae", pa.float64()),

        (
            "trajectory_sha256",
            pa.string(),
        ),
        ("config_sha256", pa.string()),

        ("motor_version", pa.string()),
        ("rules_version", pa.string()),
    ]
)


FAILURE_SCHEMA = pa.schema(
    [
        ("execution_unit_id", pa.string()),
        ("batch_id", pa.string()),
        ("experiment_id", pa.string()),
        ("date", pa.string()),
        ("exception_type", pa.string()),
        ("message", pa.string()),
        ("attempt_count", pa.int64()),
    ]
)


def sha256_file(
    path: str | Path,
) -> str:
    path = Path(path)

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


def _read_rows(
    path: str | Path,
) -> list[dict[str, Any]]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    return pq.read_table(
        path
    ).to_pylist()


def _optional_float(
    value: Any,
) -> float | None:
    if value is None:
        return None

    return float(value)


def management_config_from_row(
    row: dict[str, Any],
) -> ManagementConfig:
    return ManagementConfig(
        stop_points=float(
            row["stop_points"]
        ),

        partial_1_points=(
            _optional_float(
                row.get(
                    "partial_1_points"
                )
            )
        ),
        partial_1_pct=(
            _optional_float(
                row.get(
                    "partial_1_pct"
                )
            )
        ),

        partial_2_points=(
            _optional_float(
                row.get(
                    "partial_2_points"
                )
            )
        ),
        partial_2_pct=(
            _optional_float(
                row.get(
                    "partial_2_pct"
                )
            )
        ),

        partial_3_points=(
            _optional_float(
                row.get(
                    "partial_3_points"
                )
            )
        ),
        partial_3_pct=(
            _optional_float(
                row.get(
                    "partial_3_pct"
                )
            )
        ),

        break_even_enabled=bool(
            row.get(
                "break_even_enabled"
            )
        ),

        break_even_after_partial=(
            int(
                row[
                    "break_even_after_partial"
                ]
            )
            if row.get(
                "break_even_after_partial"
            )
            is not None
            else None
        ),

        final_target_points=(
            _optional_float(
                row.get(
                    "final_target_points"
                )
            )
        ),

        position_size=100.0,

        runner_enabled=bool(
            row.get(
                "runner_enabled"
            )
        ),

        runner_pct=(
            _optional_float(
                row.get(
                    "runner_pct"
                )
            )
        ),

        runner_exit_rule=(
            row.get(
                "runner_rule"
            )
        ),
    )


def _base_result(
    *,
    execution_unit: dict[str, Any],
    experiment: dict[str, Any],
    day: dict[str, Any],
    config: ManagementConfig,
) -> dict[str, Any]:
    return {
        "execution_unit_id": (
            execution_unit[
                "execution_unit_id"
            ]
        ),
        "batch_id": (
            execution_unit[
                "batch_id"
            ]
        ),
        "experiment_id": (
            experiment[
                "experiment_id"
            ]
        ),
        "management_name": (
            experiment.get(
                "experiment_name"
            )
            or experiment[
                "experiment_id"
            ]
        ),
        "date": day["date"],
        "trade_status": (
            day["trade1_status"]
        ),
        "direction": (
            day.get(
                "direction"
            )
        ),

        "stop_points": float(
            config.stop_points
        ),

        "partial_1_points": (
            _optional_float(
                config.partial_1_points
            )
        ),
        "partial_1_pct": (
            _optional_float(
                config.partial_1_pct
            )
        ),

        "partial_2_points": (
            _optional_float(
                config.partial_2_points
            )
        ),
        "partial_2_pct": (
            _optional_float(
                config.partial_2_pct
            )
        ),

        "partial_3_points": (
            _optional_float(
                config.partial_3_points
            )
        ),
        "partial_3_pct": (
            _optional_float(
                config.partial_3_pct
            )
        ),

        "break_even": bool(
            config.break_even_enabled
        ),
        "break_even_after_partial": (
            config.break_even_after_partial
        ),

        "runner": bool(
            config.runner_enabled
        ),
        "runner_pct": (
            _optional_float(
                config.runner_pct
            )
        ),
        "runner_rule": (
            config.runner_exit_rule
        ),

        "final_target": (
            _optional_float(
                config.final_target_points
            )
        ),

        "position_size": float(
            config.position_size
        ),

        "total_weighted_points": None,

        "trade1_result_points": None,
        "trade2_eligible": False,
        "trade2_occurred": False,
        "trade2_executed": False,
        "trade2_winner": False,
        "trade2_loser": False,
        "trade2_breakeven": False,
        "trade2_result_points": None,
        "consolidated_result_points": None,

        "trade2_direction": None,
        "trade2_trigger_level": None,
        "trade2_entry_timestamp": None,
        "trade2_entry_trade_number": None,
        "trade2_first_traded_price": None,
        "trade2_jumped_entry_level": None,
        "trade2_final_reason": None,
        "trade2_final_timestamp": None,
        "trade2_final_price": None,
        "trade2_mfe": None,
        "trade2_mae": None,
        "trade2_management_json": None,
        "lifecycle_version": None,

        "final_reason": None,
        "final_timestamp": None,
        "final_price": None,

        "mfe": (
            _optional_float(
                day.get(
                    "mfe_points"
                )
            )
        ),
        "mae": (
            _optional_float(
                day.get(
                    "mae_points"
                )
            )
        ),

        "trajectory_sha256": (
            day.get(
                "sha256"
            )
        ),

        "config_sha256": (
            experiment[
                "config_sha256"
            ]
        ),

        "motor_version": (
            MOTOR_VERSION
        ),
        "rules_version": (
            RULES_VERSION
        ),
    }


def _batch_filename(
    batch_id: str,
) -> str:
    safe_batch_id = (
        batch_id.replace(
            "-",
            "_",
        )
    )

    return (
        f"{safe_batch_id}.parquet"
    )


def write_batch_results(
    *,
    rows: list[dict[str, Any]],
    batch_id: str,
    batches_dir: str | Path,
) -> Path:
    batches_dir = Path(
        batches_dir
    )

    batches_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        batches_dir
        / _batch_filename(
            batch_id
        )
    )

    ordered = sorted(
        rows,
        key=lambda row: (
            row[
                "execution_unit_id"
            ]
        ),
    )

    table = pa.Table.from_pylist(
        ordered,
        schema=BATCH_RESULT_SCHEMA,
    )

    pq.write_table(
        table,
        output_path,
        compression="zstd",
    )

    return output_path


def execute_batch(
    *,
    batch_id: str,
    plan_path: str | Path = (
        "data/research/"
        "batch_execution_plan.parquet"
    ),
    valid_experiments_path: str | Path = (
        "data/research/"
        "valid_experiments.parquet"
    ),
    trajectory_manifest_path: str | Path = (
        "data/research/"
        "trade1_trajectory_manifest.parquet"
    ),
    normalized_dir: str | Path = (
        "data/normalized"
    ),
    batches_dir: str | Path = (
        "data/research/batches"
    ),
) -> dict[str, Any]:
    plan_rows = _read_rows(
        plan_path
    )

    experiment_rows = _read_rows(
        valid_experiments_path
    )

    day_rows = _read_rows(
        trajectory_manifest_path
    )

    experiment_by_id = {
        row["experiment_id"]: row
        for row in experiment_rows
    }

    day_by_date = {
        row["date"]: row
        for row in day_rows
    }

    batch_units = [
        row
        for row in plan_rows
        if (
            row["batch_id"]
            == batch_id
        )
    ]

    if not batch_units:
        raise ValueError(
            f"Unknown batch_id: "
            f"{batch_id}"
        )

    batch_units = sorted(
        batch_units,
        key=lambda row: (
            row[
                "execution_unit_id"
            ]
        ),
    )

    batch_output_path = (
        Path(batches_dir)
        / _batch_filename(
            batch_id
        )
    )

    existing_results: list[
        dict[str, Any]
    ] = []

    if batch_output_path.exists():
        existing_results = (
            pq.read_table(
                batch_output_path
            ).to_pylist()
        )

    existing_by_unit = {
        row[
            "execution_unit_id"
        ]: row
        for row in existing_results
    }

    trajectory_cache: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    candle_cache: dict[
        str,
        Any,
    ] = {}

    new_results: list[
        dict[str, Any]
    ] = []

    completed_unit_ids: list[
        str
    ] = []

    skipped_unit_ids: list[
        str
    ] = []

    failures: list[
        dict[str, Any]
    ] = []

    for unit in batch_units:
        execution_unit_id = (
            unit[
                "execution_unit_id"
            ]
        )

        current_status = unit[
            "execution_status"
        ]

        # COMPLETED representa uma unidade
        # de trade que já foi executada e
        # persistida anteriormente.
        if current_status == "COMPLETED":
            continue

        # SKIPPED_NO_TRADE é um estado final
        # do plano, mas sua execution unit
        # ainda precisa existir fisicamente
        # no parquet do batch para que o
        # merge preserve exatamente uma linha
        # por execution_unit_id.
        if current_status not in (
            "PENDING",
            "FAILED",
            "SKIPPED_NO_TRADE",
        ):
            continue

        experiment_id = (
            unit[
                "experiment_id"
            ]
        )

        date = unit["date"]

        attempt_count = int(
            unit.get(
                "attempt_count"
            )
            or 0
        ) + 1

        try:
            if (
                experiment_id
                not in experiment_by_id
            ):
                raise RuntimeError(
                    "Experiment missing from "
                    "valid_experiments: "
                    f"{experiment_id}"
                )

            if date not in day_by_date:
                raise RuntimeError(
                    "Session missing from "
                    "trajectory manifest: "
                    f"{date}"
                )

            experiment = (
                experiment_by_id[
                    experiment_id
                ]
            )

            day = day_by_date[
                date
            ]

            config = (
                management_config_from_row(
                    experiment
                )
            )

            base = _base_result(
                execution_unit=unit,
                experiment=experiment,
                day=day,
                config=config,
            )

            # NO_TRADE_1:
            #
            # Não executa trajectory.
            # Não executa Motor de Gestão.
            # Não produz resultado financeiro.
            #
            # Porém a execution unit precisa
            # ser persistida no resultado do
            # batch para manter a relação
            # 1 execution unit = 1 linha no
            # dataset final.
            if (
                unit[
                    "trade_status"
                ]
                == "NO_TRADE_1"
            ):
                if (
                    execution_unit_id
                    not in existing_by_unit
                ):
                    new_results.append(
                        base
                    )

                skipped_unit_ids.append(
                    execution_unit_id
                )

                continue

            trajectory_path = str(
                unit[
                    "trajectory_path"
                ]
            )

            if (
                trajectory_path
                not in trajectory_cache
            ):
                trajectory_cache[
                    trajectory_path
                ] = (
                    read_trajectory_parquet(
                        trajectory_path
                    )
                )

            trajectory = (
                trajectory_cache[
                    trajectory_path
                ]
            )

            runner_candles = None

            if config.runner_enabled:
                if date not in candle_cache:
                    source_parquet = (
                        day.get(
                            "source_parquet"
                        )
                    )

                    if not source_parquet:
                        raise RuntimeError(
                            "Runner requires "
                            "source_parquet for "
                            f"{date}."
                        )

                    source_path = (
                        Path(
                            normalized_dir
                        )
                        / source_parquet
                    )

                    candle_cache[
                        date
                    ] = (
                        build_m5_candles_from_parquet(
                            source_path
                        )
                    )

                runner_candles = (
                    candle_cache[
                        date
                    ]
                )

            management_result = (
                simulate_management(
                    trajectory=trajectory,
                    date=date,
                    direction=day[
                        "direction"
                    ],
                    entry_price=float(
                        day[
                            "entry_price"
                        ]
                    ),
                    config=config,
                    runner_candles=(
                        runner_candles
                    ),
                )
            )

            trade1_result_points = float(
                management_result[
                    "total_weighted_points"
                ]
            )

            #
            # Compatibilidade histórica.
            # Este campo NÃO muda de
            # significado na Etapa 19.
            #
            base[
                "total_weighted_points"
            ] = trade1_result_points

            base[
                "trade1_result_points"
            ] = trade1_result_points

            lifecycle = (
                simulate_trade_lifecycle(
                    trajectory=trajectory,
                    date=date,
                    trade1_status=(
                        day[
                            "trade1_status"
                        ]
                    ),
                    direction=(
                        day[
                            "direction"
                        ]
                    ),
                    entry_price=float(
                        day[
                            "entry_price"
                        ]
                    ),
                    management_config=(
                        config
                    ),
                    trade1_management=(
                        management_result
                    ),
                    runner_candles=(
                        runner_candles
                    ),
                    lifecycle_config=(
                        TradeLifecycleConfig(
                            eligible_after=(
                                "STOP",
                            )
                        )
                    ),
                )
            )

            trade2 = lifecycle[
                "trade2"
            ]

            base[
                "trade2_eligible"
            ] = bool(
                trade2[
                    "eligible"
                ]
            )

            base[
                "trade2_occurred"
            ] = bool(
                lifecycle[
                    "trade2_occurred"
                ]
            )

            base[
                "trade2_executed"
            ] = bool(
                lifecycle[
                    "trade2_executed"
                ]
            )

            base[
                "trade2_winner"
            ] = bool(
                lifecycle[
                    "trade2_winner"
                ]
            )

            base[
                "trade2_loser"
            ] = bool(
                lifecycle[
                    "trade2_loser"
                ]
            )

            base[
                "trade2_breakeven"
            ] = bool(
                lifecycle[
                    "trade2_breakeven"
                ]
            )

            base[
                "trade2_result_points"
            ] = (
                float(
                    lifecycle[
                        "trade2_result_points"
                    ]
                )
                if lifecycle[
                    "trade2_result_points"
                ]
                is not None
                else None
            )

            base[
                "consolidated_result_points"
            ] = float(
                lifecycle[
                    "consolidated_result_points"
                ]
            )

            base[
                "trade2_direction"
            ] = trade2[
                "direction"
            ]

            base[
                "trade2_trigger_level"
            ] = (
                float(
                    trade2[
                        "trigger_level"
                    ]
                )
                if trade2[
                    "trigger_level"
                ]
                is not None
                else None
            )

            base[
                "trade2_entry_timestamp"
            ] = trade2[
                "entry_timestamp"
            ]

            base[
                "trade2_entry_trade_number"
            ] = trade2[
                "entry_trade_number"
            ]

            base[
                "trade2_first_traded_price"
            ] = (
                float(
                    trade2[
                        "first_traded_price"
                    ]
                )
                if trade2[
                    "first_traded_price"
                ]
                is not None
                else None
            )

            base[
                "trade2_jumped_entry_level"
            ] = trade2[
                "jumped_entry_level"
            ]

            base[
                "trade2_final_reason"
            ] = trade2[
                "final_reason"
            ]

            base[
                "trade2_final_timestamp"
            ] = trade2[
                "final_timestamp"
            ]

            base[
                "trade2_final_price"
            ] = (
                float(
                    trade2[
                        "final_price"
                    ]
                )
                if trade2[
                    "final_price"
                ]
                is not None
                else None
            )

            base[
                "trade2_mfe"
            ] = (
                float(
                    trade2[
                        "mfe"
                    ]
                )
                if trade2[
                    "mfe"
                ]
                is not None
                else None
            )

            base[
                "trade2_mae"
            ] = (
                float(
                    trade2[
                        "mae"
                    ]
                )
                if trade2[
                    "mae"
                ]
                is not None
                else None
            )

            base[
                "trade2_management_json"
            ] = (
                json.dumps(
                    trade2[
                        "management"
                    ],
                    sort_keys=True,
                    separators=(
                        ",",
                        ":",
                    ),
                    ensure_ascii=False,
                )
                if trade2[
                    "management"
                ]
                is not None
                else None
            )

            base[
                "lifecycle_version"
            ] = lifecycle[
                "lifecycle_version"
            ]

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

            if (
                execution_unit_id
                not in existing_by_unit
            ):
                new_results.append(
                    base
                )

            completed_unit_ids.append(
                execution_unit_id
            )

        except Exception as exc:
            failures.append(
                {
                    "execution_unit_id": (
                        execution_unit_id
                    ),
                    "batch_id": (
                        batch_id
                    ),
                    "experiment_id": (
                        experiment_id
                    ),
                    "date": date,
                    "exception_type": (
                        type(exc).__name__
                    ),
                    "message": str(exc),
                    "attempt_count": (
                        attempt_count
                    ),
                }
            )

    combined_results = list(
        existing_by_unit.values()
    )

    combined_results.extend(
        new_results
    )

    duplicate_check = [
        row[
            "execution_unit_id"
        ]
        for row in combined_results
    ]

    if (
        len(duplicate_check)
        != len(
            set(
                duplicate_check
            )
        )
    ):
        raise RuntimeError(
            "Duplicate execution_unit_id "
            "inside batch result."
        )

    output_path = (
        write_batch_results(
            rows=combined_results,
            batch_id=batch_id,
            batches_dir=batches_dir,
        )
    )

    return {
        "batch_id": batch_id,
        "execution_units": len(
            batch_units
        ),
        "new_results": len(
            new_results
        ),
        "completed_unit_ids": (
            completed_unit_ids
        ),
        "skipped_unit_ids": (
            skipped_unit_ids
        ),
        "failures": failures,
        "trajectory_loads": len(
            trajectory_cache
        ),
        "runner_candle_builds": len(
            candle_cache
        ),
        "output_path": str(
            output_path
        ),
        "output_sha256": (
            sha256_file(
                output_path
            )
        ),
    }