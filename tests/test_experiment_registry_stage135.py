from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from operar_range.experiment_registry import (
    migrate_registry,
    next_available_id,
    freeze_experiment,
    supersede_experiment,
    set_parent,
    read_registry,
)


SOURCE_SCHEMA = pa.schema(
    [
        ("experiment_id", pa.string()),
        ("config_sha256", pa.string()),
        ("family", pa.string()),
        ("generation", pa.int64()),
        ("experiment_name", pa.string()),
        ("created_at", pa.string()),
        ("engine_version", pa.string()),
        ("rules_version", pa.string()),
        ("definition_sha256", pa.string()),
    ]
)


def write_source(
    path: Path,
    rows,
):
    table = pa.Table.from_pylist(
        rows,
        schema=SOURCE_SCHEMA,
    )

    pq.write_table(
        table,
        path,
    )


def row(
    experiment_id,
    config_hash,
    family="TRADE1_BASE",
    generation=1,
):
    return {
        "experiment_id": experiment_id,
        "config_sha256": config_hash,
        "family": family,
        "generation": generation,
        "experiment_name": experiment_id,
        "created_at": "2026-09-25T00:00:00Z",
        "engine_version": "v1",
        "rules_version": "rules-v1",
        "definition_sha256": "d" * 64,
    }


def test_initial_registry(
    tmp_path,
):
    source = tmp_path / "source.parquet"
    registry = tmp_path / "registry.parquet"

    write_source(
        source,
        [
            row(
                "EXP-000001",
                "a" * 64,
            ),
        ],
    )

    result = migrate_registry(
        registry_path=registry,
        source_paths=[source],
    )

    assert len(result["rows"]) == 1


def test_global_next_id():
    assert next_available_id(
        [
            {
                "experiment_id":
                "EXP-000021"
            }
        ]
    ) == "EXP-000022"


def test_idempotence(
    tmp_path,
):
    source = tmp_path / "source.parquet"
    registry = tmp_path / "registry.parquet"

    write_source(
        source,
        [
            row(
                "EXP-000001",
                "a" * 64,
            ),
        ],
    )

    first = migrate_registry(
        registry_path=registry,
        source_paths=[source],
    )

    second = migrate_registry(
        registry_path=registry,
        source_paths=[source],
    )

    assert (
        second["new_experiments"]
        == 0
    )

    assert (
        first["rows"]
        == second["rows"]
    )


def test_duplicate_configuration_rejected(
    tmp_path,
):
    source = tmp_path / "source.parquet"
    registry = tmp_path / "registry.parquet"

    write_source(
        source,
        [
            row(
                "EXP-000001",
                "a" * 64,
            ),
            row(
                "EXP-000002",
                "a" * 64,
            ),
        ],
    )

    with pytest.raises(
        RuntimeError
    ):
        migrate_registry(
            registry_path=registry,
            source_paths=[source],
        )


def test_families_and_generations(
    tmp_path,
):
    source = tmp_path / "source.parquet"
    registry = tmp_path / "registry.parquet"

    write_source(
        source,
        [
            row(
                "EXP-000001",
                "a" * 64,
                family="TRADE1_BASE",
                generation=1,
            ),
            row(
                "EXP-000002",
                "b" * 64,
                family=(
                    "TRADE1_STOP_RESEARCH"
                ),
                generation=2,
            ),
        ],
    )

    migrate_registry(
        registry_path=registry,
        source_paths=[source],
    )

    rows = read_registry(
        registry
    )

    assert rows[0]["generation"] == 1
    assert rows[1]["generation"] == 2


def test_freeze(
    tmp_path,
):
    source = tmp_path / "source.parquet"
    registry = tmp_path / "registry.parquet"

    write_source(
        source,
        [
            row(
                "EXP-000001",
                "a" * 64,
            ),
        ],
    )

    migrate_registry(
        registry_path=registry,
        source_paths=[source],
    )

    freeze_experiment(
        registry_path=registry,
        experiment_id="EXP-000001",
    )

    rows = read_registry(
        registry
    )

    assert rows[0]["status"] == "FROZEN"


def test_frozen_mutation_rejected(
    tmp_path,
):
    source = tmp_path / "source.parquet"
    registry = tmp_path / "registry.parquet"

    write_source(
        source,
        [
            row(
                "EXP-000001",
                "a" * 64,
            ),
        ],
    )

    migrate_registry(
        registry_path=registry,
        source_paths=[source],
    )

    freeze_experiment(
        registry_path=registry,
        experiment_id="EXP-000001",
    )

    write_source(
        source,
        [
            row(
                "EXP-000001",
                "b" * 64,
            ),
        ],
    )

    with pytest.raises(
        RuntimeError
    ):
        migrate_registry(
            registry_path=registry,
            source_paths=[source],
        )


def test_parent(
    tmp_path,
):
    source = tmp_path / "source.parquet"
    registry = tmp_path / "registry.parquet"

    write_source(
        source,
        [
            row(
                "EXP-000001",
                "a" * 64,
            ),
            row(
                "EXP-000002",
                "b" * 64,
            ),
        ],
    )

    migrate_registry(
        registry_path=registry,
        source_paths=[source],
    )

    set_parent(
        registry_path=registry,
        experiment_id="EXP-000002",
        parent_experiment_id=(
            "EXP-000001"
        ),
    )

    rows = read_registry(
        registry
    )

    assert (
        rows[1][
            "parent_experiment_id"
        ]
        == "EXP-000001"
    )


def test_supersedes(
    tmp_path,
):
    source = tmp_path / "source.parquet"
    registry = tmp_path / "registry.parquet"

    write_source(
        source,
        [
            row(
                "EXP-000001",
                "a" * 64,
            ),
            row(
                "EXP-000002",
                "b" * 64,
            ),
        ],
    )

    migrate_registry(
        registry_path=registry,
        source_paths=[source],
    )

    supersede_experiment(
        registry_path=registry,
        old_experiment_id=(
            "EXP-000001"
        ),
        new_experiment_id=(
            "EXP-000002"
        ),
    )

    rows = read_registry(
        registry
    )

    assert (
        rows[0]["status"]
        == "SUPERSEDED"
    )

    assert (
        rows[1][
            "supersedes_experiment_id"
        ]
        == "EXP-000001"
    )