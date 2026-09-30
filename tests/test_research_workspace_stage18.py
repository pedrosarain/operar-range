from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import operar_range.research_workspace as workspace


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


def base_definition() -> dict:
    return {
        "dataset_id": "DS-STAGE22-TEST",
        "dataset_version": 1,
        "market": "B3",
        "asset": "WIN",
        "strategy": "TRADE_1",
        "family": "TRADE1_STAGE18_TEST",
        "generation": 1,
        "period_start": "2026-08-18",
        "period_end": "2026-08-19",
        "rules_version": (
            "ADR-004+STAGE10"
        ),
        "batch_size": 3,
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
                    150,
                    170,
                ]
            },
            "partial_1_points": {
                "values": [
                    100,
                    125,
                ]
            },
            "partial_1_pct": {
                "values": [
                    40,
                    70,
                ]
            },
        },
        "composite_weights": {
            "EXPECTANCY": 35.0,
            "PROFIT_FACTOR": 25.0,
            "MAX_DRAWDOWN": 20.0,
            "NUMBER_OF_TRADES": 10.0,
            "WIN_RATE": 10.0,
        },
    }


@pytest.fixture()
def isolated_workspace(
    tmp_path,
    monkeypatch,
):
    data_root = (
        tmp_path
        / "data"
    )

    inbox_root = (
        data_root
        / "inbox"
    )

    normalized_root = (
        data_root
        / "normalized"
    )

    research_root = (
        data_root
        / "research"
    )

    reports_root = (
        data_root
        / "reports"
    )

    workspace_root = (
        research_root
        / "workspace"
    )

    inbox_root.mkdir(
        parents=True
    )

    normalized_root.mkdir(
        parents=True
    )

    research_root.mkdir(
        parents=True
    )

    reports_root.mkdir(
        parents=True
    )

    trajectory_manifest_path = (
        research_root
        / "trade1_trajectory_manifest.parquet"
    )

    trade1_database_path = (
        research_root
        / "trade1_database.parquet"
    )

    registry_path = (
        research_root
        / "experiment_registry.parquet"
    )

    write_parquet(
        trajectory_manifest_path,
        [
            {
                "date": "2026-08-18",
                "source_parquet": (
                    "day18.parquet"
                ),
                "trade1_status": (
                    "TRADE_1"
                ),
                "trajectory_exists": (
                    True
                ),
            },
            {
                "date": "2026-08-19",
                "source_parquet": (
                    "day19.parquet"
                ),
                "trade1_status": (
                    "NO_TRADE_1"
                ),
                "trajectory_exists": (
                    False
                ),
            },
        ],
    )

    write_parquet(
        trade1_database_path,
        [
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
        ],
    )

    write_parquet(
        registry_path,
        [],
    )

    dataset_root = (
        data_root
        / "datasets"
        / "DS-STAGE22-TEST"
    )

    dataset_normalized = (
        dataset_root
        / "normalized"
    )

    dataset_research = (
        dataset_root
        / "research"
    )

    dataset_trajectories = (
        dataset_root
        / "trajectories"
    )

    dataset_reports = (
        dataset_root
        / "reports"
    )

    for directory in (
        dataset_normalized,
        dataset_research,
        dataset_trajectories,
        dataset_reports,
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    dataset_trade1_database = (
        dataset_research
        / "trade1_database.parquet"
    )

    dataset_trajectory_manifest = (
        dataset_trajectories
        / "trajectory_manifest.parquet"
    )

    write_parquet(
        dataset_trade1_database,
        [
            {
                "date": "2026-08-18",
                "trade1_status": "TRADE_1",
            },
            {
                "date": "2026-08-19",
                "trade1_status": "NO_TRADE_1",
            },
        ],
    )

    write_parquet(
        dataset_trajectory_manifest,
        [
            {
                "date": "2026-08-18",
                "source_parquet": (
                    "day18.parquet"
                ),
                "trade1_status": (
                    "TRADE_1"
                ),
                "trajectory_exists": True,
            },
            {
                "date": "2026-08-19",
                "source_parquet": (
                    "day19.parquet"
                ),
                "trade1_status": (
                    "NO_TRADE_1"
                ),
                "trajectory_exists": False,
            },
        ],
    )

    dataset_manifest = (
        dataset_root
        / "dataset_manifest.json"
    )

    dataset_manifest.write_text(
        json.dumps(
            {
                "dataset_id": (
                    "DS-STAGE22-TEST"
                ),
                "dataset_version": 1,
                "market": "B3",
                "asset": "WIN",
                "provider": "TEST",
                "period_start": (
                    "2026-08-18"
                ),
                "period_end": (
                    "2026-08-19"
                ),
                "sessions_total": 2,
                "records_total": 2,
                "quality_status": "READY",
                "research_ready": True,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
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
        "INBOX_ROOT",
        inbox_root,
    )

    monkeypatch.setattr(
        workspace,
        "NORMALIZED_ROOT",
        normalized_root,
    )

    monkeypatch.setattr(
        workspace,
        "RESEARCH_ROOT",
        research_root,
    )

    monkeypatch.setattr(
        workspace,
        "REPORTS_ROOT",
        reports_root,
    )

    monkeypatch.setattr(
        workspace,
        "WORKSPACE_ROOT",
        workspace_root,
    )

    monkeypatch.setattr(
        workspace,
        "REGISTRY_PATH",
        registry_path,
    )

    monkeypatch.setattr(
        workspace,
        "TRAJECTORY_MANIFEST_PATH",
        trajectory_manifest_path,
    )

    monkeypatch.setattr(
        workspace,
        "TRADE1_DATABASE_PATH",
        trade1_database_path,
    )

    return {
        "root": tmp_path,
        "data": data_root,
        "inbox": inbox_root,
        "normalized": normalized_root,
        "research": research_root,
        "reports": reports_root,
        "workspace": workspace_root,
        "registry": registry_path,
        "trajectory_manifest": (
            trajectory_manifest_path
        ),
        "trade1_database": (
            trade1_database_path
        ),
    }


def test_empty_inbox(
    isolated_workspace,
):
    rows = (
        workspace.list_inbox_files()
    )

    assert rows == []


def test_inbox_lists_file(
    isolated_workspace,
):
    path = (
        isolated_workspace[
            "inbox"
        ]
        / "sample.zip"
    )

    path.write_bytes(
        b"abc"
    )

    rows = (
        workspace.list_inbox_files()
    )

    assert len(rows) == 1

    row = rows[0]

    assert (
        row["name"]
        == "sample.zip"
    )

    assert (
        row["size_bytes"]
        == 3
    )

    assert (
        row["status"]
        == "NEW"
    )


def test_inbox_rejects_unsupported_extension(
    isolated_workspace,
):
    path = (
        isolated_workspace[
            "inbox"
        ]
        / "sample.txt"
    )

    path.write_text(
        "test",
        encoding="utf-8",
    )

    rows = (
        workspace.list_inbox_files()
    )

    assert len(rows) == 1

    assert (
        rows[0]["status"]
        == "ERROR"
    )

    assert (
        rows[0]["error"]
        == "UNSUPPORTED_EXTENSION"
    )


def test_validate_empty_selection(
    isolated_workspace,
):
    result = (
        workspace.validate_inbox_selection(
            []
        )
    )

    assert (
        result["valid"]
        is False
    )

    assert (
        "No dataset selected."
        in result["errors"]
    )


def test_validate_missing_file(
    isolated_workspace,
):
    result = (
        workspace.validate_inbox_selection(
            [
                "does_not_exist.zip",
            ]
        )
    )

    assert (
        result["valid"]
        is False
    )

    assert any(
        "File not found"
        in message
        for message
        in result["errors"]
    )


def test_available_dataset_period(
    isolated_workspace,
):
    result = (
        workspace.available_dataset_period()
    )

    assert (
        result["available"]
        is True
    )

    assert (
        result["period_start"]
        == "2026-08-18"
    )

    assert (
        result["period_end"]
        == "2026-08-19"
    )

    assert (
        result["sessions_total"]
        == 2
    )


def test_valid_research_period(
    isolated_workspace,
):
    result = (
        workspace.validate_research_period(
            period_start=(
                "2026-08-18"
            ),
            period_end=(
                "2026-08-19"
            ),
        )
    )

    assert (
        result["valid"]
        is True
    )

    assert (
        result["sessions_total"]
        == 2
    )


def test_period_before_dataset_is_rejected(
    isolated_workspace,
):
    result = (
        workspace.validate_research_period(
            period_start=(
                "2026-08-17"
            ),
            period_end=(
                "2026-08-19"
            ),
        )
    )

    assert (
        result["valid"]
        is False
    )

    assert any(
        "before"
        in message
        for message
        in result["errors"]
    )


def test_period_after_dataset_is_rejected(
    isolated_workspace,
):
    result = (
        workspace.validate_research_period(
            period_start=(
                "2026-08-18"
            ),
            period_end=(
                "2026-08-20"
            ),
        )
    )

    assert (
        result["valid"]
        is False
    )

    assert any(
        "after"
        in message
        for message
        in result["errors"]
    )


def test_inverted_period_is_rejected(
    isolated_workspace,
):
    result = (
        workspace.validate_research_period(
            period_start=(
                "2026-08-19"
            ),
            period_end=(
                "2026-08-18"
            ),
        )
    )

    assert (
        result["valid"]
        is False
    )


def test_estimate_research_size(
    isolated_workspace,
):
    definition = (
        base_definition()
    )

    result = (
        workspace.estimate_research(
            definition
        )
    )

    #
    # 2 stops
    # x 2 parcial points
    # x 2 percentual
    # = 8 configurações
    #
    assert (
        result[
            "generated_configurations"
        ]
        == 8
    )

    assert (
        result[
            "sessions_total"
        ]
        == 2
    )

    assert (
        result[
            "execution_units_estimated"
        ]
        == 16
    )

    #
    # batch_size = 3
    # ceil(16 / 3) = 6
    #
    assert (
        result[
            "batches_estimated"
        ]
        == 6
    )


def test_estimate_does_not_create_research(
    isolated_workspace,
):
    before = (
        workspace.list_researches()
    )

    workspace.estimate_research(
        base_definition()
    )

    after = (
        workspace.list_researches()
    )

    assert before == []
    assert after == []


def test_create_research(
    isolated_workspace,
):
    result = (
        workspace.create_research(
            base_definition()
        )
    )

    research_id = (
        result["research_id"]
    )

    paths = (
        workspace.research_paths(
            research_id
        )
    )

    assert (
        paths["root"].exists()
    )

    assert (
        paths["definition"].exists()
    )

    assert (
        paths["run_manifest"].exists()
    )

    definition = (
        workspace.load_research_definition(
            research_id
        )
    )

    manifest = (
        workspace.load_research_manifest(
            research_id
        )
    )

    assert (
        definition["research_id"]
        == research_id
    )

    assert (
        "status"
        not in definition
    )

    assert (
        definition[
            "definition_status"
        ]
        == "CREATED"
    )

    assert (
        definition[
            "definition_schema_version"
        ]
        == workspace.RESEARCH_DEFINITION_SCHEMA_VERSION
    )

    assert (
        manifest["status"]
        == "CREATED"
    )

    assert (
        manifest[
            "quantitative_execution_repeated"
        ]
        is False
    )


def test_research_id_is_not_reused(
    isolated_workspace,
):
    definition = (
        base_definition()
    )

    first = (
        workspace.create_research(
            deepcopy(
                definition
            )
        )
    )

    second = (
        workspace.create_research(
            deepcopy(
                definition
            )
        )
    )

    assert (
        first["research_id"]
        != second["research_id"]
    )

    assert (
        Path(
            first["research_dir"]
        ).exists()
    )

    assert (
        Path(
            second["research_dir"]
        ).exists()
    )


def test_research_definition_hash_deterministic(
    isolated_workspace,
):
    first = (
        workspace.research_definition_sha256(
            base_definition()
        )
    )

    second = (
        workspace.research_definition_sha256(
            deepcopy(
                base_definition()
            )
        )
    )

    assert (
        first
        == second
    )


def test_list_research_history(
    isolated_workspace,
):
    first = (
        workspace.create_research(
            base_definition()
        )
    )

    definition = (
        base_definition()
    )

    definition[
        "generation"
    ] = 2

    second = (
        workspace.create_research(
            definition
        )
    )

    history = (
        workspace.list_researches()
    )

    ids = {
        row[
            "research_id"
        ]
        for row in history
    }

    assert (
        first["research_id"]
        in ids
    )

    assert (
        second["research_id"]
        in ids
    )

    assert len(
        history
    ) == 2


def test_update_run_manifest(
    isolated_workspace,
):
    created = (
        workspace.create_research(
            base_definition()
        )
    )

    research_id = (
        created[
            "research_id"
        ]
    )

    updated = (
        workspace.update_run_manifest(
            research_id,
            status="RUNNING",
            current_stage=(
                "BATCH_PLANNER"
            ),
            execution_units_total=16,
            batches_total=6,
        )
    )

    assert (
        updated["status"]
        == "RUNNING"
    )

    assert (
        updated[
            "current_stage"
        ]
        == "BATCH_PLANNER"
    )

    assert (
        updated[
            "execution_units_total"
        ]
        == 16
    )

    assert (
        updated[
            "batches_total"
        ]
        == 6
    )


def test_completed_research_cannot_be_deleted(
    isolated_workspace,
):
    created = (
        workspace.create_research(
            base_definition()
        )
    )

    research_id = (
        created[
            "research_id"
        ]
    )

    workspace.update_run_manifest(
        research_id,
        status="COMPLETED",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Cannot delete completed"
        ),
    ):
        (
            workspace
            .delete_incomplete_research_for_test(
                research_id
            )
        )


def test_incomplete_research_can_be_deleted_for_test(
    isolated_workspace,
):
    created = (
        workspace.create_research(
            base_definition()
        )
    )

    research_id = (
        created[
            "research_id"
        ]
    )

    root = (
        workspace.research_paths(
            research_id
        )["root"]
    )

    assert root.exists()

    (
        workspace
        .delete_incomplete_research_for_test(
            research_id
        )
    )

    assert not root.exists()


def test_invalid_research_id_rejected(
    isolated_workspace,
):
    with pytest.raises(
        ValueError,
        match=(
            "Invalid research_id"
        ),
    ):
        workspace.research_dir(
            "../bad"
        )


def test_only_trade1_supported(
    isolated_workspace,
):
    definition = (
        base_definition()
    )

    definition[
        "strategy"
    ] = "TRADE_2"

    with pytest.raises(
        ValueError,
        match=(
            "TRADE_1 only"
        ),
    ):
        workspace.create_research(
            definition
        )


def test_process_datasets_validation_failure_does_not_run_pipeline(
    isolated_workspace,
    monkeypatch,
):
    called = {
        "ingest": False,
        "scanner": False,
        "trajectory": False,
    }

    def fake_ingest(
        *args,
        **kwargs,
    ):
        called[
            "ingest"
        ] = True

    def fake_scanner(
        *args,
        **kwargs,
    ):
        called[
            "scanner"
        ] = True

    def fake_trajectory(
        *args,
        **kwargs,
    ):
        called[
            "trajectory"
        ] = True

    monkeypatch.setattr(
        workspace,
        "import_tick_zip",
        fake_ingest,
    )

    monkeypatch.setattr(
        workspace,
        "run_scanner",
        fake_scanner,
    )

    monkeypatch.setattr(
        workspace,
        "run_trajectory_cache",
        fake_trajectory,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Dataset validation failed"
        ),
    ):
        workspace.process_datasets(
            []
        )

    assert (
        called["ingest"]
        is False
    )

    assert (
        called["scanner"]
        is False
    )

    assert (
        called["trajectory"]
        is False
    )


def test_progress_callback(
    isolated_workspace,
    monkeypatch,
):
    path = (
        isolated_workspace[
            "inbox"
        ]
        / "sample.zip"
    )

    path.write_bytes(
        b"fake-zip"
    )

    monkeypatch.setattr(
        workspace,
        "validate_inbox_selection",
        lambda filenames: {
            "valid": True,
            "files": [
                {
                    "name": (
                        "sample.zip"
                    ),
                    "path": str(
                        path
                    ),
                }
            ],
            "errors": [],
        },
    )

    monkeypatch.setattr(
        workspace,
        "import_tick_zip",
        lambda *args, **kwargs: [
            {
                "row_count": 100,
            }
        ],
    )

    monkeypatch.setattr(
        workspace,
        "run_scanner",
        lambda *args, **kwargs: {
            "database_path": "x",
            "summary_path": "y",
        },
    )

    monkeypatch.setattr(
        workspace,
        "run_trajectory_cache",
        lambda *args, **kwargs: {
            "manifest_path": "z",
        },
    )

    events = []

    def callback(
        stage,
        fraction,
        details,
    ):
        events.append(
            (
                stage,
                fraction,
                details,
            )
        )

    result = (
        workspace.process_datasets(
            [
                "sample.zip",
            ],
            progress_callback=(
                callback
            ),
        )
    )

    stages = [
        event[0]
        for event in events
    ]

    assert (
        "VALIDATION"
        in stages
    )

    assert (
        "NORMALIZATION"
        in stages
    )

    assert (
        "SCANNER"
        in stages
    )

    assert (
        "TRAJECTORY_CACHE"
        in stages
    )

    assert (
        "ANALYTICS"
        in stages
    )

    assert (
        result[
            "analytics_status"
        ]
        == (
            "DEFERRED_UNTIL_RESEARCH"
        )
    )


def test_result_paths_are_research_local(
    isolated_workspace,
):
    created = (
        workspace.create_research(
            base_definition()
        )
    )

    research_id = (
        created[
            "research_id"
        ]
    )

    result = (
        workspace.research_result_paths(
            research_id
        )
    )

    for path_value in (
        result.values()
    ):
        assert (
            research_id
            in path_value
        )


def test_definition_file_is_not_silently_overwritten(
    isolated_workspace,
):
    created = (
        workspace.create_research(
            base_definition()
        )
    )

    research_id = (
        created[
            "research_id"
        ]
    )

    definition_path = (
        workspace.research_paths(
            research_id
        )[
            "definition"
        ]
    )

    original = (
        definition_path
        .read_text(
            encoding="utf-8"
        )
    )

    with pytest.raises(
        FileExistsError
    ):
        workspace.write_json(
            path=(
                definition_path
            ),
            value={
                "changed": True,
            },
            overwrite=False,
        )

    after = (
        definition_path
        .read_text(
            encoding="utf-8"
        )
    )

    assert original == after


def test_research_definition_file_contains_hash(
    isolated_workspace,
):
    created = (
        workspace.create_research(
            base_definition()
        )
    )

    definition = (
        json.loads(
            Path(
                created[
                    "definition_path"
                ]
            )
            .read_text(
                encoding="utf-8"
            )
        )
    )

    assert (
        definition[
            "research_definition_sha256"
        ]
        == created[
            "research_definition_sha256"
        ]
    )

# ============================================================
# Stage 22 final closure — Research status contract
# ============================================================


def test_new_research_definition_has_explicit_definition_status(
    isolated_workspace,
):
    created = workspace.create_research(
        base_definition()
    )

    research_id = created[
        "research_id"
    ]

    definition = (
        workspace.load_research_definition(
            research_id
        )
    )

    manifest = (
        workspace.load_research_manifest(
            research_id
        )
    )

    assert (
        "status"
        not in definition
    )

    assert (
        definition[
            "definition_status"
        ]
        == "CREATED"
    )

    assert (
        definition[
            "definition_schema_version"
        ]
        == workspace.RESEARCH_DEFINITION_SCHEMA_VERSION
    )

    assert (
        manifest[
            "status"
        ]
        == "CREATED"
    )


def test_definition_status_is_immutable_when_run_status_changes(
    isolated_workspace,
):
    created = workspace.create_research(
        base_definition()
    )

    research_id = created[
        "research_id"
    ]

    definition_path = Path(
        created[
            "definition_path"
        ]
    )

    before = (
        definition_path
        .read_bytes()
    )

    workspace.update_run_manifest(
        research_id,
        status="RUNNING",
        current_stage="PREPARING",
    )

    workspace.update_run_manifest(
        research_id,
        status="COMPLETED",
        current_stage="COMPLETED",
    )

    after = (
        definition_path
        .read_bytes()
    )

    definition = (
        workspace.load_research_definition(
            research_id
        )
    )

    assert before == after

    assert (
        definition[
            "definition_status"
        ]
        == "CREATED"
    )


def test_run_manifest_status_evolves_created_running_completed(
    isolated_workspace,
):
    created = workspace.create_research(
        base_definition()
    )

    research_id = created[
        "research_id"
    ]

    initial = (
        workspace.load_research_manifest(
            research_id
        )
    )

    assert (
        initial[
            "status"
        ]
        == "CREATED"
    )

    running = (
        workspace.update_run_manifest(
            research_id,
            status="RUNNING",
            current_stage="PREPARING",
        )
    )

    assert (
        running[
            "status"
        ]
        == "RUNNING"
    )

    completed = (
        workspace.update_run_manifest(
            research_id,
            status="COMPLETED",
            current_stage="COMPLETED",
        )
    )

    assert (
        completed[
            "status"
        ]
        == "COMPLETED"
    )

    definition = (
        workspace.load_research_definition(
            research_id
        )
    )

    assert (
        definition[
            "definition_status"
        ]
        == "CREATED"
    )


def test_run_manifest_status_evolves_created_running_failed(
    isolated_workspace,
):
    created = workspace.create_research(
        base_definition()
    )

    research_id = created[
        "research_id"
    ]

    initial = (
        workspace.load_research_manifest(
            research_id
        )
    )

    assert (
        initial[
            "status"
        ]
        == "CREATED"
    )

    workspace.update_run_manifest(
        research_id,
        status="RUNNING",
        current_stage="PREPARING",
    )

    failed = (
        workspace.update_run_manifest(
            research_id,
            status="FAILED",
            current_stage="FAILED",
            error_type="RuntimeError",
            error_message="test failure",
        )
    )

    assert (
        failed[
            "status"
        ]
        == "FAILED"
    )

    definition = (
        workspace.load_research_definition(
            research_id
        )
    )

    assert (
        definition[
            "definition_status"
        ]
        == "CREATED"
    )


def test_workspace_history_uses_run_manifest_status(
    isolated_workspace,
):
    created = workspace.create_research(
        base_definition()
    )

    research_id = created[
        "research_id"
    ]

    workspace.update_run_manifest(
        research_id,
        status="COMPLETED",
        current_stage="COMPLETED",
    )

    rows = workspace.list_researches()

    row = next(
        item
        for item in rows
        if (
            item[
                "research_id"
            ]
            == research_id
        )
    )

    assert (
        row[
            "status"
        ]
        == "COMPLETED"
    )

    definition = (
        workspace.load_research_definition(
            research_id
        )
    )

    assert (
        definition[
            "definition_status"
        ]
        == "CREATED"
    )


def test_legacy_research_definition_with_status_remains_readable(
    isolated_workspace,
):
    research_id = (
        "RES-LEGACY-STATUS-CONTRACT"
    )

    paths = workspace.research_paths(
        research_id
    )

    paths[
        "root"
    ].mkdir(
        parents=True,
        exist_ok=False,
    )

    legacy = {
        "research_id": research_id,
        "strategy": "TRADE_1",
        "status": "CREATED",
        "created_at": (
            "2026-01-01T00:00:00+00:00"
        ),
    }

    paths[
        "definition"
    ].write_text(
        json.dumps(
            legacy,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    before = (
        paths[
            "definition"
        ]
        .read_bytes()
    )

    loaded = (
        workspace.load_research_definition(
            research_id
        )
    )

    after = (
        paths[
            "definition"
        ]
        .read_bytes()
    )

    assert (
        loaded[
            "status"
        ]
        == "CREATED"
    )

    assert (
        "definition_status"
        not in loaded
    )

    assert before == after
