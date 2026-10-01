from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import polars as pl
import pytest

import operar_range.path_aggregation_engine as aggregation
import operar_range.path_analysis_engine as analysis
import operar_range.path_query_engine as query_engine
from operar_range.path_query_engine import (
    PathQuery,
)
from operar_range.path_research_parameters import (
    DEFAULT_STOP_VALUES,
    DEFAULT_TARGET_VALUES,
    historical_default_grid,
    resolve_path_grid,
)
from operar_range.research_workspace import (
    research_definition_sha256,
)


def _trajectory() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "timestamp": (
                    "2026-01-01T10:00:00-03:00"
                ),
                "trade_number": 10,
                "price": 1000.0,
            },
            {
                "timestamp": (
                    "2026-01-01T10:00:01-03:00"
                ),
                "trade_number": 20,
                "price": 1285.0,
            },
            {
                "timestamp": (
                    "2026-01-01T10:00:02-03:00"
                ),
                "trade_number": 30,
                "price": 835.0,
            },
        ]
    )


def _path_frame(
    *,
    targets: tuple[int, ...],
    stops: tuple[int, ...],
    trade: str = "TRADE_1",
) -> pl.DataFrame:
    grid = resolve_path_grid(
        target_values=targets,
        stop_values=stops,
    )

    import json

    rows = analysis.analyze_trade_path(
        research_id="RES-TEST",
        dataset_id="DS-TEST",
        experiment_id="EXP-TEST",
        config_sha256="CONFIG",
        motor_version="MOTOR",
        rules_version="RULES",
        trajectory_sha256="TRAJECTORY",
        session_date="2026-01-01",
        trade=trade,
        direction="LONG",
        entry_price=1000.0,
        entry_timestamp=(
            "2026-01-01T10:00:00-03:00"
        ),
        entry_trade_number=10,
        trajectory=_trajectory(),
        trade2_eligible=(
            trade == "TRADE_2"
        ),
        trade2_occurred=(
            trade == "TRADE_2"
        ),
        trade2_executed=(
            trade == "TRADE_2"
        ),
        target_values=targets,
        stop_values=stops,
        target_values_lineage=json.dumps(
            list(
                grid.target_values
            ),
            separators=(",", ":"),
        ),
        stop_values_lineage=json.dumps(
            list(
                grid.stop_values
            ),
            separators=(",", ":"),
        ),
        trade2_target_values_effective_lineage=(
            json.dumps(
                list(
                    grid
                    .trade2_target_values_effective
                ),
                separators=(",", ":"),
            )
        ),
        trade2_stop_values_effective_lineage=(
            json.dumps(
                list(
                    grid
                    .trade2_stop_values_effective
                ),
                separators=(",", ":"),
            )
        ),
        trade2_target_grid_source=(
            grid.trade2_target_grid_source
        ),
        trade2_stop_grid_source=(
            grid.trade2_stop_grid_source
        ),
        parameter_definition_sha256=(
            grid.parameter_definition_sha256
        ),
    )

    return pl.DataFrame(
        rows
    )


def _distributed(
    *,
    trade2: bool = False,
) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "experiment_id": "EXP-TEST",
                "date": "2026-01-01",
                "trade_status": "TRADE_1",
                "config_sha256": "CONFIG",
                "motor_version": "MOTOR",
                "rules_version": "RULES",
                "trade2_eligible": trade2,
                "trade2_occurred": trade2,
                "trade2_executed": trade2,
            },
            {
                "experiment_id": "EXP-TEST",
                "date": "2026-01-02",
                "trade_status": "NO_TRADE_1",
                "config_sha256": "CONFIG",
                "motor_version": "MOTOR",
                "rules_version": "RULES",
                "trade2_eligible": False,
                "trade2_occurred": False,
                "trade2_executed": False,
            },
        ]
    )


def test_explicit_target_list():
    grid = resolve_path_grid(
        target_values=[
            300,
            100,
            200,
        ],
    )

    assert grid.target_values == (
        100,
        200,
        300,
    )


def test_target_range():
    grid = resolve_path_grid(
        target_start=100,
        target_end=200,
        target_step=25,
    )

    assert grid.target_values == (
        100,
        125,
        150,
        175,
        200,
    )


def test_explicit_stop_list():
    grid = resolve_path_grid(
        stop_values=[
            190,
            100,
            130,
            160,
        ],
    )

    assert grid.stop_values == (
        100,
        130,
        160,
        190,
    )


def test_stop_range():
    grid = resolve_path_grid(
        stop_start=100,
        stop_end=125,
        stop_step=5,
    )

    assert grid.stop_values == (
        100,
        105,
        110,
        115,
        120,
        125,
    )


def test_invalid_step():
    with pytest.raises(
        ValueError
    ):
        resolve_path_grid(
            stop_start=100,
            stop_end=200,
            stop_step=0,
        )


def test_start_greater_than_end():
    with pytest.raises(
        ValueError
    ):
        resolve_path_grid(
            target_start=300,
            target_end=100,
            target_step=25,
        )


def test_duplicates_removed():
    grid = resolve_path_grid(
        target_values=[
            100,
            100,
            150,
            150,
            200,
        ],
    )

    assert grid.target_values == (
        100,
        150,
        200,
    )


def test_deterministic_ordering():
    first = resolve_path_grid(
        target_values=[
            300,
            100,
            200,
        ],
        stop_values=[
            190,
            100,
            160,
            130,
        ],
    )

    second = resolve_path_grid(
        target_values=[
            200,
            300,
            100,
        ],
        stop_values=[
            130,
            190,
            100,
            160,
        ],
    )

    assert first.target_values == (
        second.target_values
    )

    assert first.stop_values == (
        second.stop_values
    )

    assert (
        first.parameter_definition_sha256
        == second.parameter_definition_sha256
    )


def test_historical_default():
    grid = historical_default_grid()

    assert grid.target_values == (
        DEFAULT_TARGET_VALUES
    )

    assert grid.stop_values == (
        DEFAULT_STOP_VALUES
    )

    assert grid.trade1_matrix_size == 65


def test_dynamic_cardinality():
    grid = resolve_path_grid(
        target_start=100,
        target_end=500,
        target_step=25,
        stop_start=100,
        stop_end=250,
        stop_step=5,
        valid_trade1_count=2,
    )

    assert grid.target_count == 17
    assert grid.stop_count == 31
    assert grid.trade1_matrix_size == 527
    assert (
        grid.estimated_trade1_path_rows
        == 1054
    )


def test_custom_285_target():
    frame = _path_frame(
        targets=(
            100,
            200,
            285,
        ),
        stops=(
            100,
            165,
        ),
    )

    assert 285 in (
        frame[
            "target_points"
        ]
        .unique()
        .to_list()
    )


def test_custom_165_stop():
    frame = _path_frame(
        targets=(
            100,
            200,
            285,
        ),
        stops=(
            100,
            165,
        ),
    )

    assert 165 in (
        frame[
            "stop_points"
        ]
        .unique()
        .to_list()
    )


def test_dynamic_analysis_cardinality():
    frame = _path_frame(
        targets=(
            100,
            150,
            200,
            300,
        ),
        stops=(
            100,
            130,
            160,
            190,
        ),
    )

    assert frame.height == 16


def test_aggregation_dynamic_grid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    path_frame = _path_frame(
        targets=(
            100,
            150,
            200,
            300,
        ),
        stops=(
            100,
            130,
            160,
            190,
        ),
    )

    distributed = _distributed()

    path_file = (
        tmp_path
        / "path_analysis.parquet"
    )

    distributed_file = (
        tmp_path
        / "distributed.parquet"
    )

    path_frame.write_parquet(
        path_file
    )

    distributed.write_parquet(
        distributed_file
    )

    monkeypatch.setattr(
        aggregation,
        "_require_inputs",
        lambda research_id: {
            "root": tmp_path,
            "dataset_id": "DS-TEST",
            "distributed": distributed,
            "path_analysis": path_frame,
            "source_path_analysis_sha256": (
                "PATH-SHA"
            ),
            "source_distributed_results_sha256": (
                "DIST-SHA"
            ),
        },
    )

    result = (
        aggregation.build_path_aggregation(
            "RES-TEST"
        )
    )

    assert (
        result[
            "target_analytics"
        ].height
        == 4
    )

    assert (
        result[
            "target_stop_matrix"
        ].height
        == 16
    )

    assert (
        result[
            "stop_analytics"
        ].height
        == 4
    )


def test_query_dynamic_grid(
    monkeypatch: pytest.MonkeyPatch,
):
    path_frame = _path_frame(
        targets=(
            100,
            200,
            285,
        ),
        stops=(
            100,
            165,
        ),
    )

    distributed = _distributed()

    monkeypatch.setattr(
        query_engine,
        "_require_research",
        lambda research_id: {
            "dataset_id": "DS-TEST",
            "path_analysis": path_frame,
            "distributed": distributed,
            "trajectory_manifest": (
                pl.DataFrame()
            ),
        },
    )

    result = (
        query_engine.execute_path_query(
            PathQuery(
                research_id="RES-TEST",
                experiment_id="EXP-TEST",
                trade="TRADE_1",
                target_points=285,
                stop_points=165,
            )
        )
    )

    assert result[
        "sessions_found"
    ] == 1

    assert result[
        "rows_found"
    ] == 1


def test_trade2_inherits_general_grid():
    grid = resolve_path_grid(
        target_values=[
            100,
            150,
            200,
            300,
        ],
        stop_values=[
            100,
            130,
            160,
            190,
        ],
    )

    assert (
        grid.trade2_target_values_effective
        == grid.target_values
    )

    assert (
        grid.trade2_stop_values_effective
        == grid.stop_values
    )

    assert (
        grid.trade2_target_grid_source
        == "INHERITED"
    )

    assert (
        grid.trade2_stop_grid_source
        == "INHERITED"
    )


def test_trade2_explicit_grid():
    grid = resolve_path_grid(
        target_values=[
            100,
            150,
            200,
            300,
        ],
        stop_values=[
            100,
            130,
            160,
            190,
        ],
        trade2_target_values=[
            100,
            125,
            175,
            400,
        ],
        trade2_stop_values=[
            120,
            150,
            170,
        ],
    )

    assert (
        grid.trade2_target_values_effective
        == (
            100,
            125,
            175,
            400,
        )
    )

    assert (
        grid.trade2_stop_values_effective
        == (
            120,
            150,
            170,
        )
    )

    assert grid.trade2_matrix_size == 12


def test_lineage_present_in_path_rows():
    frame = _path_frame(
        targets=(
            100,
            200,
            285,
        ),
        stops=(
            100,
            165,
        ),
    )

    required = {
        "path_parameter_version",
        "target_values",
        "stop_values",
        "trade2_target_values_effective",
        "trade2_stop_values_effective",
        "trade2_target_grid_source",
        "trade2_stop_grid_source",
        "parameter_definition_sha256",
    }

    assert required.issubset(
        set(
            frame.columns
        )
    )

    assert (
        frame[
            "parameter_definition_sha256"
        ]
        .n_unique()
        == 1
    )


def test_different_grids_have_different_parameter_hash():
    first = resolve_path_grid(
        target_values=[
            100,
            200,
        ],
        stop_values=[
            100,
            170,
        ],
    )

    second = resolve_path_grid(
        target_values=[
            100,
            150,
            200,
        ],
        stop_values=[
            100,
            170,
        ],
    )

    assert (
        first.parameter_definition_sha256
        != second.parameter_definition_sha256
    )


def test_research_identity_changes_with_grid():
    base = {
        "dataset_id": "DS-TEST",
        "strategy": "TRADE_1",
        "base_config": {
            "stop_points": None,
        },
        "parameter_definition": {
            "stop_points": {
                "values": [
                    170,
                ],
            },
        },
    }

    first = deepcopy(
        base
    )

    first[
        "path_parameters"
    ] = {
        "target_values": [
            100,
            200,
        ],
        "stop_values": [
            100,
            170,
        ],
    }

    second = deepcopy(
        base
    )

    second[
        "path_parameters"
    ] = {
        "target_values": [
            100,
            150,
            200,
        ],
        "stop_values": [
            100,
            170,
        ],
    }

    assert (
        research_definition_sha256(
            first
        )
        != research_definition_sha256(
            second
        )
    )


def test_historical_definition_hash_not_changed_by_absence_of_stage28():
    base = {
        "dataset_id": "DS-TEST",
        "strategy": "TRADE_1",
        "base_config": {
            "stop_points": None,
        },
        "parameter_definition": {
            "stop_points": {
                "values": [
                    170,
                ],
            },
        },
    }

    copy = deepcopy(
        base
    )

    assert (
        research_definition_sha256(
            base
        )
        == research_definition_sha256(
            copy
        )
    )


def test_grid_resolution_is_deterministic():
    first = resolve_path_grid(
        target_values=[
            300,
            100,
            200,
        ],
        stop_values=[
            190,
            100,
            160,
            130,
        ],
    )

    second = resolve_path_grid(
        target_values=[
            100,
            200,
            300,
        ],
        stop_values=[
            100,
            130,
            160,
            190,
        ],
    )

    assert first.to_dict() == (
        second.to_dict()
    )


def test_analyze_trade_path_idempotent():
    first = _path_frame(
        targets=(
            100,
            150,
            200,
            300,
        ),
        stops=(
            100,
            130,
            160,
            190,
        ),
    )

    second = _path_frame(
        targets=(
            100,
            150,
            200,
            300,
        ),
        stops=(
            100,
            130,
            160,
            190,
        ),
    )

    assert (
        first.to_dicts()
        == second.to_dicts()
    )


def test_workspace_contains_stage28_grid_contract():
    source = Path(
        "app/pages/new_research.py"
    ).read_text(
        encoding="utf-8"
    )

    required = (
        "stage28_use_historical_grid",
        "stage28_target_mode",
        "stage28_stop_mode",
        "stage28_trade2_override",
        "_path_parameters_from_state",
        "_render_path_grid_workspace",
    )

    for token in required:
        assert token in source


def test_path_query_workspace_uses_dynamic_grid():
    source = Path(
        "app/pages/path_query.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "_path_values" in source
    assert "available_targets" in source
    assert "available_stops" in source

    historical_literal = '''[
                    "ANY",
                    "100",
                    "125",
                    "150",
                    "175",
                    "200",
                    "250",
                    "300",
                    "350",
                    "400",
                    "500",
                    "600",
                    "800",
                    "1000",
                ]'''

    assert historical_literal not in source
