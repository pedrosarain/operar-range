from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.experiment_generator import (
    build_experiment_rows,
    config_sha256,
)
from operar_range.experiment_registry import (
    REGISTRY_SCHEMA,
)


BASE_CONFIG = {
    "stop_points": 170.0,
    "partial_1_points": 125.0,
    "partial_1_pct": 70.0,
    "partial_2_points": None,
    "partial_2_pct": None,
    "partial_3_points": None,
    "partial_3_pct": None,
    "break_even_enabled": True,
    "break_even_after_partial": 1,
    "runner_enabled": False,
    "runner_pct": None,
    "runner_rule": None,
    "final_target_points": 400.0,
}


def test_stage22_reuses_historical_experiment_identity(
    tmp_path: Path,
):
    registry_path = (
        tmp_path
        / "experiment_registry.parquet"
    )

    historical_created_at = (
        "2026-09-29T14:40:34+00:00"
    )

    historical_definition_sha256 = (
        "a" * 64
    )

    config_hash = config_sha256(
        BASE_CONFIG
    )

    registry_row = {
        "experiment_id": "EXP-000046",
        "config_sha256": config_hash,
        "family": "STAGE22_REAL_E2E",
        "generation": 1,
        "experiment_name": (
            "STAGE22_REAL_E2E_G1_EXP-000046"
        ),
        "status": "ACTIVE",
        "created_at": (
            historical_created_at
        ),
        "engine_version": (
            "experiment-generator-v1"
        ),
        "rules_version": (
            "ADR-004+STAGE10"
        ),
        "parent_experiment_id": None,
        "supersedes_experiment_id": None,
        "definition_sha256": (
            historical_definition_sha256
        ),
        "source_path": (
            "/historical/generated.parquet"
        ),
        "source_sha256": "b" * 64,
        "registry_version": (
            "experiment-registry-v1"
        ),
    }

    pq.write_table(
        pa.Table.from_pylist(
            [registry_row],
            schema=REGISTRY_SCHEMA,
        ),
        registry_path,
    )

    rows = build_experiment_rows(
        family="STAGE22_REAL_E2E",
        generation=1,
        created_at=(
            "2026-09-29T17:14:59+00:00"
        ),
        rules_version=(
            "ADR-004+STAGE10"
        ),
        base_config=BASE_CONFIG,
        parameter_definition={},
        trade2_enabled=None,
        trade2_management_mode=None,
        registry_path=registry_path,
    )

    assert len(rows) == 1

    row = rows[0]

    assert (
        row["experiment_id"]
        == "EXP-000046"
    )

    assert (
        row["config_sha256"]
        == config_hash
    )

    #
    # A nova execução NÃO pode redefinir
    # identidade histórica.
    #
    assert (
        row["created_at"]
        == historical_created_at
    )

    assert (
        row["definition_sha256"]
        == historical_definition_sha256
    )

    assert (
        row["family"]
        == "STAGE22_REAL_E2E"
    )

    assert (
        row["generation"]
        == 1
    )

    assert (
        row["experiment_name"]
        == (
            "STAGE22_REAL_E2E_G1_EXP-000046"
        )
    )


def test_stage22_new_configuration_gets_new_identity(
    tmp_path: Path,
):
    registry_path = (
        tmp_path
        / "experiment_registry.parquet"
    )

    old_config = dict(
        BASE_CONFIG
    )

    old_hash = config_sha256(
        old_config
    )

    registry_row = {
        "experiment_id": "EXP-000046",
        "config_sha256": old_hash,
        "family": "OLD_FAMILY",
        "generation": 1,
        "experiment_name": "OLD_EXP",
        "status": "ACTIVE",
        "created_at": (
            "2026-09-29T14:40:34+00:00"
        ),
        "engine_version": (
            "experiment-generator-v1"
        ),
        "rules_version": (
            "ADR-004+STAGE10"
        ),
        "parent_experiment_id": None,
        "supersedes_experiment_id": None,
        "definition_sha256": "a" * 64,
        "source_path": (
            "/historical/generated.parquet"
        ),
        "source_sha256": "b" * 64,
        "registry_version": (
            "experiment-registry-v1"
        ),
    }

    pq.write_table(
        pa.Table.from_pylist(
            [registry_row],
            schema=REGISTRY_SCHEMA,
        ),
        registry_path,
    )

    new_config = dict(
        BASE_CONFIG
    )

    new_config[
        "stop_points"
    ] = 175.0

    rows = build_experiment_rows(
        family="NEW_FAMILY",
        generation=2,
        created_at=(
            "2026-09-29T18:00:00+00:00"
        ),
        rules_version=(
            "ADR-004+STAGE10"
        ),
        base_config=new_config,
        parameter_definition={},
        registry_path=registry_path,
    )

    assert len(rows) == 1

    row = rows[0]

    assert (
        row["experiment_id"]
        == "EXP-000047"
    )

    assert (
        row["family"]
        == "NEW_FAMILY"
    )

    assert (
        row["generation"]
        == 2
    )

    assert (
        row["created_at"]
        == "2026-09-29T18:00:00+00:00"
    )



# ============================================================
# Stage 22 — canonical configuration identity
# ============================================================


def test_stage22_semantically_equivalent_numeric_config_reuses_identity(
    tmp_path: Path,
):
    from operar_range.experiment_generator import (
        generate_experiment_database,
    )
    from operar_range.experiment_registry import (
        read_registry,
    )

    registry_path = (
        tmp_path
        / "experiment_registry.parquet"
    )

    first_output = (
        tmp_path
        / "first.parquet"
    )

    second_output = (
        tmp_path
        / "second.parquet"
    )

    first_config = dict(
        BASE_CONFIG
    )

    first_config[
        "stop_points"
    ] = 170

    first = generate_experiment_database(
        output_path=first_output,
        family="CANONICAL_STAGE22",
        generation=1,
        created_at=(
            "2026-09-30T01:00:00+00:00"
        ),
        rules_version=(
            "ADR-004+STAGE10"
        ),
        base_config=first_config,
        parameter_definition={},
        registry_path=registry_path,
        register_generated=True,
    )

    first_rows = (
        pq.read_table(
            first_output
        )
        .to_pylist()
    )

    assert len(
        first_rows
    ) == 1

    first_row = first_rows[
        0
    ]

    rows_after_first = (
        read_registry(
            registry_path
        )
    )

    second_config = dict(
        BASE_CONFIG
    )

    second_config[
        "stop_points"
    ] = 170.0

    second = generate_experiment_database(
        output_path=second_output,
        family="CANONICAL_STAGE22",
        generation=1,
        created_at=(
            "2026-09-30T01:05:00+00:00"
        ),
        rules_version=(
            "ADR-004+STAGE10"
        ),
        base_config=second_config,
        parameter_definition={},
        registry_path=registry_path,
        register_generated=True,
    )

    second_rows = (
        pq.read_table(
            second_output
        )
        .to_pylist()
    )

    assert len(
        second_rows
    ) == 1

    second_row = second_rows[
        0
    ]

    rows_after_second = (
        read_registry(
            registry_path
        )
    )

    assert (
        first_row[
            "experiment_id"
        ]
        == second_row[
            "experiment_id"
        ]
    )

    assert (
        first_row[
            "config_sha256"
        ]
        == second_row[
            "config_sha256"
        ]
    )

    assert (
        first_row[
            "canonical_config_json"
        ]
        == second_row[
            "canonical_config_json"
        ]
    )

    assert (
        first_row[
            "config_identity_version"
        ]
        == "CANONICAL_V2"
    )

    assert (
        second_row[
            "config_identity_version"
        ]
        == "CANONICAL_V2"
    )

    assert len(
        rows_after_first
    ) == 1

    assert len(
        rows_after_second
    ) == 1

    assert (
        first[
            "registry_new_experiments"
        ]
        == 1
    )

    assert (
        second[
            "registry_new_experiments"
        ]
        == 0
    )


def test_stage22_exp000047_original_identity_is_recoverable(
    tmp_path: Path,
):
    from operar_range.experiment_generator import (
        build_experiment_rows,
        config_hashes_from_canonical_json,
    )

    registry_path = (
        tmp_path
        / "experiment_registry.parquet"
    )

    original_config = dict(
        BASE_CONFIG
    )

    original_config[
        "stop_points"
    ] = 161.0

    #
    # EXP-000047 historical payload recovered
    # from its original Research Definition.
    #
    # This is intentionally int 400, not
    # float 400.0. LEGACY_V1 identity preserves
    # the exact historical JSON representation.
    #
    original_config[
        "final_target_points"
    ] = 400

    expected_global_hash = (
        "a12758e9eadf509582c1bcd30c2f683c"
        "958c7f851dbed4e3073f023310c25fdc"
    )

    expected_trade1_hash = (
        "07dac49af1bb01d45b7257deccc549573"
        "af7ec3a448c8ae0c70bac57af514cb7"
    )

    registry_row = {
        "experiment_id": "EXP-000047",
        "config_sha256": (
            expected_global_hash
        ),
        "config_identity_version": None,
        "canonical_config_json": None,
        "trade1_config_sha256": None,
        "trade2_override_sha256": None,
        (
            "trade2_effective_config_sha256"
        ): None,
        "family": (
            "STAGE22_REGISTRY_FINAL_AUDIT"
        ),
        "generation": 1,
        "experiment_name": (
            "STAGE22_REGISTRY_FINAL_AUDIT_"
            "G1_EXP-000047"
        ),
        "status": "ACTIVE",
        "created_at": (
            "2026-09-30T00:23:12+00:00"
        ),
        "engine_version": (
            "experiment-generator-v1"
        ),
        "rules_version": (
            "ADR-004+STAGE10"
        ),
        "parent_experiment_id": None,
        "supersedes_experiment_id": None,
        "definition_sha256": (
            "282c3a9f6aafbae2498a954d10ea9bb1"
            "674e1ace3252b882c62fe08ecff45303"
        ),
        "source_path": (
            "/historical/generated.parquet"
        ),
        "source_sha256": "b" * 64,
        "registry_version": (
            "experiment-registry-v1"
        ),
    }

    pq.write_table(
        pa.Table.from_pylist(
            [
                registry_row
            ],
            schema=REGISTRY_SCHEMA,
        ),
        registry_path,
    )

    rows = build_experiment_rows(
        family=(
            "STAGE22_REGISTRY_FINAL_AUDIT"
        ),
        generation=1,
        created_at=(
            "2026-09-30T02:00:00+00:00"
        ),
        rules_version=(
            "ADR-004+STAGE10"
        ),
        base_config={
            **original_config,
            "stop_points": None,
            "partial_1_points": None,
            "partial_1_pct": None,
        },
        parameter_definition={
            "stop_points": {
                "values": [
                    161.0,
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
        trade2_enabled=False,
        trade2_management_mode="INHERIT",
        registry_path=registry_path,
    )

    assert len(
        rows
    ) == 1

    row = rows[
        0
    ]

    assert (
        row[
            "experiment_id"
        ]
        == "EXP-000047"
    )

    assert (
        row[
            "config_sha256"
        ]
        == expected_global_hash
    )

    assert (
        row[
            "trade1_config_sha256"
        ]
        == expected_trade1_hash
    )

    assert (
        row[
            "config_identity_version"
        ]
        == "LEGACY_V1_RECOVERED"
    )

    identity = (
        config_hashes_from_canonical_json(
            row[
                "canonical_config_json"
            ]
        )
    )

    assert (
        identity[
            "config_sha256"
        ]
        == expected_global_hash
    )

    assert (
        identity[
            "trade1_config_sha256"
        ]
        == expected_trade1_hash
    )

    assert (
        identity[
            "document"
        ][
            "trade1"
        ][
            "stop_points"
        ]
        == 161.0
    )
