from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import operar_range.research_workspace as workspace


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


def _dataset(
    *,
    data_root: Path,
    dataset_id: str,
    market: str,
    asset: str,
    dates: list[str],
) -> dict:
    root = (
        data_root
        / "datasets"
        / dataset_id
    )

    normalized = (
        root
        / "normalized"
    )

    research = (
        root
        / "research"
    )

    trajectories = (
        root
        / "trajectories"
    )

    normalized.mkdir(
        parents=True
    )

    research.mkdir(
        parents=True
    )

    trajectories.mkdir(
        parents=True
    )

    #
    # Apenas a existência física é necessária
    # para estes testes de resolução.
    #
    (
        normalized
        / "placeholder.parquet"
    ).write_bytes(
        b"stage22"
    )

    trade1_path = (
        research
        / "trade1_database.parquet"
    )

    trajectory_manifest = (
        trajectories
        / "trajectory_manifest.parquet"
    )

    _write_parquet(
        trade1_path,
        [
            {
                "date": date,
                "trade1_status": (
                    "NO_TRADE_1"
                ),
            }
            for date in dates
        ],
    )

    _write_parquet(
        trajectory_manifest,
        [
            {
                "date": date,
                "source_parquet": (
                    f"{date}.parquet"
                ),
                "trade1_status": (
                    "NO_TRADE_1"
                ),
                "trajectory_exists": (
                    False
                ),
            }
            for date in dates
        ],
    )

    manifest = {
        "dataset_id": dataset_id,
        "dataset_version": 1,
        "market": market,
        "asset": asset,
        "provider": "TEST",
        "quality_status": "READY",
        "research_ready": True,
        "period_start": dates[0],
        "period_end": dates[-1],
        "sessions_total": len(
            dates
        ),
        "records_total": 0,
        "source_sha256": [
            "a" * 64,
        ],
    }

    (
        root
        / "dataset_manifest.json"
    ).write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )

    return {
        "root": root,
        "normalized": normalized,
        "trade1": trade1_path,
        "trajectory_manifest": (
            trajectory_manifest
        ),
    }


@pytest.fixture()
def isolated_stage22(
    tmp_path,
    monkeypatch,
):
    data_root = (
        tmp_path
        / "data"
    )

    research_root = (
        data_root
        / "research"
    )

    workspace_root = (
        research_root
        / "workspace"
    )

    normalized_root = (
        data_root
        / "normalized"
    )

    reports_root = (
        data_root
        / "reports"
    )

    inbox_root = (
        data_root
        / "inbox"
    )

    research_root.mkdir(
        parents=True
    )

    workspace_root.mkdir(
        parents=True
    )

    normalized_root.mkdir(
        parents=True
    )

    reports_root.mkdir(
        parents=True
    )

    inbox_root.mkdir(
        parents=True
    )

    legacy_trade1 = (
        research_root
        / "trade1_database.parquet"
    )

    legacy_trajectory = (
        research_root
        / "trade1_trajectory_manifest.parquet"
    )

    _write_parquet(
        legacy_trade1,
        [
            {
                "date": "2020-01-01",
                "trade1_status": (
                    "NO_TRADE_1"
                ),
            }
        ],
    )

    _write_parquet(
        legacy_trajectory,
        [
            {
                "date": "2020-01-01",
                "source_parquet": (
                    "legacy.parquet"
                ),
                "trade1_status": (
                    "NO_TRADE_1"
                ),
                "trajectory_exists": (
                    False
                ),
            }
        ],
    )

    registry = (
        research_root
        / "experiment_registry.parquet"
    )

    _write_parquet(
        registry,
        [],
    )

    monkeypatch.setattr(
        workspace,
        "PROJECT_ROOT",
        tmp_path,
    )

    monkeypatch.setattr(
        workspace,
        "DATA_ROOT",
        data_root,
    )

    monkeypatch.setattr(
        workspace,
        "RESEARCH_ROOT",
        research_root,
    )

    monkeypatch.setattr(
        workspace,
        "WORKSPACE_ROOT",
        workspace_root,
    )

    monkeypatch.setattr(
        workspace,
        "NORMALIZED_ROOT",
        normalized_root,
    )

    monkeypatch.setattr(
        workspace,
        "REPORTS_ROOT",
        reports_root,
    )

    monkeypatch.setattr(
        workspace,
        "INBOX_ROOT",
        inbox_root,
    )

    monkeypatch.setattr(
        workspace,
        "TRADE1_DATABASE_PATH",
        legacy_trade1,
    )

    monkeypatch.setattr(
        workspace,
        "TRAJECTORY_MANIFEST_PATH",
        legacy_trajectory,
    )

    monkeypatch.setattr(
        workspace,
        "REGISTRY_PATH",
        registry,
    )

    first = _dataset(
        data_root=data_root,
        dataset_id=(
            "DS-AAAAAAAAAAAAAAAA"
        ),
        market="B3",
        asset="WIN",
        dates=[
            "2026-08-18",
            "2026-08-19",
        ],
    )

    second = _dataset(
        data_root=data_root,
        dataset_id=(
            "DS-BBBBBBBBBBBBBBBB"
        ),
        market="CME",
        asset="ES",
        dates=[
            "2025-01-02",
        ],
    )

    return {
        "data_root": data_root,
        "first": first,
        "second": second,
    }


def _definition(
    dataset_id: str | None,
) -> dict:
    value = {
        "strategy": "TRADE_1",
        "family": "STAGE22_TEST",
        "generation": 1,
        "period_start": (
            "2026-08-18"
        ),
        "period_end": (
            "2026-08-19"
        ),
        "rules_version": (
            "ADR-004+STAGE10"
        ),
        "batch_size": 10,
        "base_config": {
            "stop_points": None,
            "partial_1_points": None,
            "partial_1_pct": None,
            "partial_2_points": None,
            "partial_2_pct": None,
            "partial_3_points": None,
            "partial_3_pct": None,
            "break_even_enabled": True,
            "break_even_after_partial": 1,
            "runner_enabled": False,
            "runner_pct": None,
            "runner_rule": None,
            "final_target_points": 400,
        },
        "parameter_definition": {
            "stop_points": {
                "values": [
                    170,
                ]
            },
            "partial_1_points": {
                "values": [
                    125,
                ]
            },
            "partial_1_pct": {
                "values": [
                    70,
                ]
            },
        },
    }

    if dataset_id is not None:
        value[
            "dataset_id"
        ] = dataset_id

    return value


def test_new_stage22_research_requires_dataset_id(
    isolated_stage22,
):
    with pytest.raises(
        RuntimeError,
        match=(
            "DATASET_RESOLUTION_ERROR"
        ),
    ):
        workspace.create_research_stage22(
            _definition(
                None
            )
        )


def test_dataset_resolution_uses_correct_dataset(
    isolated_stage22,
):
    context = (
        workspace.resolve_dataset_context(
            "DS-AAAAAAAAAAAAAAAA"
        )
    )

    assert (
        context["market"]
        == "B3"
    )

    assert (
        context["asset"]
        == "WIN"
    )

    assert (
        "DS-AAAAAAAAAAAAAAAA"
        in str(
            context[
                "normalized_dir"
            ]
        )
    )


def test_two_dataset_periods_are_isolated(
    isolated_stage22,
):
    first = (
        workspace
        .available_dataset_period(
            dataset_id_value=(
                "DS-AAAAAAAAAAAAAAAA"
            )
        )
    )

    second = (
        workspace
        .available_dataset_period(
            dataset_id_value=(
                "DS-BBBBBBBBBBBBBBBB"
            )
        )
    )

    assert (
        first["period_start"]
        == "2026-08-18"
    )

    assert (
        first["period_end"]
        == "2026-08-19"
    )

    assert (
        second["period_start"]
        == "2025-01-02"
    )

    assert (
        second["period_end"]
        == "2025-01-02"
    )


def test_sessions_for_period_do_not_cross_dataset(
    isolated_stage22,
):
    rows = (
        workspace
        ._sessions_for_period(
            period_start=(
                "2026-08-18"
            ),
            period_end=(
                "2026-08-19"
            ),
            dataset_id_value=(
                "DS-AAAAAAAAAAAAAAAA"
            ),
        )
    )

    assert {
        row["date"]
        for row in rows
    } == {
        "2026-08-18",
        "2026-08-19",
    }

    other = (
        workspace
        ._sessions_for_period(
            period_start=(
                "2025-01-02"
            ),
            period_end=(
                "2025-01-02"
            ),
            dataset_id_value=(
                "DS-BBBBBBBBBBBBBBBB"
            ),
        )
    )

    assert [
        row["date"]
        for row in other
    ] == [
        "2025-01-02",
    ]


def test_stage22_research_freezes_dataset_identity(
    isolated_stage22,
):
    created = (
        workspace
        .create_research_stage22(
            _definition(
                "DS-AAAAAAAAAAAAAAAA"
            )
        )
    )

    definition = (
        workspace
        .load_research_definition(
            created[
                "research_id"
            ]
        )
    )

    manifest = (
        workspace
        .load_research_manifest(
            created[
                "research_id"
            ]
        )
    )

    assert (
        definition["dataset_id"]
        == "DS-AAAAAAAAAAAAAAAA"
    )

    assert (
        definition["market"]
        == "B3"
    )

    assert (
        definition["asset"]
        == "WIN"
    )

    assert (
        manifest["dataset_id"]
        == "DS-AAAAAAAAAAAAAAAA"
    )

    assert (
        manifest[
            "dataset_resolution_mode"
        ]
        == "STAGE22_ISOLATED"
    )


def test_invalid_dataset_id_never_falls_back_to_legacy(
    isolated_stage22,
):
    with pytest.raises(
        RuntimeError,
        match=(
            "DATASET_RESOLUTION_ERROR"
        ),
    ):
        workspace.resolve_dataset_context(
            "DS-DOES-NOT-EXIST"
        )


def test_legacy_resolution_remains_explicit(
    isolated_stage22,
):
    context = (
        workspace
        .resolve_research_dataset_context(
            {
                "period_start": (
                    "2020-01-01"
                ),
                "period_end": (
                    "2020-01-01"
                ),
            }
        )
    )

    assert (
        context["mode"]
        == "LEGACY_GLOBAL"
    )

    assert (
        context["dataset_id"]
        is None
    )

    assert (
        context[
            "trade1_database_path"
        ]
        == workspace.TRADE1_DATABASE_PATH
    )


def test_stage22_period_manifest_is_materialized_from_selected_dataset(
    isolated_stage22,
):
    created = (
        workspace
        .create_research_stage22(
            _definition(
                "DS-AAAAAAAAAAAAAAAA"
            )
        )
    )

    result = (
        workspace
        ._materialize_period_manifest(
            research_id=(
                created[
                    "research_id"
                ]
            ),
            period_start=(
                "2026-08-18"
            ),
            period_end=(
                "2026-08-19"
            ),
            dataset_id_value=(
                "DS-AAAAAAAAAAAAAAAA"
            ),
        )
    )

    assert (
        result[
            "dataset_id"
        ]
        == "DS-AAAAAAAAAAAAAAAA"
    )

    assert (
        "DS-AAAAAAAAAAAAAAAA"
        in result[
            "source_manifest_path"
        ]
    )

    assert (
        "DS-BBBBBBBBBBBBBBBB"
        not in result[
            "source_manifest_path"
        ]
    )

    research_manifest = (
        workspace.read_parquet_rows(
            Path(
                result[
                    "path"
                ]
            )
        )
    )

    assert {
        row[
            "date"
        ]
        for row in research_manifest
    } == {
        "2026-08-18",
        "2026-08-19",
    }


def test_stage22_distributed_execution_receives_selected_dataset_normalized_dir(
    isolated_stage22,
    monkeypatch,
):
    created = (
        workspace
        .create_research_stage22(
            _definition(
                "DS-AAAAAAAAAAAAAAAA"
            )
        )
    )

    research_id = (
        created[
            "research_id"
        ]
    )

    captured = {}

    monkeypatch.setattr(
        workspace,
        "serialize_all_batches",
        lambda **kwargs: {
            "run_id": (
                "RUN-STAGE22-ISOLATION"
            ),
            "packages": [
                {
                    "batch_id": (
                        "BATCH-000001"
                    )
                }
            ],
        },
    )

    monkeypatch.setattr(
        workspace,
        "read_attempts",
        lambda **kwargs: [],
    )

    def fake_execute_worker(
        **kwargs,
    ):
        captured[
            "normalized_dir"
        ] = kwargs[
            "normalized_dir"
        ]

        captured[
            "trajectory_manifest_path"
        ] = kwargs[
            "trajectory_manifest_path"
        ]

        return {
            "status": "COMPLETED",
        }

    monkeypatch.setattr(
        workspace,
        "execute_worker",
        fake_execute_worker,
    )

    monkeypatch.setattr(
        workspace,
        "distributed_status",
        lambda **kwargs: {
            "completed": 1,
            "batches_total": 1,
            "failed_final": 0,
        },
    )

    monkeypatch.setattr(
        workspace,
        "merge_distributed_results",
        lambda **kwargs: {
            "output_path": (
                str(
                    workspace
                    .research_paths(
                        research_id
                    )[
                        "distributed_results"
                    ]
                )
            ),
            "output_sha256": (
                "a" * 64
            ),
        },
    )

    dataset_context = (
        workspace
        .resolve_dataset_context(
            "DS-AAAAAAAAAAAAAAAA"
        )
    )

    result = (
        workspace
        ._execute_distributed(
            research_id=(
                research_id
            ),
            normalized_dir=(
                dataset_context[
                    "normalized_dir"
                ]
            ),
            progress_callback=None,
        )
    )

    assert (
        result[
            "run_id"
        ]
        == "RUN-STAGE22-ISOLATION"
    )

    worker_normalized_dir = Path(
        captured[
            "normalized_dir"
        ]
    )

    #
    # Contrato distribuído:
    # paths enviados ao worker são portáveis
    # e relativos ao PROJECT_ROOT.
    #
    assert (
        worker_normalized_dir.is_absolute()
        is False
    )

    assert (
        (
            workspace.PROJECT_ROOT
            / worker_normalized_dir
        ).resolve()
        == Path(
            dataset_context[
                "normalized_dir"
            ]
        ).resolve()
    )

    assert (
        "DS-AAAAAAAAAAAAAAAA"
        in str(
            captured[
                "normalized_dir"
            ]
        )
    )

    assert (
        "DS-BBBBBBBBBBBBBBBB"
        not in str(
            captured[
                "normalized_dir"
            ]
        )
    )

    assert (
        captured[
            "trajectory_manifest_path"
        ]
        == workspace
        .research_paths(
            research_id
        )[
            "trajectory_manifest"
        ]
    )


def test_stage22_other_dataset_cannot_contaminate_period_manifest(
    isolated_stage22,
):
    created = (
        workspace
        .create_research_stage22(
            _definition(
                "DS-AAAAAAAAAAAAAAAA"
            )
        )
    )

    result = (
        workspace
        ._materialize_period_manifest(
            research_id=(
                created[
                    "research_id"
                ]
            ),
            period_start=(
                "2026-08-18"
            ),
            period_end=(
                "2026-08-19"
            ),
            dataset_id_value=(
                "DS-AAAAAAAAAAAAAAAA"
            ),
        )
    )

    rows = (
        workspace
        .read_parquet_rows(
            Path(
                result[
                    "path"
                ]
            )
        )
    )

    dates = {
        str(
            row[
                "date"
            ]
        )
        for row in rows
    }

    assert (
        "2025-01-02"
        not in dates
    )

    assert dates == {
        "2026-08-18",
        "2026-08-19",
    }


# ============================================================
# Stage 22 — Alternative C Research readiness gate
# ============================================================


def _set_dataset_state(
    root: Path,
    *,
    state: str,
    research_ready: bool,
) -> None:
    manifest_path = (
        root
        / "dataset_manifest.json"
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    manifest[
        "dataset_state"
    ] = state

    manifest[
        "research_ready"
    ] = research_ready

    manifest_path.write_text(
        json.dumps(
            manifest,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_materialized_dataset_cannot_start_new_research(
    isolated_stage22,
):
    root = isolated_stage22[
        "first"
    ][
        "root"
    ]

    _set_dataset_state(
        root,
        state="MATERIALIZED",
        research_ready=False,
    )

    with pytest.raises(
        RuntimeError,
        match="is not research ready",
    ):
        workspace.create_research_stage22(
            _definition(
                "DS-AAAAAAAAAAAAAAAA"
            )
        )


def test_failed_preparation_dataset_cannot_start_new_research(
    isolated_stage22,
):
    root = isolated_stage22[
        "first"
    ][
        "root"
    ]

    _set_dataset_state(
        root,
        state="FAILED_PREPARATION",
        research_ready=False,
    )

    with pytest.raises(
        RuntimeError,
        match="is not research ready",
    ):
        workspace.create_research_stage22(
            _definition(
                "DS-AAAAAAAAAAAAAAAA"
            )
        )


def test_ready_dataset_can_start_new_research(
    isolated_stage22,
):
    root = isolated_stage22[
        "first"
    ][
        "root"
    ]

    _set_dataset_state(
        root,
        state="READY",
        research_ready=True,
    )

    created = (
        workspace
        .create_research_stage22(
            _definition(
                "DS-AAAAAAAAAAAAAAAA"
            )
        )
    )

    assert (
        created[
            "research_id"
        ]
    )
