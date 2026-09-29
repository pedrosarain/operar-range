from __future__ import annotations

import json
from pathlib import Path

import pytest

import operar_range.research_workspace as workspace


def test_save_dataset_upload_requires_zip(
    tmp_path,
    monkeypatch,
):
    inbox = (
        tmp_path
        / "data"
        / "inbox"
    )

    monkeypatch.setattr(
        workspace,
        "INBOX_ROOT",
        inbox,
    )

    with pytest.raises(
        ValueError,
        match="ZIP",
    ):
        workspace.save_dataset_upload(
            filename="ticks.csv",
            content=b"abc",
        )


def test_save_dataset_upload_is_idempotent(
    tmp_path,
    monkeypatch,
):
    inbox = (
        tmp_path
        / "data"
        / "inbox"
    )

    monkeypatch.setattr(
        workspace,
        "INBOX_ROOT",
        inbox,
    )

    first = (
        workspace.save_dataset_upload(
            filename="ticks.zip",
            content=b"abc",
        )
    )

    second = (
        workspace.save_dataset_upload(
            filename="ticks.zip",
            content=b"abc",
        )
    )

    assert (
        first["sha256"]
        == second["sha256"]
    )

    assert (
        second["status"]
        == "ALREADY_PRESENT"
    )


def test_save_dataset_upload_rejects_same_name_different_content(
    tmp_path,
    monkeypatch,
):
    inbox = (
        tmp_path
        / "data"
        / "inbox"
    )

    monkeypatch.setattr(
        workspace,
        "INBOX_ROOT",
        inbox,
    )

    workspace.save_dataset_upload(
        filename="ticks.zip",
        content=b"abc",
    )

    with pytest.raises(
        FileExistsError
    ):
        workspace.save_dataset_upload(
            filename="ticks.zip",
            content=b"xyz",
        )


def test_stage22_catalog_reads_isolated_manifest(
    tmp_path,
    monkeypatch,
):
    data_root = (
        tmp_path
        / "data"
    )

    reports_root = (
        data_root
        / "reports"
    )

    reports_root.mkdir(
        parents=True
    )

    dataset_id = (
        "DS-0123456789ABCDEF"
    )

    dataset_root = (
        data_root
        / "datasets"
        / dataset_id
    )

    dataset_root.mkdir(
        parents=True
    )

    manifest = {
        "dataset_id": dataset_id,
        "dataset_version": 1,
        "market": "B3",
        "asset": "WIN",
        "provider": "TEST",
        "period_start": (
            "2026-08-18 09:00:00"
        ),
        "period_end": (
            "2026-08-19 18:00:00"
        ),
        "sessions_total": 2,
        "records_total": 100,
        "files_total": 1,
        "components_total": 2,
        "source_files": [
            "ticks.zip",
        ],
        "source_sha256": [
            "a" * 64,
        ],
        "quality_status": "READY",
        "research_ready": True,
        "imported_at": (
            "2026-09-29T00:00:00+00:00"
        ),
        "ingest_version": "ingest-v1",
        "normalization_version": (
            "vendor-normalization-v1"
        ),
        "derived_artifacts": {},
    }

    (
        dataset_root
        / "dataset_manifest.json"
    ).write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        workspace,
        "DATA_ROOT",
        data_root,
    )

    monkeypatch.setattr(
        workspace,
        "REPORTS_ROOT",
        reports_root,
    )

    rows = (
        workspace
        ._stage22_dataset_catalog()
    )

    assert len(
        rows
    ) == 1

    row = rows[0]

    assert (
        row["dataset_id"]
        == dataset_id
    )

    assert (
        row["market"]
        == "B3"
    )

    assert (
        row["asset"]
        == "WIN"
    )

    assert (
        row[
            "prepared_for_research"
        ]
        is True
    )

    assert (
        row["catalog_origin"]
        == "STAGE22_ISOLATED"
    )


def test_stage22_catalog_does_not_invent_legacy_market(
    tmp_path,
    monkeypatch,
):
    data_root = (
        tmp_path
        / "data"
    )

    reports_root = (
        data_root
        / "reports"
    )

    reports_root.mkdir(
        parents=True
    )

    monkeypatch.setattr(
        workspace,
        "DATA_ROOT",
        data_root,
    )

    monkeypatch.setattr(
        workspace,
        "REPORTS_ROOT",
        reports_root,
    )

    assert (
        workspace
        ._stage22_dataset_catalog()
        == []
    )
