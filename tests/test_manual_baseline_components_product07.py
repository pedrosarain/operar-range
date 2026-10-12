from __future__ import annotations

import hashlib

import pytest

from operar_range.manual_baseline_registry import (
    MANUAL_BASELINE_COMPONENT_FIELDS,
    MANUAL_BASELINE_COMPONENTS_SCHEMA_VERSION,
    build_manual_baseline_definition,
    manual_baseline_components_sha256,
    validate_manual_baseline_definition,
)


def _component(
    *,
    order: int = 1,
):
    payload = b"synthetic"

    return {
        "component_order": order,
        "original_name": (
            "synthetic.xlsx"
        ),
        "stored_name": (
            "synthetic.xlsx"
        ),
        "media_type": (
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        "extension": ".xlsx",
        "size_bytes": len(
            payload
        ),
        "sha256": hashlib.sha256(
            payload
        ).hexdigest(),
    }


def _definition(
    components,
):
    return build_manual_baseline_definition(
        baseline_id=(
            "MBL-1234567890ABCDEF"
        ),
        name=(
            "Synthetic Composite Baseline"
        ),
        description=(
            "Synthetic fixture."
        ),
        strategy="SYNTHETIC",
        market="TEST",
        asset="TEST",
        source_dataset_id=None,
        period_start="2026-01-01",
        period_end="2026-01-01",
        universe="Synthetic",
        session_count=0,
        author="Test Author",
        created_at=(
            "2026-10-12T00:00:00Z"
        ),
        status="DRAFT",
        notes="",
        version=1,
        results=[],
        components=components,
    )


def test_component_contract_fields_are_explicit():
    assert (
        MANUAL_BASELINE_COMPONENT_FIELDS
        == (
            "component_order",
            "original_name",
            "stored_name",
            "media_type",
            "extension",
            "size_bytes",
            "sha256",
        )
    )


def test_component_schema_version_is_one():
    assert (
        MANUAL_BASELINE_COMPONENTS_SCHEMA_VERSION
        == 1
    )


def test_definition_supports_composite_baseline():
    component = _component()

    definition = _definition(
        [
            component,
        ]
    )

    assert (
        definition[
            "component_count"
        ]
        == 1
    )

    assert (
        definition[
            "components"
        ]
        == [
            component,
        ]
    )

    assert (
        definition[
            "components_sha256"
        ]
        == manual_baseline_components_sha256(
            [
                component,
            ]
        )
    )

    validate_manual_baseline_definition(
        definition
    )


def test_zero_components_remains_valid_for_product06():
    definition = _definition(
        []
    )

    assert (
        definition[
            "component_count"
        ]
        == 0
    )

    validate_manual_baseline_definition(
        definition
    )


def test_duplicate_component_order_rejected():
    with pytest.raises(
        ValueError
    ):
        _definition(
            [
                _component(
                    order=1
                ),
                {
                    **_component(
                        order=1
                    ),
                    "stored_name": (
                        "second.xlsx"
                    ),
                },
            ]
        )


def test_component_hash_is_deterministic():
    component = _component()

    first = (
        manual_baseline_components_sha256(
            [
                component,
            ]
        )
    )

    second = (
        manual_baseline_components_sha256(
            [
                dict(
                    component
                ),
            ]
        )
    )

    assert first == second


def test_component_hash_changes_with_file_hash():
    first = _component()

    second = dict(
        first
    )

    second[
        "sha256"
    ] = hashlib.sha256(
        b"other"
    ).hexdigest()

    assert (
        manual_baseline_components_sha256(
            [
                first,
            ]
        )
        != manual_baseline_components_sha256(
            [
                second,
            ]
        )
    )
