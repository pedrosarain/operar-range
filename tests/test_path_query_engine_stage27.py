from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

import operar_range.path_query_engine as engine


RID = "RES-TEST"
EID = "EXP-TEST"
DID = "DS-TEST"


def _path_rows() -> pl.DataFrame:
    rows: list[dict] = []

    for target in (100, 175, 200):
        for stop in (100, 175, 200):
            rows.append(
                {
                    "research_id": RID,
                    "dataset_id": DID,
                    "experiment_id": EID,
                    "config_sha256": "CONFIG",
                    "motor_version": "MOTOR",
                    "rules_version": "RULES",
                    "trajectory_sha256": "TRAJ",
                    "path_analysis_version": (
                        "quantitative-path-analysis-v1"
                    ),
                    "session_date": "2026-01-01",
                    "trade": "TRADE_1",
                    "direction": "LONG",
                    "entry_price": 1000.0,
                    "entry_timestamp": (
                        "2026-01-01T10:00:00-03:00"
                    ),
                    "entry_trade_number": 10,
                    "trade2_eligible": True,
                    "trade2_occurred": True,
                    "trade2_executed": True,
                    "first_zero_return_occurred": True,
                    "first_zero_return_timestamp": (
                        "2026-01-01T10:00:05-03:00"
                    ),
                    "first_zero_return_trade_number": 50,
                    "target_points": target,
                    "target_label": str(target),
                    "target_reached": True,
                    "target_timestamp": (
                        "2026-01-01T10:00:02-03:00"
                        if target == 100
                        else "2026-01-01T10:00:10-03:00"
                    ),
                    "target_trade_number": (
                        20
                        if target == 100
                        else 100
                    ),
                    "target_zero_relation": (
                        "TARGET_BEFORE_FIRST_ZERO_RETURN"
                        if target == 100
                        else "TARGET_AFTER_FIRST_ZERO_RETURN"
                    ),
                    "stop_points": stop,
                    "stop_reached": True,
                    "stop_timestamp": (
                        "2026-01-01T10:00:20-03:00"
                    ),
                    "stop_trade_number": 200,
                    "stop_before_target": False,
                    "stop_after_target": True,
                }
            )

    rows.append(
        {
            "research_id": RID,
            "dataset_id": DID,
            "experiment_id": EID,
            "config_sha256": "CONFIG",
            "motor_version": "MOTOR",
            "rules_version": "RULES",
            "trajectory_sha256": "TRAJ",
            "path_analysis_version": (
                "quantitative-path-analysis-v1"
            ),
            "session_date": "2026-01-01",
            "trade": "TRADE_2",
            "direction": "LONG",
            "entry_price": 1000.0,
            "entry_timestamp": (
                "2026-01-01T10:01:00-03:00"
            ),
            "entry_trade_number": 300,
            "trade2_eligible": True,
            "trade2_occurred": True,
            "trade2_executed": True,
            "first_zero_return_occurred": True,
            "first_zero_return_timestamp": (
                "2026-01-01T10:01:02-03:00"
            ),
            "first_zero_return_trade_number": 320,
            "target_points": 100,
            "target_label": "100",
            "target_reached": True,
            "target_timestamp": (
                "2026-01-01T10:01:03-03:00"
            ),
            "target_trade_number": 330,
            "target_zero_relation": (
                "TARGET_AFTER_FIRST_ZERO_RETURN"
            ),
            "stop_points": 100,
            "stop_reached": True,
            "stop_timestamp": (
                "2026-01-01T10:01:05-03:00"
            ),
            "stop_trade_number": 350,
            "stop_before_target": False,
            "stop_after_target": True,
        }
    )

    return pl.DataFrame(rows)


def _distributed() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "experiment_id": EID,
                "date": "2026-01-01",
                "trade_status": "TRADE_1",
                "trade2_eligible": True,
                "trade2_occurred": True,
                "trade2_executed": True,
                "trade2_entry_timestamp": (
                    "2026-01-01T10:01:00-03:00"
                ),
                "trade2_entry_trade_number": 300,
                "config_sha256": "CONFIG",
            },
            {
                "experiment_id": EID,
                "date": "2026-01-02",
                "trade_status": "NO_TRADE_1",
                "trade2_eligible": False,
                "trade2_occurred": False,
                "trade2_executed": False,
                "trade2_entry_timestamp": None,
                "trade2_entry_trade_number": None,
                "config_sha256": "CONFIG",
            },
        ]
    )


@pytest.fixture
def mock_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    trajectory_path = (
        tmp_path
        / "trajectory.parquet"
    )

    pl.DataFrame(
        {
            "timestamp": [
                "2026-01-01T10:00:00-03:00",
                "2026-01-01T10:00:01-03:00",
            ],
            "trade_number": [
                10,
                20,
            ],
            "price": [
                1000.0,
                1005.0,
            ],
        }
    ).write_parquet(
        trajectory_path
    )

    path_analysis = _path_rows()
    distributed = _distributed()

    loader_name = None

    for candidate in (
        "_require_research",
        "_load_inputs",
        "_require_inputs",
    ):
        if hasattr(
            engine,
            candidate,
        ):
            loader_name = candidate
            break

    if loader_name is None:
        pytest.fail(
            "Stage 27 input loader not found."
        )

    monkeypatch.setattr(
        engine,
        loader_name,
        lambda research_id: {
            "research_id": research_id,
            "dataset_id": DID,
            "path_analysis": path_analysis,
            "distributed": distributed,
            "trajectory_manifest": pl.DataFrame(
                [
                    {
                        "date": "2026-01-01",
                        "trajectory_exists": True,
                        "trajectory_path": str(
                            trajectory_path
                        ),
                    },
                    {
                        "date": "2026-01-02",
                        "trajectory_exists": False,
                        "trajectory_path": None,
                    },
                ]
            ),
        },
    )

    return {
        "path_analysis": path_analysis,
        "distributed": distributed,
        "trajectory_path": trajectory_path,
    }


def test_target_reached(mock_inputs):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_1",
            target_points=100,
            target_reached=True,
        )
    )

    assert result["sessions_found"] == 1
    assert result["sessions"] == [
        "2026-01-01"
    ]


def test_target_before_zero(mock_inputs):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_1",
            target_points=100,
            target_before_first_zero=True,
        )
    )

    assert result["sessions_found"] == 1


def test_target_after_zero(mock_inputs):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_1",
            target_points=175,
            target_after_first_zero=True,
        )
    )

    assert result["sessions_found"] == 1


def test_target_then_zero(mock_inputs):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_1",
            target_points=100,
            target_then_zero=True,
        )
    )

    assert result["sessions_found"] == 1


def test_stop_after_target(mock_inputs):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_1",
            target_points=200,
            stop_points=175,
            stop_after_target=True,
        )
    )

    assert result["sessions_found"] == 1


def test_stop_before_target_empty(mock_inputs):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_1",
            target_points=200,
            stop_points=175,
            stop_before_target=True,
        )
    )

    assert result["sessions_found"] == 0


def test_stop_reached(mock_inputs):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_1",
            stop_points=175,
            stop_reached=True,
        )
    )

    assert result["sessions_found"] == 1


def test_combined_filters(mock_inputs):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_1",
            direction="LONG",
            target_points=175,
            target_after_first_zero=True,
            stop_points=175,
            stop_after_target=True,
        )
    )

    assert result["sessions_found"] == 1


def test_trade2_query(mock_inputs):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_2",
            trade2_executed=True,
            trade2_target_points=100,
            trade2_target_reached=True,
            trade2_stop_points=100,
            trade2_stop_reached=True,
        )
    )

    assert result["sessions_found"] == 1


def test_empty_result(mock_inputs):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_1",
            direction="SHORT",
        )
    )

    assert result["sessions_found"] == 0
    assert result["rows_found"] == 0


def test_session_filter(mock_inputs):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_1",
            session_date="2026-01-01",
        )
    )

    assert result["sessions_found"] == 1


def test_session_detail(mock_inputs):
    result = engine.get_session_detail(
        research_id=RID,
        experiment_id=EID,
        session_date="2026-01-01",
    )

    assert result["found"] is True
    assert result["rows_found"] == 10


def test_no_trade_session_detail(mock_inputs):
    result = engine.get_session_detail(
        research_id=RID,
        experiment_id=EID,
        session_date="2026-01-02",
    )

    assert result["found"] is False
    assert result["rows_found"] == 0


def test_trajectory_resolution(mock_inputs):
    result = engine.resolve_trajectory(
        research_id=RID,
        session_date="2026-01-01",
    )

    assert result["trajectory_exists"] is True
    assert result["file_exists"] is True


def test_no_trade_trajectory_resolution(mock_inputs):
    result = engine.resolve_trajectory(
        research_id=RID,
        session_date="2026-01-02",
    )

    assert result["trajectory_exists"] is False


def test_determinism(mock_inputs):
    query = engine.PathQuery(
        research_id=RID,
        experiment_id=EID,
        trade="TRADE_1",
        target_points=175,
        stop_points=175,
        stop_after_target=True,
    )

    first = (
        engine.execute_path_query(
            query
        )
    )

    second = (
        engine.execute_path_query(
            query
        )
    )

    assert first == second


def test_lineage(mock_inputs):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_1",
            target_points=100,
        )
    )

    assert result["research_id"] == RID
    assert result["dataset_id"] == DID
    assert result["experiment_id"] == EID
    assert result["path_query_version"] == (
        engine.PATH_QUERY_VERSION
    )


def test_returns_records_not_only_count(
    mock_inputs,
):
    result = engine.execute_path_query(
        engine.PathQuery(
            research_id=RID,
            experiment_id=EID,
            trade="TRADE_1",
            target_points=100,
        )
    )

    assert result["rows_found"] > 0
    assert len(
        result["records"]
    ) > 0


def test_read_only_source_contract():
    source = Path(
        engine.__file__
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "write_parquet",
        "write_text",
        "write_bytes",
        ".mkdir(",
        ".unlink(",
        ".rename(",
    )

    for token in forbidden:
        assert token not in source


def test_public_contract():
    assert (
        engine.PATH_QUERY_VERSION
        == "path-query-drilldown-v1"
    )

    assert callable(
        engine.execute_path_query
    )

    assert callable(
        engine.get_session_detail
    )

    assert callable(
        engine.resolve_trajectory
    )
