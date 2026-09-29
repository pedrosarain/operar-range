from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import operar_range.dataset_pipeline as pipeline
from operar_range.dataset_pipeline import (
    DatasetMaterializationError,
    prepare_dataset_for_research,
)
from operar_range.dataset_store import (
    dataset_paths,
)


def _write_parquet(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        [
            {
                "value": value,
            }
        ]
    )

    pq.write_table(
        table,
        path,
    )


def _create_dataset(
    *,
    root: Path,
    dataset_id: str,
    quality_status: str = "READY",
) -> dict[str, Path]:
    paths = dataset_paths(
        data_root=root,
        dataset_id_value=(
            dataset_id
        ),
    )

    for key in (
        "root",
        "normalized",
        "research",
        "trajectories",
        "reports",
    ):
        paths[
            key
        ].mkdir(
            parents=True,
            exist_ok=True,
        )

    _write_parquet(
        paths[
            "normalized"
        ]
        / "session.parquet",
        dataset_id,
    )

    manifest = {
        "dataset_id": (
            dataset_id
        ),
        "dataset_version": 1,
        "market": "B3",
        "asset": "WIN",
        "quality_status": (
            quality_status
        ),
        "research_ready": False,
        "derived_artifacts": {
            "trade1_database": None,
            "trajectory_manifest": None,
            "trajectories": [],
        },
    }

    paths[
        "manifest"
    ].write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return paths


def _install_fake_engines(
    monkeypatch,
    calls,
):
    def fake_scanner(
        *,
        normalized_dir,
        database_path,
        summary_path,
    ):
        normalized_dir = Path(
            normalized_dir
        )

        database_path = Path(
            database_path
        )

        summary_path = Path(
            summary_path
        )

        calls.append(
            {
                "engine": "scanner",
                "normalized_dir": str(
                    normalized_dir
                ),
                "database_path": str(
                    database_path
                ),
            }
        )

        _write_parquet(
            database_path,
            str(
                normalized_dir
            ),
        )

        summary_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        summary_path.write_text(
            json.dumps(
                {
                    "motor_version": (
                        "fake-scanner"
                    )
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        return {
            "records": [],
            "summary": {
                "motor_version": (
                    "fake-scanner"
                )
            },
            "database_path": str(
                database_path
            ),
            "summary_path": str(
                summary_path
            ),
        }

    def fake_trajectory_cache(
        *,
        normalized_dir,
        trajectory_dir,
        manifest_path,
    ):
        normalized_dir = Path(
            normalized_dir
        )

        trajectory_dir = Path(
            trajectory_dir
        )

        manifest_path = Path(
            manifest_path
        )

        calls.append(
            {
                "engine": (
                    "trajectory"
                ),
                "normalized_dir": str(
                    normalized_dir
                ),
                "trajectory_dir": str(
                    trajectory_dir
                ),
            }
        )

        trajectory_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        trajectory_path = (
            trajectory_dir
            / "session.parquet"
        )

        _write_parquet(
            trajectory_path,
            str(
                normalized_dir
            ),
        )

        _write_parquet(
            manifest_path,
            str(
                trajectory_path
            ),
        )

        return {
            "records": [],
            "validations": {},
            "manifest_path": str(
                manifest_path
            ),
        }

    monkeypatch.setattr(
        pipeline,
        "run_scanner",
        fake_scanner,
    )

    monkeypatch.setattr(
        pipeline,
        "run_trajectory_cache",
        fake_trajectory_cache,
    )


def test_prepare_uses_only_selected_dataset_normalized(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "data"

    first = _create_dataset(
        root=root,
        dataset_id="DS-FIRST",
    )

    second = _create_dataset(
        root=root,
        dataset_id="DS-SECOND",
    )

    calls = []

    _install_fake_engines(
        monkeypatch,
        calls,
    )

    prepare_dataset_for_research(
        dataset_id_value=(
            "DS-FIRST"
        ),
        data_root=root,
    )

    assert len(
        calls
    ) == 2

    for call in calls:
        assert (
            call[
                "normalized_dir"
            ]
            == str(
                first[
                    "normalized"
                ]
            )
        )

        assert (
            call[
                "normalized_dir"
            ]
            != str(
                second[
                    "normalized"
                ]
            )
        )


def test_trade_database_is_dataset_local(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "data"

    paths = _create_dataset(
        root=root,
        dataset_id="DS-FIRST",
    )

    calls = []

    _install_fake_engines(
        monkeypatch,
        calls,
    )

    result = (
        prepare_dataset_for_research(
            dataset_id_value=(
                "DS-FIRST"
            ),
            data_root=root,
        )
    )

    assert (
        paths[
            "trade1_database"
        ].exists()
    )

    assert (
        result[
            "manifest"
        ][
            "derived_artifacts"
        ][
            "trade1_database"
        ][
            "path"
        ]
        == str(
            paths[
                "trade1_database"
            ]
        )
    )


def test_trajectories_are_dataset_local(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "data"

    paths = _create_dataset(
        root=root,
        dataset_id="DS-FIRST",
    )

    calls = []

    _install_fake_engines(
        monkeypatch,
        calls,
    )

    result = (
        prepare_dataset_for_research(
            dataset_id_value=(
                "DS-FIRST"
            ),
            data_root=root,
        )
    )

    assert (
        paths[
            "trajectory_manifest"
        ].exists()
    )

    artifacts = (
        result[
            "manifest"
        ][
            "derived_artifacts"
        ][
            "trajectories"
        ]
    )

    assert len(
        artifacts
    ) == 1

    assert str(
        paths[
            "trajectories"
        ]
    ) in artifacts[
        0
    ][
        "path"
    ]


def test_preparation_marks_dataset_research_ready(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "data"

    _create_dataset(
        root=root,
        dataset_id="DS-FIRST",
    )

    calls = []

    _install_fake_engines(
        monkeypatch,
        calls,
    )

    result = (
        prepare_dataset_for_research(
            dataset_id_value=(
                "DS-FIRST"
            ),
            data_root=root,
        )
    )

    assert (
        result[
            "manifest"
        ][
            "research_ready"
        ]
        is True
    )

    assert (
        result[
            "status"
        ]
        == "READY"
    )


def test_invalid_quality_dataset_cannot_be_prepared(
    tmp_path,
):
    root = tmp_path / "data"

    _create_dataset(
        root=root,
        dataset_id="DS-BAD",
        quality_status="ERROR",
    )

    with pytest.raises(
        DatasetMaterializationError,
        match=(
            "quality status is not READY"
        ),
    ):
        prepare_dataset_for_research(
            dataset_id_value=(
                "DS-BAD"
            ),
            data_root=root,
        )


def test_missing_dataset_manifest_fails(
    tmp_path,
):
    with pytest.raises(
        DatasetMaterializationError,
        match=(
            "Dataset manifest does not exist"
        ),
    ):
        prepare_dataset_for_research(
            dataset_id_value=(
                "DS-MISSING"
            ),
            data_root=(
                tmp_path
                / "data"
            ),
        )


def test_two_dataset_preparations_remain_isolated(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "data"

    first = _create_dataset(
        root=root,
        dataset_id="DS-FIRST",
    )

    second = _create_dataset(
        root=root,
        dataset_id="DS-SECOND",
    )

    calls = []

    _install_fake_engines(
        monkeypatch,
        calls,
    )

    prepare_dataset_for_research(
        dataset_id_value=(
            "DS-FIRST"
        ),
        data_root=root,
    )

    first_db_before = (
        first[
            "trade1_database"
        ].read_bytes()
    )

    prepare_dataset_for_research(
        dataset_id_value=(
            "DS-SECOND"
        ),
        data_root=root,
    )

    first_db_after = (
        first[
            "trade1_database"
        ].read_bytes()
    )

    assert (
        first_db_before
        == first_db_after
    )

    assert (
        first[
            "trade1_database"
        ]
        != second[
            "trade1_database"
        ]
    )

    assert (
        first[
            "trajectory_manifest"
        ]
        != second[
            "trajectory_manifest"
        ]
    )


def test_preparation_is_idempotent(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "data"

    paths = _create_dataset(
        root=root,
        dataset_id="DS-FIRST",
    )

    calls = []

    _install_fake_engines(
        monkeypatch,
        calls,
    )

    first = (
        prepare_dataset_for_research(
            dataset_id_value=(
                "DS-FIRST"
            ),
            data_root=root,
        )
    )

    manifest_before = (
        paths[
            "manifest"
        ].read_bytes()
    )

    assert len(
        calls
    ) == 2

    second = (
        prepare_dataset_for_research(
            dataset_id_value=(
                "DS-FIRST"
            ),
            data_root=root,
        )
    )

    manifest_after = (
        paths[
            "manifest"
        ].read_bytes()
    )

    assert (
        second[
            "status"
        ]
        == "ALREADY_PREPARED"
    )

    assert len(
        calls
    ) == 2

    assert (
        manifest_before
        == manifest_after
    )

    assert (
        first[
            "dataset_id"
        ]
        == second[
            "dataset_id"
        ]
    )


def test_manifest_records_derived_hashes(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "data"

    _create_dataset(
        root=root,
        dataset_id="DS-FIRST",
    )

    calls = []

    _install_fake_engines(
        monkeypatch,
        calls,
    )

    result = (
        prepare_dataset_for_research(
            dataset_id_value=(
                "DS-FIRST"
            ),
            data_root=root,
        )
    )

    derived = (
        result[
            "manifest"
        ][
            "derived_artifacts"
        ]
    )

    assert (
        derived[
            "trade1_database"
        ][
            "sha256"
        ]
    )

    assert (
        derived[
            "scanner_summary"
        ][
            "sha256"
        ]
    )

    assert (
        derived[
            "trajectory_manifest"
        ][
            "sha256"
        ]
    )

    assert (
        derived[
            "trajectories"
        ][
            0
        ][
            "sha256"
        ]
    )
