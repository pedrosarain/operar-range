from __future__ import annotations

import hashlib
from pathlib import Path

import pyarrow.parquet as pq

from operar_range.batch_execution import (
    execute_batch,
)


PLAN_PATH = Path(
    "data/research/"
    "batch_execution_plan.parquet"
)


def sha256_file(
    path: str | Path,
) -> str:
    path = Path(path)

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def main():
    plan_rows = pq.read_table(
        PLAN_PATH
    ).to_pylist()

    batch_ids = sorted(
        {
            row["batch_id"]
            for row in plan_rows
        }
    )

    if not batch_ids:
        raise RuntimeError(
            "No batches found."
        )

    first_batch_id = (
        batch_ids[0]
    )

    print("=" * 80)
    print(
        "ETAPA 15 — BATCH EXECUTOR V1"
    )
    print(
        "BLOCO 2 — EXECUTOR + "
        "RESULT WRITER"
    )
    print("=" * 80)

    print(
        "BATCH_SELECTED:",
        first_batch_id,
    )

    result = execute_batch(
        batch_id=(
            first_batch_id
        )
    )

    print(
        "EXECUTION_UNITS:",
        result[
            "execution_units"
        ],
    )

    print(
        "COMPLETED_UNITS:",
        result[
            "completed_units"
        ],
    )

    print(
        "SKIPPED_UNITS:",
        result[
            "skipped_units"
        ],
    )

    print(
        "RESULT_ROWS:",
        result[
            "result_rows"
        ],
    )

    print(
        "TRAJECTORY_LOADS:",
        result[
            "trajectory_loads"
        ],
    )

    print(
        "RUNNER_CANDLE_BUILDS:",
        result[
            "runner_candle_builds"
        ],
    )

    print(
        "OUTPUT_PATH:",
        result[
            "output_path"
        ],
    )

    print(
        "OUTPUT_SHA256:",
        sha256_file(
            result[
                "output_path"
            ]
        ),
    )

    print("=" * 80)
    print(
        "RESULT ROWS"
    )

    rows = pq.read_table(
        result[
            "output_path"
        ]
    ).to_pylist()

    for row in rows:
        print("-" * 80)

        print(
            "EXECUTION_UNIT_ID:",
            row[
                "execution_unit_id"
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
            "RESULT:",
            row[
                "total_weighted_points"
            ],
        )

        print(
            "FINAL_REASON:",
            row[
                "final_reason"
            ],
        )


if __name__ == "__main__":
    main()