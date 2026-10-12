from __future__ import annotations

import json

import pytest

from operar_range.manual_baseline_registry import (
    MANUAL_BASELINE_COMPARISON_STATUSES,
    MANUAL_BASELINE_REQUIRED_FIELDS,
    MANUAL_BASELINE_RESULT_CATEGORIES,
    baseline_version_path,
    build_manual_baseline_definition,
    comparison_contract_definition,
    list_manual_baseline_versions,
    list_manual_baselines,
    load_latest_manual_baseline,
    load_manual_baseline,
    manual_baseline_sha256,
    new_manual_baseline_id,
    validate_manual_baseline_definition,
    write_manual_baseline_version,
)


def _definition(
    *,
    version: int = 1,
):
    baseline_id = (
        new_manual_baseline_id(
            name=(
                "Synthetic Manual Study"
            ),
            strategy=(
                "SYNTHETIC_STRATEGY"
            ),
            market="TEST",
            asset="TEST1",
            author="Test Author",
        )
    )

    return (
        build_manual_baseline_definition(
            baseline_id=(
                baseline_id
            ),
            name=(
                "Synthetic Manual Study"
            ),
            description=(
                "Synthetic test fixture only."
            ),
            strategy=(
                "SYNTHETIC_STRATEGY"
            ),
            market="TEST",
            asset="TEST1",
            source_dataset_id=None,
            period_start="2026-01-01",
            period_end="2026-01-01",
            universe=(
                "Synthetic sessions"
            ),
            session_count=0,
            author="Test Author",
            created_at=(
                "2026-10-06T00:00:00Z"
            ),
            status="DRAFT",
            notes=(
                "No production baseline."
            ),
            version=version,
            results=[],
            components=[],
        )
    )


def test_manual_baseline_has_required_contract():
    definition = _definition()

    for field in (
        MANUAL_BASELINE_REQUIRED_FIELDS
    ):
        assert field in definition

    assert (
        definition[
            "baseline_id"
        ].startswith(
            "MBL-"
        )
    )

    assert (
        definition[
            "version"
        ]
        == 1
    )

    assert (
        definition[
            "results"
        ]
        == []
    )

    assert (
        definition[
            "source_dataset_id"
        ]
        is None
    )

    validate_manual_baseline_definition(
        definition
    )


def test_baseline_hash_is_reproducible():
    definition = _definition()

    assert (
        definition[
            "baseline_sha256"
        ]
        == manual_baseline_sha256(
            definition
        )
    )

    copied = dict(
        definition
    )

    assert (
        manual_baseline_sha256(
            copied
        )
        == definition[
            "baseline_sha256"
        ]
    )


def test_registry_is_empty_when_root_missing(
    tmp_path,
):
    root = (
        tmp_path
        / "manual"
        / "baselines"
    )

    assert (
        list_manual_baselines(
            root=root
        )
        == []
    )


def test_version_is_written_and_loaded(
    tmp_path,
):
    root = (
        tmp_path
        / "manual"
        / "baselines"
    )

    definition = _definition()

    path = (
        write_manual_baseline_version(
            definition,
            root=root,
        )
    )

    assert path.exists()

    loaded = load_manual_baseline(
        definition[
            "baseline_id"
        ],
        1,
        root=root,
    )

    assert loaded == definition

    assert (
        list_manual_baseline_versions(
            definition[
                "baseline_id"
            ],
            root=root,
        )
        == [
            1,
        ]
    )


def test_manual_baseline_version_is_immutable(
    tmp_path,
):
    root = (
        tmp_path
        / "manual"
        / "baselines"
    )

    definition = _definition()

    write_manual_baseline_version(
        definition,
        root=root,
    )

    with pytest.raises(
        FileExistsError
    ):
        write_manual_baseline_version(
            definition,
            root=root,
        )


def test_revision_preserves_history(
    tmp_path,
):
    root = (
        tmp_path
        / "manual"
        / "baselines"
    )

    version1 = _definition(
        version=1
    )

    version2 = (
        build_manual_baseline_definition(
            baseline_id=(
                version1[
                    "baseline_id"
                ]
            ),
            name=version1[
                "name"
            ],
            description=(
                version1[
                    "description"
                ]
            ),
            strategy=version1[
                "strategy"
            ],
            market=version1[
                "market"
            ],
            asset=version1[
                "asset"
            ],
            source_dataset_id=None,
            period_start="2026-01-01",
            period_end="2026-01-01",
            universe=version1[
                "universe"
            ],
            session_count=0,
            author=version1[
                "author"
            ],
            created_at=(
                "2026-10-07T00:00:00Z"
            ),
            status="DRAFT",
            notes=(
                "Synthetic revision."
            ),
            version=2,
            results=[],
            components=[],
        )
    )

    write_manual_baseline_version(
        version1,
        root=root,
    )

    write_manual_baseline_version(
        version2,
        root=root,
    )

    assert (
        list_manual_baseline_versions(
            version1[
                "baseline_id"
            ],
            root=root,
        )
        == [
            1,
            2,
        ]
    )

    assert (
        load_manual_baseline(
            version1[
                "baseline_id"
            ],
            1,
            root=root,
        )
        == version1
    )

    assert (
        load_latest_manual_baseline(
            version1[
                "baseline_id"
            ],
            root=root,
        )
        == version2
    )


def test_list_returns_latest_version_only(
    tmp_path,
):
    root = (
        tmp_path
        / "manual"
        / "baselines"
    )

    version1 = _definition(
        version=1
    )

    version2 = dict(
        version1
    )

    version2[
        "version"
    ] = 2

    version2[
        "created_at"
    ] = (
        "2026-10-07T00:00:00Z"
    )

    version2[
        "baseline_sha256"
    ] = manual_baseline_sha256(
        version2
    )

    write_manual_baseline_version(
        version1,
        root=root,
    )

    write_manual_baseline_version(
        version2,
        root=root,
    )

    rows = list_manual_baselines(
        root=root
    )

    assert len(
        rows
    ) == 1

    assert (
        rows[
            0
        ][
            "version"
        ]
        == 2
    )


def test_result_contract_supports_future_answers():
    baseline_id = (
        new_manual_baseline_id(
            name="Fixture",
            strategy="STRATEGY",
            market="TEST",
            asset="TEST",
            author="Author",
        )
    )

    definition = (
        build_manual_baseline_definition(
            baseline_id=baseline_id,
            name="Fixture",
            description=(
                "Synthetic fixture."
            ),
            strategy="STRATEGY",
            market="TEST",
            asset="TEST",
            source_dataset_id=None,
            period_start="2026-01-01",
            period_end="2026-01-01",
            universe="Synthetic",
            session_count=0,
            author="Author",
            created_at=(
                "2026-10-06T00:00:00Z"
            ),
            status="DRAFT",
            notes="",
            version=1,
            components=[],
            results=[
                {
                    "question_key": (
                        "target_100"
                    ),
                    "question_label": (
                        "Target 100"
                    ),
                    "category": (
                        "TARGET"
                    ),
                    "value_type": (
                        "INTEGER"
                    ),
                    "value": None,
                    "unit": (
                        "sessions"
                    ),
                    "dimensions": {
                        "target_points": (
                            100
                        )
                    },
                    "notes": "",
                },
                {
                    "question_key": (
                        "target_100_before_zero"
                    ),
                    "question_label": (
                        "Target 100 before zero"
                    ),
                    "category": (
                        "ZERO_RELATION"
                    ),
                    "value_type": (
                        "INTEGER"
                    ),
                    "value": None,
                    "unit": (
                        "sessions"
                    ),
                    "dimensions": {
                        "target_points": (
                            100
                        ),
                        "relation": (
                            "BEFORE_FIRST_ZERO"
                        ),
                    },
                    "notes": "",
                },
            ],
        )
    )

    assert len(
        definition[
            "results"
        ]
    ) == 2

    assert (
        definition[
            "results"
        ][
            0
        ][
            "value"
        ]
        is None
    )

    assert (
        "TARGET"
        in
        MANUAL_BASELINE_RESULT_CATEGORIES
    )

    assert (
        "TRADE_2"
        in
        MANUAL_BASELINE_RESULT_CATEGORIES
    )

    assert (
        "EXPECTANCY"
        in
        MANUAL_BASELINE_RESULT_CATEGORIES
    )

    assert (
        "WIN_RATE"
        in
        MANUAL_BASELINE_RESULT_CATEGORIES
    )

    assert (
        "DRAWDOWN"
        in
        MANUAL_BASELINE_RESULT_CATEGORIES
    )


def test_comparison_is_contract_only():
    contract = (
        comparison_contract_definition()
    )

    assert (
        contract[
            "comparison_implemented"
        ]
        is False
    )

    assert (
        contract[
            "implementation_status"
        ]
        == "CONTRACT_ONLY"
    )

    assert (
        tuple(
            contract[
                "statuses"
            ]
        )
        == (
            MANUAL_BASELINE_COMPARISON_STATUSES
        )
    )

    assert (
        "research_id"
        in contract[
            "fields"
        ]
    )

    assert (
        "manual_baseline_id"
        in contract[
            "fields"
        ]
    )

    assert (
        "status"
        in contract[
            "fields"
        ]
    )


def test_manual_baseline_is_not_research_dataset_or_experiment():
    definition = _definition()

    assert (
        "research_id"
        not in definition
    )

    assert (
        "experiment_id"
        not in definition
    )

    assert (
        "dataset_id"
        not in definition
    )

    assert (
        "source_dataset_id"
        in definition
    )


def test_version_filename_contract(
    tmp_path,
):
    definition = _definition()

    path = baseline_version_path(
        definition[
            "baseline_id"
        ],
        12,
        root=tmp_path,
    )

    assert (
        path.name
        == "000012.json"
    )


def test_persisted_payload_is_json(
    tmp_path,
):
    definition = _definition()

    path = (
        write_manual_baseline_version(
            definition,
            root=tmp_path,
        )
    )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert payload == definition
