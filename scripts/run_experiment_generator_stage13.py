from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

from operar_range.experiment_generator import (
    generate_experiment_database,
    sha256_file,
)


OUTPUT_PATH = Path(
    "data/research/"
    "generated_experiments.parquet"
)

REGISTRY_PATH = Path(
    "data/research/"
    "experiment_registry.parquet"
)

EXISTING_MANIFEST = Path(
    "data/research/"
    "experiment_manifest.parquet"
)


BASE_CONFIG = {
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


PARAMETER_DEFINITION = {
    "stop_points": {
        "values": [
            100,
            125,
            150,
            170,
        ]
    },

    "partial_1_points": {
        "values": [
            100,
            125,
            150,
        ]
    },

    "partial_1_pct": {
        "values": [
            40,
            70,
        ]
    },
}


def main():
    result = (
        generate_experiment_database(
            family="TRADE1_BASE",
            generation=2,

            created_at=(
                "2026-09-25T00:00:00Z"
            ),

            rules_version=(
                "trade1-adr004-"
                "management-runner-v1"
            ),

            base_config=BASE_CONFIG,

            parameter_definition=(
                PARAMETER_DEFINITION
            ),

            output_path=OUTPUT_PATH,

            existing_generated_path=None,

            registry_path=REGISTRY_PATH,

            reserved_paths=[
                EXISTING_MANIFEST,
            ],

            register_generated=True,
        )
    )

    table = pq.read_table(
        OUTPUT_PATH
    )

    rows = table.to_pylist()

    print("=" * 80)
    print(
        "PREPARACAO ETAPA 15 — "
        "EXPERIMENT GENERATOR"
    )
    print("=" * 80)

    print(
        "GENERATED_EXPERIMENTS:",
        len(rows),
    )

    print(
        "EXPECTED_EXPERIMENTS:",
        24,
    )

    print(
        "EXPECTED_MATCH:",
        len(rows) == 24,
    )

    print(
        "DATABASE_ROWS:",
        table.num_rows,
    )

    print(
        "DATABASE_COLUMNS:",
        table.num_columns,
    )

    print(
        "OUTPUT_PATH:",
        OUTPUT_PATH,
    )

    print(
        "OUTPUT_SHA256:",
        sha256_file(
            OUTPUT_PATH
        ),
    )

    print(
        "DEFINITION_SHA256:",
        result[
            "definition_sha256"
        ],
    )

    print(
        "REGISTRY_UPDATED:",
        result[
            "registry_updated"
        ],
    )

    print(
        "REGISTRY_NEW_EXPERIMENTS:",
        result.get(
            "registry_new_experiments"
        ),
    )

    print(
        "REGISTRY_NEXT_AVAILABLE_ID:",
        result.get(
            "registry_next_available_id"
        ),
    )

    print(
        "REGISTRY_SHA256:",
        result.get(
            "registry_sha256"
        ),
    )

    print(
        "FIRST_EXPERIMENT_ID:",
        rows[0][
            "experiment_id"
        ]
        if rows
        else None,
    )

    print(
        "LAST_EXPERIMENT_ID:",
        rows[-1][
            "experiment_id"
        ]
        if rows
        else None,
    )

    print(
        "UNIQUE_IDS:",
        len(
            {
                row[
                    "experiment_id"
                ]
                for row in rows
            }
        )
        == len(rows),
    )

    print(
        "UNIQUE_CONFIG_HASHES:",
        len(
            {
                row[
                    "config_sha256"
                ]
                for row in rows
            }
        ),
    )

    print(
        "ALL_CONFIG_HASHES_UNIQUE:",
        len(
            {
                row[
                    "config_sha256"
                ]
                for row in rows
            }
        )
        == len(rows),
    )

    print("\nCONFIGURATION_DOMAIN")

    print(
        "STOPS:",
        sorted(
            {
                row[
                    "stop_points"
                ]
                for row in rows
            }
        ),
    )

    print(
        "PARTIAL_1_POINTS:",
        sorted(
            {
                row[
                    "partial_1_points"
                ]
                for row in rows
            }
        ),
    )

    print(
        "PARTIAL_1_PCTS:",
        sorted(
            {
                row[
                    "partial_1_pct"
                ]
                for row in rows
            }
        ),
    )

    print(
        "BREAK_EVEN_VALUES:",
        sorted(
            {
                row[
                    "break_even_enabled"
                ]
                for row in rows
            }
        ),
    )

    print(
        "RUNNER_VALUES:",
        sorted(
            {
                row[
                    "runner_enabled"
                ]
                for row in rows
            }
        ),
    )

    print(
        "FINAL_TARGET_VALUES:",
        sorted(
            {
                row[
                    "final_target_points"
                ]
                for row in rows
            }
        ),
    )

    print("\nFIRST_5_EXPERIMENTS")

    for row in rows[:5]:
        print("-" * 80)

        print(
            "EXPERIMENT_ID:",
            row[
                "experiment_id"
            ],
        )

        print(
            "CONFIG_SHA256:",
            row[
                "config_sha256"
            ],
        )

        print(
            "STOP:",
            row[
                "stop_points"
            ],
        )

        print(
            "PARTIAL_1_POINTS:",
            row[
                "partial_1_points"
            ],
        )

        print(
            "PARTIAL_1_PCT:",
            row[
                "partial_1_pct"
            ],
        )

        print(
            "BREAK_EVEN:",
            row[
                "break_even_enabled"
            ],
        )

        print(
            "BREAK_EVEN_AFTER_PARTIAL:",
            row[
                "break_even_after_partial"
            ],
        )

        print(
            "RUNNER:",
            row[
                "runner_enabled"
            ],
        )

        print(
            "RUNNER_PCT:",
            row[
                "runner_pct"
            ],
        )

        print(
            "RUNNER_RULE:",
            row[
                "runner_rule"
            ],
        )

        print(
            "FINAL_TARGET:",
            row[
                "final_target_points"
            ],
        )

    print("=" * 80)

    print(
        "GENERATOR_RESULT_COUNT:",
        result[
            "experiment_count"
        ],
    )

    print(
        "GENERATOR_OUTPUT_SHA256:",
        result[
            "sha256"
        ],
    )


if __name__ == "__main__":
    main()