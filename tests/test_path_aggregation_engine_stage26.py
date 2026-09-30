from __future__ import annotations

import hashlib
from pathlib import Path

import polars as pl
import pytest

import operar_range.path_aggregation_engine as engine


TARGETS = engine.TARGET_LEVELS
STOPS = engine.STOP_LEVELS


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


def _event_key(
    timestamp: str,
    trade_number: int,
) -> tuple[str, int]:
    return (
        timestamp,
        trade_number,
    )


def _path_rows(
    *,
    trade: str = "TRADE_1",
    target_before_zero: bool = False,
    no_zero: bool = False,
    target_not_reached: set[int] | None = None,
    stop_before_targets: bool = False,
) -> list[dict]:
    target_not_reached = (
        target_not_reached
        or set()
    )

    rows: list[dict] = []

    if target_before_zero:
        zero_timestamp = (
            "2026-01-01T10:00:03-03:00"
        )
        zero_trade_number = 30
        target_base_second = 1
    else:
        zero_timestamp = (
            "2026-01-01T10:00:01-03:00"
        )
        zero_trade_number = 10
        target_base_second = 3

    if no_zero:
        zero_timestamp = None
        zero_trade_number = None

    for target_index, target in enumerate(
        TARGETS,
        start=1,
    ):
        reached = (
            target
            not in target_not_reached
        )

        target_second = (
            target_base_second
            + target_index
        )

        target_timestamp = (
            (
                "2026-01-01T10:00:"
                f"{target_second:02d}-03:00"
            )
            if reached
            else None
        )

        target_trade_number = (
            100
            + target_index
            if reached
            else None
        )

        if not reached:
            relation = None

        elif no_zero:
            relation = None

        else:
            target_key = _event_key(
                target_timestamp,
                target_trade_number,
            )

            zero_key = _event_key(
                zero_timestamp,
                zero_trade_number,
            )

            relation = (
                "TARGET_BEFORE_FIRST_ZERO_RETURN"
                if target_key < zero_key
                else
                "TARGET_AFTER_FIRST_ZERO_RETURN"
            )

        for stop_index, stop in enumerate(
            STOPS,
            start=1,
        ):
            if stop_before_targets:
                stop_timestamp = (
                    "2026-01-01T10:00:00-03:00"
                )
                stop_trade_number = (
                    50
                    + stop_index
                )
            else:
                stop_timestamp = (
                    "2026-01-01T10:01:"
                    f"{stop_index:02d}-03:00"
                )
                stop_trade_number = (
                    1000
                    + stop_index
                )

            stop_reached = True

            if reached:
                stop_key = _event_key(
                    stop_timestamp,
                    stop_trade_number,
                )
                target_key = _event_key(
                    target_timestamp,
                    target_trade_number,
                )

                stop_before_target = (
                    stop_key
                    < target_key
                )

                stop_after_target = (
                    stop_key
                    > target_key
                )

            else:
                #
                # O target nunca ocorreu.
                # Um stop atingido é anterior à
                # obtenção daquele target.
                #
                stop_before_target = True
                stop_after_target = False

            rows.append(
                {
                    "research_id": "RES-TEST",
                    "dataset_id": "DS-TEST",
                    "experiment_id": "EXP-TEST",
                    "config_sha256": "CONFIG",
                    "motor_version": "MOTOR",
                    "rules_version": "RULES",
                    "trajectory_sha256": "TRAJECTORY",
                    "path_analysis_version": (
                        "quantitative-path-analysis-v1"
                    ),
                    "session_date": "2026-01-01",
                    "trade": trade,
                    "direction": "LONG",
                    "entry_price": 1000.0,
                    "entry_timestamp": (
                        "2026-01-01T10:00:00-03:00"
                    ),
                    "entry_trade_number": 1,
                    "trade2_eligible": (
                        trade == "TRADE_2"
                    ),
                    "trade2_occurred": (
                        trade == "TRADE_2"
                    ),
                    "trade2_executed": (
                        trade == "TRADE_2"
                    ),
                    "first_zero_return_occurred": (
                        not no_zero
                    ),
                    "first_zero_return_timestamp": (
                        zero_timestamp
                    ),
                    "first_zero_return_trade_number": (
                        zero_trade_number
                    ),
                    "target_points": target,
                    "target_label": (
                        "1000+"
                        if target == 1000
                        else str(target)
                    ),
                    "target_reached": reached,
                    "target_timestamp": (
                        target_timestamp
                    ),
                    "target_trade_number": (
                        target_trade_number
                    ),
                    "target_zero_relation": (
                        relation
                    ),
                    "stop_points": stop,
                    "stop_reached": (
                        stop_reached
                    ),
                    "stop_timestamp": (
                        stop_timestamp
                    ),
                    "stop_trade_number": (
                        stop_trade_number
                    ),
                    "stop_before_target": (
                        stop_before_target
                    ),
                    "stop_after_target": (
                        stop_after_target
                    ),
                }
            )

    return rows


def _inputs(
    *,
    path_rows: list[dict],
    trade2: bool = False,
) -> dict:
    return {
        "paths": {},
        "root": Path("/tmp/unused"),
        "definition": {
            "dataset_id": "DS-TEST",
        },
        "dataset_id": "DS-TEST",
        "distributed_path": (
            Path(
                "/tmp/distributed.parquet"
            )
        ),
        "path_analysis_path": (
            Path(
                "/tmp/path_analysis.parquet"
            )
        ),
        "distributed": _distributed(
            trade2=trade2,
        ),
        "path_analysis": (
            pl.DataFrame(
                path_rows
            )
        ),
        "source_distributed_results_sha256": (
            "DISTRIBUTED_SHA"
        ),
        "source_path_analysis_sha256": (
            "PATH_SHA"
        ),
    }


def _build(
    monkeypatch,
    *,
    path_rows: list[dict],
    trade2: bool = False,
) -> dict[str, pl.DataFrame]:
    payload = _inputs(
        path_rows=path_rows,
        trade2=trade2,
    )

    monkeypatch.setattr(
        engine,
        "_require_inputs",
        lambda research_id: payload,
    )

    return engine.build_path_aggregation(
        "RES-TEST"
    )


def _target_row(
    result: dict[str, pl.DataFrame],
    target: int,
) -> dict:
    return (
        result[
            "target_analytics"
        ]
        .filter(
            pl.col(
                "target_points"
            )
            == target
        )
        .row(
            0,
            named=True,
        )
    )


def _matrix_row(
    result: dict[str, pl.DataFrame],
    *,
    target: int,
    stop: int,
) -> dict:
    return (
        result[
            "target_stop_matrix"
        ]
        .filter(
            (
                pl.col(
                    "target_points"
                )
                == target
            )
            & (
                pl.col(
                    "stop_points"
                )
                == stop
            )
        )
        .row(
            0,
            named=True,
        )
    )


def test_target_before_zero(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(
            target_before_zero=True,
        ),
    )

    row = _target_row(
        result,
        100,
    )

    assert (
        row[
            "target_before_first_zero_count"
        ]
        == 1
    )

    assert (
        row[
            "target_before_first_zero_denominator"
        ]
        == 1
    )

    assert (
        row[
            "target_before_first_zero_pct"
        ]
        == 100.0
    )


def test_target_after_zero(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(),
    )

    row = _target_row(
        result,
        100,
    )

    assert (
        row[
            "target_after_first_zero_count"
        ]
        == 1
    )

    assert (
        row[
            "target_after_first_zero_pct"
        ]
        == 100.0
    )


def test_target_then_zero(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(
            target_before_zero=True,
        ),
    )

    row = _target_row(
        result,
        100,
    )

    assert (
        row[
            "target_then_zero_count"
        ]
        == 1
    )

    assert (
        row[
            "target_then_zero_denominator"
        ]
        == 1
    )

    assert (
        row[
            "target_then_zero_pct"
        ]
        == 100.0
    )


def test_target_without_zero(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(
            no_zero=True,
        ),
    )

    row = _target_row(
        result,
        100,
    )

    assert (
        row[
            "target_then_zero_count"
        ]
        == 0
    )

    assert (
        row[
            "target_then_zero_pct"
        ]
        == 0.0
    )


def test_target_not_reached(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(
            target_not_reached={
                1000,
            },
        ),
    )

    row = _target_row(
        result,
        1000,
    )

    assert (
        row[
            "target_reached_count"
        ]
        == 0
    )

    assert (
        row[
            "target_never_reached_count"
        ]
        == 1
    )

    assert (
        row[
            "target_reached_pct"
        ]
        == 0.0
    )

    assert (
        row[
            "target_then_zero_pct"
        ]
        is None
    )

    assert (
        row[
            "target_then_zero_pct_status"
        ]
        == "NO_DENOMINATOR"
    )


def test_stop_after_target(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(),
    )

    row = _matrix_row(
        result,
        target=200,
        stop=175,
    )

    assert (
        row[
            "stop_after_target_count"
        ]
        == 1
    )

    assert (
        row[
            "stop_after_target_denominator"
        ]
        == 1
    )

    assert (
        row[
            "stop_after_target_pct"
        ]
        == 100.0
    )


def test_stop_before_target(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(
            stop_before_targets=True,
        ),
    )

    row = _matrix_row(
        result,
        target=200,
        stop=175,
    )

    assert (
        row[
            "stop_before_target_count"
        ]
        == 1
    )

    assert (
        row[
            "stop_before_target_denominator"
        ]
        == 1
    )

    assert (
        row[
            "stop_before_target_pct"
        ]
        == 100.0
    )


def test_matrix_complete(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(),
    )

    matrix = result[
        "target_stop_matrix"
    ]

    assert matrix.height == (
        len(TARGETS)
        * len(STOPS)
    )

    assert (
        matrix
        .unique(
            subset=[
                "experiment_id",
                "trade",
                "target_points",
                "stop_points",
            ]
        )
        .height
        == matrix.height
    )


def test_session_universe_denominators(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(),
    )

    row = _target_row(
        result,
        100,
    )

    assert (
        row[
            "sessions_total"
        ]
        == 2
    )

    assert (
        row[
            "valid_trade_sessions"
        ]
        == 1
    )

    assert (
        row[
            "no_trade_sessions"
        ]
        == 1
    )

    assert (
        row[
            "target_reached_denominator"
        ]
        == 1
    )


def test_percentage_formula(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(),
    )

    row = _target_row(
        result,
        100,
    )

    expected = (
        row[
            "target_reached_count"
        ]
        / row[
            "target_reached_denominator"
        ]
        * 100.0
    )

    assert (
        row[
            "target_reached_pct"
        ]
        == expected
    )


def test_percentage_zero_divisor():
    percentage, status = (
        engine._percentage(
            0,
            0,
        )
    )

    assert percentage is None
    assert status == "NO_DENOMINATOR"


def test_stop_before_any_target(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(
            stop_before_targets=True,
        ),
    )

    stops = result[
        "stop_analytics"
    ]

    row = (
        stops
        .filter(
            pl.col(
                "stop_points"
            )
            == 175
        )
        .row(
            0,
            named=True,
        )
    )

    assert (
        row[
            "stop_before_any_target_count"
        ]
        == 1
    )

    assert (
        row[
            "stop_before_any_target_denominator"
        ]
        == 1
    )

    assert (
        row[
            "stop_before_any_target_pct"
        ]
        == 100.0
    )


def test_trade2_absent(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(),
        trade2=False,
    )

    trade2 = result[
        "trade2_analytics"
    ]

    assert (
        trade2[
            "trade2_executed_count"
        ]
        .max()
        == 0
    )

    assert (
        trade2[
            "trade2_target_reached_count"
        ]
        .max()
        == 0
    )

    assert (
        trade2[
            "trade2_target_reached_pct"
        ]
        .null_count()
        == trade2.height
    )

    assert (
        trade2[
            "trade2_target_reached_pct_status"
        ]
        .unique()
        .to_list()
        == [
            "NO_DENOMINATOR",
        ]
    )


def test_trade2_existing_controlled(
    monkeypatch,
):
    rows = (
        _path_rows()
        + _path_rows(
            trade="TRADE_2",
            target_before_zero=True,
        )
    )

    result = _build(
        monkeypatch,
        path_rows=rows,
        trade2=True,
    )

    trade2 = result[
        "trade2_analytics"
    ]

    row = (
        trade2
        .filter(
            (
                pl.col(
                    "trade1_stop_points"
                )
                == 175
            )
            & (
                pl.col(
                    "trade2_target_points"
                )
                == 100
            )
            & (
                pl.col(
                    "trade2_stop_points"
                )
                == 175
            )
        )
        .row(
            0,
            named=True,
        )
    )

    assert (
        row[
            "trade2_executed_count"
        ]
        == 1
    )

    assert (
        row[
            "trade2_occurrence_numerator"
        ]
        == 1
    )

    assert (
        row[
            "trade2_occurrence_denominator"
        ]
        == 1
    )

    assert (
        row[
            "trade2_occurrence_pct"
        ]
        == 100.0
    )

    assert (
        row[
            "trade2_target_reached_count"
        ]
        == 1
    )

    assert (
        row[
            "trade2_target_reached_denominator"
        ]
        == 1
    )

    assert (
        row[
            "trade2_target_reached_pct"
        ]
        == 100.0
    )

    assert (
        row[
            "trade2_stop_reached_count"
        ]
        == 1
    )

    assert (
        row[
            "trade2_stop_reached_denominator"
        ]
        == 1
    )


def test_trade2_return_to_entry(
    monkeypatch,
):
    rows = (
        _path_rows()
        + _path_rows(
            trade="TRADE_2",
            target_before_zero=True,
        )
    )

    result = _build(
        monkeypatch,
        path_rows=rows,
        trade2=True,
    )

    row = (
        result[
            "trade2_analytics"
        ]
        .row(
            0,
            named=True,
        )
    )

    assert (
        row[
            "trade2_return_to_entry_count"
        ]
        == 1
    )

    assert (
        row[
            "trade2_return_to_entry_denominator"
        ]
        == 1
    )

    assert (
        row[
            "trade2_return_to_entry_pct"
        ]
        == 100.0
    )


def test_lineage(
    monkeypatch,
):
    result = _build(
        monkeypatch,
        path_rows=_path_rows(),
    )

    for dataframe in result.values():
        row = dataframe.row(
            0,
            named=True,
        )

        assert (
            row[
                "research_id"
            ]
            == "RES-TEST"
        )

        assert (
            row[
                "dataset_id"
            ]
            == "DS-TEST"
        )

        assert (
            row[
                "experiment_id"
            ]
            == "EXP-TEST"
        )

        assert (
            row[
                "config_sha256"
            ]
            == "CONFIG"
        )

        assert (
            row[
                "source_path_analysis_sha256"
            ]
            == "PATH_SHA"
        )

        assert (
            row[
                "source_distributed_results_sha256"
            ]
            == "DISTRIBUTED_SHA"
        )

        assert (
            row[
                "aggregation_version"
            ]
            == engine.PATH_AGGREGATION_VERSION
        )


def test_build_is_deterministic(
    monkeypatch,
):
    first = _build(
        monkeypatch,
        path_rows=_path_rows(),
    )

    second = _build(
        monkeypatch,
        path_rows=_path_rows(),
    )

    assert (
        first.keys()
        == second.keys()
    )

    for key in first:
        assert (
            first[key]
            .to_dicts()
            == second[key]
            .to_dicts()
        )


def _sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as fh:
        for chunk in iter(
            lambda: fh.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def test_deterministic_parquet_writer(
    tmp_path,
):
    dataframe = pl.DataFrame(
        {
            "a": [
                1,
                2,
                3,
            ],
            "b": [
                "x",
                "y",
                "z",
            ],
        }
    )

    first = (
        tmp_path
        / "first.parquet"
    )

    second = (
        tmp_path
        / "second.parquet"
    )

    engine._write_parquet_deterministic(
        dataframe,
        first,
    )

    engine._write_parquet_deterministic(
        dataframe,
        second,
    )

    assert (
        _sha256(
            first
        )
        == _sha256(
            second
        )
    )


def test_artifact_names_are_stage26_specific():
    assert (
        engine.TARGET_ANALYTICS_ARTIFACT
        == "path_target_analytics.parquet"
    )

    assert (
        engine.TARGET_STOP_MATRIX_ARTIFACT
        == "path_target_stop_matrix.parquet"
    )

    assert (
        engine.STOP_ANALYTICS_ARTIFACT
        == "path_stop_analytics.parquet"
    )

    assert (
        engine.TRADE2_ANALYTICS_ARTIFACT
        == "path_trade2_analytics.parquet"
    )


def test_stage25_artifact_not_output_target():
    outputs = {
        engine.TARGET_ANALYTICS_ARTIFACT,
        engine.TARGET_STOP_MATRIX_ARTIFACT,
        engine.STOP_ANALYTICS_ARTIFACT,
        engine.TRADE2_ANALYTICS_ARTIFACT,
    }

    assert (
        "path_analysis.parquet"
        not in outputs
    )
