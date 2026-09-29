from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.batch_execution import (
    execute_batch,
)
from operar_range.batch_executor import (
    assign_batches,
    build_execution_units,
    write_execution_plan,
)
from operar_range.trajectory import (
    write_trajectory_parquet,
)


def _sha256(
    path: Path,
) -> str:
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


def _write_normalized(
    path: Path,
    rows: list[
        tuple[str, int, float]
    ],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    schema = pa.schema(
        [
            (
                "timestamp",
                pa.timestamp(
                    "us",
                    tz=(
                        "America/Sao_Paulo"
                    ),
                ),
            ),
            (
                "trade_number",
                pa.int64(),
            ),
            (
                "price",
                pa.float64(),
            ),
        ]
    )

    table = pa.Table.from_arrays(
        [
            pa.array(
                [
                    datetime.fromisoformat(
                        timestamp
                    )
                    for (
                        timestamp,
                        _,
                        _,
                    ) in rows
                ],
                type=schema.field(
                    "timestamp"
                ).type,
            ),
            pa.array(
                [
                    int(
                        trade_number
                    )
                    for (
                        _,
                        trade_number,
                        _,
                    ) in rows
                ],
                type=pa.int64(),
            ),
            pa.array(
                [
                    float(
                        price
                    )
                    for (
                        _,
                        _,
                        price,
                    ) in rows
                ],
                type=pa.float64(),
            ),
        ],
        schema=schema,
    )

    pq.write_table(
        table,
        path,
        compression="zstd",
    )


def _trajectory_rows(
    prices: list[
        tuple[str, int, float]
    ],
    *,
    entry_price: float,
) -> list[dict]:
    rows = []

    max_favorable = 0.0
    max_adverse = 0.0

    for (
        timestamp,
        trade_number,
        price,
    ) in prices:
        points = (
            float(price)
            - float(
                entry_price
            )
        )

        max_favorable = max(
            max_favorable,
            points,
            0.0,
        )

        max_adverse = max(
            max_adverse,
            -points,
            0.0,
        )

        rows.append(
            {
                "timestamp": (
                    timestamp
                ),
                "trade_number": (
                    trade_number
                ),
                "price": float(
                    price
                ),
                "points_from_entry": (
                    points
                ),
                (
                    "favorable_excursion"
                ): max_favorable,
                (
                    "adverse_excursion"
                ): max_adverse,
            }
        )

    return rows


def _experiment() -> dict:
    return {
        "experiment_id": (
            "EXP-STAGE22-ISOLATION"
        ),
        "experiment_name": (
            "Stage22 physical isolation"
        ),
        "config_sha256": (
            "c" * 64
        ),
        "rules_version": (
            "ADR-004+STAGE10"
        ),

        "stop_points": 170.0,

        "partial_1_points": 125.0,
        "partial_1_pct": 70.0,

        "partial_2_points": None,
        "partial_2_pct": None,

        "partial_3_points": None,
        "partial_3_pct": None,

        "break_even_enabled": False,
        "break_even_after_partial": None,

        "runner_enabled": True,
        "runner_pct": 30.0,
        "runner_rule": (
            "CANDLE_BREAK_M5"
        ),

        "final_target_points": None,

        #
        # Stage 21:
        # Trade 2 explicitamente desligado.
        #
        "trade2_enabled": False,
        "trade2_management_mode": (
            "INHERIT"
        ),
    }


def _write_experiment(
    path: Path,
    experiment: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pq.write_table(
        pa.Table.from_pylist(
            [
                experiment
            ]
        ),
        path,
        compression="zstd",
    )


def _write_manifest(
    path: Path,
    row: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pq.write_table(
        pa.Table.from_pylist(
            [
                row
            ]
        ),
        path,
        compression="zstd",
    )


def test_execute_batch_physically_isolates_selected_dataset(
    tmp_path,
):
    date = "2026-08-18"

    dataset_a = (
        tmp_path
        / "data"
        / "datasets"
        / "DS-AAAAAAAAAAAAAAAA"
    )

    dataset_b = (
        tmp_path
        / "data"
        / "datasets"
        / "DS-BBBBBBBBBBBBBBBB"
    )

    legacy = (
        tmp_path
        / "data"
        / "legacy"
    )

    for root in (
        dataset_a,
        dataset_b,
        legacy,
    ):
        (
            root
            / "normalized"
        ).mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            root
            / "trajectories"
        ).mkdir(
            parents=True,
            exist_ok=True,
        )

    source_name = (
        "same_session.parquet"
    )

    #
    # ========================================================
    # DATASET A — UNIVERSO CORRETO
    # ========================================================
    #
    # Candles M5:
    #
    # 10:30
    # O=1000 H=1150 L=990 C=1120
    #
    # 10:35
    # O=1120 H=1200 L=1100 C=1180
    #
    # 10:40
    # O=1180 H=1190 L=1070 C=1080
    #
    # Após a parcial em +125, o último candle positivo
    # protegido possui low=1100.
    #
    # O candle negativo seguinte rompe 1100.
    # O runner deve encerrar por EXIT_RUNNER_CANDLE.
    #
    _write_normalized(
        dataset_a
        / "normalized"
        / source_name,
        [
            (
                "2026-08-18T10:30:00-03:00",
                1,
                1000.0,
            ),
            (
                "2026-08-18T10:31:00-03:00",
                2,
                1150.0,
            ),
            (
                "2026-08-18T10:34:59-03:00",
                3,
                1120.0,
            ),
            (
                "2026-08-18T10:35:00-03:00",
                4,
                1120.0,
            ),
            (
                "2026-08-18T10:36:00-03:00",
                5,
                1200.0,
            ),
            (
                "2026-08-18T10:37:00-03:00",
                6,
                1100.0,
            ),
            (
                "2026-08-18T10:39:59-03:00",
                7,
                1180.0,
            ),
            (
                "2026-08-18T10:40:00-03:00",
                8,
                1180.0,
            ),
            (
                "2026-08-18T10:40:10-03:00",
                9,
                1190.0,
            ),
            (
                "2026-08-18T10:40:20-03:00",
                10,
                1070.0,
            ),
            (
                "2026-08-18T10:40:30-03:00",
                11,
                1080.0,
            ),
        ],
    )

    trajectory_a = (
        dataset_a
        / "trajectories"
        / "trade1.parquet"
    )

    write_trajectory_parquet(
        _trajectory_rows(
            [
                (
                    "2026-08-18T10:30:00-03:00",
                    1,
                    1000.0,
                ),
                (
                    "2026-08-18T10:31:00-03:00",
                    2,
                    1125.0,
                ),
                (
                    "2026-08-18T10:40:30-03:00",
                    3,
                    1080.0,
                ),
            ],
            entry_price=1000.0,
        ),
        trajectory_a,
    )

    #
    # ========================================================
    # DATASET B — SENTINELA CONFLITANTE
    # ========================================================
    #
    # Mesmo source_parquet.
    #
    # Porém os candles NÃO produzem o mesmo rompimento
    # do Dataset A.
    #
    _write_normalized(
        dataset_b
        / "normalized"
        / source_name,
        [
            (
                "2026-08-18T10:30:00-03:00",
                1,
                2000.0,
            ),
            (
                "2026-08-18T10:34:59-03:00",
                2,
                2100.0,
            ),
            (
                "2026-08-18T10:35:00-03:00",
                3,
                2100.0,
            ),
            (
                "2026-08-18T10:39:59-03:00",
                4,
                2200.0,
            ),
            (
                "2026-08-18T10:40:00-03:00",
                5,
                2200.0,
            ),
            (
                "2026-08-18T10:40:30-03:00",
                6,
                2300.0,
            ),
        ],
    )

    trajectory_b = (
        dataset_b
        / "trajectories"
        / "trade1.parquet"
    )

    write_trajectory_parquet(
        _trajectory_rows(
            [
                (
                    "2026-08-18T10:30:00-03:00",
                    1,
                    2000.0,
                ),
                (
                    "2026-08-18T10:31:00-03:00",
                    2,
                    2200.0,
                ),
            ],
            entry_price=2000.0,
        ),
        trajectory_b,
    )

    #
    # ========================================================
    # LEGACY — OUTRA SENTINELA CONFLITANTE
    # ========================================================
    #
    _write_normalized(
        legacy
        / "normalized"
        / source_name,
        [
            (
                "2026-08-18T10:30:00-03:00",
                1,
                5000.0,
            ),
            (
                "2026-08-18T10:35:00-03:00",
                2,
                5100.0,
            ),
            (
                "2026-08-18T10:40:00-03:00",
                3,
                5200.0,
            ),
        ],
    )

    trajectory_legacy = (
        legacy
        / "trajectories"
        / "trade1.parquet"
    )

    write_trajectory_parquet(
        _trajectory_rows(
            [
                (
                    "2026-08-18T10:30:00-03:00",
                    1,
                    5000.0,
                ),
                (
                    "2026-08-18T10:31:00-03:00",
                    2,
                    5300.0,
                ),
            ],
            entry_price=5000.0,
        ),
        trajectory_legacy,
    )

    experiment = (
        _experiment()
    )

    valid_experiments = (
        tmp_path
        / "research"
        / "valid_experiments.parquet"
    )

    _write_experiment(
        valid_experiments,
        experiment,
    )

    #
    # Manifest do Dataset A.
    #
    # A trajectory_path é física e aponta
    # exclusivamente para o Dataset A.
    #
    session_a = {
        "date": date,
        "source_parquet": (
            source_name
        ),
        "trade1_status": (
            "TRADE_1"
        ),
        "direction": "LONG",
        "entry_price": 1000.0,
        "entry_timestamp": (
            "2026-08-18T10:30:00-03:00"
        ),
        "trajectory_exists": True,
        "trajectory_path": str(
            trajectory_a
        ),
        "trajectory_rows": 3,
        "mfe_points": 125.0,
        "mae_points": 0.0,
        "sha256": _sha256(
            trajectory_a
        ),
        "motor_version": (
            "stage22-isolation-motor"
        ),
    }

    trajectory_manifest = (
        tmp_path
        / "research"
        / "trajectory_manifest.parquet"
    )

    _write_manifest(
        trajectory_manifest,
        session_a,
    )

    #
    # O plano é construído a partir do manifest A.
    #
    units = build_execution_units(
        experiments=[
            experiment
        ],
        sessions=[
            session_a
        ],
    )

    assert len(
        units
    ) == 1

    #
    # Prova de lineage antes mesmo da execução:
    # o plano precisa carregar a trajetória A.
    #
    assert (
        Path(
            units[0][
                "trajectory_path"
            ]
        )
        == trajectory_a
    )

    assert (
        str(
            dataset_b
        )
        not in units[0][
            "trajectory_path"
        ]
    )

    assert (
        str(
            legacy
        )
        not in units[0][
            "trajectory_path"
        ]
    )

    planned = assign_batches(
        units=units,
        batch_size=1,
    )

    batch_id = planned[0][
        "batch_id"
    ]

    plan_path = (
        tmp_path
        / "research"
        / "batch_plan.parquet"
    )

    write_execution_plan(
        rows=planned,
        output_path=(
            plan_path
        ),
    )

    batches_dir = (
        tmp_path
        / "research"
        / "batches"
    )

    #
    # ========================================================
    # EXECUÇÃO REAL
    # ========================================================
    #
    # Nenhum monkeypatch no motor.
    #
    # normalized_dir aponta explicitamente
    # para Dataset A.
    #
    execute_batch(
        batch_id=batch_id,
        plan_path=(
            plan_path
        ),
        valid_experiments_path=(
            valid_experiments
        ),
        trajectory_manifest_path=(
            trajectory_manifest
        ),
        normalized_dir=(
            dataset_a
            / "normalized"
        ),
        batches_dir=(
            batches_dir
        ),
    )

    result_files = list(
        batches_dir.glob(
            "*.parquet"
        )
    )

    assert len(
        result_files
    ) == 1

    rows = (
        pq.read_table(
            result_files[0]
        )
        .to_pylist()
    )

    assert len(
        rows
    ) == 1

    result = rows[0]

    #
    # ========================================================
    # PROVA QUANTITATIVA DO UNIVERSO A
    # ========================================================
    #
    assert (
        result[
            "trade_status"
        ]
        == "TRADE_1"
    )

    assert (
        result[
            "direction"
        ]
        == "LONG"
    )

    assert (
        result[
            "runner"
        ]
        is True
    )

    assert (
        result[
            "runner_rule"
        ]
        == "CANDLE_BREAK_M5"
    )

    assert (
        result[
            "final_reason"
        ]
        == "EXIT_RUNNER_CANDLE"
    )

    assert (
        result[
            "final_price"
        ]
        == 1080.0
    )

    #
    # 70% sai em +125:
    #
    # 125 * 0.70 = 87.5
    #
    # 30% runner sai em +80:
    #
    # 80 * 0.30 = 24
    #
    # Total = 111.5 pontos ponderados.
    #
    assert (
        result[
            "trade1_result_points"
        ]
        == 111.5
    )

    assert (
        result[
            "total_weighted_points"
        ]
        == 111.5
    )

    #
    # Trade 2 foi explicitamente desligado.
    #
    assert (
        result[
            "trade2_occurred"
        ]
        is False
    )

    assert (
        result[
            "trade2_executed"
        ]
        is False
    )

    #
    # Lineage quantitativo deve continuar
    # apontando para a trajectory do A.
    #
    assert (
        result[
            "trajectory_sha256"
        ]
        == _sha256(
            trajectory_a
        )
    )

    assert (
        result[
            "trajectory_sha256"
        ]
        != _sha256(
            trajectory_b
        )
    )

    assert (
        result[
            "trajectory_sha256"
        ]
        != _sha256(
            trajectory_legacy
        )
    )
