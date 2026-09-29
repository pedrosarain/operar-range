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
