from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

from operar_range.management import (
    ManagementConfig,
    simulate_management,
)
from operar_range.runner import (
    build_m5_candles_from_parquet,
)
from operar_range.trajectory import (
    read_trajectory_parquet,
)


MANIFEST = Path(
    "data/research/"
    "trade1_trajectory_manifest.parquet"
)

NORMALIZED = Path(
    "data/normalized"
)


CONFIGS = {
    "RUNNER_A": ManagementConfig(
        stop_points=170,
        partial_1_points=125,
        partial_1_pct=70,
        break_even_enabled=True,
        break_even_after_partial=1,
        final_target_points=None,
        runner_enabled=True,
        runner_pct=30,
        runner_exit_rule=(
            "CANDLE_BREAK_M5"
        ),
        position_size=100,
    ),
    "RUNNER_B": ManagementConfig(
        stop_points=170,
        partial_1_points=100,
        partial_1_pct=40,
        partial_2_points=175,
        partial_2_pct=30,
        break_even_enabled=True,
        break_even_after_partial=1,
        final_target_points=None,
        runner_enabled=True,
        runner_pct=30,
        runner_exit_rule=(
            "CANDLE_BREAK_M5"
        ),
        position_size=100,
    ),
}


def print_result(
    name,
    result,
):
    print("=" * 80)
    print(name)
    print("=" * 80)

    print(
        "STATUS:",
        result["status"],
    )

    print(
        "DATE:",
        result["date"],
    )

    print(
        "DIRECTION:",
        result["direction"],
    )

    print(
        "ENTRY_PRICE:",
        result["entry_price"],
    )

    for event in result[
        "executions"
    ]:
        print(
            "EVENT:",
            event,
        )

    print(
        "PARTIAL_1:",
        result[
            "partial_1_result"
        ],
    )

    print(
        "PARTIAL_2:",
        result[
            "partial_2_result"
        ],
    )

    print(
        "PARTIAL_3:",
        result[
            "partial_3_result"
        ],
    )

    print(
        "RUNNER:",
        result[
            "runner_result"
        ],
    )

    print(
        "TOTAL_WEIGHTED_POINTS:",
        result[
            "total_weighted_points"
        ],
    )

    print(
        "FINAL_REASON:",
        result[
            "final_reason"
        ],
    )

    print(
        "FINAL_TIMESTAMP:",
        result[
            "final_timestamp"
        ],
    )

    print(
        "FINAL_PRICE:",
        result[
            "final_price"
        ],
    )


def main():
    manifest = pq.read_table(
        MANIFEST
    ).to_pylist()

    by_date = {
        row["date"]: row
        for row in manifest
    }

    day = by_date[
        "2026-08-18"
    ]

    trajectory = (
        read_trajectory_parquet(
            day["trajectory_path"]
        )
    )

    source = (
        NORMALIZED
        / day["source_parquet"]
    )

    candles = (
        build_m5_candles_from_parquet(
            source
        )
    )

    for name, config in (
        CONFIGS.items()
    ):
        result = simulate_management(
            trajectory=trajectory,
            date=day["date"],
            direction=day[
                "direction"
            ],
            entry_price=float(
                day["entry_price"]
            ),
            config=config,
            runner_candles=candles,
        )

        print_result(
            name,
            result,
        )

    print("=" * 80)
    print("19/08/2026")
    print("=" * 80)

    no_trade = by_date[
        "2026-08-19"
    ]

    print(
        "STATUS:",
        no_trade[
            "trade1_status"
        ],
    )

    print(
        "RUNNER_EXECUTED: False"
    )

    print(
        "TRAJECTORY_EXISTS:",
        no_trade[
            "trajectory_exists"
        ],
    )


if __name__ == "__main__":
    main()