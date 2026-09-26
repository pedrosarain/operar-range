from __future__ import annotations

from datetime import date
from pathlib import Path

import pyarrow.parquet as pq

import operar_range.trajectory_cache as cache


def trajectory():
    return [
        {
            "timestamp": (
                "2026-08-18T10:30:00-03:00"
            ),
            "trade_number": 1,
            "price": 1000.0,
            "points_from_entry": 0.0,
            "favorable_excursion": 0.0,
            "adverse_excursion": 0.0,
        },
        {
            "timestamp": (
                "2026-08-18T10:30:01-03:00"
            ),
            "trade_number": 2,
            "price": 1100.0,
            "points_from_entry": 100.0,
            "favorable_excursion": 100.0,
            "adverse_excursion": 0.0,
        },
        {
            "timestamp": (
                "2026-08-18T10:30:02-03:00"
            ),
            "trade_number": 3,
            "price": 900.0,
            "points_from_entry": -100.0,
            "favorable_excursion": 100.0,
            "adverse_excursion": 100.0,
        },
    ]


def fake_trade(
    parquet_path,
    session_date,
):
    if session_date == date(
        2026,
        8,
        19,
    ):
        return {
            "date": "2026-08-19",
            "entry_found": False,
            "direction": None,
            "trajectory": [],
        }

    return {
        "date": "2026-08-18",
        "entry_found": True,
        "direction": "LONG",
        "entry_trigger_level": 1000.0,
        "entry_timestamp": (
            "2026-08-18T10:30:00-03:00"
        ),
        "mfe_points": 100.0,
        "mae_points": 100.0,
        "trajectory": trajectory(),
    }


def create_file(
    directory: Path,
    name: str,
):
    path = directory / name
    path.write_bytes(b"x")
    return path


def test_trade1_persists_trajectory(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        cache,
        "reconstruct_trade1",
        fake_trade,
    )

    parquet = create_file(
        tmp_path,
        "winv26_ticks_20260818_enriched.parquet",
    )

    trajectory_dir = (
        tmp_path / "trajectories"
    )

    record, checks = (
        cache.build_manifest_record(
            parquet,
            trajectory_dir,
        )
    )

    assert record[
        "trajectory_exists"
    ] is True

    assert record[
        "trade1_status"
    ] == "TRADE_1"

    assert record[
        "trajectory_rows"
    ] == 3

    assert Path(
        record["trajectory_path"]
    ).exists()

    assert all(
        checks.values()
    )


def test_no_trade1_creates_no_trajectory(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        cache,
        "reconstruct_trade1",
        fake_trade,
    )

    parquet = create_file(
        tmp_path,
        "winv26_ticks_20260819_enriched.parquet",
    )

    trajectory_dir = (
        tmp_path / "trajectories"
    )

    record, checks = (
        cache.build_manifest_record(
            parquet,
            trajectory_dir,
        )
    )

    assert record[
        "trade1_status"
    ] == "NO_TRADE_1"

    assert record[
        "trajectory_exists"
    ] is False

    assert record[
        "trajectory_path"
    ] is None

    assert record[
        "trajectory_rows"
    ] is None

    assert checks is None

    assert not (
        trajectory_dir
        / "winv26_trade1_20260819.parquet"
    ).exists()


def test_stale_no_trade1_file_removed(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        cache,
        "reconstruct_trade1",
        fake_trade,
    )

    parquet = create_file(
        tmp_path,
        "winv26_ticks_20260819_enriched.parquet",
    )

    trajectory_dir = (
        tmp_path / "trajectories"
    )

    trajectory_dir.mkdir()

    stale = (
        trajectory_dir
        / "winv26_trade1_20260819.parquet"
    )

    stale.write_bytes(
        b"stale"
    )

    cache.build_manifest_record(
        parquet,
        trajectory_dir,
    )

    assert not stale.exists()


def test_reload_integrity():
    original = trajectory()

    report = {
        "mfe_points": 100.0,
        "mae_points": 100.0,
    }

    checks = (
        cache.validate_trajectory_reload(
            original,
            list(original),
            report,
        )
    )

    assert all(
        checks.values()
    )


def test_hash_generated(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        cache,
        "reconstruct_trade1",
        fake_trade,
    )

    parquet = create_file(
        tmp_path,
        "winv26_ticks_20260818_enriched.parquet",
    )

    record, _ = (
        cache.build_manifest_record(
            parquet,
            tmp_path / "trajectories",
        )
    )

    assert record["sha256"]
    assert len(
        record["sha256"]
    ) == 64


def test_manifest_one_row_per_session(
    tmp_path,
):
    records = [
        {
            "date": "2026-08-18",
            "source_parquet": "a.parquet",
            "trade1_status": "TRADE_1",
            "direction": "LONG",
            "entry_price": 1000.0,
            "entry_timestamp": "x",
            "trajectory_exists": True,
            "trajectory_path": "t.parquet",
            "trajectory_rows": 3,
            "mfe_points": 100.0,
            "mae_points": 100.0,
            "first_timestamp": "a",
            "last_timestamp": "b",
            "file_size_bytes": 10,
            "sha256": "a" * 64,
            "motor_version": cache.MOTOR_VERSION,
        },
        {
            "date": "2026-08-19",
            "source_parquet": "b.parquet",
            "trade1_status": "NO_TRADE_1",
            "direction": None,
            "entry_price": None,
            "entry_timestamp": None,
            "trajectory_exists": False,
            "trajectory_path": None,
            "trajectory_rows": None,
            "mfe_points": None,
            "mae_points": None,
            "first_timestamp": None,
            "last_timestamp": None,
            "file_size_bytes": None,
            "sha256": None,
            "motor_version": cache.MOTOR_VERSION,
        },
    ]

    path = (
        tmp_path / "manifest.parquet"
    )

    cache.write_manifest(
        records,
        path,
    )

    table = pq.read_table(
        path
    )

    assert table.num_rows == 2

    rows = table.to_pylist()

    assert rows[0][
        "date"
    ] == "2026-08-18"

    assert rows[1][
        "date"
    ] == "2026-08-19"


def test_multiple_sessions(
    monkeypatch,
    tmp_path,
):
    normalized = (
        tmp_path / "normalized"
    )
    normalized.mkdir()

    create_file(
        normalized,
        "winv26_ticks_20260818_enriched.parquet",
    )

    create_file(
        normalized,
        "winv26_ticks_20260819_enriched.parquet",
    )

    monkeypatch.setattr(
        cache,
        "reconstruct_trade1",
        fake_trade,
    )

    result = (
        cache.run_trajectory_cache(
            normalized_dir=normalized,
            trajectory_dir=(
                tmp_path
                / "trajectories"
            ),
            manifest_path=(
                tmp_path
                / "manifest.parquet"
            ),
        )
    )

    assert len(
        result["records"]
    ) == 2

    assert result[
        "records"
    ][0]["trajectory_exists"] is True

    assert result[
        "records"
    ][1]["trajectory_exists"] is False


def test_idempotence(
    monkeypatch,
    tmp_path,
):
    normalized = (
        tmp_path / "normalized"
    )
    normalized.mkdir()

    create_file(
        normalized,
        "winv26_ticks_20260818_enriched.parquet",
    )

    monkeypatch.setattr(
        cache,
        "reconstruct_trade1",
        fake_trade,
    )

    kwargs = {
        "normalized_dir": normalized,
        "trajectory_dir": (
            tmp_path / "trajectories"
        ),
        "manifest_path": (
            tmp_path / "manifest.parquet"
        ),
    }

    first = (
        cache.run_trajectory_cache(
            **kwargs
        )
    )

    second = (
        cache.run_trajectory_cache(
            **kwargs
        )
    )

    assert (
        first["records"]
        == second["records"]
    )

    trajectory_files = list(
        (
            tmp_path
            / "trajectories"
        ).glob("*.parquet")
    )

    assert len(
        trajectory_files
    ) == 1