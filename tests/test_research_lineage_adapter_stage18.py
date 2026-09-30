from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from operar_range.research_lineage_adapter import (
    EXPERIMENT_MANIFEST_SCHEMA,
    build_manifest_rows,
    build_research_manifest,
    canonical_json,
    sha256_file,
    validate_manifest_correspondence,
)


CONFIG_FIELDS = {
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


def valid_row(
    experiment_id: str,
    config_hash: str,
) -> dict:
    return {
        "experiment_id": (
            experiment_id
        ),
        "experiment_name": (
            f"TEST_{experiment_id}"
        ),
        "config_sha256": (
            config_hash
        ),
        "family": "TRADE1_BASE",
        "generation": 1,
        "created_at": (
            "2026-09-27T00:00:00Z"
        ),
        "motor_version": (
            "trade1-scanner-v1"
        ),
        "rules_version": (
            "ADR-004+STAGE10"
        ),
        **CONFIG_FIELDS,
    }


def registry_row(
    experiment_id: str,
    config_hash: str,
) -> dict:
    return {
        "experiment_id": (
            experiment_id
        ),
        "experiment_name": (
            f"TEST_{experiment_id}"
        ),
        "config_sha256": (
            config_hash
        ),
        "family": "TRADE1_BASE",
        "generation": 1,
        "status": "ACTIVE",
        "created_at": (
            "2026-09-27T00:00:00Z"
        ),
        "engine_version": (
            "experiment-generator-v1"
        ),
        "rules_version": (
            "ADR-004+STAGE10"
        ),
    }


def distributed_row(
    *,
    execution_unit_id: str,
    experiment_id: str,
    date: str,
    config_hash: str,
) -> dict:
    return {
        "execution_unit_id": (
            execution_unit_id
        ),
        "experiment_id": (
            experiment_id
        ),
        "date": date,
        "config_sha256": (
            config_hash
        ),
        "motor_version": (
            "trade1-scanner-v1"
        ),
        "rules_version": (
            "ADR-004+STAGE10"
        ),
        "trade_status": "TRADE_1",
        "total_weighted_points": 100.0,
    }


def trajectory_row(
    date: str,
) -> dict:
    return {
        "date": date,
        "trade1_status": "TRADE_1",
        "trajectory_exists": True,
    }


def base_inputs():
    exp1 = "EXP-000001"
    exp2 = "EXP-000002"

    hash1 = "a" * 64
    hash2 = "b" * 64

    valid = [
        valid_row(
            exp1,
            hash1,
        ),
        valid_row(
            exp2,
            hash2,
        ),
    ]

    registry = [
        registry_row(
            exp1,
            hash1,
        ),
        registry_row(
            exp2,
            hash2,
        ),
    ]

    results = [
        distributed_row(
            execution_unit_id=(
                "EU-000001"
            ),
            experiment_id=exp1,
            date="2026-08-18",
            config_hash=hash1,
        ),
        distributed_row(
            execution_unit_id=(
                "EU-000002"
            ),
            experiment_id=exp1,
            date="2026-08-19",
            config_hash=hash1,
        ),
        distributed_row(
            execution_unit_id=(
                "EU-000003"
            ),
            experiment_id=exp2,
            date="2026-08-18",
            config_hash=hash2,
        ),
        distributed_row(
            execution_unit_id=(
                "EU-000004"
            ),
            experiment_id=exp2,
            date="2026-08-19",
            config_hash=hash2,
        ),
    ]

    trajectories = [
        trajectory_row(
            "2026-08-18"
        ),
        trajectory_row(
            "2026-08-19"
        ),
    ]

    return (
        results,
        valid,
        registry,
        trajectories,
    )


def test_manifest_correct():
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    manifest = build_manifest_rows(
        distributed_results_rows=(
            results
        ),
        valid_experiment_rows=(
            valid
        ),
        registry_rows=(
            registry
        ),
        trajectory_rows=(
            trajectories
        ),
    )

    assert len(
        manifest
    ) == 2

    first = manifest[0]

    assert (
        first[
            "experiment_id"
        ]
        == "EXP-000001"
    )

    assert (
        first[
            "sessions_executed"
        ]
        == 2
    )

    assert (
        first[
            "config_sha256"
        ]
        == "a" * 64
    )

    assert (
        first[
            "motor_version"
        ]
        == "trade1-scanner-v1"
    )

    assert (
        first[
            "rules_version"
        ]
        == "ADR-004+STAGE10"
    )

    expected_config = (
        canonical_json(
            CONFIG_FIELDS
        )
    )

    assert (
        first[
            "config_json"
        ]
        == expected_config
    )


def test_manifest_schema_contract(
    tmp_path,
):
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    results_path = (
        tmp_path
        / "results.parquet"
    )

    valid_path = (
        tmp_path
        / "valid.parquet"
    )

    registry_path = (
        tmp_path
        / "registry.parquet"
    )

    trajectory_path = (
        tmp_path
        / "trajectory.parquet"
    )

    manifest_path = (
        tmp_path
        / "experiment_manifest.parquet"
    )

    write_parquet(
        results_path,
        results,
    )

    write_parquet(
        valid_path,
        valid,
    )

    write_parquet(
        registry_path,
        registry,
    )

    write_parquet(
        trajectory_path,
        trajectories,
    )

    build_research_manifest(
        distributed_results_path=(
            results_path
        ),
        valid_experiments_path=(
            valid_path
        ),
        registry_path=(
            registry_path
        ),
        trajectory_manifest_path=(
            trajectory_path
        ),
        output_path=(
            manifest_path
        ),
    )

    table = pq.read_table(
        manifest_path
    )

    assert (
        table.schema
        == EXPERIMENT_MANIFEST_SCHEMA
    )


def test_correspondence_one_to_one():
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    manifest = build_manifest_rows(
        distributed_results_rows=(
            results
        ),
        valid_experiment_rows=(
            valid
        ),
        registry_rows=(
            registry
        ),
        trajectory_rows=(
            trajectories
        ),
    )

    result = (
        validate_manifest_correspondence(
            distributed_results_rows=(
                results
            ),
            manifest_rows=(
                manifest
            ),
        )
    )

    assert (
        result[
            "match"
        ]
        is True
    )

    assert (
        result[
            "results_experiment_count"
        ]
        == 2
    )

    assert (
        result[
            "manifest_experiment_count"
        ]
        == 2
    )

    assert (
        result[
            "missing_manifest"
        ]
        == []
    )

    assert (
        result[
            "extra_manifest"
        ]
        == []
    )


def test_experiment_id_divergent():
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    valid = deepcopy(
        valid
    )

    valid[1][
        "experiment_id"
    ] = "EXP-999999"

    with pytest.raises(
        RuntimeError,
        match=(
            "missing from "
            "valid_experiments"
        ),
    ):
        build_manifest_rows(
            distributed_results_rows=(
                results
            ),
            valid_experiment_rows=(
                valid
            ),
            registry_rows=(
                registry
            ),
            trajectory_rows=(
                trajectories
            ),
        )


def test_config_sha256_divergent():
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    results = deepcopy(
        results
    )

    results[0][
        "config_sha256"
    ] = "c" * 64

    results[1][
        "config_sha256"
    ] = "c" * 64

    with pytest.raises(
        RuntimeError,
        match=(
            "Config hash mismatch"
        ),
    ):
        build_manifest_rows(
            distributed_results_rows=(
                results
            ),
            valid_experiment_rows=(
                valid
            ),
            registry_rows=(
                registry
            ),
            trajectory_rows=(
                trajectories
            ),
        )


def test_missing_experiment():
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    valid = [
        valid[0]
    ]

    with pytest.raises(
        RuntimeError,
        match=(
            "missing from "
            "valid_experiments"
        ),
    ):
        build_manifest_rows(
            distributed_results_rows=(
                results
            ),
            valid_experiment_rows=(
                valid
            ),
            registry_rows=(
                registry
            ),
            trajectory_rows=(
                trajectories
            ),
        )


def test_extra_experiment():
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    valid.append(
        valid_row(
            "EXP-000003",
            "c" * 64,
        )
    )

    registry.append(
        registry_row(
            "EXP-000003",
            "c" * 64,
        )
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "experiment absent from "
            "distributed results"
        ),
    ):
        build_manifest_rows(
            distributed_results_rows=(
                results
            ),
            valid_experiment_rows=(
                valid
            ),
            registry_rows=(
                registry
            ),
            trajectory_rows=(
                trajectories
            ),
        )


def test_hash_deterministic(
    tmp_path,
):
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    results_path = (
        tmp_path
        / "results.parquet"
    )

    valid_path = (
        tmp_path
        / "valid.parquet"
    )

    registry_path = (
        tmp_path
        / "registry.parquet"
    )

    trajectory_path = (
        tmp_path
        / "trajectory.parquet"
    )

    manifest_path = (
        tmp_path
        / "manifest.parquet"
    )

    write_parquet(
        results_path,
        results,
    )

    write_parquet(
        valid_path,
        valid,
    )

    write_parquet(
        registry_path,
        registry,
    )

    write_parquet(
        trajectory_path,
        trajectories,
    )

    first = build_research_manifest(
        distributed_results_path=(
            results_path
        ),
        valid_experiments_path=(
            valid_path
        ),
        registry_path=(
            registry_path
        ),
        trajectory_manifest_path=(
            trajectory_path
        ),
        output_path=(
            manifest_path
        ),
    )

    first_hash = (
        first[
            "experiment_manifest_sha256"
        ]
    )

    second = (
        build_research_manifest(
            distributed_results_path=(
                results_path
            ),
            valid_experiments_path=(
                valid_path
            ),
            registry_path=(
                registry_path
            ),
            trajectory_manifest_path=(
                trajectory_path
            ),
            output_path=(
                manifest_path
            ),
        )
    )

    second_hash = (
        second[
            "experiment_manifest_sha256"
        ]
    )

    assert (
        first_hash
        == second_hash
    )

    assert (
        first_hash
        == sha256_file(
            manifest_path
        )
    )


def test_idempotence(
    tmp_path,
):
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    results_path = (
        tmp_path
        / "results.parquet"
    )

    valid_path = (
        tmp_path
        / "valid.parquet"
    )

    registry_path = (
        tmp_path
        / "registry.parquet"
    )

    trajectory_path = (
        tmp_path
        / "trajectory.parquet"
    )

    manifest_path = (
        tmp_path
        / "manifest.parquet"
    )

    write_parquet(
        results_path,
        results,
    )

    write_parquet(
        valid_path,
        valid,
    )

    write_parquet(
        registry_path,
        registry,
    )

    write_parquet(
        trajectory_path,
        trajectories,
    )

    first = build_research_manifest(
        distributed_results_path=(
            results_path
        ),
        valid_experiments_path=(
            valid_path
        ),
        registry_path=(
            registry_path
        ),
        trajectory_manifest_path=(
            trajectory_path
        ),
        output_path=(
            manifest_path
        ),
    )

    second = build_research_manifest(
        distributed_results_path=(
            results_path
        ),
        valid_experiments_path=(
            valid_path
        ),
        registry_path=(
            registry_path
        ),
        trajectory_manifest_path=(
            trajectory_path
        ),
        output_path=(
            manifest_path
        ),
    )

    assert (
        first[
            "experiment_manifest_sha256"
        ]
        == second[
            "experiment_manifest_sha256"
        ]
    )

    assert (
        first[
            "lineage_match"
        ]
        is True
    )

    assert (
        second[
            "lineage_match"
        ]
        is True
    )


def test_research_ids_independent(
    tmp_path,
):
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    results_path = (
        tmp_path
        / "results.parquet"
    )

    valid_path = (
        tmp_path
        / "valid.parquet"
    )

    registry_path = (
        tmp_path
        / "registry.parquet"
    )

    trajectory_path = (
        tmp_path
        / "trajectory.parquet"
    )

    research_a = (
        tmp_path
        / "workspace"
        / "RESEARCH-A"
        / "experiment_manifest.parquet"
    )

    research_b = (
        tmp_path
        / "workspace"
        / "RESEARCH-B"
        / "experiment_manifest.parquet"
    )

    write_parquet(
        results_path,
        results,
    )

    write_parquet(
        valid_path,
        valid,
    )

    write_parquet(
        registry_path,
        registry,
    )

    write_parquet(
        trajectory_path,
        trajectories,
    )

    first = build_research_manifest(
        distributed_results_path=(
            results_path
        ),
        valid_experiments_path=(
            valid_path
        ),
        registry_path=(
            registry_path
        ),
        trajectory_manifest_path=(
            trajectory_path
        ),
        output_path=(
            research_a
        ),
    )

    second = build_research_manifest(
        distributed_results_path=(
            results_path
        ),
        valid_experiments_path=(
            valid_path
        ),
        registry_path=(
            registry_path
        ),
        trajectory_manifest_path=(
            trajectory_path
        ),
        output_path=(
            research_b
        ),
    )

    assert research_a.exists()
    assert research_b.exists()

    assert (
        research_a
        != research_b
    )

    assert (
        first[
            "experiment_manifest_sha256"
        ]
        == second[
            "experiment_manifest_sha256"
        ]
    )


def test_no_quantitative_recalculation(
    tmp_path,
):
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    results_path = (
        tmp_path
        / "results.parquet"
    )

    valid_path = (
        tmp_path
        / "valid.parquet"
    )

    registry_path = (
        tmp_path
        / "registry.parquet"
    )

    trajectory_path = (
        tmp_path
        / "trajectory.parquet"
    )

    manifest_path = (
        tmp_path
        / "manifest.parquet"
    )

    write_parquet(
        results_path,
        results,
    )

    write_parquet(
        valid_path,
        valid,
    )

    write_parquet(
        registry_path,
        registry,
    )

    write_parquet(
        trajectory_path,
        trajectories,
    )

    result = build_research_manifest(
        distributed_results_path=(
            results_path
        ),
        valid_experiments_path=(
            valid_path
        ),
        registry_path=(
            registry_path
        ),
        trajectory_manifest_path=(
            trajectory_path
        ),
        output_path=(
            manifest_path
        ),
    )

    assert (
        result[
            "quantitative_execution_repeated"
        ]
        is False
    )

    original_results = (
        pq.read_table(
            results_path
        )
        .to_pylist()
    )

    assert (
        original_results
        == results
    )


def test_incomplete_input():
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    broken = deepcopy(
        valid
    )

    del broken[0][
        "partial_1_pct"
    ]

    with pytest.raises(
        RuntimeError,
        match=(
            "missing configuration field"
        ),
    ):
        build_manifest_rows(
            distributed_results_rows=(
                results
            ),
            valid_experiment_rows=(
                broken
            ),
            registry_rows=(
                registry
            ),
            trajectory_rows=(
                trajectories
            ),
        )


def test_lineage_preserved(
    tmp_path,
):
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    results_path = (
        tmp_path
        / "results.parquet"
    )

    valid_path = (
        tmp_path
        / "valid.parquet"
    )

    registry_path = (
        tmp_path
        / "registry.parquet"
    )

    trajectory_path = (
        tmp_path
        / "trajectory.parquet"
    )

    manifest_path = (
        tmp_path
        / "manifest.parquet"
    )

    write_parquet(
        results_path,
        results,
    )

    write_parquet(
        valid_path,
        valid,
    )

    write_parquet(
        registry_path,
        registry,
    )

    write_parquet(
        trajectory_path,
        trajectories,
    )

    result = build_research_manifest(
        distributed_results_path=(
            results_path
        ),
        valid_experiments_path=(
            valid_path
        ),
        registry_path=(
            registry_path
        ),
        trajectory_manifest_path=(
            trajectory_path
        ),
        output_path=(
            manifest_path
        ),
    )

    assert (
        result[
            "distributed_results_sha256"
        ]
        == sha256_file(
            results_path
        )
    )

    assert (
        result[
            "source_valid_experiments_sha256"
        ]
        == sha256_file(
            valid_path
        )
    )

    assert (
        result[
            "registry_sha256"
        ]
        == sha256_file(
            registry_path
        )
    )

    assert (
        result[
            "trajectory_manifest_sha256"
        ]
        == sha256_file(
            trajectory_path
        )
    )

    assert (
        result[
            "lineage_match"
        ]
        is True
    )


def test_unknown_trajectory_session():
    (
        results,
        valid,
        registry,
        trajectories,
    ) = base_inputs()

    trajectories = [
        trajectory_row(
            "2026-08-18"
        )
    ]

    with pytest.raises(
        RuntimeError,
        match=(
            "sessions absent from "
            "trajectory manifest"
        ),
    ):
        build_manifest_rows(
            distributed_results_rows=(
                results
            ),
            valid_experiment_rows=(
                valid
            ),
            registry_rows=(
                registry
            ),
            trajectory_rows=(
                trajectories
            ),
        )


# ============================================================
# Stage 22 — canonical configuration lineage
# ============================================================


def test_stage22_lineage_uses_persisted_canonical_config_after_parquet_roundtrip(
    tmp_path,
):
    import pyarrow.parquet as pq

    import operar_range.research_lineage_adapter as lineage

    from operar_range.experiment_generator import (
        GENERATED_EXPERIMENT_SCHEMA,
        build_experiment_rows,
        config_hashes_from_canonical_json,
    )

    base_config = {
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
    }

    rows = build_experiment_rows(
        family="STAGE22_CANONICAL_LINEAGE",
        generation=1,
        created_at=(
            "2026-09-30T03:00:00+00:00"
        ),
        rules_version=(
            "ADR-004+STAGE10"
        ),
        base_config=base_config,
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
    )

    assert len(
        rows
    ) == 1

    generated_path = (
        tmp_path
        / "generated.parquet"
    )

    pq.write_table(
        pa.Table.from_pylist(
            rows,
            schema=(
                GENERATED_EXPERIMENT_SCHEMA
            ),
        ),
        generated_path,
    )

    reloaded = (
        pq.read_table(
            generated_path
        )
        .to_pylist()
    )

    assert len(
        reloaded
    ) == 1

    row = reloaded[
        0
    ]

    #
    # Individual numeric columns have passed
    # through Arrow/Parquet coercion.
    #
    assert isinstance(
        row[
            "stop_points"
        ],
        float,
    )

    assert isinstance(
        row[
            "partial_1_points"
        ],
        float,
    )

    #
    # Identity source survives unchanged.
    #
    canonical_before = rows[
        0
    ][
        "canonical_config_json"
    ]

    canonical_after = row[
        "canonical_config_json"
    ]

    assert (
        canonical_before
        == canonical_after
    )

    hashes = (
        config_hashes_from_canonical_json(
            canonical_after
        )
    )

    assert (
        hashes[
            "config_sha256"
        ]
        == row[
            "config_sha256"
        ]
    )

    assert (
        hashes[
            "trade1_config_sha256"
        ]
        == row[
            "trade1_config_sha256"
        ]
    )

    payload = (
        lineage._config_payload(
            row
        )
    )

    assert (
        payload[
            "canonical_config_json"
        ]
        == canonical_after
    )

    assert (
        payload[
            "trade1_config_sha256"
        ]
        == row[
            "trade1_config_sha256"
        ]
    )

    assert (
        payload[
            "trade2_override_sha256"
        ]
        == row[
            "trade2_override_sha256"
        ]
    )

    assert (
        payload[
            "trade2_effective_config_sha256"
        ]
        == row[
            "trade2_effective_config_sha256"
        ]
    )


def test_stage22_lineage_legacy_fallback_remains_available():
    import operar_range.research_lineage_adapter as lineage

    row = {
        "experiment_id": "EXP-LEGACY-TEST",
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

    payload = (
        lineage._config_payload(
            row
        )
    )

    assert (
        "canonical_config_json"
        not in payload
    )

    assert (
        payload[
            "stop_points"
        ]
        == 170.0
    )
