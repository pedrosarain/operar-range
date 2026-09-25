from __future__ import annotations

import pyarrow.parquet as pq

from operar_range.trajectory import (
    TRAJECTORY_SCHEMA,
    read_trajectory_parquet,
    write_trajectory_parquet,
)


def sample_trajectory():
    return [
        {
            "timestamp": (
                "2026-08-18T10:30:29.741000-03:00"
            ),
            "trade_number": 14559560,
            "price": 170480.0,
            "points_from_entry": 0.0,
            "favorable_excursion": 0.0,
            "adverse_excursion": 0.0,
        },
        {
            "timestamp": (
                "2026-08-18T10:30:29.752000-03:00"
            ),
            "trade_number": 14561090,
            "price": 170475.0,
            "points_from_entry": -5.0,
            "favorable_excursion": 0.0,
            "adverse_excursion": 5.0,
        },
        {
            "timestamp": (
                "2026-08-18T11:00:34.981000-03:00"
            ),
            "trade_number": 20519430,
            "price": 171500.0,
            "points_from_entry": 1020.0,
            "favorable_excursion": 1020.0,
            "adverse_excursion": 35.0,
        },
        {
            "timestamp": (
                "2026-08-18T17:11:55.949000-03:00"
            ),
            "trade_number": 43084750,
            "price": 169170.0,
            "points_from_entry": -1310.0,
            "favorable_excursion": 1020.0,
            "adverse_excursion": 1310.0,
        },
    ]


def test_save_and_reload_without_loss(
    tmp_path,
):
    trajectory = sample_trajectory()

    path = (
        tmp_path
        / "trajectory.parquet"
    )

    write_trajectory_parquet(
        trajectory,
        path,
    )

    reloaded = (
        read_trajectory_parquet(
            path
        )
    )

    assert len(reloaded) == len(
        trajectory
    )


def test_schema_preserved(
    tmp_path,
):
    path = (
        tmp_path
        / "trajectory.parquet"
    )

    write_trajectory_parquet(
        sample_trajectory(),
        path,
    )

    schema = (
        pq.read_schema(path)
    )

    assert schema.equals(
        TRAJECTORY_SCHEMA
    )


def test_first_record_identical(
    tmp_path,
):
    trajectory = sample_trajectory()

    path = (
        tmp_path
        / "trajectory.parquet"
    )

    write_trajectory_parquet(
        trajectory,
        path,
    )

    reloaded = (
        read_trajectory_parquet(
            path
        )
    )

    assert (
        reloaded[0]
        == trajectory[0]
    )


def test_last_record_identical(
    tmp_path,
):
    trajectory = sample_trajectory()

    path = (
        tmp_path
        / "trajectory.parquet"
    )

    write_trajectory_parquet(
        trajectory,
        path,
    )

    reloaded = (
        read_trajectory_parquet(
            path
        )
    )

    assert (
        reloaded[-1]
        == trajectory[-1]
    )


def test_mfe_identical_after_reload(
    tmp_path,
):
    trajectory = sample_trajectory()

    path = (
        tmp_path
        / "trajectory.parquet"
    )

    write_trajectory_parquet(
        trajectory,
        path,
    )

    reloaded = (
        read_trajectory_parquet(
            path
        )
    )

    original_mfe = max(
        row["favorable_excursion"]
        for row in trajectory
    )

    reloaded_mfe = max(
        row["favorable_excursion"]
        for row in reloaded
    )

    assert (
        reloaded_mfe
        == original_mfe
    )


def test_mae_identical_after_reload(
    tmp_path,
):
    trajectory = sample_trajectory()

    path = (
        tmp_path
        / "trajectory.parquet"
    )

    write_trajectory_parquet(
        trajectory,
        path,
    )

    reloaded = (
        read_trajectory_parquet(
            path
        )
    )

    original_mae = max(
        row["adverse_excursion"]
        for row in trajectory
    )

    reloaded_mae = max(
        row["adverse_excursion"]
        for row in reloaded
    )

    assert (
        reloaded_mae
        == original_mae
    )


def test_timestamps_preserved(
    tmp_path,
):
    trajectory = sample_trajectory()

    path = (
        tmp_path
        / "trajectory.parquet"
    )

    write_trajectory_parquet(
        trajectory,
        path,
    )

    reloaded = (
        read_trajectory_parquet(
            path
        )
    )

    assert [
        row["timestamp"]
        for row in reloaded
    ] == [
        row["timestamp"]
        for row in trajectory
    ]


def test_trade_numbers_preserved(
    tmp_path,
):
    trajectory = sample_trajectory()

    path = (
        tmp_path
        / "trajectory.parquet"
    )

    write_trajectory_parquet(
        trajectory,
        path,
    )

    reloaded = (
        read_trajectory_parquet(
            path
        )
    )

    assert [
        row["trade_number"]
        for row in reloaded
    ] == [
        row["trade_number"]
        for row in trajectory
    ]