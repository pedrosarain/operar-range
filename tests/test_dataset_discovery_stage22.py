from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from operar_range.dataset_discovery import (
    DatasetDiscoveryError,
    discover_dataset,
)


HEADER = (
    "ticker,date,time,trade_number,"
    "price,qty,vol,buy_agent,"
    "sell_agent,trade_type,aft\n"
)


def _csv(
    *,
    ticker: str,
    date: str,
    first_trade: int = 10,
) -> str:
    return (
        HEADER
        + (
            f"{ticker},{date},"
            "10:25:00.000,"
            f"{first_trade},"
            "100000,1,100000,"
            "A,B,T,N\n"
        )
        + (
            f"{ticker},{date},"
            "10:30:00.000,"
            f"{first_trade + 10},"
            "100100,1,100100,"
            "A,B,T,N\n"
        )
    )


def _zip(
    root: Path,
    name: str,
    members: dict[
        str,
        str,
    ],
) -> Path:
    path = (
        root
        / name
    )

    with zipfile.ZipFile(
        path,
        "w",
        compression=(
            zipfile.ZIP_DEFLATED
        ),
    ) as archive:
        for member_name, content in (
            members.items()
        ):
            archive.writestr(
                member_name,
                content,
            )

    return path


def test_market_is_required(
    tmp_path,
):
    path = _zip(
        tmp_path,
        "one.zip",
        {
            "one.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    with pytest.raises(
        DatasetDiscoveryError,
        match="market is required",
    ):
        discover_dataset(
            market="",
            asset="WIN",
            selected_files=[
                path
            ],
        )


def test_asset_is_required(
    tmp_path,
):
    path = _zip(
        tmp_path,
        "one.zip",
        {
            "one.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    with pytest.raises(
        DatasetDiscoveryError,
        match="asset is required",
    ):
        discover_dataset(
            market="B3",
            asset="",
            selected_files=[
                path
            ],
        )


def test_provider_is_optional(
    tmp_path,
):
    path = _zip(
        tmp_path,
        "one.zip",
        {
            "one.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    result = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            path
        ],
    )

    assert (
        result[
            "provider"
        ]
        is None
    )


def test_provider_is_preserved(
    tmp_path,
):
    path = _zip(
        tmp_path,
        "one.zip",
        {
            "one.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    result = discover_dataset(
        market="B3",
        asset="WIN",
        provider="TickData",
        selected_files=[
            path
        ],
    )

    assert (
        result[
            "provider"
        ]
        == "TickData"
    )


def test_declared_asset_must_match_file(
    tmp_path,
):
    path = _zip(
        tmp_path,
        "one.zip",
        {
            "one.csv": _csv(
                ticker="WDO",
                date="2026-01-02",
            )
        },
    )

    with pytest.raises(
        DatasetDiscoveryError,
        match=(
            "Declared asset WIN "
            "does not match discovered "
            "asset WDO"
        ),
    ):
        discover_dataset(
            market="B3",
            asset="WIN",
            selected_files=[
                path
            ],
        )


def test_multiple_source_files_form_one_dataset(
    tmp_path,
):
    first = _zip(
        tmp_path,
        "2025.zip",
        {
            "2025.csv": _csv(
                ticker="WIN",
                date="2025-06-10",
            )
        },
    )

    second = _zip(
        tmp_path,
        "2026.zip",
        {
            "2026.csv": _csv(
                ticker="WIN",
                date="2026-08-18",
            )
        },
    )

    result = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            first,
            second,
        ],
    )

    assert (
        result[
            "files_total"
        ]
        == 2
    )

    assert (
        result[
            "components_total"
        ]
        == 2
    )

    assert len(
        {
            item[
                "dataset_id"
            ]
            for item
            in result[
                "components"
            ]
        }
    ) == 1


def test_selection_order_does_not_change_identity(
    tmp_path,
):
    first = _zip(
        tmp_path,
        "2025.zip",
        {
            "2025.csv": _csv(
                ticker="WIN",
                date="2025-06-10",
            )
        },
    )

    second = _zip(
        tmp_path,
        "2026.zip",
        {
            "2026.csv": _csv(
                ticker="WIN",
                date="2026-08-18",
            )
        },
    )

    left = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            first,
            second,
        ],
    )

    right = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            second,
            first,
        ],
    )

    assert (
        left[
            "dataset_id"
        ]
        == right[
            "dataset_id"
        ]
    )

    assert (
        left[
            "source_sha256"
        ]
        == right[
            "source_sha256"
        ]
    )


def test_aggregate_period_is_correct(
    tmp_path,
):
    first = _zip(
        tmp_path,
        "2025.zip",
        {
            "2025.csv": _csv(
                ticker="WIN",
                date="2025-06-10",
            )
        },
    )

    second = _zip(
        tmp_path,
        "2026.zip",
        {
            "2026.csv": _csv(
                ticker="WIN",
                date="2026-08-18",
            )
        },
    )

    result = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            first,
            second,
        ],
    )

    assert result[
        "period_start"
    ].startswith(
        "2025-06-10"
    )

    assert result[
        "period_end"
    ].startswith(
        "2026-08-18"
    )


def test_aggregate_statistics_are_correct(
    tmp_path,
):
    first = _zip(
        tmp_path,
        "one.zip",
        {
            "one.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    second = _zip(
        tmp_path,
        "two.zip",
        {
            "two.csv": _csv(
                ticker="WIN",
                date="2026-01-05",
            )
        },
    )

    result = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            first,
            second,
        ],
    )

    assert (
        result[
            "records_total"
        ]
        == 4
    )

    assert (
        result[
            "sessions_total"
        ]
        == 2
    )


def test_same_content_is_idempotent(
    tmp_path,
):
    path = _zip(
        tmp_path,
        "one.zip",
        {
            "one.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    first = discover_dataset(
        market="B3",
        asset="WIN",
        provider="TickData",
        selected_files=[
            path
        ],
    )

    second = discover_dataset(
        market="B3",
        asset="WIN",
        provider="TickData",
        selected_files=[
            path
        ],
    )

    assert (
        first[
            "dataset_id"
        ]
        == second[
            "dataset_id"
        ]
    )

    assert (
        first[
            "source_sha256"
        ]
        == second[
            "source_sha256"
        ]
    )


def test_provider_does_not_change_dataset_identity(
    tmp_path,
):
    path = _zip(
        tmp_path,
        "one.zip",
        {
            "one.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    first = discover_dataset(
        market="B3",
        asset="WIN",
        provider="TickData",
        selected_files=[
            path
        ],
    )

    second = discover_dataset(
        market="B3",
        asset="WIN",
        provider="LSEG",
        selected_files=[
            path
        ],
    )

    assert (
        first[
            "dataset_id"
        ]
        == second[
            "dataset_id"
        ]
    )


def test_market_participates_in_identity(
    tmp_path,
):
    path = _zip(
        tmp_path,
        "one.zip",
        {
            "one.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    first = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            path
        ],
    )

    second = discover_dataset(
        market="OTHER",
        asset="WIN",
        selected_files=[
            path
        ],
    )

    assert (
        first[
            "dataset_id"
        ]
        != second[
            "dataset_id"
        ]
    )


def test_asset_participates_in_identity_functionally(
    tmp_path,
):
    win = _zip(
        tmp_path,
        "win.zip",
        {
            "win.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    wdo = _zip(
        tmp_path,
        "wdo.zip",
        {
            "wdo.csv": _csv(
                ticker="WDO",
                date="2026-01-02",
            )
        },
    )

    first = discover_dataset(
        market="B3",
        asset="WIN",
        selected_files=[
            win
        ],
    )

    second = discover_dataset(
        market="B3",
        asset="WDO",
        selected_files=[
            wdo
        ],
    )

    assert (
        first[
            "dataset_id"
        ]
        != second[
            "dataset_id"
        ]
    )


def test_manifest_contains_aggregate_lineage(
    tmp_path,
):
    path = _zip(
        tmp_path,
        "one.zip",
        {
            "one.csv": _csv(
                ticker="WIN",
                date="2026-01-02",
            )
        },
    )

    result = discover_dataset(
        market="B3",
        asset="WIN",
        provider="TickData",
        selected_files=[
            path
        ],
    )

    required = {
        "dataset_id",
        "dataset_version",
        "market",
        "asset",
        "provider",
        "period_start",
        "period_end",
        "files_total",
        "components_total",
        "sessions_total",
        "records_total",
        "source_files",
        "source_sha256",
        "sources",
        "components",
        "discovery_version",
    }

    assert required.issubset(
        result
    )

    assert (
        result[
            "market"
        ]
        == "B3"
    )

    assert (
        result[
            "asset"
        ]
        == "WIN"
    )

    assert (
        result[
            "components"
        ][
            0
        ][
            "dataset_id"
        ]
        == result[
            "dataset_id"
        ]
    )
