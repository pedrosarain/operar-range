from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import operar_range.research_query_engine as query_engine


def _write_parquet(
    path: Path,
    rows: list[dict],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pq.write_table(
        pa.Table.from_pylist(
            rows
        ),
        path,
        compression="zstd",
    )


def _result_row(
    *,
    execution_unit_id: str,
    experiment_id: str,
    date: str,
    trade_status: str = "TRADE_1",
    direction: str | None = "LONG",
    trade1_result_points: float | None = 100.0,
    trade2_eligible: bool = False,
    trade2_executed: bool = False,
    trade2_winner: bool = False,
    trade2_loser: bool = False,
    trade2_breakeven: bool = False,
    trade2_result_points: float | None = None,
    consolidated_result_points: float | None = 100.0,
    final_reason: str | None = "FINAL_TARGET",
) -> dict:
    return {
        "execution_unit_id": (
            execution_unit_id
        ),
        "batch_id": "BATCH-1",
        "experiment_id": (
            experiment_id
        ),
        "management_name": (
            experiment_id
        ),
        "date": date,
        "trade_status": (
            trade_status
        ),
        "direction": direction,

        "stop_points": 170.0,

        "partial_1_points": 125.0,
        "partial_1_pct": 70.0,

        "partial_2_points": None,
        "partial_2_pct": None,

        "partial_3_points": None,
        "partial_3_pct": None,

        "break_even": True,
        "break_even_after_partial": 1,

        "runner": True,
        "runner_pct": 30.0,
        "runner_rule": (
            "CANDLE_BREAK_M5"
        ),

        "final_target": 400.0,
        "position_size": 100.0,

        "total_weighted_points": (
            trade1_result_points
        ),
        "trade1_result_points": (
            trade1_result_points
        ),

        "trade2_eligible": (
            trade2_eligible
        ),
        "trade2_occurred": (
            trade2_executed
        ),
        "trade2_executed": (
            trade2_executed
        ),
        "trade2_winner": (
            trade2_winner
        ),
        "trade2_loser": (
            trade2_loser
        ),
        "trade2_breakeven": (
            trade2_breakeven
        ),
        "trade2_result_points": (
            trade2_result_points
        ),
        "consolidated_result_points": (
            consolidated_result_points
        ),

        "trade2_direction": None,
        "trade2_trigger_level": None,
        "trade2_entry_timestamp": None,
        "trade2_entry_trade_number": None,
        "trade2_first_traded_price": None,
        "trade2_jumped_entry_level": None,
        "trade2_reason": None,
        "trade2_final_reason": None,
        "trade2_final_timestamp": None,
        "trade2_final_price": None,
        "trade2_mfe": None,
        "trade2_mae": None,
        "trade2_management_json": None,
        "lifecycle_version": (
            "trade-lifecycle-v1"
        ),

        "final_reason": (
            final_reason
        ),
        "final_timestamp": None,
        "final_price": None,

        "mfe": 200.0,
        "mae": 50.0,

        "trajectory_sha256": (
            "a" * 64
        ),
        "config_sha256": (
            "b" * 64
        ),

        "motor_version": (
            "test-motor"
        ),
        "rules_version": (
            "test-rules"
        ),
    }


@pytest.fixture()
def query_workspace(
    tmp_path,
    monkeypatch,
):
    workspace_root = (
        tmp_path
        / "workspace"
    )

    workspace_root.mkdir()

    research_id = (
        "RES-STAGE23"
    )

    research_root = (
        workspace_root
        / research_id
    )

    research_root.mkdir()

    definition = {
        "research_id": (
            research_id
        ),
        "dataset_id": (
            "DS-STAGE23"
        ),
        "dataset_version": 1,
        "market": "B3",
        "asset": "WIN",
        "definition_status": (
            "CREATED"
        ),
    }

    manifest = {
        "research_id": (
            research_id
        ),
        "dataset_id": (
            "DS-STAGE23"
        ),
        "status": "COMPLETED",
    }

    (
        research_root
        / "research_definition.json"
    ).write_text(
        json.dumps(
            definition
        ),
        encoding="utf-8",
    )

    (
        research_root
        / "research_run_manifest.json"
    ).write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )

    valid_rows = [
        {
            "experiment_id": (
                "EXP-000001"
            ),
            "trade2_enabled": True,
        },
        {
            "experiment_id": (
                "EXP-000002"
            ),
            "trade2_enabled": False,
        },
    ]

    _write_parquet(
        research_root
        / "valid_experiments.parquet",
        valid_rows,
    )

    rows = [
        _result_row(
            execution_unit_id="EU-1",
            experiment_id=(
                "EXP-000001"
            ),
            date="2026-01-10",
            direction="LONG",
            trade1_result_points=(
                100.0
            ),
            consolidated_result_points=(
                100.0
            ),
        ),
        _result_row(
            execution_unit_id="EU-2",
            experiment_id=(
                "EXP-000001"
            ),
            date="2026-01-11",
            direction="LONG",
            trade1_result_points=(
                -170.0
            ),
            trade2_eligible=True,
            trade2_executed=True,
            trade2_winner=True,
            trade2_result_points=(
                200.0
            ),
            consolidated_result_points=(
                30.0
            ),
            final_reason=(
                "STOP"
            ),
        ),
        _result_row(
            execution_unit_id="EU-3",
            experiment_id=(
                "EXP-000001"
            ),
            date="2026-02-05",
            direction="SHORT",
            trade1_result_points=(
                0.0
            ),
            trade2_eligible=True,
            trade2_executed=True,
            trade2_breakeven=True,
            trade2_result_points=(
                0.0
            ),
            consolidated_result_points=(
                0.0
            ),
            final_reason=(
                "BREAK_EVEN"
            ),
        ),
        _result_row(
            execution_unit_id="EU-4",
            experiment_id=(
                "EXP-000002"
            ),
            date="2025-12-20",
            direction="SHORT",
            trade1_result_points=(
                -170.0
            ),
            trade2_eligible=True,
            trade2_executed=True,
            trade2_loser=True,
            trade2_result_points=(
                -170.0
            ),
            consolidated_result_points=(
                -340.0
            ),
            final_reason=(
                "STOP"
            ),
        ),
        _result_row(
            execution_unit_id="EU-5",
            experiment_id=(
                "EXP-000002"
            ),
            date="2026-02-06",
            direction="LONG",
            trade1_result_points=(
                250.0
            ),
            consolidated_result_points=(
                250.0
            ),
            final_reason=(
                "EXIT_RUNNER_CANDLE"
            ),
        ),
        _result_row(
            execution_unit_id="EU-6",
            experiment_id=(
                "EXP-000002"
            ),
            date="2026-02-07",
            trade_status=(
                "NO_TRADE_1"
            ),
            direction=None,
            trade1_result_points=None,
            consolidated_result_points=None,
            final_reason=None,
        ),
    ]

    _write_parquet(
        research_root
        / (
            "distributed_"
            "experiment_results.parquet"
        ),
        rows,
    )

    def fake_paths(
        requested_id: str,
    ):
        root = (
            workspace_root
            / requested_id
        )

        return {
            "root": root,
            "definition": (
                root
                / "research_definition.json"
            ),
            "run_manifest": (
                root
                / "research_run_manifest.json"
            ),
            "valid": (
                root
                / "valid_experiments.parquet"
            ),
            "distributed_results": (
                root
                / (
                    "distributed_"
                    "experiment_results.parquet"
                )
            ),
        }

    def fake_definition(
        requested_id: str,
    ):
        path = (
            fake_paths(
                requested_id
            )[
                "definition"
            ]
        )

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    def fake_manifest(
        requested_id: str,
    ):
        path = (
            fake_paths(
                requested_id
            )[
                "run_manifest"
            ]
        )

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    monkeypatch.setattr(
        query_engine,
        "research_paths",
        fake_paths,
    )

    monkeypatch.setattr(
        query_engine,
        "load_research_definition",
        fake_definition,
    )

    monkeypatch.setattr(
        query_engine,
        "load_research_manifest",
        fake_manifest,
    )

    return {
        "research_id": (
            research_id
        ),
        "root": research_root,
    }


def _query(
    query_workspace,
    **kwargs,
):
    return query_engine.execute_query(
        query_engine.ResearchQuery(
            research_id=(
                query_workspace[
                    "research_id"
                ]
            ),
            **kwargs,
        )
    )


def _ids(
    result,
) -> list[str]:
    if not result[
        "rows_found"
    ]:
        return []

    return (
        result[
            "rows"
        ][
            "execution_unit_id"
        ]
        .to_list()
    )


def test_query_research_summary(
    query_workspace,
):
    result = _query(
        query_workspace
    )

    assert result[
        "research_id"
    ] == "RES-STAGE23"

    assert result[
        "dataset_id"
    ] == "DS-STAGE23"

    assert result[
        "sessions"
    ] == 6

    assert result[
        "experiments"
    ] == 2

    assert result[
        "rows_found"
    ] == 6


@pytest.mark.parametrize(
    (
        "outcome",
        "expected",
    ),
    [
        (
            "WIN",
            [
                "EU-1",
                "EU-5",
            ],
        ),
        (
            "LOSS",
            [
                "EU-4",
                "EU-2",
            ],
        ),
        (
            "BREAK_EVEN",
            [
                "EU-3",
            ],
        ),
        (
            "NO_TRADE",
            [
                "EU-6",
            ],
        ),
    ],
)
def test_trade1_outcome_filters(
    query_workspace,
    outcome,
    expected,
):
    result = _query(
        query_workspace,
        trade1_outcome=outcome,
    )

    assert _ids(
        result
    ) == expected


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "expected",
    ),
    [
        (
            "trade2_enabled",
            True,
            [
                "EU-1",
                "EU-2",
                "EU-3",
            ],
        ),
        (
            "trade2_enabled",
            False,
            [
                "EU-4",
                "EU-5",
                "EU-6",
            ],
        ),
        (
            "trade2_eligible",
            True,
            [
                "EU-4",
                "EU-2",
                "EU-3",
            ],
        ),
        (
            "trade2_executed",
            True,
            [
                "EU-4",
                "EU-2",
                "EU-3",
            ],
        ),
        (
            "trade2_winner",
            True,
            [
                "EU-2",
            ],
        ),
        (
            "trade2_loser",
            True,
            [
                "EU-4",
            ],
        ),
        (
            "trade2_breakeven",
            True,
            [
                "EU-3",
            ],
        ),
    ],
)
def test_trade2_filters(
    query_workspace,
    field,
    value,
    expected,
):
    result = _query(
        query_workspace,
        **{
            field: value,
        },
    )

    assert _ids(
        result
    ) == expected


def test_experiment_filter(
    query_workspace,
):
    result = _query(
        query_workspace,
        experiment_id=(
            "EXP-000001"
        ),
    )

    assert result[
        "experiments"
    ] == 1

    assert set(
        result[
            "rows"
        ][
            "experiment_id"
        ]
        .to_list()
    ) == {
        "EXP-000001",
    }


def test_date_filter(
    query_workspace,
):
    result = _query(
        query_workspace,
        date="2026-02-05",
    )

    assert _ids(
        result
    ) == [
        "EU-3",
    ]


def test_year_filter(
    query_workspace,
):
    result = _query(
        query_workspace,
        year=2025,
    )

    assert _ids(
        result
    ) == [
        "EU-4",
    ]


def test_month_filter(
    query_workspace,
):
    result = _query(
        query_workspace,
        month=2,
    )

    assert _ids(
        result
    ) == [
        "EU-3",
        "EU-5",
        "EU-6",
    ]


def test_direction_filter(
    query_workspace,
):
    result = _query(
        query_workspace,
        direction="SHORT",
    )

    assert _ids(
        result
    ) == [
        "EU-4",
        "EU-3",
    ]


@pytest.mark.parametrize(
    (
        "result_sign",
        "expected",
    ),
    [
        (
            "POSITIVE",
            [
                "EU-1",
                "EU-2",
                "EU-5",
            ],
        ),
        (
            "NEGATIVE",
            [
                "EU-4",
            ],
        ),
        (
            "ZERO",
            [
                "EU-3",
            ],
        ),
    ],
)
def test_result_sign_filters(
    query_workspace,
    result_sign,
    expected,
):
    result = _query(
        query_workspace,
        result_sign=(
            result_sign
        ),
    )

    assert _ids(
        result
    ) == expected


def test_runner_occurred_filter(
    query_workspace,
):
    occurred = _query(
        query_workspace,
        runner_occurred=True,
    )

    assert _ids(
        occurred
    ) == [
        "EU-5",
    ]

    not_occurred = _query(
        query_workspace,
        runner_occurred=False,
    )

    assert "EU-5" not in _ids(
        not_occurred
    )

    assert not_occurred[
        "rows_found"
    ] == 5


def test_combined_filters(
    query_workspace,
):
    result = _query(
        query_workspace,
        trade1_outcome="LOSS",
        trade2_executed=True,
        direction="LONG",
        year=2026,
        experiment_id=(
            "EXP-000001"
        ),
    )

    assert _ids(
        result
    ) == [
        "EU-2",
    ]


def test_empty_result(
    query_workspace,
):
    result = _query(
        query_workspace,
        trade1_outcome="LOSS",
        runner_occurred=True,
    )

    assert result[
        "rows_found"
    ] == 0

    assert result[
        "sessions"
    ] == 0

    assert result[
        "experiments"
    ] == 0

    assert isinstance(
        result[
            "rows"
        ],
        pl.DataFrame,
    )


def test_missing_research(
    query_workspace,
):
    with pytest.raises(
        FileNotFoundError,
        match="Research not found",
    ):
        query_engine.execute_query(
            query_engine.ResearchQuery(
                research_id=(
                    "RES-DOES-NOT-EXIST"
                )
            )
        )


def test_missing_experiment(
    query_workspace,
):
    with pytest.raises(
        ValueError,
        match="Experiment not found",
    ):
        _query(
            query_workspace,
            experiment_id=(
                "EXP-999999"
            ),
        )


def test_determinism_and_idempotence(
    query_workspace,
):
    query = (
        query_engine.ResearchQuery(
            research_id=(
                query_workspace[
                    "research_id"
                ]
            ),
            year=2026,
            direction="LONG",
        )
    )

    first = (
        query_engine.execute_query(
            query
        )
    )

    second = (
        query_engine.execute_query(
            query
        )
    )

    assert first[
        "rows"
    ].to_dicts() == second[
        "rows"
    ].to_dicts()

    assert first[
        "sessions"
    ] == second[
        "sessions"
    ]

    assert first[
        "experiments"
    ] == second[
        "experiments"
    ]

    assert first[
        "rows_found"
    ] == second[
        "rows_found"
    ]


def test_legacy_research_definition(
    query_workspace,
):
    path = (
        query_workspace[
            "root"
        ]
        / "research_definition.json"
    )

    definition = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    definition.pop(
        "definition_status",
        None,
    )

    definition[
        "status"
    ] = "CREATED"

    path.write_text(
        json.dumps(
            definition
        ),
        encoding="utf-8",
    )

    result = _query(
        query_workspace
    )

    assert result[
        "rows_found"
    ] == 6

    assert result[
        "dataset_id"
    ] == "DS-STAGE23"


def test_dataset_architecture_identity(
    query_workspace,
):
    result = _query(
        query_workspace,
        experiment_id=(
            "EXP-000002"
        ),
    )

    assert result[
        "research_id"
    ] == "RES-STAGE23"

    assert result[
        "dataset_id"
    ] == "DS-STAGE23"

    assert result[
        "experiments"
    ] == 1
