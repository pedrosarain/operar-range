from __future__ import annotations

import time
from pathlib import Path

from operar_range.distributed_executor import (
    compare_with_stage15,
    distributed_status,
    execute_worker,
    merge_distributed_results,
    read_attempts,
    serialize_all_batches,
    sha256_file,
)


PROJECT_ROOT = Path(".").resolve()

DISTRIBUTED_ROOT = Path(
    "data/research/distributed_runs"
)

BATCH_PLAN = Path(
    "data/research/"
    "batch_execution_plan.parquet"
)

REGISTRY = Path(
    "data/research/"
    "experiment_registry.parquet"
)

TRAJECTORY_MANIFEST = Path(
    "data/research/"
    "trade1_trajectory_manifest.parquet"
)

VALID_EXPERIMENTS = Path(
    "data/research/"
    "valid_experiments.parquet"
)

CONSTRAINT_SUMMARY = Path(
    "data/reports/"
    "constraint_engine_summary.json"
)

STAGE15_RESULT = Path(
    "data/research/"
    "batch_experiment_results.parquet"
)

DISTRIBUTED_RESULT = Path(
    "data/research/"
    "distributed_experiment_results.parquet"
)

NORMALIZED_DIR = Path(
    "data/normalized"
)


WORKERS = [
    "WORKER-001",
    "WORKER-002",
    "WORKER-003",
]


def has_completed_attempt(
    *,
    run_id: str,
    batch_id: str,
) -> bool:
    attempts = read_attempts(
        distributed_root=(
            DISTRIBUTED_ROOT
        ),
        run_id=run_id,
        batch_id=batch_id,
    )

    return any(
        row["status"] == "COMPLETED"
        for row in attempts
    )


def completed_attempt_count(
    *,
    run_id: str,
    batch_id: str,
) -> int:
    attempts = read_attempts(
        distributed_root=(
            DISTRIBUTED_ROOT
        ),
        run_id=run_id,
        batch_id=batch_id,
    )

    return sum(
        1
        for row in attempts
        if row["status"] == "COMPLETED"
    )


def build_out_of_order_batches(
    batch_ids: list[str],
) -> list[str]:
    if len(batch_ids) < 4:
        return list(
            reversed(
                batch_ids
            )
        )

    #
    # Exemplo solicitado pelo CTO:
    # batch 4, batch 1,
    # batch 3, batch 2...
    #
    first_four = [
        batch_ids[3],
        batch_ids[0],
        batch_ids[2],
        batch_ids[1],
    ]

    remaining = (
        batch_ids[4:]
    )

    #
    # Restante também fora da
    # ordem original.
    #
    remaining = list(
        reversed(
            remaining
        )
    )

    return (
        first_four
        + remaining
    )


def main():
    started = time.perf_counter()

    print(
        "=" * 80
    )
    print(
        "ETAPA 15.5 — "
        "DISTRIBUTED EXECUTOR "
        "ARCHITECTURE"
    )
    print(
        "=" * 80
    )

    print()
    print(
        "SERIALIZACAO DOS BATCHES"
    )
    print(
        "-" * 80
    )

    serialization = (
        serialize_all_batches(
            project_root=(
                PROJECT_ROOT
            ),
            batch_plan_path=(
                BATCH_PLAN
            ),
            registry_path=(
                REGISTRY
            ),
            trajectory_manifest_path=(
                TRAJECTORY_MANIFEST
            ),
            valid_experiments_path=(
                VALID_EXPERIMENTS
            ),
            constraint_summary_path=(
                CONSTRAINT_SUMMARY
            ),
            distributed_root=(
                DISTRIBUTED_ROOT
            ),
        )
    )

    run_id = serialization[
        "run_id"
    ]

    packages = serialization[
        "packages"
    ]

    batch_ids = [
        package["batch_id"]
        for package in packages
    ]

    ordered_batches = (
        build_out_of_order_batches(
            batch_ids
        )
    )

    print(
        "RUN_ID:",
        run_id,
    )

    print(
        "BATCHES_TOTAL:",
        serialization[
            "batches_total"
        ],
    )

    print(
        "EXECUTION_UNITS_TOTAL:",
        serialization[
            "execution_units_total"
        ],
    )

    print(
        "RUN_MANIFEST:",
        serialization[
            "run_manifest_path"
        ],
    )

    print(
        "RUN_MANIFEST_SHA256:",
        serialization[
            "run_manifest_sha256"
        ],
    )

    print()
    print(
        "ORDEM DISTRIBUIDA"
    )
    print(
        "-" * 80
    )

    for index, batch_id in enumerate(
        ordered_batches,
        start=1,
    ):
        worker_id = WORKERS[
            (index - 1)
            % len(WORKERS)
        ]

        print(
            f"{index:02d} | "
            f"{batch_id} | "
            f"{worker_id}"
        )

    #
    # O primeiro batch desta ordem
    # será usado para provar retry.
    #
    retry_batch = (
        ordered_batches[0]
    )

    print()
    print(
        "=" * 80
    )
    print(
        "TESTE DE FALHA CONTROLADA "
        "+ RETRY"
    )
    print(
        "=" * 80
    )

    retry_attempts_before = (
        read_attempts(
            distributed_root=(
                DISTRIBUTED_ROOT
            ),
            run_id=run_id,
            batch_id=retry_batch,
        )
    )

    if not retry_attempts_before:
        failed = execute_worker(
            project_root=(
                PROJECT_ROOT
            ),
            distributed_root=(
                DISTRIBUTED_ROOT
            ),
            run_id=run_id,
            batch_id=retry_batch,
            worker_id="WORKER-001",
            batch_plan_path=(
                BATCH_PLAN
            ),
            registry_path=(
                REGISTRY
            ),
            trajectory_manifest_path=(
                TRAJECTORY_MANIFEST
            ),
            valid_experiments_path=(
                VALID_EXPERIMENTS
            ),
            constraint_summary_path=(
                CONSTRAINT_SUMMARY
            ),
            normalized_dir=(
                NORMALIZED_DIR
            ),
            force_failure=True,
        )

        print(
            "FIRST_ATTEMPT_STATUS:",
            failed["status"],
        )

        print(
            "FIRST_ATTEMPT_COUNT:",
            failed[
                "attempt_count"
            ],
        )

        print(
            "FIRST_ATTEMPT_ERROR:",
            failed.get(
                "error_message"
            ),
        )

        retry = execute_worker(
            project_root=(
                PROJECT_ROOT
            ),
            distributed_root=(
                DISTRIBUTED_ROOT
            ),
            run_id=run_id,
            batch_id=retry_batch,
            worker_id="WORKER-002",
            batch_plan_path=(
                BATCH_PLAN
            ),
            registry_path=(
                REGISTRY
            ),
            trajectory_manifest_path=(
                TRAJECTORY_MANIFEST
            ),
            valid_experiments_path=(
                VALID_EXPERIMENTS
            ),
            constraint_summary_path=(
                CONSTRAINT_SUMMARY
            ),
            normalized_dir=(
                NORMALIZED_DIR
            ),
            force_failure=False,
        )

        print(
            "RETRY_STATUS:",
            retry["status"],
        )

        print(
            "RETRY_ATTEMPT_COUNT:",
            retry[
                "attempt_count"
            ],
        )

    else:
        print(
            "RETRY_BATCH_ALREADY_HAS_"
            "AUDIT_HISTORY: True"
        )

        print(
            "ATTEMPTS_EXISTING:",
            len(
                retry_attempts_before
            ),
        )

        print(
            "COMPLETED_EXISTING:",
            has_completed_attempt(
                run_id=run_id,
                batch_id=retry_batch,
            ),
        )

        if not has_completed_attempt(
            run_id=run_id,
            batch_id=retry_batch,
        ):
            retry = execute_worker(
                project_root=(
                    PROJECT_ROOT
                ),
                distributed_root=(
                    DISTRIBUTED_ROOT
                ),
                run_id=run_id,
                batch_id=retry_batch,
                worker_id="WORKER-002",
                batch_plan_path=(
                    BATCH_PLAN
                ),
                registry_path=(
                    REGISTRY
                ),
                trajectory_manifest_path=(
                    TRAJECTORY_MANIFEST
                ),
                valid_experiments_path=(
                    VALID_EXPERIMENTS
                ),
                constraint_summary_path=(
                    CONSTRAINT_SUMMARY
                ),
                normalized_dir=(
                    NORMALIZED_DIR
                ),
                force_failure=False,
            )

            print(
                "RETRY_STATUS:",
                retry["status"],
            )

            print(
                "RETRY_ATTEMPT_COUNT:",
                retry[
                    "attempt_count"
                ],
            )

    print()
    print(
        "=" * 80
    )
    print(
        "EXECUCAO MULTI-WORKER "
        "FORA DE ORDEM"
    )
    print(
        "=" * 80
    )

    newly_executed_batches = 0

    for index, batch_id in enumerate(
        ordered_batches,
        start=1,
    ):
        if has_completed_attempt(
            run_id=run_id,
            batch_id=batch_id,
        ):
            print(
                batch_id,
                "| ALREADY_COMPLETED",
            )

            continue

        worker_id = WORKERS[
            (index - 1)
            % len(WORKERS)
        ]

        result = execute_worker(
            project_root=(
                PROJECT_ROOT
            ),
            distributed_root=(
                DISTRIBUTED_ROOT
            ),
            run_id=run_id,
            batch_id=batch_id,
            worker_id=worker_id,
            batch_plan_path=(
                BATCH_PLAN
            ),
            registry_path=(
                REGISTRY
            ),
            trajectory_manifest_path=(
                TRAJECTORY_MANIFEST
            ),
            valid_experiments_path=(
                VALID_EXPERIMENTS
            ),
            constraint_summary_path=(
                CONSTRAINT_SUMMARY
            ),
            normalized_dir=(
                NORMALIZED_DIR
            ),
            force_failure=False,
        )

        newly_executed_batches += 1

        print(
            batch_id,
            "|",
            worker_id,
            "|",
            result[
                "status"
            ],
            "| ATTEMPT:",
            result[
                "attempt_count"
            ],
        )

        if (
            result["status"]
            != "COMPLETED"
        ):
            raise RuntimeError(
                "Distributed worker "
                "failed unexpectedly: "
                f"{batch_id}: "
                f"{result}"
            )

    print()
    print(
        "=" * 80
    )
    print(
        "STATUS DISTRIBUIDO"
    )
    print(
        "=" * 80
    )

    status = distributed_status(
        distributed_root=(
            DISTRIBUTED_ROOT
        ),
        run_id=run_id,
    )

    print(
        "BATCHES_TOTAL:",
        status[
            "batches_total"
        ],
    )

    print(
        "WORKERS_TOTAL:",
        status[
            "workers_total"
        ],
    )

    print(
        "WORKERS:",
        status[
            "workers"
        ],
    )

    print(
        "EXECUTION_UNITS_TOTAL:",
        status[
            "execution_units_total"
        ],
    )

    print(
        "COMPLETED:",
        status[
            "completed"
        ],
    )

    print(
        "FAILED_FINAL:",
        status[
            "failed_final"
        ],
    )

    print(
        "RETRIES:",
        status[
            "retries"
        ],
    )

    print(
        "ATTEMPTS_TOTAL:",
        status[
            "attempts_total"
        ],
    )

    if (
        status[
            "completed"
        ]
        != status[
            "batches_total"
        ]
    ):
        raise RuntimeError(
            "Not all distributed batches "
            "completed."
        )

    if (
        status[
            "failed_final"
        ]
        != 0
    ):
        raise RuntimeError(
            "Distributed validation "
            "finished with failed batches."
        )

    print()
    print(
        "=" * 80
    )
    print(
        "MERGE DISTRIBUIDO"
    )
    print(
        "=" * 80
    )

    merged = (
        merge_distributed_results(
            distributed_root=(
                DISTRIBUTED_ROOT
            ),
            run_id=run_id,
            output_path=(
                DISTRIBUTED_RESULT
            ),
        )
    )

    print(
        "MERGED_ROWS:",
        merged[
            "rows"
        ],
    )

    print(
        "MERGED_BATCHES:",
        merged[
            "batches"
        ],
    )

    print(
        "DUPLICATE_COMPLETED_ATTEMPTS:",
        merged[
            "duplicate_completed_attempts"
        ],
    )

    print(
        "DUPLICATE_LOGICAL_RESULTS:",
        merged[
            "duplicate_logical_results"
        ],
    )

    print(
        "DISTRIBUTED_RESULT_SHA256:",
        merged[
            "output_sha256"
        ],
    )

    print(
        "DISTRIBUTED_LOGICAL_SHA256:",
        merged[
            "logical_sha256"
        ],
    )

    print()
    print(
        "=" * 80
    )
    print(
        "COMPARACAO COM ETAPA 15"
    )
    print(
        "=" * 80
    )

    comparison = (
        compare_with_stage15(
            distributed_result_path=(
                DISTRIBUTED_RESULT
            ),
            stage15_result_path=(
                STAGE15_RESULT
            ),
        )
    )

    print(
        "DISTRIBUTED_RESULT_MATCH:",
        comparison[
            "match"
        ],
    )

    print(
        "SAME_EXECUTION_UNIT_IDS:",
        comparison[
            "same_execution_unit_ids"
        ],
    )

    print(
        "MISMATCH_COUNT:",
        comparison.get(
            "mismatch_count",
            0,
        ),
    )

    print(
        "DISTRIBUTED_LOGICAL_SHA256:",
        comparison[
            "distributed_logical_sha256"
        ],
    )

    print(
        "STAGE15_LOGICAL_SHA256:",
        comparison[
            "stage15_logical_sha256"
        ],
    )

    print(
        "MERGED_HASH_LOGICAL_MATCH:",
        comparison.get(
            "logical_hash_match",
            False,
        ),
    )

    if not comparison[
        "match"
    ]:
        raise RuntimeError(
            "Distributed result differs "
            "from Stage 15."
        )

    if not comparison.get(
        "logical_hash_match",
        False,
    ):
        raise RuntimeError(
            "Logical hash differs from "
            "Stage 15."
        )

    print()
    print(
        "=" * 80
    )
    print(
        "IDEMPOTENCIA DO MERGER"
    )
    print(
        "=" * 80
    )

    first_merge_hash = (
        sha256_file(
            DISTRIBUTED_RESULT
        )
    )

    second_merge = (
        merge_distributed_results(
            distributed_root=(
                DISTRIBUTED_ROOT
            ),
            run_id=run_id,
            output_path=(
                DISTRIBUTED_RESULT
            ),
        )
    )

    second_merge_hash = (
        sha256_file(
            DISTRIBUTED_RESULT
        )
    )

    merger_idempotent = (
        first_merge_hash
        == second_merge_hash
    )

    print(
        "FIRST_MERGE_SHA256:",
        first_merge_hash,
    )

    print(
        "SECOND_MERGE_SHA256:",
        second_merge_hash,
    )

    print(
        "MERGER_IDEMPOTENT:",
        merger_idempotent,
    )

    if not merger_idempotent:
        raise RuntimeError(
            "Distributed merger is not "
            "idempotent."
        )

    #
    # Prova de exactly-once lógico:
    # cada execution_unit_id deve
    # aparecer uma única vez no merge.
    #
    exactly_once = (
        merged[
            "duplicate_logical_results"
        ]
        == 0
        and merged[
            "rows"
        ]
        == status[
            "execution_units_total"
        ]
    )

    print()
    print(
        "=" * 80
    )
    print(
        "EXACTLY-ONCE LOGICO"
    )
    print(
        "=" * 80
    )

    print(
        "EXACTLY_ONCE_LOGICAL:",
        exactly_once,
    )

    print(
        "DUPLICATE_LOGICAL_RESULTS:",
        merged[
            "duplicate_logical_results"
        ],
    )

    if not exactly_once:
        raise RuntimeError(
            "Exactly-once logical "
            "validation failed."
        )

    elapsed = (
        time.perf_counter()
        - started
    )

    units = status[
        "execution_units_total"
    ]

    units_per_second = (
        units / elapsed
        if elapsed > 0
        else 0.0
    )

    print()
    print(
        "=" * 80
    )
    print(
        "PERFORMANCE BASELINE"
    )
    print(
        "=" * 80
    )

    print(
        "BATCHES:",
        status[
            "batches_total"
        ],
    )

    print(
        "WORKERS_SIMULATED:",
        status[
            "workers_total"
        ],
    )

    print(
        "EXECUTION_UNITS:",
        units,
    )

    print(
        "NEW_BATCHES_EXECUTED_THIS_RUN:",
        newly_executed_batches,
    )

    print(
        "TOTAL_SECONDS:",
        round(
            elapsed,
            6,
        ),
    )

    print(
        "UNITS_PER_SECOND:",
        round(
            units_per_second,
            6,
        ),
    )

    print()
    print(
        "=" * 80
    )
    print(
        "ETAPA 15.5 — "
        "VALIDACAO FINAL"
    )
    print(
        "=" * 80
    )

    print(
        "RUN_ID:",
        run_id,
    )

    print(
        "BATCHES_TOTAL:",
        status[
            "batches_total"
        ],
    )

    print(
        "WORKERS_TOTAL:",
        status[
            "workers_total"
        ],
    )

    print(
        "EXECUTION_UNITS_TOTAL:",
        status[
            "execution_units_total"
        ],
    )

    print(
        "COMPLETED:",
        status[
            "completed"
        ],
    )

    print(
        "FAILED_FINAL:",
        status[
            "failed_final"
        ],
    )

    print(
        "RETRIES:",
        status[
            "retries"
        ],
    )

    print(
        "DUPLICATE_LOGICAL_RESULTS:",
        merged[
            "duplicate_logical_results"
        ],
    )

    print(
        "EXACTLY_ONCE_LOGICAL:",
        exactly_once,
    )

    print(
        "DISTRIBUTED_RESULT_MATCH:",
        comparison[
            "match"
        ],
    )

    print(
        "MERGED_HASH_LOGICAL_MATCH:",
        comparison[
            "logical_hash_match"
        ],
    )

    print(
        "MERGER_IDEMPOTENT:",
        merger_idempotent,
    )

    print(
        "DISTRIBUTED_RESULT_SHA256:",
        sha256_file(
            DISTRIBUTED_RESULT
        ),
    )

    print(
        "STAGE15_RESULT_SHA256:",
        sha256_file(
            STAGE15_RESULT
        ),
    )

    print(
        "RUN_MANIFEST_SHA256:",
        serialization[
            "run_manifest_sha256"
        ],
    )


if __name__ == "__main__":
    main()