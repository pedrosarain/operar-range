from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from operar_range.management import (
    ManagementConfig,
    simulate_management,
)
from operar_range.runner import (
    M5Candle,
)


TRADE_LIFECYCLE_VERSION = (
    "trade-lifecycle-v1"
)


@dataclass(frozen=True)
class TradeLifecycleConfig:
    trade2_enabled: bool = True

    eligible_after: tuple[str, ...] = (
        "STOP",
    )


def _row_is_after_event(
    *,
    row: dict[str, Any],
    event_timestamp: str,
    event_trade_number: int,
) -> bool:
    timestamp = str(
        row[
            "timestamp"
        ]
    )

    trade_number = int(
        row[
            "trade_number"
        ]
    )

    if timestamp > event_timestamp:
        return True

    if (
        timestamp
        == event_timestamp
        and trade_number
        > event_trade_number
    ):
        return True

    return False


def _triggered(
    *,
    direction: str,
    price: float,
    trigger_level: float,
) -> bool:
    if direction == "LONG":
        return (
            price
            >= trigger_level
        )

    if direction == "SHORT":
        return (
            price
            <= trigger_level
        )

    raise ValueError(
        (
            "Unsupported direction: "
            f"{direction}"
        )
    )


def _points(
    *,
    direction: str,
    entry_price: float,
    price: float,
) -> float:
    if direction == "LONG":
        return (
            price
            - entry_price
        )

    if direction == "SHORT":
        return (
            entry_price
            - price
        )

    raise ValueError(
        (
            "Unsupported direction: "
            f"{direction}"
        )
    )


def _trade_excursions(
    *,
    trajectory: list[
        dict[str, Any]
    ],
    direction: str,
    entry_price: float,
) -> dict[str, Any]:
    if not trajectory:
        return {
            "mfe": None,
            "mae": None,
            "mfe_timestamp": None,
            "mfe_price": None,
            "mae_timestamp": None,
            "mae_price": None,
        }

    mfe = 0.0
    mae = 0.0

    mfe_timestamp = None
    mfe_price = None

    mae_timestamp = None
    mae_price = None

    for row in trajectory:
        price = float(
            row[
                "price"
            ]
        )

        points = _points(
            direction=direction,
            entry_price=(
                entry_price
            ),
            price=price,
        )

        favorable = max(
            0.0,
            points,
        )

        adverse = max(
            0.0,
            -points,
        )

        if favorable > mfe:
            mfe = favorable
            mfe_timestamp = str(
                row[
                    "timestamp"
                ]
            )
            mfe_price = price

        if adverse > mae:
            mae = adverse
            mae_timestamp = str(
                row[
                    "timestamp"
                ]
            )
            mae_price = price

    return {
        "mfe": float(
            mfe
        ),
        "mae": float(
            mae
        ),
        "mfe_timestamp": (
            mfe_timestamp
        ),
        "mfe_price": (
            mfe_price
        ),
        "mae_timestamp": (
            mae_timestamp
        ),
        "mae_price": (
            mae_price
        ),
    }


def _empty_trade2(
    *,
    eligible: bool,
    reason: str,
    direction: (
        str
        | None
    ),
    trigger_level: (
        float
        | None
    ),
) -> dict[str, Any]:
    return {
        "exists": False,
        "eligible": bool(
            eligible
        ),
        "executed": False,
        "reason": reason,
        "direction": (
            direction
        ),
        "trigger_level": (
            trigger_level
        ),
        "entry_timestamp": None,
        "entry_trade_number": None,
        "first_traded_price": None,
        "jumped_entry_level": None,
        "mfe": None,
        "mae": None,
        "mfe_timestamp": None,
        "mfe_price": None,
        "mae_timestamp": None,
        "mae_price": None,
        "management": None,
        "result_points": None,
        "final_reason": None,
        "final_timestamp": None,
        "final_price": None,
    }


def simulate_trade_lifecycle(
    *,
    trajectory: list[
        dict[str, Any]
    ],
    date: str,
    trade1_status: str,
    direction: (
        str
        | None
    ),
    entry_price: (
        float
        | None
    ),
    management_config: ManagementConfig,
    trade1_management: (
        dict[str, Any]
        | None
    ),
    trade2_management_config: (
        ManagementConfig
        | None
    ) = None,
    runner_candles: (
        list[M5Candle]
        | None
    ) = None,
    lifecycle_config: (
        TradeLifecycleConfig
    ) = TradeLifecycleConfig(),
) -> dict[str, Any]:
    if (
        trade1_status
        != "TRADE_1"
        or direction is None
        or entry_price is None
        or trade1_management is None
    ):
        trade2 = _empty_trade2(
            eligible=False,
            reason="NO_TRADE_1",
            direction=direction,
            trigger_level=(
                float(
                    entry_price
                )
                if entry_price
                is not None
                else None
            ),
        )

        return {
            "lifecycle_version": (
                TRADE_LIFECYCLE_VERSION
            ),
            "trade1": (
                trade1_management
            ),
            "trade2": trade2,
            "trade2_occurred": False,
            "trade2_executed": False,
            "trade2_winner": False,
            "trade2_loser": False,
            "trade2_breakeven": False,
            "trade2_result_points": None,
            "consolidated_result_points": (
                None
                if trade1_management
                is None
                else float(
                    trade1_management[
                        "total_weighted_points"
                    ]
                )
            ),
        }

    if not lifecycle_config.trade2_enabled:
        trade2 = _empty_trade2(
            eligible=False,
            reason="TRADE2_DISABLED",
            direction=direction,
            trigger_level=(
                float(
                    entry_price
                )
            ),
        )

        trade1_result = float(
            trade1_management[
                "total_weighted_points"
            ]
        )

        return {
            "lifecycle_version": (
                TRADE_LIFECYCLE_VERSION
            ),
            "trade1": (
                trade1_management
            ),
            "trade2": trade2,
            "trade2_occurred": False,
            "trade2_executed": False,
            "trade2_winner": False,
            "trade2_loser": False,
            "trade2_breakeven": False,
            "trade2_result_points": None,
            "consolidated_result_points": (
                trade1_result
            ),
        }

    trade1_final_reason = (
        trade1_management.get(
            "final_reason"
        )
    )

    eligible = (
        trade1_final_reason
        in lifecycle_config.eligible_after
    )

    trigger_level = float(
        entry_price
    )

    if not eligible:
        trade2 = _empty_trade2(
            eligible=False,
            reason=(
                "TRADE_1_RESULT_NOT_ELIGIBLE"
            ),
            direction=direction,
            trigger_level=(
                trigger_level
            ),
        )

        trade1_result = float(
            trade1_management[
                "total_weighted_points"
            ]
        )

        return {
            "lifecycle_version": (
                TRADE_LIFECYCLE_VERSION
            ),
            "trade1": (
                trade1_management
            ),
            "trade2": trade2,
            "trade2_occurred": False,
            "trade2_executed": False,
            "trade2_winner": False,
            "trade2_loser": False,
            "trade2_breakeven": False,
            "trade2_result_points": None,
            "consolidated_result_points": (
                trade1_result
            ),
        }

    executions = (
        trade1_management.get(
            "executions"
        )
        or []
    )

    if not executions:
        raise RuntimeError(
            (
                "Eligible Trade 1 has no "
                "management executions."
            )
        )

    final_event = (
        executions[
            -1
        ]
    )

    final_timestamp = str(
        final_event[
            "timestamp"
        ]
    )

    final_trade_number = int(
        final_event[
            "trade_number"
        ]
    )

    post_trade1 = [
        row
        for row in trajectory
        if _row_is_after_event(
            row=row,
            event_timestamp=(
                final_timestamp
            ),
            event_trade_number=(
                final_trade_number
            ),
        )
    ]

    entry_index = None

    for index, row in enumerate(
        post_trade1
    ):
        if _triggered(
            direction=direction,
            price=float(
                row[
                    "price"
                ]
            ),
            trigger_level=(
                trigger_level
            ),
        ):
            entry_index = index
            break

    if entry_index is None:
        trade2 = _empty_trade2(
            eligible=True,
            reason=(
                "TRIGGER_NOT_REVISITED"
            ),
            direction=direction,
            trigger_level=(
                trigger_level
            ),
        )

        trade1_result = float(
            trade1_management[
                "total_weighted_points"
            ]
        )

        return {
            "lifecycle_version": (
                TRADE_LIFECYCLE_VERSION
            ),
            "trade1": (
                trade1_management
            ),
            "trade2": trade2,
            "trade2_occurred": False,
            "trade2_executed": False,
            "trade2_winner": False,
            "trade2_loser": False,
            "trade2_breakeven": False,
            "trade2_result_points": None,
            "consolidated_result_points": (
                trade1_result
            ),
        }

    trade2_trajectory = (
        post_trade1[
            entry_index:
        ]
    )

    entry_row = (
        trade2_trajectory[
            0
        ]
    )

    first_traded_price = float(
        entry_row[
            "price"
        ]
    )

    effective_trade2_management_config = (
        trade2_management_config
        if trade2_management_config
        is not None
        else management_config
    )

    management = simulate_management(
        trajectory=(
            trade2_trajectory
        ),
        date=date,
        direction=direction,
        entry_price=(
            trigger_level
        ),
        config=(
            effective_trade2_management_config
        ),
        runner_candles=(
            runner_candles
        ),
    )

    excursions = _trade_excursions(
        trajectory=(
            trade2_trajectory
        ),
        direction=direction,
        entry_price=(
            trigger_level
        ),
    )

    trade2_result = float(
        management[
            "total_weighted_points"
        ]
    )

    trade1_result = float(
        trade1_management[
            "total_weighted_points"
        ]
    )

    trade2 = {
        "exists": True,
        "eligible": True,
        "executed": True,
        "reason": (
            "TRIGGER_REVISITED"
        ),
        "direction": direction,
        "trigger_level": (
            trigger_level
        ),
        "entry_timestamp": str(
            entry_row[
                "timestamp"
            ]
        ),
        "entry_trade_number": int(
            entry_row[
                "trade_number"
            ]
        ),
        "first_traded_price": (
            first_traded_price
        ),
        "jumped_entry_level": (
            first_traded_price
            != trigger_level
        ),
        **excursions,
        "management": management,
        "result_points": (
            trade2_result
        ),
        "final_reason": (
            management[
                "final_reason"
            ]
        ),
        "final_timestamp": (
            management[
                "final_timestamp"
            ]
        ),
        "final_price": (
            management[
                "final_price"
            ]
        ),
    }

    return {
        "lifecycle_version": (
            TRADE_LIFECYCLE_VERSION
        ),
        "trade1": (
            trade1_management
        ),
        "trade2": trade2,
        "trade2_occurred": True,
        "trade2_executed": True,
        "trade2_winner": (
            trade2_result > 0
        ),
        "trade2_loser": (
            trade2_result < 0
        ),
        "trade2_breakeven": (
            trade2_result == 0
        ),
        "trade2_result_points": (
            trade2_result
        ),
        "consolidated_result_points": (
            trade1_result
            + trade2_result
        ),
    }
