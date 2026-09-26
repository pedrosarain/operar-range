from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.constraint_engine import (
    run_constraint_engine,
    sha256_file,
)
from operar_range.experiment_generator import (
    CONFIG_FIELDS,
    config_sha256,
)


GENERATED = Path(
    "data/research/"
    "generated_experiments.parquet"
)

REGISTRY = Path(
    "data/research/"
    "experiment_registry.parquet"
)

VALID = Path(
    "data/research/"
    "valid_experiments.parquet"
)

REJECTED = Path(
    "data/research/"
    "rejected_experiments.parquet"
)

RULES = Path(
    "data/research/"
    "constraint_rules.parquet"
)

SUMMARY = Path(
    "data/reports/"
    "constraint_engine_summary.json"
)


CONTROLLED_GENERATED = Path(
    "data/research/"
    "constraint_stage14_controlled_generated.parquet"
)

CONTROLLED_REGISTRY = Path(
    "data/research/"
    "constraint_stage14_controlled_registry.parquet"
)

CONTROLLED_VALID = Path(
    "data/research/"
    "constraint_stage14_controlled_valid.parquet"
)

CONTROLLED_REJECTED = Path(
    "data/research/"
    "constraint_stage14_controlled_rejected.parquet"
)

CONTROLLED_RULES = Path(
    "data/research/"
    "constraint_stage14_controlled_rules.parquet"
)

CONTROLLED_SUMMARY = Path(
    "data/reports/"
    "constraint_stage14_controlled_summary.json"
)


def execute():
    registry_before = sha256_file(
        REGISTRY
    )

    result = run_constraint_engine(
        generated_path=GENERATED,
        registry_path=REGISTRY,
        valid_path=VALID,
        rejected_path=REJECTED,
        rules_path=RULES,
        summary_path=SUMMARY,
    )

    registry_after = sha256_file(
        REGISTRY
    )

    return (
        result,
        registry_before,
        registry_after,
    )


def valid_base_config() -> dict[str, Any]:
    return {
        "stop_points": 170.0,

        "partial_1_points": 125.0,
        "partial_1_pct": 70.0,

        "partial_2_points": None,
        "partial_2_pct": None,

        "partial_3_points": None,
        "partial_3_pct": None,

        "break_even_enabled": False,
        "break_even_after_partial": None,

        "runner_enabled": False,
        "runner_pct": None,
        "runner_rule": None,

        "final_target_points": 400.0,
    }


def changed(
    base: dict[str, Any],
    **updates: Any,
) -> dict[str, Any]:
    config = dict(base)
    config.update(updates)
    return config


def controlled_cases():
    base = valid_base_config()

    cases = [
        (
            "VALID_SIMPLE",
            dict(base),
        ),

        (
            "STOP_NEGATIVE",
            changed(
                base,
                stop_points=-170.0,
            ),
        ),

        (
            "PARTIAL_WITHOUT_PCT",
            changed(
                base,
                partial_1_points=125.0,
                partial_1_pct=None,
            ),
        ),

        (
            "PCT_WITHOUT_PARTIAL",
            changed(
                base,
                partial_1_points=None,
                partial_1_pct=70.0,
            ),
        ),

        (
            "PARTIALS_OUT_OF_ORDER",
            changed(
                base,
                partial_1_points=175.0,
                partial_1_pct=40.0,
                partial_2_points=125.0,
                partial_2_pct=30.0,
            ),
        ),

        (
            "SUM_OVER_100",
            changed(
                base,
                partial_1_points=100.0,
                partial_1_pct=70.0,
                partial_2_points=175.0,
                partial_2_pct=40.0,
                final_target_points=None,
            ),
        ),

        (
            "BE_WITHOUT_PARTIAL",
            changed(
                base,
                partial_1_points=None,
                partial_1_pct=None,
                break_even_enabled=True,
                break_even_after_partial=1,
            ),
        ),

        (
            "BE_POINTS_TO_MISSING_PARTIAL",
            changed(
                base,
                break_even_enabled=True,
                break_even_after_partial=2,
            ),
        ),

        (
            "RUNNER_WITHOUT_PCT",
            changed(
                base,
                runner_enabled=True,
                runner_pct=None,
                runner_rule="CANDLE_BREAK_M5",
                final_target_points=None,
            ),
        ),

        (
            "RUNNER_WITHOUT_RULE",
            changed(
                base,
                runner_enabled=True,
                runner_pct=30.0,
                runner_rule=None,
                final_target_points=None,
            ),
        ),

        (
            "RUNNER_DISABLED_WITH_PCT",
            changed(
                base,
                runner_enabled=False,
                runner_pct=30.0,
                runner_rule=None,
            ),
        ),

        (
            "FINAL_TARGET_ZERO",
            changed(
                base,
                final_target_points=0.0,
            ),
        ),

        # Duplicata intencional de VALID_SIMPLE.
        (
            "DUPLICATE_CONFIG",
            dict(base),
        ),

        (
            "VALID_MULTIPLE_PARTIALS",
            changed(
                base,
                partial_1_points=100.0,
                partial_1_pct=40.0,
                partial_2_points=175.0,
                partial_2_pct=30.0,
                final_target_points=400.0,
            ),
        ),

        (
            "VALID_RUNNER",
            changed(
                base,
                partial_1_points=125.0,
                partial_1_pct=70.0,
                runner_enabled=True,
                runner_pct=30.0,
                runner_rule="CANDLE_BREAK_M5",
                final_target_points=None,
            ),
        ),

        (
            "VALID_BREAK_EVEN",
            changed(
                base,
                partial_1_points=125.0,
                partial_1_pct=70.0,
                break_even_enabled=True,
                break_even_after_partial=1,
                runner_enabled=False,
                runner_pct=None,
                runner_rule=None,
                final_target_points=400.0,
            ),
        ),
    ]

    return cases


def build_controlled_generated():
    source_table = pq.read_table(
        GENERATED
    )

    source_rows = source_table.to_pylist()

    if not source_rows:
        raise RuntimeError(
            "generated_experiments.parquet "
            "contains no rows."
        )

    template = source_rows[0]

    rows = []
    labels = {}

    for index, (
        label,
        config,
    ) in enumerate(
        controlled_cases(),
        start=1,
    ):
        experiment_id = (
            f"EXP-{900000 + index:06d}"
        )

        row = dict(template)

        row["experiment_id"] = (
            experiment_id
        )

        row["family"] = (
            "TRADE1_STAGE14_VALIDATION"
        )

        row["generation"] = 1

        row["experiment_name"] = (
            "STAGE14_"
            + label
        )

        row["created_at"] = (
            "2026-09-25T00:00:00Z"
        )

        row["engine_version"] = (
            "stage14-controlled-validation"
        )

        row["rules_version"] = (
            "trade1-adr004-"
            "management-runner-v1"
        )

        for field in CONFIG_FIELDS:
            row[field] = config.get(
                field
            )

        row["config_sha256"] = (
            config_sha256(
                config
            )
        )

        rows.append(row)

        labels[
            experiment_id
        ] = label

    CONTROLLED_GENERATED.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        rows,
        schema=source_table.schema,
    )

    pq.write_table(
        table,
        CONTROLLED_GENERATED,
        compression="zstd",
    )

    return rows, labels


def build_controlled_registry(
    generated_rows,
):
    registry_table = pq.read_table(
        REGISTRY
    )

    registry_rows = (
        registry_table.to_pylist()
    )

    if not registry_rows:
        raise RuntimeError(
            "experiment_registry.parquet "
            "contains no rows."
        )

    template = registry_rows[0]

    controlled_rows = []

    for generated in generated_rows:
        row = dict(template)

        values = {
            "experiment_id": (
                generated[
                    "experiment_id"
                ]
            ),
            "config_sha256": (
                generated[
                    "config_sha256"
                ]
            ),
            "family": (
                generated[
                    "family"
                ]
            ),
            "generation": (
                generated[
                    "generation"
                ]
            ),
            "experiment_name": (
                generated[
                    "experiment_name"
                ]
            ),
            "status": "ACTIVE",
            "created_at": (
                generated[
                    "created_at"
                ]
            ),
            "engine_version": (
                generated[
                    "engine_version"
                ]
            ),
            "rules_version": (
                generated[
                    "rules_version"
                ]
            ),
            "definition_sha256": (
                generated.get(
                    "definition_sha256"
                )
            ),
            "parent_experiment_id": None,
            "supersedes_experiment_id": None,
        }

        for key, value in (
            values.items()
        ):
            if key in row:
                row[key] = value

        controlled_rows.append(
            row
        )

    CONTROLLED_REGISTRY.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        controlled_rows,
        schema=registry_table.schema,
    )

    pq.write_table(
        table,
        CONTROLLED_REGISTRY,
        compression="zstd",
    )


def execute_controlled():
    generated_rows, labels = (
        build_controlled_generated()
    )

    build_controlled_registry(
        generated_rows
    )

    registry_before = sha256_file(
        CONTROLLED_REGISTRY
    )

    first = run_constraint_engine(
        generated_path=(
            CONTROLLED_GENERATED
        ),
        registry_path=(
            CONTROLLED_REGISTRY
        ),
        valid_path=(
            CONTROLLED_VALID
        ),
        rejected_path=(
            CONTROLLED_REJECTED
        ),
        rules_path=(
            CONTROLLED_RULES
        ),
        summary_path=(
            CONTROLLED_SUMMARY
        ),
    )

    registry_after_first = (
        sha256_file(
            CONTROLLED_REGISTRY
        )
    )

    valid_hash_first = (
        sha256_file(
            CONTROLLED_VALID
        )
    )

    rejected_hash_first = (
        sha256_file(
            CONTROLLED_REJECTED
        )
    )

    rules_hash_first = (
        sha256_file(
            CONTROLLED_RULES
        )
    )

    first_summary = first[
        "summary"
    ]

    second = run_constraint_engine(
        generated_path=(
            CONTROLLED_GENERATED
        ),
        registry_path=(
            CONTROLLED_REGISTRY
        ),
        valid_path=(
            CONTROLLED_VALID
        ),
        rejected_path=(
            CONTROLLED_REJECTED
        ),
        rules_path=(
            CONTROLLED_RULES
        ),
        summary_path=(
            CONTROLLED_SUMMARY
        ),
    )

    second_summary = second[
        "summary"
    ]

    registry_after_second = (
        sha256_file(
            CONTROLLED_REGISTRY
        )
    )

    deterministic = (
        valid_hash_first
        == sha256_file(
            CONTROLLED_VALID
        )
        and rejected_hash_first
        == sha256_file(
            CONTROLLED_REJECTED
        )
        and rules_hash_first
        == sha256_file(
            CONTROLLED_RULES
        )
        and first_summary[
            "rule_set_sha256"
        ]
        == second_summary[
            "rule_set_sha256"
        ]
    )

    registry_unchanged = (
        registry_before
        == registry_after_first
        == registry_after_second
    )

    valid_rows = pq.read_table(
        CONTROLLED_VALID
    ).to_pylist()

    rejected_rows = pq.read_table(
        CONTROLLED_REJECTED
    ).to_pylist()

    valid_ids = {
        row["experiment_id"]
        for row in valid_rows
    }

    rejected_by_id = {
        row["experiment_id"]: row
        for row in rejected_rows
    }

    expected_valid = {
        "EXP-900001",
        "EXP-900014",
        "EXP-900015",
        "EXP-900016",
    }

    if valid_ids != expected_valid:
        raise RuntimeError(
            "Controlled validation produced "
            "unexpected VALID set. "
            f"Expected={sorted(expected_valid)} "
            f"Actual={sorted(valid_ids)}"
        )

    if len(valid_rows) != 4:
        raise RuntimeError(
            "Expected 4 controlled VALID "
            f"rows, got {len(valid_rows)}."
        )

    if len(rejected_rows) != 12:
        raise RuntimeError(
            "Expected 12 controlled INVALID "
            f"rows, got {len(rejected_rows)}."
        )

    return {
        "first": first,
        "second": second,
        "labels": labels,
        "valid_rows": valid_rows,
        "rejected_rows": rejected_rows,
        "rejected_by_id": rejected_by_id,
        "deterministic": deterministic,
        "registry_unchanged": (
            registry_unchanged
        ),
    }


def print_production_result(
    first,
    deterministic,
    registry_unchanged,
):
    summary = first["summary"]

    print("=" * 80)
    print(
        "ETAPA 14 — RULE ENGINE V1 / "
        "CONSTRAINT ENGINE"
    )
    print("=" * 80)

    print("\nPRODUCTION INPUT")

    print(
        "GENERATED_TOTAL:",
        summary[
            "generated_total"
        ],
    )

    print(
        "VALID_TOTAL:",
        summary[
            "valid_total"
        ],
    )

    print(
        "INVALID_TOTAL:",
        summary[
            "invalid_total"
        ],
    )

    print(
        "WARNING_TOTAL:",
        summary[
            "warning_total"
        ],
    )

    print(
        "REJECTIONS_BY_RULE:"
    )

    for rule_code, count in (
        summary[
            "rejection_count_by_rule"
        ].items()
    ):
        print(
            f"{rule_code}: {count}"
        )

    print(
        "WARNINGS_BY_RULE:"
    )

    for rule_code, count in (
        summary[
            "warning_count_by_rule"
        ].items()
    ):
        print(
            f"{rule_code}: {count}"
        )

    print(
        "DEFINITION_SHA256:",
        summary[
            "definition_sha256"
        ],
    )

    print(
        "RULE_SET_SHA256:",
        summary[
            "rule_set_sha256"
        ],
    )

    print(
        "GENERATED_SHA256:",
        summary[
            "generated_experiments_sha256"
        ],
    )

    print(
        "VALID_SHA256:",
        summary[
            "valid_experiments_sha256"
        ],
    )

    print(
        "REJECTED_SHA256:",
        summary[
            "rejected_experiments_sha256"
        ],
    )

    print(
        "CONSTRAINT_RULES_SHA256:",
        summary[
            "constraint_rules_sha256"
        ],
    )

    print(
        "REGISTRY_SHA256:",
        summary[
            "registry_sha256"
        ],
    )

    print(
        "DETERMINISTIC_RERUN:",
        deterministic,
    )

    print(
        "REGISTRY_UNCHANGED:",
        registry_unchanged,
    )

    print(
        "IDEMPOTENT:",
        (
            deterministic
            and registry_unchanged
        ),
    )

    print(
        "DECISION_PENDING_C013:",
        "CONSTRAINT_REQUIRES_CTO_DECISION",
    )


def print_controlled_result(
    controlled,
):
    summary = controlled[
        "first"
    ]["summary"]

    print("\n" + "=" * 80)

    print(
        "ETAPA 14 — CONTROLLED VALIDATION"
    )

    print("=" * 80)

    print(
        "CONTROLLED_TOTAL:",
        summary[
            "generated_total"
        ],
    )

    print(
        "CONTROLLED_VALID:",
        summary[
            "valid_total"
        ],
    )

    print(
        "CONTROLLED_INVALID:",
        summary[
            "invalid_total"
        ],
    )

    print(
        "CONTROLLED_WARNINGS:",
        summary[
            "warning_total"
        ],
    )

    print(
        "CONTROLLED_REJECTIONS_BY_RULE:"
    )

    for rule_code, count in (
        summary[
            "rejection_count_by_rule"
        ].items()
    ):
        print(
            f"{rule_code}: {count}"
        )

    print("\nCONTROLLED_CASES")

    valid_ids = {
        row["experiment_id"]
        for row in controlled[
            "valid_rows"
        ]
    }

    rejected_by_id = (
        controlled[
            "rejected_by_id"
        ]
    )

    for experiment_id, label in (
        controlled[
            "labels"
        ].items()
    ):
        if experiment_id in valid_ids:
            print(
                experiment_id,
                "|",
                label,
                "| VALID",
            )

            continue

        rejected = (
            rejected_by_id.get(
                experiment_id
            )
        )

        if rejected is None:
            print(
                experiment_id,
                "|",
                label,
                "| UNKNOWN",
            )

            continue

        print(
            experiment_id,
            "|",
            label,
            "| INVALID",
            "| CODES:",
            rejected.get(
                "rejection_codes"
            ),
        )

    print(
        "\nCONTROLLED_DETERMINISTIC_RERUN:",
        controlled[
            "deterministic"
        ],
    )

    print(
        "CONTROLLED_REGISTRY_UNCHANGED:",
        controlled[
            "registry_unchanged"
        ],
    )

    print(
        "CONTROLLED_IDEMPOTENT:",
        (
            controlled[
                "deterministic"
            ]
            and controlled[
                "registry_unchanged"
            ]
        ),
    )

    print(
        "CONTROLLED_RULE_SET_SHA256:",
        summary[
            "rule_set_sha256"
        ],
    )

    print(
        "CONTROLLED_VALID_SHA256:",
        summary[
            "valid_experiments_sha256"
        ],
    )

    print(
        "CONTROLLED_REJECTED_SHA256:",
        summary[
            "rejected_experiments_sha256"
        ],
    )


def main():
    (
        first,
        registry_before,
        registry_after_first,
    ) = execute()

    first_summary = first[
        "summary"
    ]

    first_valid_hash = sha256_file(
        VALID
    )

    first_rejected_hash = (
        sha256_file(
            REJECTED
        )
    )

    first_rules_hash = (
        first_summary[
            "rule_set_sha256"
        ]
    )

    (
        second,
        _,
        registry_after_second,
    ) = execute()

    second_summary = second[
        "summary"
    ]

    deterministic = (
        first_valid_hash
        == sha256_file(
            VALID
        )
        and first_rejected_hash
        == sha256_file(
            REJECTED
        )
        and first_rules_hash
        == second_summary[
            "rule_set_sha256"
        ]
    )

    registry_unchanged = (
        registry_before
        == registry_after_first
        == registry_after_second
    )

    print_production_result(
        first,
        deterministic,
        registry_unchanged,
    )

    controlled = (
        execute_controlled()
    )

    print_controlled_result(
        controlled
    )


if __name__ == "__main__":
    main()