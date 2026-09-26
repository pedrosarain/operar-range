from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

from operar_range.management import (
    ManagementConfig,
    simulate_management,
)
from operar_range.trajectory import (
    read_trajectory_parquet,
)


MANIFEST = Path(
    "data/research/"
    "trade1_trajectory_manifest.parquet"
)


CONFIGS = {
    "A": ManagementConfig(
        stop_points=100,
        final_target_points=100,
        position_size=100,
    ),
    "B": ManagementConfig(
        stop_points=170,
        partial_1_points=125,
        partial_1_pct=70,
        break_even_enabled=True,
        break_even_after_partial=1,
        final_target_points=400,
        position_size=100,
    ),
    "C": ManagementConfig(
        stop_points=170,
        partial_1_points=100,
        partial_1_pct=40,
        partial_2_points=175,
        partial_2_pct=30,
        break_even_enabled=True,
        break_even_after_partial=1,
        final_target_points=400,
        position_size=100,
    ),
}


def print_result(
    name,
    result,
):
    print("=" * 78)
    print(
        f"GESTAO {name}"
    )
    print("=" * 78)

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

    print(
        "POSITION_SIZE:",
        result["position_size"],
    )

    print(
        "EXECUTIONS:"
    )

    for event in result[
        "executions"
    ]:
        print(
            event[
                "sequence"
            ],
            "|",
            event[
                "event_type"
            ],
            "| timestamp=",
            event[
                "timestamp"
            ],
            "| trade_number=",
            event[
                "trade_number"
            ],
            "| trigger_level=",
            event[
                "trigger_level"
            ],
            "| first_traded_price_after_trigger=",
            event[
                "first_traded_price_after_trigger"
            ],
            "| jumped_trigger_level=",
            event[
                "jumped_trigger_level"
            ],
            "| realized_points=",
            event[
                "realized_points"
            ],
            "| pct_closed=",
            event[
                "pct_closed"
            ],
            "| quantity_closed=",
            event[
                "quantity_closed"
            ],
            "| remaining_position=",
            event[
                "remaining_position"
            ],
            "| weighted_points=",
            event[
                "weighted_points"
            ],
        )

    print(
        "PARTIAL_1_RESULT:",
        result[
            "partial_1_result"
        ],
    )

    print(
        "PARTIAL_2_RESULT:",
        result[
            "partial_2_result"
        ],
    )

    print(
        "PARTIAL_3_RESULT:",
        result[
            "partial_3_result"
        ],
    )

    print(
        "REMAINING_POSITION_RESULT:",
        result[
            "remaining_position_result"
        ],
    )

    print(
        "TOTAL_WEIGHTED_POINTS:",
        result[
            "total_weighted_points"
        ],
    )

    print(
        "TOTAL_POSITION_POINTS:",
        result[
            "total_position_points"
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

    row_18 = by_date[
        "2026-08-18"
    ]

    if (
        row_18[
            "trade1_status"
        ]
        != "TRADE_1"
    ):
        raise RuntimeError(
            "18/08/2026 unexpectedly "
            "has no Trade 1."
        )

    trajectory = (
        read_trajectory_parquet(
            row_18[
                "trajectory_path"
            ]
        )
    )

    for name, config in (
        CONFIGS.items()
    ):
        result = simulate_management(
            trajectory=trajectory,
            date=row_18["date"],
            direction=row_18[
                "direction"
            ],
            entry_price=float(
                row_18[
                    "entry_price"
                ]
            ),
            config=config,
        )

        print_result(
            name,
            result,
        )

    print("=" * 78)
    print("19/08/2026")
    print("=" * 78)

    row_19 = by_date[
        "2026-08-19"
    ]

    if (
        row_19[
            "trade1_status"
        ]
        == "NO_TRADE_1"
    ):
        print(
            "STATUS: NO_TRADE_1"
        )
        print(
            "MANAGEMENT_EXECUTED: False"
        )
        print(
            "TRAJECTORY_EXISTS:",
            row_19[
                "trajectory_exists"
            ],
        )
    else:
        raise RuntimeError(
            "19/08/2026 should be "
            "NO_TRADE_1."
        )


if __name__ == "__main__":
    main()