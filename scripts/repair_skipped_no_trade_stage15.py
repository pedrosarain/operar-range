from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

from operar_range.batch_execution import (
    execute_batch,
)


PLAN = Path(
    "data/research/"
    "batch_execution_plan.parquet"
)

VALID = Path(
    "data/research/"
    "valid_experiments.parquet"
)

TRAJECTORY_MANIFEST = Path(
    "data/research/"
    "trade1_trajectory_manifest.parquet"
)

NORMALIZED = Path(
    "data/normalized"
)

BATCHES_DIR = Path(
    "data/research/batches"
)


def main():
    if not PLAN.exists():
        raise FileNotFoundError(
            PLAN
        )

    rows = pq.read_table(
        PLAN
    ).to_pylist()

    batch_ids = sorted(
        {
            row["batch_id"]
            for row in rows
        }
    )

    skipped_units = {
        row["execution_unit_id"]
        for row in rows
        if (
            row["execution_status"]
            == "SKIPPED_NO_TRADE"
        )
    }

    print("=" * 80)
    print(
        "ETAPA 15 — REPAIR "
        "SKIPPED_NO_TRADE"
    )
    print("=" * 80)

    print(
        "BATCHES_TOTAL:",
        len(batch_ids),
    )

    print(
        "SKIPPED_UNITS_EXPECTED:",
        len(skipped_units),
    )

    total_new_results = 0
    total_failures = 0

    for batch_id in batch_ids:
        result = execute_batch(
            batch_id=batch_id,
            plan_path=PLAN,
            valid_experiments_path=VALID,
            trajectory_manifest_path=(
                TRAJECTORY_MANIFEST
            ),
            normalized_dir=NORMALIZED,
            batches_dir=BATCHES_DIR,
        )

        total_new_results += int(
            result["new_results"]
        )

        total_failures += len(
            result["failures"]
        )

        print(
            batch_id,
            "| NEW_RESULTS:",
            result["new_results"],
            "| FAILURES:",
            len(
                result["failures"]
            ),
        )

    persisted_ids = set()

    for path in sorted(
        BATCHES_DIR.glob(
            "*.parquet"
        )
    ):
        batch_rows = pq.read_table(
            path
        ).to_pylist()

        for row in batch_rows:
            persisted_ids.add(
                row[
                    "execution_unit_id"
                ]
            )

    missing_skipped = (
        skipped_units
        - persisted_ids
    )

    print("=" * 80)
    print("REPAIR RESULT")
    print("=" * 80)

    print(
        "NEW_RESULTS_CREATED:",
        total_new_results,
    )

    print(
        "FAILURES:",
        total_failures,
    )

    print(
        "SKIPPED_UNITS_PERSISTED:",
        len(
            skipped_units
            - missing_skipped
        ),
    )

    print(
        "SKIPPED_UNITS_MISSING:",
        len(
            missing_skipped
        ),
    )

    print(
        "REPAIR_OK:",
        (
            total_failures == 0
            and len(
                missing_skipped
            ) == 0
        ),
    )

    if missing_skipped:
        print(
            "MISSING_IDS:"
        )

        for execution_unit_id in (
            sorted(
                missing_skipped
            )
        ):
            print(
                execution_unit_id
            )


if __name__ == "__main__":
    main()