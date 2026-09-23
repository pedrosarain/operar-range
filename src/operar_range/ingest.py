from __future__ import annotations

from pathlib import Path
import polars as pl

REQUIRED_TICK_COLUMNS = {"timestamp", "symbol", "price"}


def read_tick_sample(path: str | Path) -> pl.DataFrame:
    """Read a vendor sample and enforce only the minimum raw tick contract.

    Accepted here: CSV or Parquet. Vendor-specific column mapping will be added
    when we receive the first real sample; we do not guess column names now.
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
