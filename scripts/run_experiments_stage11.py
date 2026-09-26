from __future__ import annotations

import hashlib
from pathlib import Path

import pyarrow.parquet as pq

from operar_range.management import (
    ManagementConfig,
)
from operar_range.research_engine import (
    ExperimentDefinition,
    run_experiments,
)


EXPERIMENTS = [
    ExperimentDefinition(
        experiment_id="EXP-000001",
        name="STOP_100_TARGET_100",
        config=ManagementConfig(
            stop_points=100,
            final_target_points=100,
            position_size=100,
        ),
    ),
    ExperimentDefinition(
        experiment_id="EXP-000002",
        name="STOP_170_END",
        config=ManagementConfig(
            stop_points=170,
            position_size=100,
        ),
    ),
    ExperimentDefinition(
        experiment_id="EXP-000003",
        name=(
            "STOP170_P125_70_BE_TARGET400"
        ),
        config=ManagementConfig(
            stop_points=170,
            partial_1_points=125,
            partial_1_pct=70,
            break_even_enabled=True,
            break_even_after_partial=1,
            final_target_points=400,
            position_size=100,
        ),
    ),
    ExperimentDefinition(
        experiment_id="EXP-000004",
        name=(
            "STOP170_P125_70_RUNNER30"
        ),
        config=ManagementConfig(
            stop_points=170,
            partial_1_points=125,
            partial_1_pct=70,
            runner_enabled=True,
            runner_pct=30,
            runner_exit_rule=(
                "CANDLE_BREAK_M5"
            ),
            position_size=100,
        ),
    ),
    ExperimentDefinition(
        experiment_id="EXP-000005",
        name=(
            "STOP170_P125_70_BE_RUNNER30"
        ),
        config=ManagementConfig(
            stop_points=170,
            partial_1_points=125,
            partial_1_pct=70,
            break_even_enabled=True,
            break_even_after_partial=1,
            runner_enabled=True,
            runner_pct=30,
            runner_exit_rule=(
                "CANDLE_BREAK_M5"
            ),
            position_size=100,
        ),
    ),
]


def sha256_file(
    path: Path,
) -> str:
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
    result = run_experiments(
        experiments=EXPERIMENTS
    )

    results_path = Path(
        result["results_path"]
    )

    manifest_path = Path(
        result[
            "experiment_manifest_path"
        ]
    )

    rows = pq.read_table(
        results_path
    ).to_pylist()

    manifest_rows = pq.read_table(
        manifest_path
    ).to_pylist()

    print("=" * 80)
    print(
        "ETAPA 11 — RESEARCH ENGINE V1"
    )
    print("=" * 80)

    print(
        "EXPERIMENTS:",
        result["experiments"],
    )

    print(
        "SESSIONS:",
        result["sessions"],
    )

    print(
        "RESULT_ROWS:",
        len(rows),
    )

    print(
        "MANIFEST_ROWS:",
        len(manifest_rows),
    )

    print(
        "RESULTS_PATH:",
        results_path,
    )

    print(
        "RESULTS_SHA256:",
        sha256_file(
            results_path
        ),
    )

    print(
        "MANIFEST_PATH:",
        manifest_path,
    )

    print(
        "MANIFEST_SHA256:",
        sha256_file(
            manifest_path
        ),
    )

    for manifest in manifest_rows:
        print("-" * 80)

        print(
            "EXPERIMENT_ID:",
            manifest[
                "experiment_id"
            ],
        )

        print(
            "NAME:",
            manifest["name"],
        )

        print(
            "CONFIG_SHA256:",
            manifest[
                "config_sha256"
            ],
        )

        print(
            "SESSIONS_EXECUTED:",
            manifest[
                "sessions_executed"
            ],
        )

        experiment_rows = [
            row
            for row in rows
            if row["experiment_id"]
            == manifest[
                "experiment_id"
            ]
        ]

        for row in experiment_rows:
            print(
                "DATE:",
                row["date"],
                "| STATUS:",
                row["trade_status"],
                "| RESULT:",
                row[
                    "total_weighted_points"
                ],
                "| FINAL_REASON:",
                row["final_reason"],
            )


if __name__ == "__main__":
    main()