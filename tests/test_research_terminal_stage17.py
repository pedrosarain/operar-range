from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from app import data_access
from app.data_access import (
    MONTHLY_SCOPE,
    OVERALL_SCOPE,
    YEARLY_SCOPE,
    available_columns,
    compare_experiments,
    downsample_dataframe,
    experiment_detail,
    rankings_for_scope,
    session_row,
    trajectory_chart_frame,
)
from app.formatting import (
    NA_TEXT,
    format_points,
    metric_value_or_status,
    numeric_difference,
)


def write_parquet(
    path: Path,
    rows: list[dict],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        rows
    )

    pq.write_table(
        table,
        path,
    )


def test_read_parquet_existing_dataset(
    tmp_path,
):
    path = (
        tmp_path
        / "sample.parquet"
    )

    write_parquet(
        path,
        [
            {
                "experiment_id":
                    "EXP-000001",
                "value": 10,
            },
            {
                "experiment_id":
                    "EXP-000002",
                "value": 20,
            },
        ],
    )

    dataframe = (
        data_access.read_parquet(
            path
        )
    )

    assert len(
        dataframe
    ) == 2

    assert list(
        dataframe[
            "experiment_id"
        ]
    ) == [
        "EXP-000001",
        "EXP-000002",
    ]


def test_read_parquet_missing_dataset(
    tmp_path,
):
    path = (
        tmp_path
        / "missing.parquet"
    )

    dataframe = (
        data_access.read_parquet(
            path
        )
    )

    assert isinstance(
        dataframe,
        pd.DataFrame,
    )

    assert dataframe.empty


def test_read_parquet_empty_dataset(
    tmp_path,
):
    path = (
        tmp_path
        / "empty.parquet"
    )

    table = pa.table(
        {
            "experiment_id":
                pa.array(
                    [],
                    type=pa.string(),
                )
        }
    )

    pq.write_table(
        table,
        path,
    )

    dataframe = (
        data_access.read_parquet(
            path
        )
    )

    assert dataframe.empty

    assert (
        "experiment_id"
        in dataframe.columns
    )


def test_available_columns():
    dataframe = pd.DataFrame(
        {
            "a": [1],
            "b": [2],
        }
    )

    result = available_columns(
        dataframe,
        [
            "a",
            "c",
            "b",
        ],
    )

    assert result == [
        "a",
        "b",
    ]


def test_experiment_detail(
    monkeypatch,
):
    experiments = pd.DataFrame(
        [
            {
                "experiment_id":
                    "EXP-000001",
                "experiment_name":
                    "TEST_A",
                "stop_points":
                    170.0,
            },
            {
                "experiment_id":
                    "EXP-000002",
                "experiment_name":
                    "TEST_B",
                "stop_points":
                    100.0,
            },
        ]
    )

    metrics = pd.DataFrame(
        [
            {
                "experiment_id":
                    "EXP-000001",
                "profit_factor":
                    1.5,
            },
            {
                "experiment_id":
                    "EXP-000002",
                "profit_factor":
                    None,
            },
        ]
    )

    monkeypatch.setattr(
        data_access,
        "experiments_table",
        lambda: experiments,
    )

    monkeypatch.setattr(
        data_access,
        "experiment_metrics",
        lambda: metrics,
    )

    detail = experiment_detail(
        "EXP-000001"
    )

    assert (
        detail[
            "experiment"
        ][
            "experiment_name"
        ]
        == "TEST_A"
    )

    assert (
        detail[
            "metrics"
        ][
            "profit_factor"
        ]
        == 1.5
    )


def test_compare_experiments(
    monkeypatch,
):
    def fake_detail(
        experiment_id,
    ):
        return {
            "experiment": {
                "experiment_id":
                    experiment_id,
            },
            "metrics": {
                "total_weighted_points":
                    (
                        100.0
                        if experiment_id
                        == "EXP-A"
                        else 50.0
                    )
            },
        }

    monkeypatch.setattr(
        data_access,
        "experiment_detail",
        fake_detail,
    )

    result = compare_experiments(
        "EXP-A",
        "EXP-B",
    )

    assert (
        result[
            "a"
        ][
            "experiment"
        ][
            "experiment_id"
        ]
        == "EXP-A"
    )

    assert (
        result[
            "b"
        ][
            "experiment"
        ][
            "experiment_id"
        ]
        == "EXP-B"
    )


def test_numeric_difference():
    assert (
        numeric_difference(
            100,
            75,
        )
        == 25.0
    )

    assert (
        numeric_difference(
            None,
            75,
        )
        is None
    )


def test_metric_unavailable_formatting():
    result = (
        metric_value_or_status(
            value=None,
            status="NO_LOSSES",
            formatter=format_points,
        )
    )

    assert result == "NO_LOSSES"


def test_metric_missing_without_status():
    result = (
        metric_value_or_status(
            value=None,
            status=None,
            formatter=format_points,
        )
    )

    assert result == NA_TEXT


def test_session_row_trade1(
    monkeypatch,
):
    dataframe = pd.DataFrame(
        [
            {
                "date":
                    "2026-08-18",
                "trade1_status":
                    "TRADE_1",
                "direction":
                    "BUY",
            },
            {
                "date":
                    "2026-08-19",
                "trade1_status":
                    "NO_TRADE_1",
                "direction":
                    None,
            },
        ]
    )

    monkeypatch.setattr(
        data_access,
        "trade1_database",
        lambda: dataframe,
    )

    row = session_row(
        "2026-08-18"
    )

    assert row is not None

    assert (
        row[
            "trade1_status"
        ]
        == "TRADE_1"
    )


def test_session_row_no_trade1(
    monkeypatch,
):
    dataframe = pd.DataFrame(
        [
            {
                "date":
                    "2026-08-19",
                "trade1_status":
                    "NO_TRADE_1",
                "direction":
                    None,
                "reason":
                    "NO_BREAKOUT",
            },
        ]
    )

    monkeypatch.setattr(
        data_access,
        "trade1_database",
        lambda: dataframe,
    )

    row = session_row(
        "2026-08-19"
    )

    assert row is not None

    assert (
        row[
            "trade1_status"
        ]
        == "NO_TRADE_1"
    )

    assert (
        row[
            "reason"
        ]
        == "NO_BREAKOUT"
    )


def test_trajectory_lazy_loading(
    monkeypatch,
    tmp_path,
):
    trajectory_path = (
        tmp_path
        / "trajectory.parquet"
    )

    write_parquet(
        trajectory_path,
        [
            {
                "timestamp":
                    "2026-08-18 10:30:00",
                "price":
                    120000.0,
            }
        ],
    )

    calls = {
        "count": 0,
    }

    monkeypatch.setattr(
        data_access,
        "trajectory_manifest_row",
        lambda date_value: {
            "date":
                date_value,
            "trajectory_path":
                str(
                    trajectory_path
                ),
        },
    )

    monkeypatch.setattr(
        data_access,
        "resolve_trajectory_path",
        lambda row: (
            trajectory_path
        ),
    )

    original = (
        data_access.read_trajectory
    )

    def counted_read(
        path,
    ):
        calls[
            "count"
        ] += 1

        return original(
            path
        )

    monkeypatch.setattr(
        data_access,
        "read_trajectory",
        counted_read,
    )

    assert (
        calls[
            "count"
        ]
        == 0
    )

    dataframe = (
        data_access
        .load_session_trajectory(
            "2026-08-18"
        )
    )

    assert (
        calls[
            "count"
        ]
        == 1
    )

    assert len(
        dataframe
    ) == 1


def test_downsampling_small_dataset():
    dataframe = pd.DataFrame(
        {
            "value": list(
                range(
                    10
                )
            )
        }
    )

    result = downsample_dataframe(
        dataframe,
        max_points=100,
    )

    assert len(
        result
    ) == 10


def test_downsampling_large_dataset():
    dataframe = pd.DataFrame(
        {
            "value": list(
                range(
                    10000
                )
            )
        }
    )

    result = downsample_dataframe(
        dataframe,
        max_points=500,
    )

    assert len(
        result
    ) <= 500

    assert (
        result.iloc[0][
            "value"
        ]
        == 0
    )

    assert (
        result.iloc[-1][
            "value"
        ]
        == 9999
    )


def test_downsampling_invalid_limit():
    dataframe = pd.DataFrame(
        {
            "value": [1, 2, 3],
        }
    )

    with pytest.raises(
        ValueError
    ):
        downsample_dataframe(
            dataframe,
            max_points=0,
        )


def test_trajectory_chart_frame():
    dataframe = pd.DataFrame(
        {
            "timestamp": [
                "2026-08-18 10:30:00",
                "2026-08-18 10:30:01",
            ],
            "price": [
                120000.0,
                120010.0,
            ],
        }
    )

    result = trajectory_chart_frame(
        dataframe,
        max_points=500,
    )

    assert list(
        result.columns
    ) == [
        "timestamp",
        "price",
    ]

    assert len(
        result
    ) == 2


def test_trajectory_chart_missing_columns():
    dataframe = pd.DataFrame(
        {
            "foo": [1],
            "bar": [2],
        }
    )

    result = trajectory_chart_frame(
        dataframe
    )

    assert result.empty


def test_rankings_scope_overall(
    monkeypatch,
):
    expected = pd.DataFrame(
        [
            {
                "ranking_type":
                    "EXPECTANCY",
            }
        ]
    )

    monkeypatch.setattr(
        data_access,
        "rankings_overall",
        lambda: expected,
    )

    result = rankings_for_scope(
        scope=OVERALL_SCOPE
    )

    assert result.equals(
        expected
    )


def test_rankings_scope_yearly(
    monkeypatch,
    tmp_path,
):
    fake_root = (
        tmp_path
        / "research"
    )

    expected_path = (
        fake_root
        / "stage16_validation"
        / "yearly_2026"
        / "experiment_rankings.parquet"
    )

    write_parquet(
        expected_path,
        [
            {
                "ranking_type":
                    "EXPECTANCY",
                "scope":
                    "YEARLY",
                "year":
                    2026,
            }
        ],
    )

    monkeypatch.setattr(
        data_access,
        "RESEARCH_ROOT",
        fake_root,
    )

    result = rankings_for_scope(
        scope=YEARLY_SCOPE,
        year=2026,
    )

    assert len(
        result
    ) == 1

    assert (
        result.iloc[0][
            "scope"
        ]
        == "YEARLY"
    )


def test_rankings_scope_monthly(
    monkeypatch,
    tmp_path,
):
    fake_root = (
        tmp_path
        / "research"
    )

    expected_path = (
        fake_root
        / "stage16_validation"
        / "monthly_2026_08"
        / "experiment_rankings.parquet"
    )

    write_parquet(
        expected_path,
        [
            {
                "ranking_type":
                    "EXPECTANCY",
                "scope":
                    "MONTHLY",
                "year":
                    2026,
                "month":
                    8,
            }
        ],
    )

    monkeypatch.setattr(
        data_access,
        "RESEARCH_ROOT",
        fake_root,
    )

    result = rankings_for_scope(
        scope=MONTHLY_SCOPE,
        year=2026,
        month=8,
    )

    assert len(
        result
    ) == 1

    assert (
        result.iloc[0][
            "scope"
        ]
        == "MONTHLY"
    )

    assert (
        result.iloc[0][
            "month"
        ]
        == 8
    )


def test_invalid_scope_returns_empty():
    result = rankings_for_scope(
        scope="INVALID_SCOPE"
    )

    assert result.empty