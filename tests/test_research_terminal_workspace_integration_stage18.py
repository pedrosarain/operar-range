from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import app.data_access as data_access


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
        compression="zstd",
    )


@pytest.fixture()
def research_environment(
    tmp_path,
    monkeypatch,
):
    canonical_root = (
        tmp_path
        / "data"
        / "research"
    )

    research_root = (
        canonical_root
        / "workspace"
        / "RES-TEST"
    )

    canonical_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    research_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    canonical_metrics = (
        canonical_root
        / "experiment_metrics.parquet"
    )

    local_metrics = (
        research_root
        / "experiment_metrics.parquet"
    )

    canonical_rankings = (
        canonical_root
        / "experiment_rankings.parquet"
    )

    local_rankings = (
        research_root
        / "experiment_rankings.parquet"
    )

    canonical_manifest = (
        canonical_root
        / "ranking_manifest.parquet"
    )

    local_manifest = (
        research_root
        / "ranking_manifest.parquet"
    )

    canonical_results = (
        canonical_root
        / "experiment_results.parquet"
    )

    local_results = (
        research_root
        / "distributed_experiment_results.parquet"
    )

    canonical_valid = (
        canonical_root
        / "valid_experiments.parquet"
    )

    local_valid = (
        research_root
        / "valid_experiments.parquet"
    )

    canonical_trade1 = (
        canonical_root
        / "trade1_database.parquet"
    )

    canonical_trajectory_manifest = (
        canonical_root
        / "trade1_trajectory_manifest.parquet"
    )

    local_trajectory_manifest = (
        research_root
        / "trajectory_manifest.parquet"
    )

    write_parquet(
        canonical_metrics,
        [
            {
                "experiment_id": (
                    "EXP-CANONICAL"
                ),
                "value": 1.0,
            }
        ],
    )

    write_parquet(
        local_metrics,
        [
            {
                "experiment_id": (
                    "EXP-LOCAL"
                ),
                "value": 2.0,
            }
        ],
    )

    write_parquet(
        canonical_rankings,
        [
            {
                "ranking_type": (
                    "EXPECTANCY"
                ),
                "experiment_id": (
                    "EXP-CANONICAL"
                ),
            }
        ],
    )

    write_parquet(
        local_rankings,
        [
            {
                "ranking_type": (
                    "EXPECTANCY"
                ),
                "experiment_id": (
                    "EXP-LOCAL"
                ),
            }
        ],
    )

    write_parquet(
        canonical_manifest,
        [
            {
                "ranking_type": (
                    "EXPECTANCY"
                ),
                "ranking_id": (
                    "RANK-CANONICAL"
                ),
            }
        ],
    )

    write_parquet(
        local_manifest,
        [
            {
                "ranking_type": (
                    "EXPECTANCY"
                ),
                "ranking_id": (
                    "RANK-LOCAL"
                ),
            }
        ],
    )

    write_parquet(
        canonical_results,
        [
            {
                "experiment_id": (
                    "EXP-CANONICAL"
                ),
                "date": "2026-08-18",
            }
        ],
    )

    write_parquet(
        local_results,
        [
            {
                "experiment_id": (
                    "EXP-LOCAL"
                ),
                "date": "2026-08-18",
            }
        ],
    )

    write_parquet(
        canonical_valid,
        [
            {
                "experiment_id": (
                    "EXP-CANONICAL"
                ),
            }
        ],
    )

    write_parquet(
        local_valid,
        [
            {
                "experiment_id": (
                    "EXP-LOCAL"
                ),
            }
        ],
    )

    write_parquet(
        canonical_trade1,
        [
            {
                "date": "2026-08-17",
                "trade1_status": (
                    "TRADE_1"
                ),
            },
            {
                "date": "2026-08-18",
                "trade1_status": (
                    "TRADE_1"
                ),
            },
            {
                "date": "2026-08-19",
                "trade1_status": (
                    "NO_TRADE_1"
                ),
            },
            {
                "date": "2026-08-20",
                "trade1_status": (
                    "TRADE_1"
                ),
            },
        ],
    )

    write_parquet(
        canonical_trajectory_manifest,
        [
            {
                "date": "2026-08-18",
            }
        ],
    )

    write_parquet(
        local_trajectory_manifest,
        [
            {
                "date": "2026-08-18",
            },
            {
                "date": "2026-08-19",
            },
        ],
    )

    definition_path = (
        research_root
        / "research_definition.json"
    )

    definition_path.write_text(
        """
{
  "research_id": "RES-TEST",
  "period_start": "2026-08-18",
  "period_end": "2026-08-19"
}
""".strip(),
        encoding="utf-8",
    )

    ranking_summary = (
        research_root
        / "ranking_summary.json"
    )

    ranking_summary.write_text(
        """
{
  "scope": "OVERALL",
  "experiments_classified": 1
}
""".strip(),
        encoding="utf-8",
    )

    constraint_summary = (
        research_root
        / "constraint_engine_summary.json"
    )

    constraint_summary.write_text(
        """
{
  "valid_total": 1
}
""".strip(),
        encoding="utf-8",
    )

    paths = {
        "root": research_root,
        "definition": definition_path,
        "trajectory_manifest": (
            local_trajectory_manifest
        ),
        "valid": local_valid,
        "distributed_results": (
            local_results
        ),
        "metrics": local_metrics,
        "metrics_yearly": (
            research_root
            / "experiment_metrics_yearly.parquet"
        ),
        "metrics_monthly": (
            research_root
            / "experiment_metrics_monthly.parquet"
        ),
        "rankings": local_rankings,
        "ranking_manifest": (
            local_manifest
        ),
        "batch_plan": (
            research_root
            / "batch_execution_plan.parquet"
        ),
        "ranking_summary": (
            ranking_summary
        ),
        "constraint_summary": (
            constraint_summary
        ),
    }

    monkeypatch.setattr(
        data_access,
        "DATASETS",
        {
            "trade1_database": (
                canonical_trade1
            ),
            "trajectory_manifest": (
                canonical_trajectory_manifest
            ),
            "valid_experiments": (
                canonical_valid
            ),
            "experiment_results": (
                canonical_results
            ),
            "experiment_metrics": (
                canonical_metrics
            ),
            "experiment_metrics_yearly": (
                canonical_root
                / "experiment_metrics_yearly.parquet"
            ),
            "experiment_metrics_monthly": (
                canonical_root
                / "experiment_metrics_monthly.parquet"
            ),
            "experiment_rankings": (
                canonical_rankings
            ),
            "ranking_manifest": (
                canonical_manifest
            ),
            "batch_execution_plan": (
                canonical_root
                / "batch_execution_plan.parquet"
            ),
        },
    )

    monkeypatch.setattr(
        data_access,
        "REPORTS",
        {
            "ranking_summary": (
                canonical_root
                / "ranking_summary.json"
            ),
            "constraint_engine_summary": (
                canonical_root
                / "constraint_engine_summary.json"
            ),
        },
    )

    monkeypatch.setattr(
        data_access,
        "active_research_id",
        lambda: "RES-TEST",
    )

    monkeypatch.setattr(
        data_access,
        "active_research_paths",
        lambda: paths,
    )

    data_access.read_parquet.clear()
    data_access.read_json.clear()

    yield {
        "canonical_root": (
            canonical_root
        ),
        "research_root": (
            research_root
        ),
        "paths": paths,
    }

    data_access.read_parquet.clear()
    data_access.read_json.clear()


def test_active_research_reads_local_metrics(
    research_environment,
):
    dataframe = (
        data_access.experiment_metrics()
    )

    assert len(
        dataframe
    ) == 1

    assert (
        dataframe.iloc[0][
            "experiment_id"
        ]
        == "EXP-LOCAL"
    )


def test_active_research_reads_local_results(
    research_environment,
):
    dataframe = (
        data_access.experiment_results()
    )

    assert len(
        dataframe
    ) == 1

    assert (
        dataframe.iloc[0][
            "experiment_id"
        ]
        == "EXP-LOCAL"
    )


def test_active_research_reads_local_valid_experiments(
    research_environment,
):
    dataframe = (
        data_access.valid_experiments()
    )

    assert len(
        dataframe
    ) == 1

    assert (
        dataframe.iloc[0][
            "experiment_id"
        ]
        == "EXP-LOCAL"
    )


def test_active_research_reads_local_overall_rankings(
    research_environment,
):
    dataframe = (
        data_access.rankings_for_scope(
            scope="OVERALL",
        )
    )

    assert len(
        dataframe
    ) == 1

    assert (
        dataframe.iloc[0][
            "experiment_id"
        ]
        == "EXP-LOCAL"
    )


def test_active_research_reads_local_ranking_manifest(
    research_environment,
):
    dataframe = (
        data_access.ranking_manifest_for_scope(
            scope="OVERALL",
        )
    )

    assert len(
        dataframe
    ) == 1

    assert (
        dataframe.iloc[0][
            "ranking_id"
        ]
        == "RANK-LOCAL"
    )


def test_active_research_does_not_fallback_to_yearly_stage16(
    research_environment,
):
    dataframe = (
        data_access.rankings_for_scope(
            scope="YEARLY",
            year=2026,
        )
    )

    assert isinstance(
        dataframe,
        pd.DataFrame,
    )

    assert dataframe.empty


def test_active_research_does_not_fallback_to_monthly_stage16(
    research_environment,
):
    dataframe = (
        data_access.rankings_for_scope(
            scope="MONTHLY",
            year=2026,
            month=8,
        )
    )

    assert dataframe.empty


def test_active_research_manifest_does_not_fallback_temporally(
    research_environment,
):
    yearly = (
        data_access.ranking_manifest_for_scope(
            scope="YEARLY",
            year=2026,
        )
    )

    monthly = (
        data_access.ranking_manifest_for_scope(
            scope="MONTHLY",
            year=2026,
            month=8,
        )
    )

    assert yearly.empty
    assert monthly.empty


def test_trade1_database_is_filtered_to_research_period(
    research_environment,
):
    dataframe = (
        data_access.trade1_database()
    )

    dates = (
        dataframe[
            "date"
        ]
        .astype(str)
        .tolist()
    )

    assert dates == [
        "2026-08-18",
        "2026-08-19",
    ]


def test_local_trajectory_manifest_is_used(
    research_environment,
):
    dataframe = (
        data_access.trajectory_manifest()
    )

    assert len(
        dataframe
    ) == 2

    assert set(
        dataframe[
            "date"
        ].astype(str)
    ) == {
        "2026-08-18",
        "2026-08-19",
    }


def test_local_ranking_summary_is_used(
    research_environment,
):
    value = (
        data_access.report(
            "ranking_summary"
        )
    )

    assert (
        value[
            "experiments_classified"
        ]
        == 1
    )


def test_local_constraint_summary_is_used(
    research_environment,
):
    value = (
        data_access.report(
            "constraint_engine_summary"
        )
    )

    assert (
        value[
            "valid_total"
        ]
        == 1
    )


def test_missing_local_artifact_does_not_fallback_to_canonical(
    research_environment,
):
    local_metrics = (
        research_environment[
            "paths"
        ][
            "metrics"
        ]
    )

    local_metrics.unlink()

    data_access.read_parquet.clear()

    dataframe = (
        data_access.experiment_metrics()
    )

    assert dataframe.empty


def test_resolved_dataset_path_is_research_local(
    research_environment,
):
    path = (
        data_access.resolved_dataset_path(
            "experiment_metrics"
        )
    )

    assert (
        path
        == research_environment[
            "paths"
        ][
            "metrics"
        ]
    )


def test_resolved_report_path_is_research_local(
    research_environment,
):
    path = (
        data_access.resolved_report_path(
            "ranking_summary"
        )
    )

    assert (
        path
        == research_environment[
            "paths"
        ][
            "ranking_summary"
        ]
    )