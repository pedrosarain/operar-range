from __future__ import annotations

import json
import zipfile
from pathlib import Path

from operar_range.dataset_discovery import (
    discover_dataset,
)
from operar_range.dataset_pipeline import (
    materialize_dataset,
)
from operar_range.ingest import (
    sha256_file,
)


HEADER = (
    "ticker,date,time,trade_number,"
    "price,qty,vol,buy_agent,"
    "sell_agent,trade_type,aft\n"
)


def _csv(
    *,
    ticker: str,
    date: str,
) -> str:
    return (
        HEADER
        + (
            f"{ticker},{date},"
            "10:25:00.000,"
            "10,100000,1,100000,"
            "A,B,T,N\n"
        )
        + (
            f"{ticker},{date},"
            "10:30:00.000,"
            "20,100100,1,100100,"
            "A,B,T,N\n"
        )
    )


def _zip(
    root: Path,
    name: str,
    members: dict[str, str],
) -> Path:
    path = root / name

    with zipfile.ZipFile(
        path,
        "w",
        compression=(
            zipfile.ZIP_DEFLATED
        ),
    ) as archive:
        for member, content in (
            members.items()
        ):
            archive.writestr(
                member,
                content,
            )

    return path


def test_materialized_dataset_uses_isolated_root(
    tmp_path,
):
    source = _zip(
        tmp_path,
        "win.zip",
        {
            "day.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    discovery = discover_dataset(
        market="B3",
        asset="WIN",
        provider="TickData",
        selected_files=[
            source
        ],
    )

    result = materialize_dataset(
        discovery=discovery,
        selected_files=[
            source
        ],
        data_root=tmp_path / "data",
    )

    root = Path(
        result[
            "paths"
        ][
            "root"
        ]
    )

    assert root == (
        tmp_path
        / "data"
        / "datasets"
        / discovery[
            "dataset_id"
        ]
    )

    assert (
        root
        / "dataset_manifest.json"
    ).exists()

    assert (
        root
        / "normalized"
    ).exists()

    assert (
        root
        / "quality"
    ).exists()


def test_quality_report_points_to_aggregate_dataset(
    tmp_path,
):
    source = _zip(
        tmp_path,
        "win.zip",
        {
            "day.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    discovery = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            source
        ],
    )

    result = materialize_dataset(
        discovery=discovery,
        selected_files=[
            source
        ],
        data_root=tmp_path / "data",
    )

    quality_dir = Path(
        result[
            "paths"
        ][
            "quality"
        ]
    )

    reports = list(
        quality_dir.glob(
            "*.quality.json"
        )
    )

    assert len(
        reports
    ) == 1

    report = json.loads(
        reports[
            0
        ].read_text(
            encoding="utf-8"
        )
    )

    assert (
        report[
            "dataset_id"
        ]
        == discovery[
            "dataset_id"
        ]
    )

    assert (
        report[
            "market"
        ]
        == "B3"
    )

    assert (
        report[
            "asset"
        ]
        == "WIN"
    )


def test_manifest_contains_required_dataset_metadata(
    tmp_path,
):
    source = _zip(
        tmp_path,
        "win.zip",
        {
            "day.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    discovery = discover_dataset(
        market="B3",
        asset="WIN",
        provider="TickData",
        selected_files=[
            source
        ],
    )

    result = materialize_dataset(
        discovery=discovery,
        selected_files=[
            source
        ],
        data_root=tmp_path / "data",
    )

    manifest = result[
        "manifest"
    ]

    required = {
        "dataset_id",
        "dataset_version",
        "market",
        "asset",
        "provider",
        "imported_at",
        "ingest_version",
        "normalization_version",
        "period_start",
        "period_end",
        "files_total",
        "components_total",
        "sessions_total",
        "records_total",
        "source_files",
        "source_sha256",
        "sources",
        "normalized_artifacts",
        "quality_artifacts",
        "quality_status",
        "research_ready",
        "derived_artifacts",
    }

    assert required.issubset(
        manifest
    )

    assert (
        manifest[
            "provider"
        ]
        == "TickData"
    )

    assert (
        manifest[
            "quality_status"
        ]
        == "READY"
    )

    assert (
        manifest[
            "research_ready"
        ]
        is False
    )


def test_two_datasets_are_physically_isolated(
    tmp_path,
):
    first_source = _zip(
        tmp_path,
        "first.zip",
        {
            "day.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    second_source = _zip(
        tmp_path,
        "second.zip",
        {
            "day.csv": _csv(
                ticker="WIN",
                date="2026-01-05",
            )
        },
    )

    first_discovery = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            first_source
        ],
    )

    second_discovery = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            second_source
        ],
    )

    first = materialize_dataset(
        discovery=first_discovery,
        selected_files=[
            first_source
        ],
        data_root=tmp_path / "data",
    )

    second = materialize_dataset(
        discovery=second_discovery,
        selected_files=[
            second_source
        ],
        data_root=tmp_path / "data",
    )

    assert (
        first_discovery[
            "dataset_id"
        ]
        != second_discovery[
            "dataset_id"
        ]
    )

    assert (
        first[
            "paths"
        ][
            "root"
        ]
        != second[
            "paths"
        ][
            "root"
        ]
    )

    assert (
        first[
            "paths"
        ][
            "normalized"
        ]
        != second[
            "paths"
        ][
            "normalized"
        ]
    )


def test_importing_second_dataset_does_not_change_first(
    tmp_path,
):
    first_source = _zip(
        tmp_path,
        "first.zip",
        {
            "first.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    second_source = _zip(
        tmp_path,
        "second.zip",
        {
            "second.csv": _csv(
                ticker="WIN",
                date="2026-01-05",
            )
        },
    )

    first_discovery = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            first_source
        ],
    )

    first = materialize_dataset(
        discovery=first_discovery,
        selected_files=[
            first_source
        ],
        data_root=tmp_path / "data",
    )

    first_manifest = Path(
        first[
            "manifest_path"
        ]
    )

    before = (
        first_manifest
        .read_bytes()
    )

    second_discovery = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            second_source
        ],
    )

    materialize_dataset(
        discovery=second_discovery,
        selected_files=[
            second_source
        ],
        data_root=tmp_path / "data",
    )

    after = (
        first_manifest
        .read_bytes()
    )

    assert before == after


def test_materialization_is_idempotent(
    tmp_path,
):
    source = _zip(
        tmp_path,
        "win.zip",
        {
            "day.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    discovery = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            source
        ],
    )

    first = materialize_dataset(
        discovery=discovery,
        selected_files=[
            source
        ],
        data_root=tmp_path / "data",
    )

    manifest_path = Path(
        first[
            "manifest_path"
        ]
    )

    before = (
        manifest_path
        .read_bytes()
    )

    second = materialize_dataset(
        discovery=discovery,
        selected_files=[
            source
        ],
        data_root=tmp_path / "data",
    )

    after = (
        manifest_path
        .read_bytes()
    )

    assert (
        second[
            "status"
        ]
        == "ALREADY_MATERIALIZED"
    )

    assert before == after


def test_source_and_normalized_hashes_are_recorded(
    tmp_path,
):
    source = _zip(
        tmp_path,
        "win.zip",
        {
            "day.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    discovery = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            source
        ],
    )

    result = materialize_dataset(
        discovery=discovery,
        selected_files=[
            source
        ],
        data_root=tmp_path / "data",
    )

    manifest = result[
        "manifest"
    ]

    assert (
        manifest[
            "sources"
        ][
            0
        ][
            "sha256"
        ]
        == sha256_file(
            source
        )
    )

    normalized = (
        manifest[
            "normalized_artifacts"
        ][
            0
        ]
    )

    assert (
        normalized[
            "sha256"
        ]
        == sha256_file(
            normalized[
                "path"
            ]
        )
    )


def test_multiple_zip_files_share_one_dataset_root(
    tmp_path,
):
    first_source = _zip(
        tmp_path,
        "2025.zip",
        {
            "2025.csv": _csv(
                ticker="WIN",
                date="2025-06-10",
            )
        },
    )

    second_source = _zip(
        tmp_path,
        "2026.zip",
        {
            "2026.csv": _csv(
                ticker="WIN",
                date="2026-08-18",
            )
        },
    )

    discovery = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            first_source,
            second_source,
        ],
    )

    result = materialize_dataset(
        discovery=discovery,
        selected_files=[
            first_source,
            second_source,
        ],
        data_root=tmp_path / "data",
    )

    root = Path(
        result[
            "paths"
        ][
            "root"
        ]
    )

    source_zips = list(
        (
            root
            / "source"
            / "zip"
        ).glob(
            "*.zip"
        )
    )

    normalized = list(
        (
            root
            / "normalized"
        ).glob(
            "*.parquet"
        )
    )

    assert len(
        source_zips
    ) == 2

    assert len(
        normalized
    ) == 2

    assert (
        result[
            "manifest"
        ][
            "files_total"
        ]
        == 2
    )

    assert (
        result[
            "manifest"
        ][
            "sessions_total"
        ]
        == 2
    )


# ============================================================
# Stage 22 — Alternative C transactional Materialization
# ============================================================

import pytest
import operar_range.dataset_pipeline as pipeline


@pytest.mark.parametrize(
    "failure_call",
    [
        1,
        2,
        3,
    ],
)
def test_materialization_failure_never_exposes_partial_dataset(
    tmp_path,
    monkeypatch,
    failure_call,
):
    source = _zip(
        tmp_path,
        "three_components.zip",
        {
            "01.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            ),
            "02.csv": _csv(
                ticker="WIN",
                date="2026-01-05",
            ),
            "03.csv": _csv(
                ticker="WIN",
                date="2026-01-06",
            ),
        },
    )

    discovery = discover_dataset(
        market="B3",
        asset="WIN",
        provider="AUDIT_GATE",
        selected_files=[
            source
        ],
    )

    original = (
        pipeline.normalize_vendor_csv
    )

    calls = {
        "count": 0,
    }

    def controlled_failure(
        *args,
        **kwargs,
    ):
        calls[
            "count"
        ] += 1

        if (
            calls[
                "count"
            ]
            == failure_call
        ):
            raise RuntimeError(
                f"CONTROLLED_FAILURE_{failure_call}"
            )

        return original(
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        pipeline,
        "normalize_vendor_csv",
        controlled_failure,
    )

    data_root = (
        tmp_path
        / "data"
    )

    final_root = (
        data_root
        / "datasets"
        / discovery[
            "dataset_id"
        ]
    )

    staging_root = (
        data_root
        / "datasets"
        / ".staging"
        / discovery[
            "dataset_id"
        ]
    )

    with pytest.raises(
        RuntimeError,
        match=(
            f"CONTROLLED_FAILURE_{failure_call}"
        ),
    ):
        materialize_dataset(
            discovery=discovery,
            selected_files=[
                source
            ],
            data_root=data_root,
        )

    #
    # Fundamental Stage 22 invariant:
    # partial Materialization never becomes a Dataset.
    #
    assert (
        final_root.exists()
        is False
    )

    assert (
        (
            final_root
            / "dataset_manifest.json"
        ).exists()
        is False
    )

    #
    # Staging may exist for diagnostics,
    # but it is physically outside the definitive
    # Dataset path.
    #
    assert staging_root.exists()

    state_path = (
        staging_root
        / ".dataset_state.json"
    )

    assert state_path.exists()

    state = json.loads(
        state_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        state[
            "dataset_state"
        ]
        == "FAILED_MATERIALIZATION"
    )


def test_successful_materialization_atomically_promotes_dataset(
    tmp_path,
):
    source = _zip(
        tmp_path,
        "success.zip",
        {
            "01.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            ),
            "02.csv": _csv(
                ticker="WIN",
                date="2026-01-05",
            ),
        },
    )

    discovery = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            source
        ],
    )

    data_root = (
        tmp_path
        / "data"
    )

    result = materialize_dataset(
        discovery=discovery,
        selected_files=[
            source
        ],
        data_root=data_root,
    )

    final_root = (
        data_root
        / "datasets"
        / discovery[
            "dataset_id"
        ]
    )

    staging_root = (
        data_root
        / "datasets"
        / ".staging"
        / discovery[
            "dataset_id"
        ]
    )

    assert (
        result[
            "status"
        ]
        == "MATERIALIZED"
    )

    assert final_root.exists()

    assert (
        final_root
        / "dataset_manifest.json"
    ).exists()

    assert (
        staging_root.exists()
        is False
    )

    manifest = json.loads(
        (
            final_root
            / "dataset_manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        manifest[
            "dataset_state"
        ]
        == "MATERIALIZED"
    )

    assert (
        manifest[
            "research_ready"
        ]
        is False
    )


def test_materialization_retry_discards_failed_staging_and_succeeds(
    tmp_path,
    monkeypatch,
):
    source = _zip(
        tmp_path,
        "retry.zip",
        {
            "01.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            ),
            "02.csv": _csv(
                ticker="WIN",
                date="2026-01-05",
            ),
        },
    )

    discovery = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            source
        ],
    )

    data_root = (
        tmp_path
        / "data"
    )

    original = (
        pipeline.normalize_vendor_csv
    )

    calls = {
        "count": 0,
    }

    def fail_second(
        *args,
        **kwargs,
    ):
        calls[
            "count"
        ] += 1

        if (
            calls[
                "count"
            ]
            == 2
        ):
            raise RuntimeError(
                "CONTROLLED_MID_FAILURE"
            )

        return original(
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        pipeline,
        "normalize_vendor_csv",
        fail_second,
    )

    with pytest.raises(
        RuntimeError,
        match="CONTROLLED_MID_FAILURE",
    ):
        materialize_dataset(
            discovery=discovery,
            selected_files=[
                source
            ],
            data_root=data_root,
        )

    final_root = (
        data_root
        / "datasets"
        / discovery[
            "dataset_id"
        ]
    )

    assert (
        final_root.exists()
        is False
    )

    monkeypatch.setattr(
        pipeline,
        "normalize_vendor_csv",
        original,
    )

    result = materialize_dataset(
        discovery=discovery,
        selected_files=[
            source
        ],
        data_root=data_root,
    )

    assert (
        result[
            "status"
        ]
        == "MATERIALIZED"
    )

    assert final_root.exists()

    assert (
        result[
            "manifest"
        ][
            "research_ready"
        ]
        is False
    )
