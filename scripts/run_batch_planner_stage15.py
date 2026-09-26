from __future__ import annotations

from operar_range.batch_executor import (
    build_execution_plan,
)


def main():
    result = build_execution_plan(
        batch_size=3,
    )

    print("=" * 80)
    print(
        "ETAPA 15 — BATCH EXECUTOR V1"
    )
    print(
        "BLOCO 1 — PLANNER"
    )
    print("=" * 80)

    print(
        "EXECUTION_UNITS_TOTAL:",
        result[
            "execution_units_total"
        ],
    )

    print(
        "PENDING_TOTAL:",
        result[
            "pending_total"
        ],
    )

    print(
        "SKIPPED_NO_TRADE_TOTAL:",
        result[
            "skipped_total"
        ],
    )

    print(
        "BATCH_SIZE:",
        result[
            "batch_size"
        ],
    )

    print(
        "BATCHES_TOTAL:",
        result[
            "batches_total"
        ],
    )

    print(
        "PLAN_PATH:",
        result[
            "output_path"
        ],
    )

    print(
        "PLAN_SHA256:",
        result[
            "output_sha256"
        ],
    )

    print(
        "VALID_EXPERIMENTS_SHA256:",
        result[
            "source_valid_experiments_sha256"
        ],
    )

    print(
        "REGISTRY_SHA256:",
        result[
            "source_registry_sha256"
        ],
    )

    print(
        "TRAJECTORY_MANIFEST_SHA256:",
        result[
            "source_trajectory_manifest_sha256"
        ],
    )

    print("=" * 80)
    print("FIRST_10_UNITS")

    for row in result[
        "rows"
    ][:10]:
        print("-" * 80)

        print(
            "EXECUTION_UNIT_ID:",
            row[
                "execution_unit_id"
            ],
        )

        print(
            "BATCH_ID:",
            row[
                "batch_id"
            ],
        )

        print(
            "EXPERIMENT_ID:",
            row[
                "experiment_id"
            ],
        )

        print(
            "DATE:",
            row[
                "date"
            ],
        )

        print(
            "TRADE_STATUS:",
            row[
                "trade_status"
            ],
        )

        print(
            "EXECUTION_STATUS:",
            row[
                "execution_status"
            ],
        )

        print(
            "RUNNER_CANDLES:",
            row[
                "requires_runner_candles"
            ],
        )


if __name__ == "__main__":
    main()