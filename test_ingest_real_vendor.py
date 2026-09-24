import json
import zipfile
from pathlib import Path

import polars as pl

from operar_range.ingest import import_tick_zip


CSV_CONTENT = """ticker,date,time,trade_number,price,qty,vol,buy_agent,sell_agent,trade_type,aft
WINV26,2026-08-18,09:02:56.413,10,169640.0,1400,47499200.0,XP,XP,Auction,n
WINV26,2026-08-18,09:02:56.413,20,169640.0,500,16964000.0,XP,XP,Auction,n
WINV26,2026-08-18,09:02:56.414,40,169645.0,100,16964500.0,BTG,XP,Trade,n
"""


def make_test_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "sample.zip"

    with zipfile.ZipFile(
        zip_path,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "winv26_ticks_20260818_enriched.csv",
            CSV_CONTENT,
        )

    return zip_path


def test_import_preserves_original_columns(tmp_path):
    zip_path = make_test_zip(tmp_path)

    import_tick_zip(
        zip_path,
        data_root=tmp_path / "data",
    )

    parquet = (
        tmp_path
        / "data"
        / "normalized"
        / "winv26_ticks_20260818_enriched.parquet"
    )

    df = pl.read_parquet(parquet)

    original_columns = {
        "ticker",
        "date",
        "time",
        "trade_number",
        "price",
        "qty",
        "vol",
        "buy_agent",
        "sell_agent",
        "trade_type",
        "aft",
    }

    assert original_columns.issubset(set(df.columns))
    assert "timestamp" in df.columns
    assert df.height == 3


def test_timestamp_has_milliseconds_and_timezone(tmp_path):
    zip_path = make_test_zip(tmp_path)

    import_tick_zip(
        zip_path,
        data_root=tmp_path / "data",
    )

    parquet = (
        tmp_path
        / "data"
        / "normalized"
        / "winv26_ticks_20260818_enriched.parquet"
    )

    df = pl.read_parquet(parquet)

    assert df["timestamp"][0].microsecond == 413000
    assert "America/Sao_Paulo" in str(
        df.schema["timestamp"]
    )


def test_trade_number_gap_is_reported(tmp_path):
    zip_path = make_test_zip(tmp_path)

    reports = import_tick_zip(
        zip_path,
        data_root=tmp_path / "data",
    )

    report = reports[0]

    assert report["expected_trade_step"] == 10
    assert report["trade_gap_events"] == 1
    assert report["estimated_missing_trade_numbers"] == 1


def test_raw_files_are_preserved(tmp_path):
    zip_path = make_test_zip(tmp_path)

    import_tick_zip(
        zip_path,
        data_root=tmp_path / "data",
    )

    assert (
        tmp_path
        / "data"
        / "raw"
        / "zip"
        / "sample.zip"
    ).exists()

    assert (
        tmp_path
        / "data"
        / "raw"
        / "csv"
        / "winv26_ticks_20260818_enriched.csv"
    ).exists()


def test_quality_report_is_created(tmp_path):
    zip_path = make_test_zip(tmp_path)

    import_tick_zip(
        zip_path,
        data_root=tmp_path / "data",
    )

    report_path = (
        tmp_path
        / "data"
        / "reports"
        / "winv26_ticks_20260818_enriched.quality.json"
    )

    assert report_path.exists()

    report = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    assert report["row_count"] == 3
    assert report["original_columns_preserved"] is True
    assert report["is_sorted_by_timestamp_trade_number"] is True