from __future__ import annotations

from operar_range.dataset_store import (
    dataset_id,
    dataset_identity_payload,
    dataset_paths,
)


H1 = "a" * 64
H2 = "b" * 64


def test_single_file_dataset_id_is_deterministic():
    first = dataset_id(
        market="B3",
        asset="WIN",
        source_sha256=[
            H1
        ],
        period_start="2026-01-01",
        period_end="2026-12-31",
    )

    second = dataset_id(
        market="B3",
        asset="WIN",
        source_sha256=[
            H1
        ],
        period_start="2026-01-01",
        period_end="2026-12-31",
    )

    assert first == second
    assert first.startswith(
        "DS-"
    )


def test_multiple_files_are_one_dataset():
    identifier = dataset_id(
        market="B3",
        asset="WIN",
        source_sha256=[
            H1,
            H2,
        ],
        period_start="2025-01-01",
        period_end="2026-12-31",
    )

    assert identifier.startswith(
        "DS-"
    )


def test_source_order_does_not_change_dataset_id():
    first = dataset_id(
        market="B3",
        asset="WIN",
        source_sha256=[
            H1,
            H2,
        ],
        period_start="2025-01-01",
        period_end="2026-12-31",
    )

    second = dataset_id(
        market="B3",
        asset="WIN",
        source_sha256=[
            H2,
            H1,
        ],
        period_start="2025-01-01",
        period_end="2026-12-31",
    )

    assert first == second


def test_duplicate_source_hash_does_not_change_identity():
    first = dataset_id(
        market="B3",
        asset="WIN",
        source_sha256=[
            H1,
            H2,
        ],
        period_start="2025-01-01",
        period_end="2026-12-31",
    )

    second = dataset_id(
        market="B3",
        asset="WIN",
        source_sha256=[
            H1,
            H2,
            H1,
        ],
        period_start="2025-01-01",
        period_end="2026-12-31",
    )

    assert first == second


def test_content_change_changes_dataset_id():
    first = dataset_id(
        market="B3",
        asset="WIN",
        source_sha256=[
            H1
        ],
        period_start="2026-01-01",
        period_end="2026-12-31",
    )

    second = dataset_id(
        market="B3",
        asset="WIN",
        source_sha256=[
            H2
        ],
        period_start="2026-01-01",
        period_end="2026-12-31",
    )

    assert first != second


def test_aggregate_period_participates_in_identity():
    first = dataset_id(
        market="B3",
        asset="WIN",
        source_sha256=[
            H1
        ],
        period_start="2026-01-01",
        period_end="2026-06-30",
    )

    second = dataset_id(
        market="B3",
        asset="WIN",
        source_sha256=[
            H1
        ],
        period_start="2026-01-01",
        period_end="2026-12-31",
    )

    assert first != second


def test_identity_payload_sorts_source_hashes():
    payload = dataset_identity_payload(
        market="B3",
        asset="WIN",
        source_sha256=[
            H2,
            H1,
        ],
        period_start="2025-01-01",
        period_end="2026-12-31",
    )

    assert payload[
        "source_sha256"
    ] == [
        H1,
        H2,
    ]


def test_dataset_paths_are_isolated(tmp_path):
    first = dataset_paths(
        data_root=tmp_path,
        dataset_id_value=(
            "DS-FIRST"
        ),
    )

    second = dataset_paths(
        data_root=tmp_path,
        dataset_id_value=(
            "DS-SECOND"
        ),
    )

    assert (
        first[
            "normalized"
        ]
        != second[
            "normalized"
        ]
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
