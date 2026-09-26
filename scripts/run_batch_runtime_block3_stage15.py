from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

from operar_range.batch_runtime import (
    execute_pending_batches,
    merge_batch_results,
    pending_batches,
    plan_status_counts,
    sha256_file,
)


PLAN = Path(
    "data/research/"
    "batch_execution_plan.parquet"
)

FAILURES = Path(
    "data/research/"
    "batch_failures.parquet"
)

MERGED = Path(
    "data/research/"
    "batch_experiment_results.parquet"
)


def print_counts(
    title,
):
    counts = plan_status_counts(
        PLAN
    )

    print("-" * 80)
    print(title)
    print("-" * 80)

    for key in (
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "SKIPPED_NO_TRADE",
    ):
        print(
            f"{key}:",
            counts.get(
                key,
                0,
            ),
        )


def main():
    print("=" * 80)
    print(
        "ETAPA 15 — BATCH EXECUTOR V1"
    )
    print(
        "BLOCO 3 — CHECKPOINT / "
        "RESUME / MERGE"
    )
    print("=" * 80)

    print_counts(
        "STATUS BEFORE"
    )

    pending_before = (
        pending_batches(
            PLAN
        )
    )

    print(
        "PENDING_BATCHES_BEFORE:",
        len(
            pending_before
        ),
    )

    print()
    print("=" * 80)
    print(
        "CHECKPOINT TEST — EXECUTAR "
        "APENAS 2 BATCHES"
    )
    print("=" * 80)

    first = (
        execute_pending_batches(
            plan_path=PLAN,
            failure_path=FAILURES,
            max_batches=2,
        )
    )

    print(
        "BATCHES_EXECUTED:",
        first[
            "batches_executed"
        ],
    )

    print(
        "NEW_RESULTS:",
        first[
            "new_results"
        ],
    )

    print(
        "FAILURES:",
        first[
            "failures"
        ],
    )

    print(
        "TRAJECTORY_LOADS:",
        first[
            "trajectory_loads"
        ],
    )

    print(
        "RUNNER_CANDLE_BUILDS:",
        first[
            "runner_candle_builds"
        ],
    )

    print_counts(
        "STATUS AFTER CHECKPOINT"
    )

    pending_after_checkpoint = (
        pending_batches(
            PLAN
        )
    )

    print(
        "PENDING_BATCHES_AFTER_CHECKPOINT:",
        len(
            pending_after_checkpoint
        ),
    )

    checkpoint_work_remains = (
        len(
            pending_after_checkpoint
        )
        > 0
    )

    print(
        "CHECKPOINT_WORK_REMAINS:",
        checkpoint_work_remains,
    )

    print()
    print("=" * 80)
    print(
        "RESUME — EXECUTAR RESTANTE"
    )
    print("=" * 80)

    second = (
        execute_pending_batches(
            plan_path=PLAN,
            failure_path=FAILURES,
        )
    )

    print(
        "RESUME_BATCHES_EXECUTED:",
        second[
            "batches_executed"
        ],
    )

    print(
        "RESUME_NEW_RESULTS:",
        second[
            "new_results"
        ],
    )

    print(
        "RESUME_FAILURES:",
        second[
            "failures"
        ],
    )

    print_counts(
        "STATUS AFTER RESUME"
    )

    pending_after_resume = (
        pending_batches(
            PLAN
        )
    )

    print(
        "PENDING_BATCHES_AFTER_RESUME:",
        len(
            pending_after_resume
        ),
    )

    print()
    print("=" * 80)
    print(
        "MERGE"
    )
    print("=" * 80)

    merged = (
        merge_batch_results(
            plan_path=PLAN,
            output_path=MERGED,
        )
    )

    print(
        "MERGED_ROWS:",
        merged["rows"],
    )

    print(
        "MERGED_PATH:",
        merged[
            "output_path"
        ],
    )

    print(
        "MERGED_SHA256:",
        merged["sha256"],
    )

    if FAILURES.exists():
        failure_rows = (
            pq.read_table(
                FAILURES
            ).num_rows
        )
    else:
        failure_rows = 0

    print(
        "FAILURE_ROWS:",
        failure_rows,
    )

    print()
    print("=" * 80)
    print(
        "IDEMPOTENCE TEST"
    )
    print("=" * 80)

    hash_before = (
        sha256_file(
            MERGED
        )
    )

    third = (
        execute_pending_batches(
            plan_path=PLAN,
            failure_path=FAILURES,
        )
    )

    merged_second = (
        merge_batch_results(
            plan_path=PLAN,
            output_path=MERGED,
        )
    )

    hash_after = (
        sha256_file(
            MERGED
        )
    )

    print(
        "SECOND_RUN_BATCHES_EXECUTED:",
        third[
            "batches_executed"
        ],
    )

    print(
        "SECOND_RUN_NEW_RESULTS:",
        third[
            "new_results"
        ],
    )

    print(
        "SECOND_RUN_FAILURES:",
        third[
            "failures"
        ],
    )

    print(
        "PENDING_AFTER_SECOND_RUN:",
        len(
            pending_batches(
                PLAN
            )
        ),
    )

    print(
        "MERGED_ROWS_SECOND_RUN:",
        merged_second[
            "rows"
        ],
    )

    print(
        "MERGED_HASH_UNCHANGED:",
        (
            hash_before
            == hash_after
        ),
    )

    print(
        "IDEMPOTENT:",
        (
            third[
                "batches_executed"
            ]
            == 0
            and third[
                "new_results"
            ]
            == 0
            and hash_before
            == hash_after
        ),
    )


if __name__ == "__main__":
    main()