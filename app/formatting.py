from __future__ import annotations

import math
from typing import Any

import pandas as pd


NA_TEXT = "N/A"


def is_missing(
    value: Any,
) -> bool:
    if value is None:
        return True

    try:
        if pd.isna(value):
            return True
    except (
        TypeError,
        ValueError,
    ):
        pass

    return False


def as_text(
    value: Any,
    default: str = NA_TEXT,
) -> str:
    if is_missing(
        value
    ):
        return default

    return str(
        value
    )


def format_integer(
    value: Any,
    default: str = NA_TEXT,
) -> str:
    if is_missing(
        value
    ):
        return default

    try:
        return f"{int(value):,}".replace(
            ",",
            ".",
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


def format_float(
    value: Any,
    decimals: int = 2,
    default: str = NA_TEXT,
) -> str:
    if is_missing(
        value
    ):
        return default

    try:
        numeric = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return default

    if not math.isfinite(
        numeric
    ):
        return default

    return (
        f"{numeric:,.{decimals}f}"
        .replace(
            ",",
            "_",
        )
        .replace(
            ".",
            ",",
        )
        .replace(
            "_",
            ".",
        )
    )


def format_points(
    value: Any,
    decimals: int = 2,
    default: str = NA_TEXT,
) -> str:
    formatted = format_float(
        value,
        decimals=decimals,
        default=default,
    )

    if formatted == default:
        return default

    return (
        f"{formatted} pts"
    )


def format_percent(
    value: Any,
    decimals: int = 2,
    default: str = NA_TEXT,
) -> str:
    formatted = format_float(
        value,
        decimals=decimals,
        default=default,
    )

    if formatted == default:
        return default

    return (
        f"{formatted}%"
    )


def format_ratio(
    value: Any,
    decimals: int = 3,
    default: str = NA_TEXT,
) -> str:
    return format_float(
        value,
        decimals=decimals,
        default=default,
    )


def format_boolean(
    value: Any,
    default: str = NA_TEXT,
) -> str:
    if is_missing(
        value
    ):
        return default

    if isinstance(
        value,
        str,
    ):
        normalized = (
            value.strip()
            .lower()
        )

        if normalized in {
            "true",
            "1",
            "yes",
            "sim",
        }:
            return "ON"

        if normalized in {
            "false",
            "0",
            "no",
            "nao",
            "não",
        }:
            return "OFF"

    return (
        "ON"
        if bool(value)
        else "OFF"
    )


def format_date(
    value: Any,
    default: str = NA_TEXT,
) -> str:
    if is_missing(
        value
    ):
        return default

    try:
        timestamp = pd.to_datetime(
            value,
            errors="coerce",
        )

    except Exception:
        return default

    if pd.isna(
        timestamp
    ):
        return default

    return timestamp.strftime(
        "%d/%m/%Y"
    )


def format_datetime(
    value: Any,
    default: str = NA_TEXT,
) -> str:
    if is_missing(
        value
    ):
        return default

    try:
        timestamp = pd.to_datetime(
            value,
            errors="coerce",
        )

    except Exception:
        return default

    if pd.isna(
        timestamp
    ):
        return default

    return timestamp.strftime(
        "%d/%m/%Y %H:%M:%S"
    )


def format_hash(
    value: Any,
    visible: int = 12,
    default: str = NA_TEXT,
) -> str:
    if is_missing(
        value
    ):
        return default

    text = str(
        value
    )

    if len(text) <= visible:
        return text

    return (
        text[:visible]
        + "..."
    )


def metric_value_or_status(
    *,
    value: Any,
    status: Any = None,
    formatter=None,
    default: str = NA_TEXT,
) -> str:
    if not is_missing(
        value
    ):
        if formatter is None:
            return as_text(
                value,
                default=default,
            )

        return formatter(
            value
        )

    if not is_missing(
        status
    ):
        return str(
            status
        )

    return default


def ranking_status_text(
    status: Any,
) -> str:
    if is_missing(
        status
    ):
        return NA_TEXT

    return str(
        status
    )


def display_metric_name(
    ranking_type: str,
) -> str:
    labels = {
        "PROFIT_FACTOR": (
            "Profit Factor"
        ),
        "EXPECTANCY": (
            "Expectancy"
        ),
        "NET_POINTS": (
            "Net Points"
        ),
        "WIN_RATE": (
            "Win Rate"
        ),
        "AVERAGE_TRADE": (
            "Average Trade"
        ),
        "MAX_DRAWDOWN": (
            "Max Drawdown"
        ),
        "RECOVERY_FACTOR": (
            "Recovery Factor"
        ),
        "PAYOFF": (
            "Payoff"
        ),
        "NUMBER_OF_TRADES": (
            "Number of Trades"
        ),
        "FREQUENCY": (
            "Frequency"
        ),
        "CAGR": (
            "CAGR"
        ),
        "COMPOSITE_SCORE": (
            "Composite Score"
        ),
    }

    return labels.get(
        ranking_type,
        ranking_type.replace(
            "_",
            " ",
        ).title(),
    )


def format_ranking_metric(
    ranking_type: str,
    value: Any,
    status: Any = None,
) -> str:
    if is_missing(
        value
    ):
        if not is_missing(
            status
        ):
            return str(
                status
            )

        return NA_TEXT

    if ranking_type in {
        "WIN_RATE",
        "FREQUENCY",
        "CAGR",
    }:
        return format_percent(
            value
        )

    if ranking_type in {
        "NET_POINTS",
        "AVERAGE_TRADE",
        "MAX_DRAWDOWN",
        "EXPECTANCY",
    }:
        return format_points(
            value
        )

    if ranking_type in {
        "PROFIT_FACTOR",
        "PAYOFF",
        "RECOVERY_FACTOR",
        "COMPOSITE_SCORE",
    }:
        return format_ratio(
            value
        )

    if ranking_type == (
        "NUMBER_OF_TRADES"
    ):
        return format_integer(
            value
        )

    return as_text(
        value
    )


def numeric_difference(
    left: Any,
    right: Any,
) -> float | None:
    if (
        is_missing(left)
        or is_missing(right)
    ):
        return None

    try:
        left_value = float(
            left
        )

        right_value = float(
            right
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if (
        not math.isfinite(
            left_value
        )
        or not math.isfinite(
            right_value
        )
    ):
        return None

    return (
        left_value
        - right_value
    )


def format_bytes(
    value: Any,
    default: str = NA_TEXT,
) -> str:
    if is_missing(
        value
    ):
        return default

    try:
        size = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return default

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ]

    unit_index = 0

    while (
        size >= 1024
        and unit_index
        < len(units) - 1
    ):
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return (
            f"{int(size)} "
            f"{units[unit_index]}"
        )

    return (
        f"{size:.2f} "
        f"{units[unit_index]}"
    )