from __future__ import annotations

from operar_range.experiment_generator import (
    config_sha256,
    expand_parameter,
    expand_range,
    generate_configurations,
    build_experiment_rows,
)


BASE_CONFIG = {
    "stop_points": None,

    "partial_1_points": None,
    "partial_1_pct": 70,

    "partial_2_points": None,
    "partial_2_pct": None,

    "partial_3_points": None,
    "partial_3_pct": None,

    "break_even_enabled": False,
    "break_even_after_partial": 1,

    "runner_enabled": False,
    "runner_pct": 30,

    "runner_rule": (
        "CANDLE_BREAK_M5"
    ),

    "final_target_points": 400,
}


PARAMETERS = {
    "stop_points": {
        "values": [
            100,
            170,
        ]
    },

    "partial_1_points": {
        "values": [
            100,
            125,
        ]
    },

    "break_even_enabled": {
        "values": [
            True,
            False,
        ]
    },

    "runner_enabled": {
        "values": [
            True,
            False,
        ]
    },
}


def build_rows():
    return build_experiment_rows(
        family="TRADE1_BASE",
        generation=1,
        created_at=(
            "2026-09-25T00:00:00Z"
        ),
        rules_version=(
            "test-rules"
        ),
        base_config=BASE_CONFIG,
        parameter_definition=(
            PARAMETERS
        ),
    )


def test_range():
    assert expand_range(
        start=100,
        end=120,
        step=5,
    ) == [
        100,
        105,
        110,
        115,
        120,
    ]


def test_decimal_range():
    assert expand_range(
        start=1,
        end=2,
        step=0.5,
    ) == [
        1,
        1.5,
        2,
    ]


def test_list_parameter():
    result = expand_parameter(
        {
            "values": [
                100,
                125,
                150,
            ]
        }
    )

    assert result == [
        100,
        125,
        150,
    ]


def test_multiple_parameters():
    configs = (
        generate_configurations(
            base_config=(
                BASE_CONFIG
            ),
            parameter_definition=(
                PARAMETERS
            ),
        )
    )

    assert len(configs) == 16


def test_generation_deterministic():
    first = build_rows()
    second = build_rows()

    assert first == second


def test_unique_ids():
    rows = build_rows()

    ids = [
        row["experiment_id"]
        for row in rows
    ]

    assert len(ids) == len(
        set(ids)
    )


def test_unique_hashes():
    rows = build_rows()

    hashes = [
        row["config_sha256"]
        for row in rows
    ]

    assert len(hashes) == len(
        set(hashes)
    )


def test_hash_changes():
    first = dict(
        BASE_CONFIG
    )

    first[
        "stop_points"
    ] = 100

    second = dict(first)

    second[
        "stop_points"
    ] = 105

    assert (
        config_sha256(first)
        != config_sha256(second)
    )


def test_order():
    rows = build_rows()

    assert (
        rows[0][
            "stop_points"
        ]
        == 100
    )

    assert (
        rows[0][
            "partial_1_points"
        ]
        == 100
    )

    assert (
        rows[0][
            "break_even_enabled"
        ]
        is True
    )

    assert (
        rows[0][
            "runner_enabled"
        ]
        is True
    )

    assert (
        rows[1][
            "runner_enabled"
        ]
        is False
    )


def test_family():
    rows = build_rows()

    assert all(
        row["family"]
        == "TRADE1_BASE"
        for row in rows
    )


def test_generation():
    rows = build_rows()

    assert all(
        row["generation"] == 1
        for row in rows
    )


def test_complete_configuration():
    rows = build_rows()

    required = {
        "stop_points",
        "partial_1_points",
        "partial_1_pct",
        "partial_2_points",
        "partial_2_pct",
        "partial_3_points",
        "partial_3_pct",
        "break_even_enabled",
        "break_even_after_partial",
        "runner_enabled",
        "runner_pct",
        "runner_rule",
        "final_target_points",
    }

    for row in rows:
        assert required.issubset(
            row.keys()
        )


def test_metadata_present():
    row = build_rows()[0]

    assert row[
        "experiment_id"
    ]

    assert row[
        "experiment_name"
    ]

    assert row[
        "config_sha256"
    ]

    assert row[
        "definition_sha256"
    ]

    assert row[
        "engine_version"
    ]

    assert row[
        "rules_version"
    ]

    assert row[
        "created_at"
    ]


def test_reexecution_identical():
    assert (
        build_rows()
        == build_rows()
    )


def test_expected_first_hash_stable():
    rows = build_rows()

    first = rows[0]

    rebuilt_hash = (
        config_sha256(
            {
                key: first[key]
                for key in (
                    "stop_points",
                    "partial_1_points",
                    "partial_1_pct",
                    "partial_2_points",
                    "partial_2_pct",
                    "partial_3_points",
                    "partial_3_pct",
                    "break_even_enabled",
                    "break_even_after_partial",
                    "runner_enabled",
                    "runner_pct",
                    "runner_rule",
                    "final_target_points",
                )
            }
        )
    )

    assert (
        rebuilt_hash
        == first[
            "config_sha256"
        ]
    )