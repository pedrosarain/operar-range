from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import operar_range.research_engine as engine

from operar_range.management import (
    ManagementConfig,
)
from operar_range.research_engine import (
    ExperimentDefinition,
    config_sha256,
    validate_experiments,
)


def experiment(
    experiment_id: str,
    stop: float,
):
    return ExperimentDefinition(
        experiment_id=experiment_id,
        name=experiment_id,
        config=ManagementConfig(
            stop_points=stop,
            position_size=100,
        ),
    )


def test_config_hash_is_deterministic():
    config = ManagementConfig(
        stop_points=170,
        partial_1_points=125,
        partial_1_pct=70,
    )

    assert (
        config_sha256(config)
        == config_sha256(config)
    )


def test_config_change_changes_hash():
    first = ManagementConfig(
        stop_points=100
    )

    second = ManagementConfig(
        stop_points=170
    )

    assert (
        config_sha256(first)
        != config_sha256(second)
    )


def test_duplicate_ids_rejected():
    experiments = [
        ExperimentDefinition(
            "EXP-000001",
            "A",
            ManagementConfig(
                stop_points=100
            ),
        ),
        ExperimentDefinition(
            "EXP-000001",
            "B",
            ManagementConfig(
                stop_points=170
            ),
        ),
    ]

    with pytest.raises(ValueError):
        validate_experiments(
            experiments
        )


def create_manifest(
    path: Path,
):
    rows = [
        {
            "date": "2026-08-18",
            "source_parquet": (
                "winv26_ticks_"
                "20260818_enriched.parquet"
            ),
            "trade1_status": "TRADE_1",
            "direction": "LONG",
            "entry_price": 1000.0,
            "trajectory_exists": True,
            "trajectory_path": (
                "fake_trajectory.parquet"
            ),
            "mfe_points": 500.0,
            "mae_points": 100.0,
            "sha256": "a" * 64,
        },
        {
            "date": "2026-08-19",
            "source_parquet": (
                "winv26_ticks_"
                "20260819_enriched.parquet"
            ),
            "trade1_status": "NO_TRADE_1",
            "direction": None,
            "entry_price": None,
            "trajectory_exists": False,
            "trajectory_path": None,
            "mfe_points": None,
            "mae_points": None,
            "sha256": None,
        },
    ]

    table = pa.Table.from_pylist(
        rows
    )

    pq.write_table(
        table,
        path,
    )


def fake_trajectory():
    return [
        {
            "timestamp": (
                "2026-08-18T10:30:00-03:00"
            ),
            "trade_number": 1,
            "price": 1000.0,
        },
        {
            "timestamp": (
                "2026-08-18T10:31:00-03:00"
            ),
            "trade_number": 2,
            "price": 1100.0,
        },
    ]


def fake_management(
    *,
    trajectory,
    date,
    direction,
    entry_price,
    config,
    runner_candles=None,
):
    return {
        "total_weighted_points": (
            config.stop_points
        ),
        "final_reason": "TEST",
        "final_timestamp": (
            trajectory[-1][
                "timestamp"
            ]
        ),
        "final_price": (
            trajectory[-1]["price"]
        ),
    }


def test_multiple_experiments_and_sessions(
    monkeypatch,
    tmp_path,
):
    manifest = (
        tmp_path / "manifest.parquet"
    )

    create_manifest(
        manifest
    )

    monkeypatch.setattr(
        engine,
        "read_trajectory_parquet",
        lambda path: fake_trajectory(),
    )

    monkeypatch.setattr(
        engine,
        "simulate_management",
        fake_management,
    )

    experiments = [
        experiment(
            "EXP-000001",
            100,
        ),
        experiment(
            "EXP-000002",
            170,
        ),
    ]

    result = engine.run_experiments(
        experiments=experiments,
        trajectory_manifest_path=manifest,
        normalized_dir=tmp_path,
        results_path=(
            tmp_path
            / "results.parquet"
        ),
        experiment_manifest_path=(
            tmp_path
            / "experiment_manifest.parquet"
        ),
    )

    assert len(
        result["results"]
    ) == 4

    assert len(
        result["manifest"]
    ) == 2


def test_no_trade_generates_record(
    monkeypatch,
    tmp_path,
):
    manifest = (
        tmp_path / "manifest.parquet"
    )

    create_manifest(
        manifest
    )

    monkeypatch.setattr(
        engine,
        "read_trajectory_parquet",
        lambda path: fake_trajectory(),
    )

    monkeypatch.setattr(
        engine,
        "simulate_management",
        fake_management,
    )

    result = engine.run_experiments(
        experiments=[
            experiment(
                "EXP-000001",
                100,
            )
        ],
        trajectory_manifest_path=manifest,
        normalized_dir=tmp_path,
        results_path=(
            tmp_path
            / "results.parquet"
        ),
        experiment_manifest_path=(
            tmp_path
            / "experiment_manifest.parquet"
        ),
    )

    rows = result["results"]

    no_trade = [
        row
        for row in rows
        if row["date"]
        == "2026-08-19"
    ][0]

    assert (
        no_trade["trade_status"]
        == "NO_TRADE_1"
    )

    assert (
        no_trade[
            "total_weighted_points"
        ]
        is None
    )


def test_reexecution_is_identical(
    monkeypatch,
    tmp_path,
):
    manifest = (
        tmp_path / "manifest.parquet"
    )

    create_manifest(
        manifest
    )

    monkeypatch.setattr(
        engine,
        "read_trajectory_parquet",
        lambda path: fake_trajectory(),
    )

    monkeypatch.setattr(
        engine,
        "simulate_management",
        fake_management,
    )

    experiments = [
        experiment(
            "EXP-000001",
            100,
        ),
        experiment(
            "EXP-000002",
            170,
        ),
    ]

    kwargs = {
        "experiments": experiments,
        "trajectory_manifest_path": (
            manifest
        ),
        "normalized_dir": tmp_path,
        "results_path": (
            tmp_path
            / "results.parquet"
        ),
        "experiment_manifest_path": (
            tmp_path
            / "experiment_manifest.parquet"
        ),
    }

    first = engine.run_experiments(
        **kwargs
    )

    second = engine.run_experiments(
        **kwargs
    )

    assert (
        first["results"]
        == second["results"]
    )

    assert (
        first["manifest"]
        == second["manifest"]
    )


def test_experiments_are_independent(
    monkeypatch,
    tmp_path,
):
    manifest = (
        tmp_path / "manifest.parquet"
    )

    create_manifest(
        manifest
    )

    monkeypatch.setattr(
        engine,
        "read_trajectory_parquet",
        lambda path: fake_trajectory(),
    )

    monkeypatch.setattr(
        engine,
        "simulate_management",
        fake_management,
    )

    result = engine.run_experiments(
        experiments=[
            experiment(
                "EXP-000001",
                100,
            ),
            experiment(
                "EXP-000002",
                170,
            ),
        ],
        trajectory_manifest_path=manifest,
        normalized_dir=tmp_path,
        results_path=(
            tmp_path
            / "results.parquet"
        ),
        experiment_manifest_path=(
            tmp_path
            / "experiment_manifest.parquet"
        ),
    )

    day_rows = [
        row
        for row in result["results"]
        if row["date"]
        == "2026-08-18"
    ]

    assert (
        day_rows[0][
            "total_weighted_points"
        ]
        == 100
    )

    assert (
        day_rows[1][
            "total_weighted_points"
        ]
        == 170
    )


def test_manifest_files_created(
    monkeypatch,
    tmp_path,
):
    manifest = (
        tmp_path / "manifest.parquet"
    )

    create_manifest(
        manifest
    )

    monkeypatch.setattr(
        engine,
        "read_trajectory_parquet",
        lambda path: fake_trajectory(),
    )

    monkeypatch.setattr(
        engine,
        "simulate_management",
        fake_management,
    )

    results_path = (
        tmp_path / "results.parquet"
    )

    experiments_path = (
        tmp_path
        / "experiment_manifest.parquet"
    )

    engine.run_experiments(
        experiments=[
            experiment(
                "EXP-000001",
                100,
            )
        ],
        trajectory_manifest_path=manifest,
        normalized_dir=tmp_path,
        results_path=results_path,
        experiment_manifest_path=(
            experiments_path
        ),
    )

    assert results_path.exists()
    assert experiments_path.exists()

    assert (
        pq.read_table(
            results_path
        ).num_rows
        == 2
    )

    assert (
        pq.read_table(
            experiments_path
        ).num_rows
        == 1
    )