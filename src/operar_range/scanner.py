from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.reference import reconstruct_reference_session
from operar_range.trade1 import reconstruct_trade1


MOTOR_VERSION = "trade1-adr004"

TRADE1_DATABASE_SCHEMA = pa.schema(
    [
        ("date", pa.string()),
        ("source_parquet", pa.string()),
        ("entry_found", pa.bool_()),
        ("trade1_status", pa.string()),
        ("direction", pa.string()),

        ("reference_candle_start", pa.string()),
        ("reference_candle_end", pa.string()),
        ("reference_high", pa.float64()),
        ("reference_low", pa.float64()),

        ("intraday_high_until_open", pa.float64()),
        ("intraday_low_until_open", pa.float64()),

        ("buy_offset", pa.int64()),
        ("sell_offset", pa.int64()),
        ("buy_level", pa.float64()),
        ("sell_level", pa.float64()),

        ("entry_trigger_level", pa.float64()),
        ("entry_timestamp", pa.string()),
        ("entry_trade_number", pa.int64()),
        ("first_traded_price_after_trigger", pa.float64()),
        ("jumped_entry_level", pa.bool_()),

        ("mfe_points", pa.float64()),
        ("mfe_price", pa.float64()),
        ("mfe_timestamp", pa.string()),

        ("mae_points", pa.float64()),
        ("mae_price", pa.float64()),
        ("mae_timestamp", pa.string()),

        ("returned_to_zero_exact", pa.bool_()),
        ("zero_return_timestamp", pa.string()),
        ("max_favorable_before_first_zero", pa.float64()),

        ("target_100", pa.bool_()),
        ("target_125", pa.bool_()),
        ("target_150", pa.bool_()),
        ("target_175", pa.bool_()),
        ("target_200", pa.bool_()),
        ("target_400", pa.bool_()),
        ("target_1000", pa.bool_()),

        ("stop_100", pa.bool_()),
        ("stop_125", pa.bool_()),
        ("stop_150", pa.bool_()),
        ("stop_170", pa.bool_()),
        ("stop_175", pa.bool_()),
        ("stop_200", pa.bool_()),

        ("last_timestamp", pa.string()),
        ("last_price", pa.float64()),

        ("motor_version", pa.string()),
    ]
)


def _extract_session_date(
    parquet_path: Path,
) -> date:
    match = re.search(
        r"(\d{8})",
        parquet_path.name,
    )

    if match is None:
        raise ValueError(
            "Unable to extract session date from filename: "
            f"{parquet_path.name}"
        )

    return datetime.strptime(
        match.group(1),
        "%Y%m%d",
    ).date()


def discover_normalized_parquets(
    normalized_dir: str | Path,
) -> list[Path]:
    normalized_dir = Path(normalized_dir)

    if not normalized_dir.exists():
        return []

    return sorted(
        path
        for path in normalized_dir.glob("*.parquet")
        if path.is_file()
    )


def _target(
    trade: dict[str, Any],
    level: int,
) -> bool | None:
    targets = trade.get("targets")

    if targets is None:
        return None

    return bool(
        targets[str(level)]["reached"]
    )


def _stop(
    trade: dict[str, Any],
    level: int,
) -> bool | None:
    stops = trade.get("stops")

    if stops is None:
        return None

    return bool(
        stops[str(level)]["hit"]
    )


def build_trade1_record(
    parquet_path: str | Path,
) -> dict[str, Any]:
    parquet_path = Path(parquet_path)

    session_date = _extract_session_date(
        parquet_path
    )

    reference = reconstruct_reference_session(
        parquet_path=parquet_path,
        session_date=session_date,
    )

    trade = reconstruct_trade1(
        parquet_path=parquet_path,
        session_date=session_date,
    )

    entry_found = bool(
        trade.get("entry_found")
    )

    last_tick = trade.get(
        "last_tick",
        {},
    )

    return {
        "date": session_date.isoformat(),
        "source_parquet": parquet_path.name,
        "entry_found": entry_found,
        "trade1_status": (
            "TRADE_1"
            if entry_found
            else "NO_TRADE_1"
        ),
        "direction": trade.get("direction"),

        "reference_candle_start": reference[
            "reference_candle_start"
        ],
        "reference_candle_end": reference[
            "reference_candle_end"
        ],
        "reference_high": float(
            reference["high"]
        ),
        "reference_low": float(
            reference["low"]
        ),

        "intraday_high_until_open": float(
            reference[
                "intraday_high_until_open"
            ]
        ),
        "intraday_low_until_open": float(
            reference[
                "intraday_low_until_open"
            ]
        ),

        "buy_offset": int(
            reference["buy_offset"]
        ),
        "sell_offset": int(
            reference["sell_offset"]
        ),
        "buy_level": float(
            reference["buy_level"]
        ),
        "sell_level": float(
            reference["sell_level"]
        ),

        "entry_trigger_level": trade.get(
            "entry_trigger_level"
        ),
        "entry_timestamp": trade.get(
            "entry_timestamp"
        ),
        "entry_trade_number": trade.get(
            "entry_trade_number"
        ),
        "first_traded_price_after_trigger": trade.get(
            "first_traded_price_after_trigger"
        ),
        "jumped_entry_level": trade.get(
            "jumped_entry_level"
        ),

        "mfe_points": trade.get(
            "mfe_points"
        ),
        "mfe_price": trade.get(
            "mfe_price"
        ),
        "mfe_timestamp": trade.get(
            "mfe_timestamp"
        ),

        "mae_points": trade.get(
            "mae_points"
        ),
        "mae_price": trade.get(
            "mae_price"
        ),
        "mae_timestamp": trade.get(
            "mae_timestamp"
        ),

        "returned_to_zero_exact": trade.get(
            "returned_to_zero_exact"
        ),
        "zero_return_timestamp": trade.get(
            "zero_return_timestamp"
        ),
        "max_favorable_before_first_zero": trade.get(
            "max_favorable_before_first_zero"
        ),

        "target_100": _target(
            trade,
            100,
        ),
        "target_125": _target(
            trade,
            125,
        ),
        "target_150": _target(
            trade,
            150,
        ),
        "target_175": _target(
            trade,
            175,
        ),
        "target_200": _target(
            trade,
            200,
        ),
        "target_400": _target(
            trade,
            400,
        ),
        "target_1000": _target(
            trade,
            1000,
        ),

        "stop_100": _stop(
            trade,
            100,
        ),
        "stop_125": _stop(
            trade,
            125,
        ),
        "stop_150": _stop(
            trade,
            150,
        ),
        "stop_170": _stop(
            trade,
            170,
        ),
        "stop_175": _stop(
            trade,
            175,
        ),
        "stop_200": _stop(
            trade,
            200,
        ),

        "last_timestamp": last_tick.get(
            "timestamp"
        ),
        "last_price": last_tick.get(
            "price"
        ),

        "motor_version": MOTOR_VERSION,
    }


def scan_normalized_directory(
    normalized_dir: str | Path,
) -> list[dict[str, Any]]:
    parquet_files = (
        discover_normalized_parquets(
            normalized_dir
        )
    )

    records = [
        build_trade1_record(path)
        for path in parquet_files
    ]

    return sorted(
        records,
        key=lambda row: (
            row["date"],
            row["source_parquet"],
        ),
    )


def write_trade1_database(
    records: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        records,
        schema=TRADE1_DATABASE_SCHEMA,
    )

    pq.write_table(
        table,
        output_path,
        compression="zstd",
    )

    return output_path


def build_summary(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    total = len(records)

    trade1_count = sum(
        1
        for record in records
        if record["entry_found"]
    )

    no_trade1_count = (
        total - trade1_count
    )

    dates = [
        record["date"]
        for record in records
    ]

    return {
        "pregoes_analisados": total,
        "trade1_count": trade1_count,
        "sem_trade1_count": no_trade1_count,
        "periodo_inicial": (
            min(dates)
            if dates
            else None
        ),
        "periodo_final": (
            max(dates)
            if dates
            else None
        ),
        "data_execucao_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "motor_version": MOTOR_VERSION,
    }


def write_summary(
    summary: dict[str, Any],
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return output_path


def run_scanner(
    normalized_dir: str | Path = "data/normalized",
    database_path: str | Path = (
        "data/research/"
        "trade1_database.parquet"
    ),
    summary_path: str | Path = (
        "data/reports/"
        "trade1_database_summary.json"
    ),
) -> dict[str, Any]:
    records = scan_normalized_directory(
        normalized_dir
    )

    write_trade1_database(
        records,
        database_path,
    )

    summary = build_summary(
        records
    )

    write_summary(
        summary,
        summary_path,
    )

    return {
        "records": records,
        "summary": summary,
        "database_path": str(
            database_path
        ),
        "summary_path": str(
            summary_path
        ),
    }