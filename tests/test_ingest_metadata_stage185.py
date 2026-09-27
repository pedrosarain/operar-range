from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime
from pathlib import Path

import polars as pl

from operar_range import ingest


VENDOR_HEADER = (
    "ticker,date,time,trade_number,price,qty,vol,"
    "buy_agent,sell_agent,trade_type,aft\n"
)


def _vendor_csv_text() -> str:
    return (
        VENDOR_HEADER
        + (
            "WINV26,2026-08-18,09:00:00.000,"
            "10,170000,1,170000,A,B,TRADE,N\n"
        )
        + (
            "WINV26,2026-08-18,09:00:00.100,"
            "20,170005,2,340010,A,B,TRADE,N\n"
        )
        + (
            "WINV26,2026-08-18,09:00:00.200,"
            "30,170010,1,170010,A,B,TRADE,N\n"
        )
    )


def _create_vendor_zip(
    root: Path,
    *,
    zip_name: str = "sample.zip",
) -> Path:
    csv_name = "winv26_sample.csv"

    source_csv = (
        root
        / csv_name
    )

    source_csv.write_text(
        _vendor_csv_text(),
        encoding="utf-8",
    )

    zip_path = (
        root
        / zip_name
    )

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.write(
            source_csv,
            arcname=csv_name,
        )

    source_csv.unlink()

    return zip_path


def test_ingest_versions_are_formalized():
    assert (
        ingest.INGEST_VERSION
        == "ingest-v1"
    )

    assert (
        ingest.NORMALIZATION_VERSION
        == "vendor-normalization-v1"
    )

    assert (
        ingest.DATASET_VERSION
        == 1
    )


def test_new_import_persists_lineage_metadata(
    tmp_path,
):
    zip_path = (
        _create_vendor_zip(
            tmp_path
        )
    )

    data_root = (
        tmp_path
        / "data"
    )

    reports = (
        ingest.import_tick_zip(
            zip_path,
            data_root=data_root,
        )
    )

    assert len(reports) == 1

    report = reports[0]

    assert (
        report[
            "dataset_version"
        ]
        == 1
    )

    assert (
        report[
            "ingest_version"
        ]
        == "ingest-v1"
    )

    assert (
        report[
            "normalization_version"
        ]
        == "vendor-normalization-v1"
    )

    assert (
        report[
            "imported_at_status"
        ]
        == "RECORDED"
    )

    assert (
        report[
            "imported_at"
        ]
        is not None
    )

    parsed = datetime.fromisoformat(
        report[
            "imported_at"
        ]
    )

    assert (
        parsed.tzinfo
        is not None
    )

    assert (
        parsed.utcoffset()
        is not None
    )

    assert (
        report[
            "dataset_id"
        ].startswith(
            "DS-"
        )
    )

    assert (
        report[
            "source_sha256"
        ]
        == report[
            "zip_sha256"
        ]
    )

    report_path = (
        data_root
        / "reports"
        / "winv26_sample.quality.json"
    )

    persisted = json.loads(
        report_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        persisted[
            "dataset_id"
        ]
        == report[
            "dataset_id"
        ]
    )

    assert (
        persisted[
            "imported_at"
        ]
        == report[
            "imported_at"
        ]
    )

    assert (
        persisted[
            "normalization_version"
        ]
        == "vendor-normalization-v1"
    )


def test_dataset_id_is_deterministic_for_same_content(
    tmp_path,
):
    first_root = (
        tmp_path
        / "first"
    )

    second_root = (
        tmp_path
        / "second"
    )

    first_root.mkdir()
    second_root.mkdir()

    first_zip = (
        _create_vendor_zip(
            first_root,
            zip_name="same.zip",
        )
    )

    second_zip = (
        _create_vendor_zip(
            second_root,
            zip_name="same.zip",
        )
    )

    first = (
        ingest.import_tick_zip(
            first_zip,
            data_root=(
                first_root
                / "data"
            ),
        )[0]
    )

    second = (
        ingest.import_tick_zip(
            second_zip,
            data_root=(
                second_root
                / "data"
            ),
        )[0]
    )

    assert (
        first[
            "zip_sha256"
        ]
        == second[
            "zip_sha256"
        ]
    )

    assert (
        first[
            "dataset_id"
        ]
        == second[
            "dataset_id"
        ]
    )


def test_source_hash_is_preserved(
    tmp_path,
):
    zip_path = (
        _create_vendor_zip(
            tmp_path
        )
    )

    expected_hash = (
        ingest.sha256_file(
            zip_path
        )
    )

    report = (
        ingest.import_tick_zip(
            zip_path,
            data_root=(
                tmp_path
                / "data"
            ),
        )[0]
    )

    assert (
        report[
            "source_sha256"
        ]
        == expected_hash
    )

    assert (
        report[
            "zip_sha256"
        ]
        == expected_hash
    )


def test_normalized_quantitative_content_is_unchanged(
    tmp_path,
):
    zip_path = (
        _create_vendor_zip(
            tmp_path
        )
    )

    data_root = (
        tmp_path
        / "data"
    )

    ingest.import_tick_zip(
        zip_path,
        data_root=data_root,
    )

    parquet_path = (
        data_root
        / "normalized"
        / "winv26_sample.parquet"
    )

    dataframe = (
        pl.read_parquet(
            parquet_path
        )
    )

    assert dataframe.height == 3

    assert (
        dataframe[
            "trade_number"
        ].to_list()
        == [
            10,
            20,
            30,
        ]
    )

    assert (
        dataframe[
            "price"
        ].to_list()
        == [
            170000.0,
            170005.0,
            170010.0,
        ]
    )

    assert (
        dataframe[
            "qty"
        ].to_list()
        == [
            1,
            2,
            1,
        ]
    )

    assert (
        dataframe[
            "ticker"
        ].to_list()
        == [
            "WINV26",
            "WINV26",
            "WINV26",
        ]
    )


def test_imported_at_is_not_filesystem_mtime(
    tmp_path,
):
    zip_path = (
        _create_vendor_zip(
            tmp_path
        )
    )

    old_timestamp = 946684800

    os.utime(
        zip_path,
        (
            old_timestamp,
            old_timestamp,
        ),
    )

    report = (
        ingest.import_tick_zip(
            zip_path,
            data_root=(
                tmp_path
                / "data"
            ),
        )[0]
    )

    imported_at = (
        datetime.fromisoformat(
            report[
                "imported_at"
            ]
        )
    )

    filesystem_time = (
        datetime.fromtimestamp(
            old_timestamp,
            tz=(
                imported_at.tzinfo
            ),
        )
    )

    assert (
        imported_at
        != filesystem_time
    )


def test_fixed_imported_at_is_persisted_exactly(
    tmp_path,
):
    raw_csv = (
        tmp_path
        / "sample.csv"
    )

    raw_csv.write_text(
        _vendor_csv_text(),
        encoding="utf-8",
    )

    raw_zip = (
        tmp_path
        / "sample.zip"
    )

    with zipfile.ZipFile(
        raw_zip,
        "w",
    ) as archive:
        archive.write(
            raw_csv,
            arcname=(
                raw_csv.name
            ),
        )

    output = (
        tmp_path
        / "sample.parquet"
    )

    report_path = (
        tmp_path
        / "sample.quality.json"
    )

    fixed = (
        "2026-09-27T18:00:00+00:00"
    )

    report = (
        ingest.normalize_vendor_csv(
            raw_csv=raw_csv,
            output_parquet=output,
            report_path=report_path,
            raw_zip=raw_zip,
            imported_at=fixed,
        )
    )

    assert (
        report[
            "imported_at"
        ]
        == fixed
    )

    persisted = json.loads(
        report_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        persisted[
            "imported_at"
        ]
        == fixed
    )
