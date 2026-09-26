from __future__ import annotations

from pathlib import Path

from operar_range.analytics import (
    run_analytics,
    sha256_file,
)


def fmt(value):
    if value is None:
        return "N/A"

    return value


def main():
    result = run_analytics()

    print("=" * 80)
    print(
        "ETAPA 12 — ANALYTICS ENGINE V1"
    )
    print("=" * 80)

    print(
        "EXPERIMENTS:",
        len(result["metrics"]),
    )

    print(
        "YEARLY_ROWS:",
        len(result["yearly"]),
    )

    print(
        "MONTHLY_ROWS:",
        len(result["monthly"]),
    )

    print(
        "SOURCE_RESULTS_SHA256:",
        result[
            "source_results_sha256"
        ],
    )

    print(
        "SOURCE_MANIFEST_SHA256:",
        result[
            "source_manifest_sha256"
        ],
    )

    paths = [
        (
            "METRICS",
            Path(
                result[
                    "metrics_path"
                ]
            ),
        ),
        (
            "YEARLY",
            Path(
                result[
                    "yearly_path"
                ]
            ),
        ),
        (
            "MONTHLY",
            Path(
                result[
                    "monthly_path"
                ]
            ),
        ),
    ]

    for name, path in paths:
        print(
            f"{name}_PATH:",
            path,
        )

        print(
            f"{name}_SHA256:",
            sha256_file(path),
        )

    for row in result[
        "metrics"
    ]:
        print("-" * 80)

        print(
            "EXPERIMENT_ID:",
            row["experiment_id"],
        )

        print(
            "SESSIONS_TOTAL:",
            row["sessions_total"],
        )

        print(
            "TRADE1_COUNT:",
            row["trade1_count"],
        )

        print(
            "NO_TRADE1_COUNT:",
            row[
                "no_trade1_count"
            ],
        )

        print(
            "TRADE_FREQUENCY_PCT:",
            row[
                "trade_frequency_pct"
            ],
        )

        print(
            "TOTAL_WEIGHTED_POINTS:",
            row[
                "total_weighted_points"
            ],
        )

        print(
            "AVERAGE_WEIGHTED_POINTS:",
            fmt(
                row[
                    "average_weighted_points"
                ]
            ),
        )

        print(
            "MEDIAN_WEIGHTED_POINTS:",
            fmt(
                row[
                    "median_weighted_points"
                ]
            ),
        )

        print(
            "BEST_TRADE_POINTS:",
            fmt(
                row[
                    "best_trade_points"
                ]
            ),
        )

        print(
            "WORST_TRADE_POINTS:",
            fmt(
                row[
                    "worst_trade_points"
                ]
            ),
        )

        print(
            "WINNING_TRADES:",
            row["winning_trades"],
        )

        print(
            "LOSING_TRADES:",
            row["losing_trades"],
        )

        print(
            "BREAKEVEN_TRADES:",
            row[
                "breakeven_trades"
            ],
        )

        print(
            "WIN_RATE_PCT:",
            fmt(
                row["win_rate_pct"]
            ),
        )

        print(
            "LOSS_RATE_PCT:",
            fmt(
                row["loss_rate_pct"]
            ),
        )

        print(
            "GROSS_PROFIT_POINTS:",
            row[
                "gross_profit_points"
            ],
        )

        print(
            "GROSS_LOSS_POINTS:",
            row[
                "gross_loss_points"
            ],
        )

        print(
            "AVERAGE_WIN_POINTS:",
            fmt(
                row[
                    "average_win_points"
                ]
            ),
        )

        print(
            "AVERAGE_LOSS_POINTS:",
            fmt(
                row[
                    "average_loss_points"
                ]
            ),
        )

        print(
            "PAYOFF_RATIO:",
            fmt(
                row[
                    "payoff_ratio"
                ]
            ),
        )

        print(
            "PAYOFF_RATIO_STATUS:",
            row[
                "payoff_ratio_status"
            ],
        )

        print(
            "PROFIT_FACTOR:",
            fmt(
                row[
                    "profit_factor"
                ]
            ),
        )

        print(
            "PROFIT_FACTOR_STATUS:",
            row[
                "profit_factor_status"
            ],
        )

        print(
            "EXPECTANCY:",
            fmt(
                row[
                    "expectancy_points_per_trade"
                ]
            ),
        )

        print(
            "MAX_DRAWDOWN_POINTS:",
            row[
                "max_drawdown_points"
            ],
        )

        print(
            "MAX_DRAWDOWN_START:",
            fmt(
                row[
                    "max_drawdown_start_date"
                ]
            ),
        )

        print(
            "MAX_DRAWDOWN_END:",
            fmt(
                row[
                    "max_drawdown_end_date"
                ]
            ),
        )

        print(
            "MAX_CONSECUTIVE_WINS:",
            row[
                "max_consecutive_wins"
            ],
        )

        print(
            "MAX_CONSECUTIVE_LOSSES:",
            row[
                "max_consecutive_losses"
            ],
        )

        print(
            "POSITIVE_DAYS:",
            row["positive_days"],
        )

        print(
            "NEGATIVE_DAYS:",
            row["negative_days"],
        )

        print(
            "ZERO_RESULT_DAYS:",
            row[
                "zero_result_days"
            ],
        )


if __name__ == "__main__":
    main()