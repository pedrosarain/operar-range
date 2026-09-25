from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from operar_range.reference import reconstruct_reference_session


DEFAULT_STOPS = (100, 125, 150, 170, 175, 200)
DEFAULT_TARGETS = (100, 125, 150, 175, 200, 400, 1000)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _favorable_points(
    direction: str,
    price: float,
    trigger_level: float,
) -> float:
    if direction == "LONG":
        return price - trigger_level
    return trigger_level - price


def _adverse_points(
    direction: str,
    price: float,
    trigger_level: float,
) -> float:
    if direction == "LONG":
        return max(0.0, trigger_level - price)
    return max(0.0, price - trigger_level)


def _points_from_entry(
    direction: str,
    price: float,
    trigger_level: float,
) -> float:
    if direction == "LONG":
        return price - trigger_level
    return trigger_level - price


def reconstruct_trade1(
    parquet_path: str | Path,
    session_date: date,
    stops: tuple[int, ...] = DEFAULT_STOPS,
    targets: tuple[int, ...] = DEFAULT_TARGETS,
    batch_size: int = 131_072,
) -> dict[str, Any]:
    """Reconstruct Trade 1 tick by tick.

    Excursions are measured against entry_trigger_level.

    first_traded_price_after_trigger is preserved separately and is NOT
    assumed to be the financial fill price.

    A return to 0x0 is only marked as exact when a subsequent tick actually
    trades at entry_trigger_level. If price crosses through that level without
    trading exactly there, the case is flagged as ambiguous instead of
    inventing a break-even rule.
    """

    parquet_path = Path(parquet_path)

    if not parquet_path.exists():
        raise FileNotFoundError(parquet_path)

    reference = reconstruct_reference_session(
        parquet_path=parquet_path,
        session_date=session_date,
    )

    ny_open = datetime.fromisoformat(reference["ny_open_brt"])

    buy_level = float(reference["buy_level"])
    sell_level = float(reference["sell_level"])

    parquet = pq.ParquetFile(parquet_path)

    entry_found = False
    direction: str | None = None
    trigger_level: float | None = None

    entry_timestamp: datetime | None = None
    entry_trade_number: int | None = None
    first_traded_price: float | None = None
    jumped_entry_level = False

    mfe_points = 0.0
    mae_points = 0.0

    mfe_timestamp: datetime | None = None
    mae_timestamp: datetime | None = None

    mfe_price: float | None = None
    mae_price: float | None = None

    returned_to_zero_exact = False
    zero_return_timestamp: datetime | None = None
    zero_return_trade_number: int | None = None

    crossed_zero_without_exact_trade = False
    first_zero_cross_timestamp: datetime | None = None
    first_zero_cross_trade_number: int | None = None
    first_zero_cross_price: float | None = None

    pre_return_mfe = 0.0
    pre_return_mae = 0.0

    targets_result = {
        level: {
            "reached": False,
            "timestamp": None,
            "trade_number": None,
            "price": None,
        }
        for level in targets
    }

    stops_result = {
        level: {
            "hit": False,
            "timestamp": None,
            "trade_number": None,
            "price": None,
            "max_favorable_before_stop": None,
        }
        for level in stops
    }

    max_favorable_seen = 0.0

    last_timestamp: datetime | None = None
    last_trade_number: int | None = None
    last_price: float | None = None

    previous_timestamp: datetime | None = None
    previous_trade_number: int | None = None

    ambiguity_flags: list[str] = []

    # ETAPA 5 — trajetória do Trade 1.
    # Registra a entrada e cada mudança posterior de preço.
    trajectory: list[dict[str, Any]] = []

    trajectory_last_price: float | None = None
    trajectory_max_favorable = 0.0
    trajectory_max_adverse = 0.0

    for batch in parquet.iter_batches(
        columns=["timestamp", "trade_number", "price"],
        batch_size=batch_size,
    ):
        timestamps = batch.column("timestamp").to_pylist()
        trade_numbers = batch.column("trade_number").to_pylist()
        prices = batch.column("price").to_pylist()

        for timestamp, trade_number, raw_price in zip(
            timestamps,
            trade_numbers,
            prices,
        ):
            if timestamp < ny_open:
                continue

            trade_number = int(trade_number)
            price = float(raw_price)

            if previous_timestamp is not None:
                if timestamp < previous_timestamp:
                    raise ValueError(
                        "Ticks are not ordered by timestamp."
                    )

                if (
                    timestamp == previous_timestamp
                    and trade_number < previous_trade_number
                ):
                    raise ValueError(
                        "Ticks with identical timestamp are not ordered "
                        "by trade_number."
                    )

            previous_timestamp = timestamp
            previous_trade_number = trade_number

            if not entry_found:
                long_trigger = price >= buy_level
                short_trigger = price <= sell_level

                if not long_trigger and not short_trigger:
                    continue

                if long_trigger and short_trigger:
                    raise ValueError(
                        "One tick simultaneously satisfies buy and sell "
                        "levels. Operational definition required."
                    )

                entry_found = True

                if long_trigger:
                    direction = "LONG"
                    trigger_level = buy_level
                else:
                    direction = "SHORT"
                    trigger_level = sell_level

                entry_timestamp = timestamp
                entry_trade_number = trade_number
                first_traded_price = price

                jumped_entry_level = price != trigger_level

                favorable = _favorable_points(
                    direction,
                    price,
                    trigger_level,
                )

                adverse = _adverse_points(
                    direction,
                    price,
                    trigger_level,
                )

                if favorable > mfe_points:
                    mfe_points = favorable
                    mfe_timestamp = timestamp
                    mfe_price = price

                if adverse > mae_points:
                    mae_points = adverse
                    mae_timestamp = timestamp
                    mae_price = price

                max_favorable_seen = max(
                    max_favorable_seen,
                    favorable,
                )

                # ETAPA 5 — primeiro evento da trajetória.
                entry_points = _points_from_entry(
                    direction,
                    price,
                    trigger_level,
                )

                trajectory_max_favorable = max(
                    0.0,
                    entry_points,
                )

                trajectory_max_adverse = max(
                    0.0,
                    -entry_points,
                )

                trajectory.append(
                    {
                        "timestamp": _iso(timestamp),
                        "trade_number": trade_number,
                        "price": price,
                        "points_from_entry": entry_points,
                        "favorable_excursion": (
                            trajectory_max_favorable
                        ),
                        "adverse_excursion": (
                            trajectory_max_adverse
                        ),
                    }
                )

                trajectory_last_price = price

                for level in targets:
                    if (
                        not targets_result[level]["reached"]
                        and favorable >= level
                    ):
                        targets_result[level] = {
                            "reached": True,
                            "timestamp": _iso(timestamp),
                            "trade_number": trade_number,
                            "price": price,
                        }

                last_timestamp = timestamp
                last_trade_number = trade_number
                last_price = price

                continue

            favorable = max(
                0.0,
                _favorable_points(
                    direction,
                    price,
                    trigger_level,
                ),
            )

            adverse = _adverse_points(
                direction,
                price,
                trigger_level,
            )

            # ETAPA 5 — atualiza a trajetória na mesma leitura
            # já utilizada pelo motor.
            current_points = _points_from_entry(
                direction,
                price,
                trigger_level,
            )

            trajectory_max_favorable = max(
                trajectory_max_favorable,
                max(0.0, current_points),
            )

            trajectory_max_adverse = max(
                trajectory_max_adverse,
                max(0.0, -current_points),
            )

            if price != trajectory_last_price:
                trajectory.append(
                    {
                        "timestamp": _iso(timestamp),
                        "trade_number": trade_number,
                        "price": price,
                        "points_from_entry": current_points,
                        "favorable_excursion": (
                            trajectory_max_favorable
                        ),
                        "adverse_excursion": (
                            trajectory_max_adverse
                        ),
                    }
                )

                trajectory_last_price = price

            if favorable > mfe_points:
                mfe_points = favorable
                mfe_timestamp = timestamp
                mfe_price = price

            if adverse > mae_points:
                mae_points = adverse
                mae_timestamp = timestamp
                mae_price = price

            # First exact return to theoretical entry level.
            if not returned_to_zero_exact:
                if price == trigger_level:
                    returned_to_zero_exact = True
                    zero_return_timestamp = timestamp
                    zero_return_trade_number = trade_number

                else:
                    crossed = (
                        direction == "LONG"
                        and price < trigger_level
                    ) or (
                        direction == "SHORT"
                        and price > trigger_level
                    )

                    if crossed and not crossed_zero_without_exact_trade:
                        crossed_zero_without_exact_trade = True
                        first_zero_cross_timestamp = timestamp
                        first_zero_cross_trade_number = trade_number
                        first_zero_cross_price = price

                if not returned_to_zero_exact:
                    pre_return_mfe = max(
                        pre_return_mfe,
                        favorable,
                    )
                    pre_return_mae = max(
                        pre_return_mae,
                        adverse,
                    )

            # Observational targets.
            for level in targets:
                if (
                    not targets_result[level]["reached"]
                    and favorable >= level
                ):
                    targets_result[level] = {
                        "reached": True,
                        "timestamp": _iso(timestamp),
                        "trade_number": trade_number,
                        "price": price,
                    }

            # Stop classification.
            # max_favorable_seen still represents the best favorable
            # excursion before the current tick.
            for level in stops:
                if (
                    not stops_result[level]["hit"]
                    and adverse >= level
                ):
                    stops_result[level] = {
                        "hit": True,
                        "timestamp": _iso(timestamp),
                        "trade_number": trade_number,
                        "price": price,
                        "max_favorable_before_stop": (
                            max_favorable_seen
                        ),
                    }

            max_favorable_seen = max(
                max_favorable_seen,
                favorable,
            )

            last_timestamp = timestamp
            last_trade_number = trade_number
            last_price = price

    if not entry_found:
        return {
            "date": session_date.isoformat(),
            "source_parquet": parquet_path.name,
            "ny_open": reference["ny_open_brt"],
            "buy_level": buy_level,
            "sell_level": sell_level,
            "entry_found": False,
            "direction": None,
            "trajectory": [],
            "ambiguity_flags": [],
        }

    if crossed_zero_without_exact_trade:
        ambiguity_flags.append(
            "PRICE_CROSSED_ENTRY_LEVEL_WITHOUT_EXACT_TRADE"
        )

    if returned_to_zero_exact:
        max_favorable_before_zero = pre_return_mfe
        mfe_before_zero = pre_return_mfe
        mae_before_zero = pre_return_mae
    else:
        max_favorable_before_zero = None
        mfe_before_zero = None
        mae_before_zero = None

    return {
        "date": session_date.isoformat(),
        "source_parquet": parquet_path.name,
        "ny_open": reference["ny_open_brt"],
        "buy_level": buy_level,
        "sell_level": sell_level,

        "entry_found": True,
        "direction": direction,
        "entry_trigger_level": trigger_level,
        "entry_timestamp": _iso(entry_timestamp),
        "entry_trade_number": entry_trade_number,
        "first_traded_price_after_trigger": first_traded_price,
        "jumped_entry_level": jumped_entry_level,

        "mfe_points": mfe_points,
        "mfe_price": mfe_price,
        "mfe_timestamp": _iso(mfe_timestamp),

        "mae_points": mae_points,
        "mae_price": mae_price,
        "mae_timestamp": _iso(mae_timestamp),

        "returned_to_zero_exact": returned_to_zero_exact,
        "zero_return_timestamp": _iso(zero_return_timestamp),
        "zero_return_trade_number": zero_return_trade_number,

        "crossed_zero_without_exact_trade": (
            crossed_zero_without_exact_trade
        ),
        "first_zero_cross_timestamp": _iso(
            first_zero_cross_timestamp
        ),
        "first_zero_cross_trade_number": (
            first_zero_cross_trade_number
        ),
        "first_zero_cross_price": first_zero_cross_price,

        "max_favorable_before_first_zero": (
            max_favorable_before_zero
        ),
        "mfe_before_first_zero": mfe_before_zero,
        "mae_before_first_zero": mae_before_zero,

        "stops": {
            str(level): stops_result[level]
            for level in stops
        },

        "targets": {
            str(level): targets_result[level]
            for level in targets
        },

        "last_tick": {
            "timestamp": _iso(last_timestamp),
            "trade_number": last_trade_number,
            "price": last_price,
        },

        "sequence_locator": {
            "source_parquet": parquet_path.name,
            "start_timestamp": _iso(entry_timestamp),
            "start_trade_number": entry_trade_number,
            "end_timestamp": _iso(last_timestamp),
            "end_trade_number": last_trade_number,
        },

        "trade_number": entry_trade_number,
        "never_returned_to_entry": not returned_to_zero_exact,
        "last_price_of_session": last_price,

        "trajectory": trajectory,

        "ambiguity_flags": ambiguity_flags,
    }


def write_trade1_report(
    parquet_path: str | Path,
    session_date: date,
    output_path: str | Path,
    stops: tuple[int, ...] = DEFAULT_STOPS,
    targets: tuple[int, ...] = DEFAULT_TARGETS,
) -> dict[str, Any]:
    report = reconstruct_trade1(
        parquet_path=parquet_path,
        session_date=session_date,
        stops=stops,
        targets=targets,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return report