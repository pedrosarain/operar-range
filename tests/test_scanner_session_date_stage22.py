from __future__ import annotations

from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from operar_range.scanner import (
    _extract_session_date,
)


def _write_dates(
    path: Path,
    dates: list[str],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "date": value,
                    "timestamp": None,
                    "trade_number": index,
                    "price": 1000.0,
                    "qty": 1,
                }
                for index, value
                in enumerate(
                    dates,
                    start=1,
                )
            ]
        ),
        path,
    )


def test_stage22_session_date_comes_from_parquet_content(
    tmp_path,
):
    path = (
        tmp_path
        / (
            "winv26_ticks_20260818_"
            "enriched_1790282243650__"
            "000002__"
            "winv26_ticks_20260819_"
            "enriched.parquet"
        )
    )

    _write_dates(
        path,
        [
            "2026-08-19",
            "2026-08-19",
        ],
    )

    assert (
        _extract_session_date(
            path
        )
        == date(
            2026,
            8,
            19,
        )
    )


def test_stage22_first_component_resolves_its_real_date(
    tmp_path,
):
    path = (
        tmp_path
        / (
            "winv26_ticks_20260818_"
            "enriched_1790282243650__"
            "000001__"
            "winv26_ticks_20260818_"
            "enriched.parquet"
        )
    )

    _write_dates(
        path,
        [
            "2026-08-18",
        ],
    )

    assert (
        _extract_session_date(
            path
        )
        == date(
            2026,
            8,
            18,
        )
    )


def test_multiple_session_dates_are_rejected(
    tmp_path,
):
    path = (
        tmp_path
        / "multi_20260818.parquet"
    )

    _write_dates(
        path,
        [
            "2026-08-18",
            "2026-08-19",
        ],
    )

    with pytest.raises(
        ValueError,
        match=(
            "multiple session dates"
        ),
    ):
        _extract_session_date(
            path
        )


def test_legacy_filename_fallback_remains_available(
    tmp_path,
):
    path = (
        tmp_path
        / (
            "winv26_ticks_"
            "20260818_enriched.parquet"
        )
    )

    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "timestamp": None,
                    "trade_number": 1,
                    "price": 1000.0,
                    "qty": 1,
                }
            ]
        ),
        path,
    )

    assert (
        _extract_session_date(
            path
        )
        == date(
            2026,
            8,
            18,
        )
    )
