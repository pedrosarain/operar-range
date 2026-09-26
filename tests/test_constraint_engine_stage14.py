from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.constraint_engine import (
    evaluate_config,
    rule_manifest_rows,
    rule_set_sha256,
    run_constraint_engine,
    sha256_file,
)


def base_config():
    return {
        "experiment_id": "EXP-000001",
        "config_sha256": "a" * 64,
        "family": "TRADE1_BASE",
        "generation": 1,
        "experiment_name": "TEST",
        "definition_sha256": "d" * 64,
        "stop_points": 170.0,
        "partial_1_points": 125.0,
        "partial_1_pct": 70.0,
        "partial_2_points": None,
        "partial_2_pct": None,
        "partial_3_points": None,
        "partial_3_pct": None,
        "break_even_enabled": True,
        "break_even_after_partial": 1,
        "runner_enabled": True,
        "runner_pct": 30.0,
        "runner_rule": "CANDLE_BREAK_M5",
        "final_target_points": None,
    }


def codes(config):
    errors, warnings = (
        evaluate_config(
            config
        )
    )

    return (
        [
            item.rule_code
            for item in errors
        ],
        [
            item.rule_code
            for item in warnings
        ],
    )


def test_valid_simple():
    config = base_config()

    config[
        "partial_1_points"
    ] = None
    config[
        "partial_1_pct"
    ] = None

    config[
        "break_even_enabled"
    ] = False
    config[
        "break_even_after_partial"
    ] = None

    config[
        "runner_enabled"
    ] = False
    config[
        "runner_pct"
    ] = None
    config[
        "runner_rule"
    ] = None

    config[
        "final_target_points"
    ] = 100.0

    errors, _ = codes(config)

    assert errors == []


def test_c001_negative_stop():
    config = base_config()
    config["stop_points"] = -1

    errors, _ = codes(config)

    assert "C001" in errors


def test_c002_invalid_pct():
    config = base_config()
    config["partial_1_pct"] = 101

    errors, _ = codes(config)

    assert "C002" in errors


def test_c003_allocation_sum():
    config = base_config()
    config["partial_1_pct"] = 80
    config["runner_pct"] = 30

    errors, _ = codes(config)

    assert "C003" in errors
    assert "C010" in errors


def test_c004_points_without_pct():
    config = base_config()
    config["partial_1_pct"] = None

    errors, _ = codes(config)

    assert "C004" in errors


def test_c004_pct_without_points():
    config = base_config()
    config["partial_1_points"] = None

    errors, _ = codes(config)

    assert "C004" in errors


def test_c005_partial_order():
    config = base_config()

    config["partial_1_points"] = 200
    config["partial_1_pct"] = 30
    config["partial_2_points"] = 100
    config["partial_2_pct"] = 30
    config["runner_pct"] = 40

    errors, _ = codes(config)

    assert "C005" in errors


def test_c006_be_without_partial():
    config = base_config()

    config["partial_1_points"] = None
    config["partial_1_pct"] = None

    errors, _ = codes(config)

    assert "C006" in errors


def test_c006_be_missing_partial_2():
    config = base_config()

    config[
        "break_even_after_partial"
    ] = 2

    errors, _ = codes(config)

    assert "C006" in errors


def test_c007_inactive_be_reference():
    config = base_config()

    config[
        "break_even_enabled"
    ] = False

    errors, _ = codes(config)

    assert "C007" in errors


def test_c008_runner_without_pct():
    config = base_config()
    config["runner_pct"] = None

    errors, _ = codes(config)

    assert "C008" in errors


def test_c008_runner_without_rule():
    config = base_config()
    config["runner_rule"] = None

    errors, _ = codes(config)

    assert "C008" in errors


def test_c009_disabled_runner_fields():
    config = base_config()
    config["runner_enabled"] = False

    errors, _ = codes(config)

    assert "C009" in errors


def test_c011_target_without_residual():
    config = base_config()

    config[
        "final_target_points"
    ] = 400

    errors, warnings = codes(
        config
    )

    assert "C011" in errors
    assert "C013" in errors
    assert "C013" not in warnings


def test_c012_invalid_target():
    config = base_config()

    config[
        "final_target_points"
    ] = 0

    errors, _ = codes(config)

    assert "C012" in errors


def test_c013_is_error():
    config = base_config()

    config[
        "partial_1_pct"
    ] = 40

    config[
        "runner_pct"
    ] = 30

    config[
        "final_target_points"
    ] = 400

    errors, warnings = codes(
        config
    )

    assert "C013" in errors
    assert "C013" not in warnings


def test_valid_multiple_partials():
    config = base_config()

    config[
        "partial_1_points"
    ] = 100
    config[
        "partial_1_pct"
    ] = 30

    config[
        "partial_2_points"
    ] = 175
    config[
        "partial_2_pct"
    ] = 30

    config[
        "runner_pct"
    ] = 40

    errors, _ = codes(config)

    assert errors == []


def test_valid_be():
    config = base_config()

    errors, _ = codes(config)

    assert errors == []


def test_multiple_violations():
    config = base_config()

    config["stop_points"] = -1
    config["partial_1_pct"] = None
    config["runner_pct"] = 200

    errors, _ = codes(config)

    assert "C001" in errors
    assert "C002" in errors
    assert "C004" in errors


def test_rule_set_hash_deterministic():
    first = rule_set_sha256()
    second = rule_set_sha256()

    assert first == second
    assert len(first) == 64


def test_rule_manifest():
    rows = rule_manifest_rows(
        created_at=(
            "2026-09-25T00:00:00Z"
        )
    )

    assert rows
    assert rows[0]["rule_code"] == "C001"

    codes_found = {
        row["rule_code"]
        for row in rows
    }

    assert "C013" in codes_found

    c013 = next(
        row
        for row in rows
        if row["rule_code"] == "C013"
    )

    assert c013["severity"] == "ERROR"


GENERATED_SCHEMA = pa.schema(
    [
        ("experiment_id", pa.string()),
        ("config_sha256", pa.string()),
        ("family", pa.string()),
        ("generation", pa.int64()),
        ("experiment_name", pa.string()),
        ("definition_sha256", pa.string()),
        ("stop_points", pa.float64()),
        ("partial_1_points", pa.float64()),
        ("partial_1_pct", pa.float64()),
        ("partial_2_points", pa.float64()),
        ("partial_2_pct", pa.float64()),
        ("partial_3_points", pa.float64()),
        ("partial_3_pct", pa.float64()),
        ("break_even_enabled", pa.bool_()),
        (
            "break_even_after_partial",
            pa.int64(),
        ),
        ("runner_enabled", pa.bool_()),
        ("runner_pct", pa.float64()),
        ("runner_rule", pa.string()),
        (
            "final_target_points",
            pa.float64(),
        ),
    ]
)


REGISTRY_SCHEMA = pa.schema(
    [
        ("experiment_id", pa.string()),
        ("config_sha256", pa.string()),
        ("status", pa.string()),
    ]
)


def write_generated(
    path: Path,
    rows,
):
    pq.write_table(
        pa.Table.from_pylist(
            rows,
            schema=GENERATED_SCHEMA,
        ),
        path,
    )


def write_registry(
    path: Path,
    rows,
):
    pq.write_table(
        pa.Table.from_pylist(
            rows,
            schema=REGISTRY_SCHEMA,
        ),
        path,
    )


def source_row(
    experiment_id,
    config_hash,
):
    row = base_config()

    row["experiment_id"] = (
        experiment_id
    )

    row["config_sha256"] = (
        config_hash
    )

    return row


def test_engine_outputs_and_registry_unchanged(
    tmp_path,
):
    generated = (
        tmp_path / "generated.parquet"
    )

    registry = (
        tmp_path / "registry.parquet"
    )

    valid = (
        tmp_path / "valid.parquet"
    )

    rejected = (
        tmp_path / "rejected.parquet"
    )

    rules = (
        tmp_path / "rules.parquet"
    )

    summary = (
        tmp_path / "summary.json"
    )

    valid_row = source_row(
        "EXP-000001",
        "a" * 64,
    )

    invalid_row = source_row(
        "EXP-000002",
        "b" * 64,
    )

    invalid_row[
        "stop_points"
    ] = -1

    write_generated(
        generated,
        [
            valid_row,
            invalid_row,
        ],
    )

    write_registry(
        registry,
        [
            {
                "experiment_id":
                    "EXP-000001",
                "config_sha256":
                    "a" * 64,
                "status": "FROZEN",
            },
            {
                "experiment_id":
                    "EXP-000002",
                "config_sha256":
                    "b" * 64,
                "status": "ACTIVE",
            },
        ],
    )

    registry_hash = (
        sha256_file(
            registry
        )
    )

    result = run_constraint_engine(
        generated_path=generated,
        registry_path=registry,
        valid_path=valid,
        rejected_path=rejected,
        rules_path=rules,
        summary_path=summary,
        executed_at=(
            "2026-09-25T00:00:00Z"
        ),
    )

    assert (
        result[
            "summary"
        ]["generated_total"]
        == 2
    )

    assert (
        result[
            "summary"
        ]["valid_total"]
        == 1
    )

    assert (
        result[
            "summary"
        ]["invalid_total"]
        == 1
    )

    assert (
        sha256_file(
            registry
        )
        == registry_hash
    )


def test_duplicate_config_rejected(
    tmp_path,
):
    generated = (
        tmp_path / "generated.parquet"
    )

    registry = (
        tmp_path / "registry.parquet"
    )

    valid = (
        tmp_path / "valid.parquet"
    )

    rejected = (
        tmp_path / "rejected.parquet"
    )

    rules = (
        tmp_path / "rules.parquet"
    )

    summary = (
        tmp_path / "summary.json"
    )

    first = source_row(
        "EXP-000001",
        "a" * 64,
    )

    second = deepcopy(first)

    second["experiment_id"] = (
        "EXP-000002"
    )

    write_generated(
        generated,
        [
            first,
            second,
        ],
    )

    write_registry(
        registry,
        [
            {
                "experiment_id":
                    "EXP-000001",
                "config_sha256":
                    "a" * 64,
                "status": "ACTIVE",
            },
            {
                "experiment_id":
                    "EXP-000002",
                "config_sha256":
                    "a" * 64,
                "status": "ACTIVE",
            },
        ],
    )

    result = run_constraint_engine(
        generated_path=generated,
        registry_path=registry,
        valid_path=valid,
        rejected_path=rejected,
        rules_path=rules,
        summary_path=summary,
        executed_at=(
            "2026-09-25T00:00:00Z"
        ),
    )

    rejected_rows = result[
        "rejected_rows"
    ]

    assert len(
        rejected_rows
    ) == 1

    assert (
        "C014"
        in rejected_rows[0][
            "rejection_codes"
        ]
    )


def test_determinism_and_idempotence(
    tmp_path,
):
    generated = (
        tmp_path / "generated.parquet"
    )

    registry = (
        tmp_path / "registry.parquet"
    )

    valid = (
        tmp_path / "valid.parquet"
    )

    rejected = (
        tmp_path / "rejected.parquet"
    )

    rules = (
        tmp_path / "rules.parquet"
    )

    summary = (
        tmp_path / "summary.json"
    )

    row = source_row(
        "EXP-000001",
        "a" * 64,
    )

    write_generated(
        generated,
        [row],
    )

    write_registry(
        registry,
        [
            {
                "experiment_id":
                    "EXP-000001",
                "config_sha256":
                    "a" * 64,
                "status": "FROZEN",
            },
        ],
    )

    kwargs = {
        "generated_path": generated,
        "registry_path": registry,
        "valid_path": valid,
        "rejected_path": rejected,
        "rules_path": rules,
        "summary_path": summary,
        "executed_at": (
            "2026-09-25T00:00:00Z"
        ),
    }

    registry_hash_before = (
        sha256_file(
            registry
        )
    )

    run_constraint_engine(
        **kwargs
    )

    valid_hash_1 = (
        sha256_file(
            valid
        )
    )

    rejected_hash_1 = (
        sha256_file(
            rejected
        )
    )

    run_constraint_engine(
        **kwargs
    )

    assert (
        valid_hash_1
        == sha256_file(
            valid
        )
    )

    assert (
        rejected_hash_1
        == sha256_file(
            rejected
        )
    )

    assert (
        registry_hash_before
        == sha256_file(
            registry
        )
    )