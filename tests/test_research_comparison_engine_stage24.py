from __future__ import annotations

import hashlib
import json
from pathlib import Path

import polars as pl
import pytest

import operar_range.research_comparison_engine as engine


def _write_json(
    path: Path,
    value: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _write_parquet(
    path: Path,
    rows: list[dict],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pl.DataFrame(
        rows
    ).write_parquet(
        path
    )


def _sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def _paths(
    root: Path,
) -> dict[str, Path]:
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
        "metrics": (
            root
            / "experiment_metrics.parquet"
        ),
        "trade2_analytics": (
            root
            / "trade2_analytics.parquet"
        ),
        "consolidated_analytics": (
            root
            / (
                "trade_lifecycle_"
                "consolidated_analytics.parquet"
            )
        ),
        "lifecycle_comparison": (
            root
            / "trade1_vs_lifecycle_comparison.parquet"
        ),
        "experiment_manifest": (
            root
            / "experiment_manifest.parquet"
        ),
    }


def _valid_row(
    *,
    experiment_id: str,
    config_sha256: str,
    stop_points: float,
    identity_version: str = "CANONICAL_V2",
) -> dict:
    return {
        "experiment_id": experiment_id,
        "family": "STAGE24_TEST",
        "generation": 1,
        "experiment_name": (
            f"STAGE24_TEST_G1_{experiment_id}"
        ),
        "config_sha256": (
            config_sha256
        ),
        "config_identity_version": (
            identity_version
        ),
        "stop_points": (
            stop_points
        ),
        "partial_1_points": 125.0,
        "partial_1_pct": 70.0,
        "partial_2_points": None,
        "partial_2_pct": None,
        "partial_3_points": None,
        "partial_3_pct": None,
        "break_even_enabled": True,
        "break_even_after_partial": 1,
        "runner_enabled": False,
        "runner_pct": None,
        "runner_rule": None,
        "final_target_points": 400.0,
        "trade2_enabled": False,
        "trade2_management_mode": "INHERIT",
        "trade2_stop_mode": "INHERIT",
        "trade2_stop_points": None,
        "trade2_partial_1_mode": "INHERIT",
        "trade2_partial_1_points": None,
        "trade2_partial_1_pct": None,
        "trade2_partial_2_mode": "INHERIT",
        "trade2_partial_2_points": None,
        "trade2_partial_2_pct": None,
        "trade2_partial_3_mode": "INHERIT",
        "trade2_partial_3_points": None,
        "trade2_partial_3_pct": None,
        "trade2_break_even_mode": "INHERIT",
        "trade2_break_even_after_partial": None,
        "trade2_runner_mode": "INHERIT",
        "trade2_runner_pct": None,
        "trade2_runner_rule": None,
        "trade2_final_target_mode": "INHERIT",
        "trade2_final_target_points": None,
        "motor_version": "trade1-adr004",
        "rules_version": "ADR-004+STAGE10",
    }


def _metrics_row(
    *,
    experiment_id: str,
    config_sha256: str,
    result: float,
) -> dict:
    return {
        "experiment_id": experiment_id,
        "config_sha256": (
            config_sha256
        ),
        "motor_version": "trade1-adr004",
        "rules_version": "ADR-004+STAGE10",
        "sessions_total": 10,
        "trade1_count": 8,
        "no_trade1_count": 2,
        "total_weighted_points": result,
        "consolidated_total_result_points": (
            result + 10.0
        ),
        "winning_trades": 5,
        "losing_trades": 2,
        "breakeven_trades": 1,
        "win_rate_pct": 62.5,
        "loss_rate_pct": 25.0,
        "profit_factor": 2.0,
        "profit_factor_status": "OK",
        "payoff_ratio": 1.5,
        "payoff_ratio_status": "OK",
        "expectancy_points_per_trade": (
            result / 8.0
        ),
        "max_drawdown_points": 100.0,
        "max_drawdown_start_date": (
            "2026-01-01"
        ),
        "max_drawdown_end_date": (
            "2026-01-02"
        ),
    }


def _trade2_row(
    *,
    experiment_id: str,
    config_sha256: str,
) -> dict:
    return {
        "experiment_id": experiment_id,
        "config_sha256": (
            config_sha256
        ),
        "motor_version": "trade1-adr004",
        "rules_version": "ADR-004+STAGE10",
        "analytics_version": (
            "trade-lifecycle-analytics-v1"
        ),
        "sessions_total": 10,
        "trade2_eligible_count": 3,
        "trade2_occurred_count": 2,
        "trade2_executed_count": 2,
        "trade2_winning_count": 1,
        "trade2_losing_count": 1,
        "trade2_breakeven_count": 0,
        "trade2_runner_count": 0,
        "trade2_weighted_result_points": 20.0,
        "trade2_total_position_points": 20.0,
    }


def _consolidated_row(
    *,
    experiment_id: str,
    config_sha256: str,
    result: float,
) -> dict:
    return {
        "experiment_id": experiment_id,
        "config_sha256": (
            config_sha256
        ),
        "motor_version": "trade1-adr004",
        "rules_version": "ADR-004+STAGE10",
        "analytics_version": (
            "trade-lifecycle-analytics-v1"
        ),
        "total_cycles": 8,
        "cycles_with_trade2": 2,
        "cycles_without_trade2": 6,
        "trade2_pct": 25.0,
        "recovered_cycle_count": 1,
        "recovery_pct": 50.0,
        "total_result_points": (
            result + 10.0
        ),
        "expectancy_points_per_cycle": (
            (result + 10.0) / 8.0
        ),
        "winning_cycles": 5,
        "losing_cycles": 2,
        "breakeven_cycles": 1,
        "win_rate_pct": 62.5,
        "loss_rate_pct": 25.0,
        "breakeven_rate_pct": 12.5,
        "profit_factor": 2.1,
        "profit_factor_status": "OK",
        "payoff_ratio": 1.6,
        "payoff_ratio_status": "OK",
        "max_drawdown_points": 90.0,
        "max_drawdown_start_date": (
            "2026-01-01"
        ),
        "max_drawdown_end_date": (
            "2026-01-02"
        ),
    }


def _lifecycle_row(
    *,
    experiment_id: str,
    config_sha256: str,
    result: float,
) -> dict:
    return {
        "experiment_id": experiment_id,
        "config_sha256": (
            config_sha256
        ),
        "motor_version": "trade1-adr004",
        "rules_version": "ADR-004+STAGE10",
        "analytics_version": (
            "trade-lifecycle-analytics-v1"
        ),
        "trade1_total_result_points": result,
        "consolidated_total_result_points": (
            result + 10.0
        ),
        "difference_total_result_points": 10.0,
        "trade1_expectancy_points": (
            result / 8.0
        ),
        "consolidated_expectancy_points": (
            (result + 10.0) / 8.0
        ),
        "difference_expectancy_points": 1.25,
        "trade1_profit_factor": 2.0,
        "consolidated_profit_factor": 2.1,
        "difference_profit_factor": 0.1,
        "trade1_max_drawdown_points": 100.0,
        "consolidated_max_drawdown_points": 90.0,
        "difference_max_drawdown_points": -10.0,
        "trade1_win_rate_pct": 62.5,
        "consolidated_win_rate_pct": 62.5,
        "difference_win_rate_pct": 0.0,
    }


def _experiment_manifest_row(
    *,
    experiment_id: str,
    config_sha256: str,
) -> dict:
    return {
        "experiment_id": experiment_id,
        "name": (
            f"TEST_{experiment_id}"
        ),
        "config_json": "{}",
        "created_at": (
            "2026-09-30T00:00:00+00:00"
        ),
        "motor_version": "trade1-adr004",
        "rules_version": "ADR-004+STAGE10",
        "sessions_executed": 10,
        "config_sha256": (
            config_sha256
        ),
    }


def _create_research(
    root: Path,
    *,
    research_id: str,
    dataset_id: str,
    period_start: str,
    period_end: str,
    experiments: list[dict],
) -> dict[str, Path]:
    research_root = (
        root
        / research_id
    )

    paths = _paths(
        research_root
    )

    _write_json(
        paths[
            "definition"
        ],
        {
            "research_id": (
                research_id
            ),
            "dataset_id": (
                dataset_id
            ),
            "dataset_version": 1,
            "market": "B3",
            "asset": "WIN",
            "strategy": "TRADE_1",
            "family": "STAGE24_TEST",
            "generation": 1,
            "period_start": (
                period_start
            ),
            "period_end": (
                period_end
            ),
            "rules_version": (
                "ADR-004+STAGE10"
            ),
            "definition_status": "CREATED",
        },
    )

    _write_json(
        paths[
            "run_manifest"
        ],
        {
            "research_id": (
                research_id
            ),
            "dataset_id": (
                dataset_id
            ),
            "dataset_version": 1,
            "market": "B3",
            "asset": "WIN",
            "status": "COMPLETED",
            "current_stage": "COMPLETED",
        },
    )

    _write_parquet(
        paths[
            "valid"
        ],
        experiments,
    )

    metrics = []
    trade2 = []
    consolidated = []
    lifecycle = []
    manifest_rows = []

    for index, experiment in enumerate(
        experiments,
        start=1,
    ):
        experiment_id = str(
            experiment[
                "experiment_id"
            ]
        )

        config_hash = str(
            experiment[
                "config_sha256"
            ]
        )

        result = (
            100.0
            * index
        )

        metrics.append(
            _metrics_row(
                experiment_id=(
                    experiment_id
                ),
                config_sha256=(
                    config_hash
                ),
                result=result,
            )
        )

        trade2.append(
            _trade2_row(
                experiment_id=(
                    experiment_id
                ),
                config_sha256=(
                    config_hash
                ),
            )
        )

        consolidated.append(
            _consolidated_row(
                experiment_id=(
                    experiment_id
                ),
                config_sha256=(
                    config_hash
                ),
                result=result,
            )
        )

        lifecycle.append(
            _lifecycle_row(
                experiment_id=(
                    experiment_id
                ),
                config_sha256=(
                    config_hash
                ),
                result=result,
            )
        )

        manifest_rows.append(
            _experiment_manifest_row(
                experiment_id=(
                    experiment_id
                ),
                config_sha256=(
                    config_hash
                ),
            )
        )

    _write_parquet(
        paths[
            "metrics"
        ],
        metrics,
    )

    _write_parquet(
        paths[
            "trade2_analytics"
        ],
        trade2,
    )

    _write_parquet(
        paths[
            "consolidated_analytics"
        ],
        consolidated,
    )

    _write_parquet(
        paths[
            "lifecycle_comparison"
        ],
        lifecycle,
    )

    _write_parquet(
        paths[
            "experiment_manifest"
        ],
        manifest_rows,
    )

    return paths


@pytest.fixture()
def isolated_comparison(
    tmp_path,
    monkeypatch,
):
    workspace = (
        tmp_path
        / "workspace"
    )

    workspace.mkdir()

    def fake_paths(
        research_id: str,
    ) -> dict[str, Path]:
        return _paths(
            workspace
            / research_id
        )

    def fake_definition(
        research_id: str,
    ) -> dict:
        path = fake_paths(
            research_id
        )[
            "definition"
        ]

        if not path.exists():
            raise FileNotFoundError(
                path
            )

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    def fake_manifest(
        research_id: str,
    ) -> dict:
        path = fake_paths(
            research_id
        )[
            "run_manifest"
        ]

        if not path.exists():
            raise FileNotFoundError(
                path
            )

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    monkeypatch.setattr(
        engine,
        "research_paths",
        fake_paths,
    )

    monkeypatch.setattr(
        engine,
        "load_research_definition",
        fake_definition,
    )

    monkeypatch.setattr(
        engine,
        "load_research_manifest",
        fake_manifest,
    )

    return workspace


def test_single_experiment_research_matches_by_config(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-001",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-001",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    result = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-B",
    )

    assert result[
        "status"
    ] == "MATCHED_EXPERIMENTS"

    assert result[
        "counts"
    ][
        "matched_experiments"
    ] == 1

    matched = result[
        "matched_experiments"
    ][0]

    assert matched[
        "config_sha256"
    ] == "aaa"

    assert matched[
        "experiment_a_id"
    ] == "EXP-001"

    assert matched[
        "experiment_b_id"
    ] == "EXP-001"


def test_different_experiment_ids_same_config_match(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-001",
                config_sha256="same",
                stop_points=170.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-999",
                config_sha256="same",
                stop_points=170.0,
            ),
        ],
    )

    result = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-B",
    )

    matched = result[
        "matched_experiments"
    ]

    assert len(
        matched
    ) == 1

    assert matched[0][
        "experiment_a_id"
    ] == "EXP-001"

    assert matched[0][
        "experiment_b_id"
    ] == "EXP-999"


def test_multiple_experiments_complete_intersection(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A1",
                config_sha256="aaa",
                stop_points=150.0,
            ),
            _valid_row(
                experiment_id="EXP-A2",
                config_sha256="bbb",
                stop_points=170.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-B1",
                config_sha256="bbb",
                stop_points=170.0,
            ),
            _valid_row(
                experiment_id="EXP-B2",
                config_sha256="aaa",
                stop_points=150.0,
            ),
        ],
    )

    result = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-B",
    )

    assert result[
        "counts"
    ] == {
        "experiments_a": 2,
        "experiments_b": 2,
        "matched_experiments": 2,
        "only_in_a": 0,
        "only_in_b": 0,
        "identity_conflicts": 0,
    }

    assert {
        row[
            "config_sha256"
        ]
        for row in result[
            "matched_experiments"
        ]
    } == {
        "aaa",
        "bbb",
    }


def test_partial_intersection(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A1",
                config_sha256="aaa",
                stop_points=150.0,
            ),
            _valid_row(
                experiment_id="EXP-A2",
                config_sha256="bbb",
                stop_points=170.0,
            ),
            _valid_row(
                experiment_id="EXP-A3",
                config_sha256="ccc",
                stop_points=190.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-B1",
                config_sha256="aaa",
                stop_points=150.0,
            ),
            _valid_row(
                experiment_id="EXP-B2",
                config_sha256="ccc",
                stop_points=190.0,
            ),
            _valid_row(
                experiment_id="EXP-B3",
                config_sha256="ddd",
                stop_points=210.0,
            ),
        ],
    )

    result = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-B",
    )

    assert {
        row[
            "config_sha256"
        ]
        for row in result[
            "matched_experiments"
        ]
    } == {
        "aaa",
        "ccc",
    }

    assert [
        row[
            "config_sha256"
        ]
        for row in result[
            "only_in_a"
        ]
    ] == [
        "bbb",
    ]

    assert [
        row[
            "config_sha256"
        ]
        for row in result[
            "only_in_b"
        ]
    ] == [
        "ddd",
    ]


def test_no_intersection_is_not_error(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A",
                config_sha256="aaa",
                stop_points=150.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-B",
                config_sha256="bbb",
                stop_points=170.0,
            ),
        ],
    )

    result = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-B",
    )

    assert result[
        "status"
    ] == "NO_MATCHED_EXPERIMENTS"

    assert result[
        "matched_experiments"
    ] == []

    assert len(
        result[
            "only_in_a"
        ]
    ) == 1

    assert len(
        result[
            "only_in_b"
        ]
    ) == 1


def test_same_experiment_id_different_config_is_conflict(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-001",
                config_sha256="aaa",
                stop_points=150.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-001",
                config_sha256="bbb",
                stop_points=170.0,
            ),
        ],
    )

    result = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-B",
    )

    assert result[
        "matched_experiments"
    ] == []

    assert result[
        "counts"
    ][
        "identity_conflicts"
    ] == 1

    conflict = result[
        "identity_conflicts"
    ][0]

    assert conflict[
        "status"
    ] == "IDENTITY_CONFLICT"

    assert conflict[
        "experiment_id"
    ] == "EXP-001"

    assert conflict[
        "config_sha256_a"
    ] == "aaa"

    assert conflict[
        "config_sha256_b"
    ] == "bbb"


def test_only_in_a_and_only_in_b(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A1",
                config_sha256="aaa",
                stop_points=150.0,
            ),
            _valid_row(
                experiment_id="EXP-A2",
                config_sha256="only-a",
                stop_points=160.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-B1",
                config_sha256="aaa",
                stop_points=150.0,
            ),
            _valid_row(
                experiment_id="EXP-B2",
                config_sha256="only-b",
                stop_points=180.0,
            ),
        ],
    )

    result = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-B",
    )

    assert result[
        "counts"
    ][
        "only_in_a"
    ] == 1

    assert result[
        "counts"
    ][
        "only_in_b"
    ] == 1


def test_explicit_different_configs_are_comparable(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A",
                config_sha256="aaa",
                stop_points=150.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-B",
                config_sha256="bbb",
                stop_points=170.0,
            ),
        ],
    )

    result = engine.compare_experiments(
        research_a_id="RES-A",
        experiment_a_id="EXP-A",
        research_b_id="RES-B",
        experiment_b_id="EXP-B",
    )

    assert result[
        "status"
    ] == "EXPLICIT_COMPARISON"

    assert result[
        "same_config"
    ] is False

    comparison = result[
        "comparison"
    ]

    assert comparison[
        "experiment_a"
    ][
        "configuration"
    ][
        "stop_points"
    ] == 150.0

    assert comparison[
        "experiment_b"
    ][
        "configuration"
    ][
        "stop_points"
    ] == 170.0

    assert comparison[
        "configuration_delta"
    ][
        "stop_points"
    ] == -20.0


def test_different_datasets_are_reported_not_blocked(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-A",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-B",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-B",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    result = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-B",
    )

    assert result[
        "same_dataset"
    ] is False

    assert result[
        "counts"
    ][
        "matched_experiments"
    ] == 1


def test_different_periods_are_reported_not_blocked(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-02-01",
        period_end="2026-02-28",
        experiments=[
            _valid_row(
                experiment_id="EXP-B",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    result = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-B",
    )

    assert result[
        "same_period"
    ] is False

    assert result[
        "counts"
    ][
        "matched_experiments"
    ] == 1


def test_same_research_is_supported(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    result = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-A",
    )

    assert result[
        "same_dataset"
    ] is True

    assert result[
        "same_period"
    ] is True

    assert result[
        "counts"
    ][
        "matched_experiments"
    ] == 1


def test_missing_research_raises(
    isolated_comparison,
):
    with pytest.raises(
        FileNotFoundError,
    ):
        engine.compare_researches(
            research_a_id="RES-MISSING",
            research_b_id="RES-MISSING-2",
        )


def test_missing_explicit_experiment_raises(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-B",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    with pytest.raises(
        ValueError,
        match="Experiment not found",
    ):
        engine.compare_experiments(
            research_a_id="RES-A",
            experiment_a_id="EXP-404",
            research_b_id="RES-B",
            experiment_b_id="EXP-B",
        )


def test_lineage_is_preserved(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-B",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    result = engine.compare_experiments(
        research_a_id="RES-A",
        experiment_a_id="EXP-A",
        research_b_id="RES-B",
        experiment_b_id="EXP-B",
    )

    left = result[
        "comparison"
    ][
        "experiment_a"
    ]

    identity = left[
        "identity"
    ]

    assert identity[
        "experiment_id"
    ] == "EXP-A"

    assert identity[
        "config_sha256"
    ] == "aaa"

    assert identity[
        "motor_version"
    ] == "trade1-adr004"

    assert identity[
        "rules_version"
    ] == "ADR-004+STAGE10"

    assert identity[
        "analytics_version"
    ] == (
        "trade-lifecycle-analytics-v1"
    )

    assert left[
        "research"
    ][
        "dataset_id"
    ] == "DS-1"


def test_lifecycle_analytics_are_consumed(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-B",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    result = engine.compare_experiments(
        research_a_id="RES-A",
        experiment_a_id="EXP-A",
        research_b_id="RES-B",
        experiment_b_id="EXP-B",
    )

    left = result[
        "comparison"
    ][
        "experiment_a"
    ]

    assert (
        left[
            "trade2_metrics"
        ][
            "trade2_executed_count"
        ]
        == 2
    )

    assert (
        left[
            "lifecycle_metrics"
        ][
            "total_cycles"
        ]
        == 8
    )

    assert (
        left[
            "lifecycle_comparison"
        ][
            "difference_total_result_points"
        ]
        == 10.0
    )


def test_query_engine_contract_is_preserved(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    result = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-A",
    )

    assert (
        result[
            "query_engine_version"
        ]
        == "research-query-engine-v1"
    )


def test_determinism(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A1",
                config_sha256="aaa",
                stop_points=150.0,
            ),
            _valid_row(
                experiment_id="EXP-A2",
                config_sha256="bbb",
                stop_points=170.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-B2",
                config_sha256="bbb",
                stop_points=170.0,
            ),
            _valid_row(
                experiment_id="EXP-B1",
                config_sha256="aaa",
                stop_points=150.0,
            ),
        ],
    )

    first = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-B",
    )

    second = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-B",
    )

    assert first == second


def test_idempotence(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-B",
                config_sha256="bbb",
                stop_points=190.0,
            ),
        ],
    )

    first = engine.compare_experiments(
        research_a_id="RES-A",
        experiment_a_id="EXP-A",
        research_b_id="RES-B",
        experiment_b_id="EXP-B",
    )

    second = engine.compare_experiments(
        research_a_id="RES-A",
        experiment_a_id="EXP-A",
        research_b_id="RES-B",
        experiment_b_id="EXP-B",
    )

    assert first == second


def test_read_only(
    isolated_comparison,
):
    root = isolated_comparison

    paths_a = _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    paths_b = _create_research(
        root,
        research_id="RES-B",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-B",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    files = sorted(
        [
            path
            for path in (
                list(
                    paths_a.values()
                )
                + list(
                    paths_b.values()
                )
            )
            if (
                path.is_file()
            )
        ],
        key=str,
    )

    before = {
        str(
            path
        ): _sha256(
            path
        )
        for path in files
    }

    engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-B",
    )

    engine.compare_experiments(
        research_a_id="RES-A",
        experiment_a_id="EXP-A",
        research_b_id="RES-B",
        experiment_b_id="EXP-B",
    )

    after = {
        str(
            path
        ): _sha256(
            path
        )
        for path in files
    }

    assert before == after


def test_engine_does_not_expose_ranking_or_winner(
    isolated_comparison,
):
    root = isolated_comparison

    _create_research(
        root,
        research_id="RES-A",
        dataset_id="DS-1",
        period_start="2026-01-01",
        period_end="2026-01-31",
        experiments=[
            _valid_row(
                experiment_id="EXP-A",
                config_sha256="aaa",
                stop_points=170.0,
            ),
        ],
    )

    result = engine.compare_researches(
        research_a_id="RES-A",
        research_b_id="RES-A",
    )

    serialized = json.dumps(
        result,
        sort_keys=True,
    ).lower()

    assert '"winner"' not in serialized
    assert '"best"' not in serialized
    assert '"ranking"' not in serialized
