from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import polars as pl


REQUIRED_TICK_COLUMNS = {"timestamp", "symbol", "price"}

VENDOR_COLUMNS = [
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
]


def read_tick_sample(path: str | Path) -> pl.DataFrame:
    """Read a canonical CSV or Parquet sample.

    Kept for compatibility with the initial project/tests.
    """
    path = Path(path)

    if path.suffix.lower() == ".parquet":
        df = pl.read_parquet(path)

    elif path.suffix.lower() in {".csv", ".txt"}:
        df = pl.read_csv(path, try_parse_dates=True)

    else:
        raise ValueError(f"Unsupported sample format: {path.suffix}")

    missing = REQUIRED_TICK_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(
            "Sample still needs a vendor-specific mapping. Missing canonical "
            f"columns: {sorted(missing)}; received: {df.columns}"
        )

    return df


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """Calculate SHA-256 without loading the whole file into memory."""
    path = Path(path)

    digest = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)

    return digest.hexdigest()


def _copy_raw_file_without_overwrite(source: Path, destination: Path) -> None:
    """Preserve RAW data and never silently overwrite it."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        source_hash = sha256_file(source)
        destination_hash = sha256_file(destination)

        if source_hash != destination_hash:
            raise FileExistsError(
                f"RAW file already exists with different content: {destination}"
            )

        return

    shutil.copy2(source, destination)


def _extract_raw_csv(
    archive: zipfile.ZipFile,
    member_name: str,
    destination: Path,
) -> None:
    """Extract a CSV while protecting an existing RAW copy."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        return

    with archive.open(member_name) as source:
        with destination.open("wb") as target:
            shutil.copyfileobj(source, target)


def _scan_vendor_csv(path: Path) -> pl.LazyFrame:
    """Create a lazy scan over the vendor CSV.

    The file is not loaded completely into RAM.
    """
    return pl.scan_csv(
        path,
        schema_overrides={
            "ticker": pl.String,
            "date": pl.String,
            "time": pl.String,
            "trade_number": pl.Int64,
            "price": pl.Float64,
            "qty": pl.Int64,
            "vol": pl.Float64,
            "buy_agent": pl.String,
            "sell_agent": pl.String,
            "trade_type": pl.String,
            "aft": pl.String,
        },
        try_parse_dates=False,
    )


def _validate_vendor_columns(lf: pl.LazyFrame) -> None:
    schema = lf.collect_schema()
    columns = set(schema.names())

    missing = set(VENDOR_COLUMNS) - columns

    if missing:
        raise ValueError(
            "Vendor file is missing required original columns: "
            f"{sorted(missing)}"
        )


def _normalized_lazyframe(raw_csv: Path) -> pl.LazyFrame:
    lf = _scan_vendor_csv(raw_csv)

    _validate_vendor_columns(lf)

    # We preserve every original vendor column.
    # timestamp is added; date/time are not removed.
    return lf.with_columns(
        pl.concat_str(
            [
                pl.col("date"),
                pl.lit(" "),
                pl.col("time"),
            ]
        )
        .str.strptime(
            pl.Datetime(time_unit="ms"),
            format="%Y-%m-%d %H:%M:%S%.3f",
            strict=True,
        )
        .dt.replace_time_zone("America/Sao_Paulo")
        .alias("timestamp")
    )


def _infer_trade_number_step(lf: pl.LazyFrame) -> int | None:
    """Infer the base increment of trade_number deterministically.

    Uses the GCD of all positive differences. This correctly identifies
    the vendor base sequence even when the file contains gaps.

    Example:
    10, 20, 40 -> diffs 10, 20 -> base step 10.
    """
    from math import gcd

    result = (
        lf.select(
            pl.col("trade_number")
            .diff()
            .alias("trade_step")
        )
        .filter(pl.col("trade_step") > 0)
        .select(
            pl.col("trade_step")
            .unique()
            .alias("trade_step")
        )
        .collect(engine="streaming")
    )

    if result.height == 0:
        return None

    steps = [
        int(value)
        for value in result["trade_step"].to_list()
    ]

    base_step = steps[0]

    for step in steps[1:]:
        base_step = gcd(base_step, step)

    return base_step


def _build_quality_report(
    normalized_parquet: Path,
    raw_csv: Path,
    raw_zip: Path,
) -> dict:
    lf = pl.scan_parquet(normalized_parquet)

    schema = lf.collect_schema()
    columns = schema.names()

    summary = (
        lf.select(
            pl.len().alias("row_count"),
            pl.col("ticker").n_unique().alias("ticker_count"),
            pl.col("date").n_unique().alias("date_count"),
            pl.col("timestamp").min().alias("timestamp_min"),
            pl.col("timestamp").max().alias("timestamp_max"),
            pl.col("trade_number").min().alias("trade_number_min"),
            pl.col("trade_number").max().alias("trade_number_max"),
        )
        .collect(engine="streaming")
        .row(0, named=True)
    )

    expected_step = _infer_trade_number_step(lf)

    ordered_check = (
        lf.select(
            (
                (pl.col("timestamp") < pl.col("timestamp").shift(1))
                | (
                    (pl.col("timestamp") == pl.col("timestamp").shift(1))
                    & (
                        pl.col("trade_number")
                        < pl.col("trade_number").shift(1)
                    )
                )
            )
            .fill_null(False)
            .sum()
            .alias("out_of_order_rows")
        )
        .collect(engine="streaming")
        .item()
    )

    duplicates = (
        lf.select(
            pl.struct(["timestamp", "trade_number"])
            .is_duplicated()
            .sum()
            .alias("duplicate_timestamp_trade_number")
        )
        .collect(engine="streaming")
        .item()
    )

    null_counts_row = (
        lf.select(
            [
                pl.col(column).null_count().alias(column)
                for column in columns
            ]
        )
        .collect(engine="streaming")
        .row(0, named=True)
    )

    trade_gap_events = 0
    estimated_missing_trade_numbers = 0
    irregular_trade_jumps = 0

    if expected_step is not None:
        gaps = (
            lf.with_columns(
                pl.col("trade_number").diff().alias("_trade_diff")
            )
            .select(
                (
                    (pl.col("_trade_diff") > expected_step)
                    & (
                        pl.col("_trade_diff") % expected_step
                        == 0
                    )
                )
                .sum()
                .alias("trade_gap_events"),
                (
                    pl.when(
                        (pl.col("_trade_diff") > expected_step)
                        & (
                            pl.col("_trade_diff") % expected_step
                            == 0
                        )
                    )
                    .then(
                        (pl.col("_trade_diff") // expected_step) - 1
                    )
                    .otherwise(0)
                )
                .sum()
                .alias("estimated_missing_trade_numbers"),
                (
                    (pl.col("_trade_diff").is_not_null())
                    & (pl.col("_trade_diff") != expected_step)
                    & (pl.col("_trade_diff") > 0)
                    & (
                        pl.col("_trade_diff") % expected_step
                        != 0
                    )
                )
                .sum()
                .alias("irregular_trade_jumps"),
            )
            .collect(engine="streaming")
            .row(0, named=True)
        )

        trade_gap_events = int(gaps["trade_gap_events"])
        estimated_missing_trade_numbers = int(
            gaps["estimated_missing_trade_numbers"]
        )
        irregular_trade_jumps = int(
            gaps["irregular_trade_jumps"]
        )

    report = {
        "source_zip": raw_zip.name,
        "source_csv": raw_csv.name,
        "zip_sha256": sha256_file(raw_zip),
        "csv_sha256": sha256_file(raw_csv),
        "row_count": int(summary["row_count"]),
        "ticker_count": int(summary["ticker_count"]),
        "date_count": int(summary["date_count"]),
        "timestamp_min": str(summary["timestamp_min"]),
        "timestamp_max": str(summary["timestamp_max"]),
        "trade_number_min": int(summary["trade_number_min"]),
        "trade_number_max": int(summary["trade_number_max"]),
        "expected_trade_step": expected_step,
        "trade_gap_events": trade_gap_events,
        "estimated_missing_trade_numbers": (
            estimated_missing_trade_numbers
        ),
        "irregular_trade_jumps": irregular_trade_jumps,
        "duplicate_timestamp_trade_number": int(duplicates),
        "out_of_order_rows": int(ordered_check),
        "is_sorted_by_timestamp_trade_number": (
            int(ordered_check) == 0
        ),
        "null_counts": {
            key: int(value)
            for key, value in null_counts_row.items()
        },
        "original_columns_preserved": all(
            column in columns
            for column in VENDOR_COLUMNS
        ),
        "normalized_columns": columns,
    }

    return report


def normalize_vendor_csv(
    raw_csv: str | Path,
    output_parquet: str | Path,
    report_path: str | Path,
    raw_zip: str | Path,
) -> dict:
    """Normalize one RAW vendor CSV into Parquet."""
    raw_csv = Path(raw_csv)
    output_parquet = Path(output_parquet)
    report_path = Path(report_path)
    raw_zip = Path(raw_zip)

    output_parquet.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lf = _normalized_lazyframe(raw_csv)

    # Streaming/lazy write. The whole CSV is not materialized
    # as a Pandas or Polars DataFrame in memory.
    lf.sink_parquet(
        output_parquet,
        compression="zstd",
    )

    report = _build_quality_report(
        normalized_parquet=output_parquet,
        raw_csv=raw_csv,
        raw_zip=raw_zip,
    )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return report


def import_tick_zip(
    zip_path: str | Path,
    data_root: str | Path = "data",
) -> list[dict]:
    """Import every CSV pregão contained in a vendor ZIP.

    RAW ZIP and CSV files are preserved.
    Each CSV generates one normalized Parquet and one quality report.
    """
    zip_path = Path(zip_path)
    data_root = Path(data_root)

    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    if zip_path.suffix.lower() != ".zip":
        raise ValueError(
            f"Expected a ZIP file, received: {zip_path}"
        )

    raw_zip_dir = data_root / "raw" / "zip"
    raw_csv_dir = data_root / "raw" / "csv"
    normalized_dir = data_root / "normalized"
    reports_dir = data_root / "reports"

    preserved_zip = raw_zip_dir / zip_path.name

    _copy_raw_file_without_overwrite(
        zip_path,
        preserved_zip,
    )

    results: list[dict] = []

    with zipfile.ZipFile(preserved_zip, "r") as archive:
        members = [
            name
            for name in archive.namelist()
            if name.lower().endswith(".csv")
            and not name.endswith("/")
        ]

        if not members:
            raise ValueError(
                f"No CSV files found inside {preserved_zip}"
            )

        for member in members:
            csv_name = Path(member).name
            raw_csv = raw_csv_dir / csv_name

            _extract_raw_csv(
                archive,
                member,
                raw_csv,
            )

            stem = Path(csv_name).stem

            parquet_path = (
                normalized_dir / f"{stem}.parquet"
            )

            report_path = (
                reports_dir / f"{stem}.quality.json"
            )

            report = normalize_vendor_csv(
                raw_csv=raw_csv,
                output_parquet=parquet_path,
                report_path=report_path,
                raw_zip=preserved_zip,
            )

            results.append(report)

    return results