from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq

import operar_range.scanner as scanner


def fake_record(
    parquet_path,
):
    date_text = (
        scanner
        ._extract_session_date(
            Path(parquet_path)
        )
        .isoformat()
    )

    entry_found = (
        "20260818"
        in str(parquet_path)
    )

    return {
        "date": date_text,
        "source_parquet": (
            Path(parquet_path).name
        ),
        "entry_found": entry_found,
        "trade1_status": (
            "TRADE_1"
            if entry_found
            else "NO_TRADE_1"
        ),
        "direction": (
            "LONG"
            if entry_found
            else None
        ),

        "reference_candle_start": None,
        "reference_candle_end": None,
        "reference_high": None,
        "reference_low": None,

        "intraday_high_until_open": None,
        "intraday_low_until_open": None,

        "buy_offset": None,
        "sell_offset": None,
        "buy_level": None,
        "sell_level": None,

        "entry_trigger_level": None,
        "entry_timestamp": None,
        "entry_trade_number": None,
        "first_traded_price_after_trigger": None,
        "jumped_entry_level": None,

        "mfe_points": None,
        "mfe_price": None,
        "mfe_timestamp": None,

        "mae_points": None,
        "mae_price": None,
        "mae_timestamp": None,

        "returned_to_zero_exact": None,
        "zero_return_timestamp": None,
        "max_favorable_before_first_zero": None,

        "target_100": None,
        "target_125": None,
        "target_150": None,
        "target_175": None,
        "target_200": None,
        "target_400": None,
        "target_1000": None,

        "stop_100": None,
        "stop_125": None,
        "stop_150": None,
        "stop_170": None,
        "stop_175": None,
        "stop_200": None,

        "last_timestamp": None,
        "last_price": None,

        "motor_version": (
            scanner.MOTOR_VERSION
        ),
    }


def touch_parquet(
    directory,
    name,
):
    path = directory / name
    path.write_bytes(b"test")
    return path


def test_empty_directory(
    tmp_path,
):
    records = (
        scanner
        .scan_normalized_directory(
            tmp_path
        )
    )

    assert records == []


def test_one_session(
    monkeypatch,
    tmp_path,
):
    touch_parquet(
        tmp_path,
        "winv26_ticks_20260818_enriched.parquet",
    )

    monkeypatch.setattr(
        scanner,
        "build_trade1_record",
        fake_record,
    )

    records = (
        scanner
        .scan_normalized_directory(
            tmp_path
        )
    )

    assert len(records) == 1
    assert (
        records[0]["date"]
        == "2026-08-18"
    )


def test_multiple_sessions_sorted(
    monkeypatch,
    tmp_path,
):
    touch_parquet(
        tmp_path,
        "winv26_ticks_20260819_enriched.parquet",
    )

    touch_parquet(
        tmp_path,
        "winv26_ticks_20260818_enriched.parquet",
    )

    monkeypatch.setattr(
        scanner,
        "build_trade1_record",
        fake_record,
    )

    records = (
        scanner
        .scan_normalized_directory(
            tmp_path
        )
    )

    assert [
        row["date"]
        for row in records
    ] == [
        "2026-08-18",
        "2026-08-19",
    ]


def test_no_trade1_preserved(
    monkeypatch,
    tmp_path,
):
    touch_parquet(
        tmp_path,
        "winv26_ticks_20260819_enriched.parquet",
    )

    monkeypatch.setattr(
        scanner,
        "build_trade1_record",
        fake_record,
    )

    records = (
        scanner
        .scan_normalized_directory(
            tmp_path
        )
    )

    assert (
        records[0]["entry_found"]
        is False
    )

    assert (
        records[0]["trade1_status"]
        == "NO_TRADE_1"
    )


def test_determinism(
    monkeypatch,
    tmp_path,
):
    touch_parquet(
        tmp_path,
        "winv26_ticks_20260818_enriched.parquet",
    )

    touch_parquet(
        tmp_path,
        "winv26_ticks_20260819_enriched.parquet",
    )

    monkeypatch.setattr(
        scanner,
        "build_trade1_record",
        fake_record,
    )

    first = (
        scanner
        .scan_normalized_directory(
            tmp_path
        )
    )

    second = (
        scanner
        .scan_normalized_directory(
            tmp_path
        )
    )

    assert first == second


def test_database_roundtrip(
    monkeypatch,
    tmp_path,
):
    normalized = (
        tmp_path / "normalized"
    )
    normalized.mkdir()

    touch_parquet(
        normalized,
        "winv26_ticks_20260818_enriched.parquet",
    )

    touch_parquet(
        normalized,
        "winv26_ticks_20260819_enriched.parquet",
    )

    monkeypatch.setattr(
        scanner,
        "build_trade1_record",
        fake_record,
    )

    records = (
        scanner
        .scan_normalized_directory(
            normalized
        )
    )

    output = (
        tmp_path
        / "trade1_database.parquet"
    )

    scanner.write_trade1_database(
        records,
        output,
    )

    table = pq.read_table(
        output
    )

    reloaded = table.to_pylist()

    assert len(reloaded) == 2

    assert reloaded[0]["date"] == (
        "2026-08-18"
    )

    assert reloaded[1]["date"] == (
        "2026-08-19"
    )

    assert (
        reloaded[0]["entry_found"]
        is True
    )

    assert (
        reloaded[1]["entry_found"]
        is False
    )


def test_summary_counts():
    records = [
        {
            "date": "2026-08-18",
            "entry_found": True,
        },
        {
            "date": "2026-08-19",
            "entry_found": False,
        },
    ]

    summary = scanner.build_summary(
        records
    )

    assert (
        summary["pregoes_analisados"]
        == 2
    )

    assert (
        summary["trade1_count"]
        == 1
    )

    assert (
        summary["sem_trade1_count"]
        == 1
    )

    assert (
        summary["periodo_inicial"]
        == "2026-08-18"
    )

    assert (
        summary["periodo_final"]
        == "2026-08-19"
    )


def test_run_scanner_outputs_files(
    monkeypatch,
    tmp_path,
):
    normalized = (
        tmp_path / "normalized"
    )
    normalized.mkdir()

    touch_parquet(
        normalized,
        "winv26_ticks_20260818_enriched.parquet",
    )

    monkeypatch.setattr(
        scanner,
        "build_trade1_record",
        fake_record,
    )

    database = (
        tmp_path
        / "research"
        / "trade1_database.parquet"
    )

    summary_file = (
        tmp_path
        / "reports"
        / "trade1_database_summary.json"
    )

    scanner.run_scanner(
        normalized_dir=normalized,
        database_path=database,
        summary_path=summary_file,
    )

    assert database.exists()
    assert summary_file.exists()

    data = json.loads(
        summary_file.read_text(
            encoding="utf-8"
        )
    )

    assert (
        data["pregoes_analisados"]
        == 1
    )