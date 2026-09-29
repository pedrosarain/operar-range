from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Any

import polars as pl

from operar_range.dataset_store import (
    DATASET_VERSION,
    dataset_id,
)
from operar_range.ingest import (
    VENDOR_COLUMNS,
    sha256_file,
)


DATASET_DISCOVERY_VERSION = (
    "dataset-discovery-v1"
)


class DatasetDiscoveryError(
    RuntimeError
):
    pass


def _required_text(
    value: str | None,
    *,
    field: str,
) -> str:
    normalized = str(
        value
        or ""
    ).strip()

    if not normalized:
        raise DatasetDiscoveryError(
            "DATASET_DISCOVERY_ERROR: "
            f"{field} is required."
        )

    return normalized


def _scan_vendor_csv(
    path: Path,
) -> pl.LazyFrame:
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


def _validate_vendor_schema(
    lf: pl.LazyFrame,
    *,
    source_name: str,
) -> None:
    schema = lf.collect_schema()

    columns = set(
        schema.names()
    )

    missing = (
        set(
            VENDOR_COLUMNS
        )
        - columns
    )

    if missing:
        raise DatasetDiscoveryError(
            "DATASET_DISCOVERY_ERROR: "
            f"{source_name} is missing "
            "required vendor columns: "
            f"{sorted(missing)}"
        )


def _with_timestamp(
    lf: pl.LazyFrame,
) -> pl.LazyFrame:
    return lf.with_columns(
        pl.concat_str(
            [
                pl.col(
                    "date"
                ),
                pl.lit(
                    " "
                ),
                pl.col(
                    "time"
                ),
            ]
        )
        .str.strptime(
            pl.Datetime(
                time_unit="ms"
            ),
            format=(
                "%Y-%m-%d "
                "%H:%M:%S%.3f"
            ),
            strict=True,
        )
        .dt.replace_time_zone(
            "America/Sao_Paulo"
        )
        .alias(
            "timestamp"
        )
    )


def _discover_csv(
    *,
    csv_path: Path,
    source_zip: str,
    declared_asset: str,
) -> dict[str, Any]:
    lf = _scan_vendor_csv(
        csv_path
    )

    _validate_vendor_schema(
        lf,
        source_name=(
            csv_path.name
        ),
    )

    normalized = (
        _with_timestamp(
            lf
        )
    )

    summary = (
        normalized
        .select(
            pl.len().alias(
                "row_count"
            ),
            pl.col(
                "ticker"
            )
            .drop_nulls()
            .n_unique()
            .alias(
                "ticker_count"
            ),
            pl.col(
                "timestamp"
            )
            .min()
            .alias(
                "timestamp_min"
            ),
            pl.col(
                "timestamp"
            )
            .max()
            .alias(
                "timestamp_max"
            ),
        )
        .collect(
            engine="streaming"
        )
        .row(
            0,
            named=True,
        )
    )

    tickers = (
        normalized
        .select(
            pl.col(
                "ticker"
            )
            .drop_nulls()
            .unique()
            .sort()
        )
        .collect(
            engine="streaming"
        )[
            "ticker"
        ]
        .to_list()
    )

    tickers = [
        str(
            value
        ).strip()
        for value in tickers
        if value is not None
        and str(
            value
        ).strip()
    ]

    if len(
        tickers
    ) != 1:
        raise DatasetDiscoveryError(
            "DATASET_DISCOVERY_ERROR: "
            f"{csv_path.name} must contain "
            "exactly one ticker. "
            f"Discovered: {tickers}"
        )

    discovered_asset = (
        tickers[
            0
        ]
    )

    if (
        discovered_asset
        != declared_asset
    ):
        raise DatasetDiscoveryError(
            "DATASET_DISCOVERY_ERROR: "
            f"Declared asset "
            f"{declared_asset} does not "
            f"match discovered asset "
            f"{discovered_asset} in "
            f"{csv_path.name}."
        )

    dates = (
        normalized
        .select(
            pl.col(
                "date"
            )
            .drop_nulls()
            .unique()
            .sort()
        )
        .collect(
            engine="streaming"
        )[
            "date"
        ]
        .to_list()
    )

    dates = [
        str(
            value
        )
        for value in dates
        if value is not None
    ]

    timestamp_min = (
        summary[
            "timestamp_min"
        ]
    )

    timestamp_max = (
        summary[
            "timestamp_max"
        ]
    )

    if (
        timestamp_min is None
        or timestamp_max is None
    ):
        raise DatasetDiscoveryError(
            "DATASET_DISCOVERY_ERROR: "
            f"{csv_path.name} contains "
            "no valid timestamps."
        )

    return {
        "source_zip": (
            source_zip
        ),
        "source_csv": (
            csv_path.name
        ),
        "ticker": (
            discovered_asset
        ),
        "row_count": int(
            summary[
                "row_count"
            ]
        ),
        "date_count": len(
            dates
        ),
        "dates": dates,
        "timestamp_min": str(
            timestamp_min
        ),
        "timestamp_max": str(
            timestamp_max
        ),
    }


def discover_dataset(
    *,
    market: str,
    asset: str,
    selected_files: list[
        str | Path
    ],
    provider: str | None = None,
    dataset_version: int = (
        DATASET_VERSION
    ),
) -> dict[str, Any]:
    market = _required_text(
        market,
        field="market",
    )

    asset = _required_text(
        asset,
        field="asset",
    )

    provider_value = (
        str(
            provider
        ).strip()
        if provider is not None
        and str(
            provider
        ).strip()
        else None
    )

    if not selected_files:
        raise DatasetDiscoveryError(
            "DATASET_DISCOVERY_ERROR: "
            "at least one source file "
            "is required."
        )

    paths = [
        Path(
            value
        )
        for value in selected_files
    ]

    #
    # A ordem fornecida pelo pesquisador
    # não participa da identidade.
    #
    paths = sorted(
        paths,
        key=lambda path: (
            path.name,
            str(
                path
            ),
        ),
    )

    source_records = []
    component_records = []
    source_hashes = []

    all_dates: set[
        str
    ] = set()

    period_starts = []
    period_ends = []

    records_total = 0

    for path in paths:
        if not path.exists():
            raise DatasetDiscoveryError(
                "DATASET_DISCOVERY_ERROR: "
                "source file not found: "
                f"{path}"
            )

        if (
            path.suffix.lower()
            != ".zip"
        ):
            raise DatasetDiscoveryError(
                "DATASET_DISCOVERY_ERROR: "
                f"unsupported source format: "
                f"{path.name}"
            )

        source_hash = (
            sha256_file(
                path
            )
        )

        source_hashes.append(
            source_hash
        )

        zip_components = []

        try:
            archive = zipfile.ZipFile(
                path,
                "r",
            )
        except zipfile.BadZipFile as exc:
            raise DatasetDiscoveryError(
                "DATASET_DISCOVERY_ERROR: "
                f"invalid ZIP file: "
                f"{path.name}"
            ) from exc

        with archive:
            members = sorted(
                [
                    member
                    for member
                    in archive.namelist()
                    if (
                        member.lower()
                        .endswith(
                            ".csv"
                        )
                        and not member.endswith(
                            "/"
                        )
                    )
                ]
            )

            if not members:
                raise DatasetDiscoveryError(
                    "DATASET_DISCOVERY_ERROR: "
                    f"{path.name} contains "
                    "no CSV files."
                )

            with tempfile.TemporaryDirectory() as (
                temp_dir
            ):
                temp_root = Path(
                    temp_dir
                )

                for index, member in enumerate(
                    members,
                    start=1,
                ):
                    original_name = (
                        Path(
                            member
                        ).name
                    )

                    temp_csv = (
                        temp_root
                        / (
                            f"{index:06d}_"
                            + original_name
                        )
                    )

                    with archive.open(
                        member
                    ) as source:
                        with temp_csv.open(
                            "wb"
                        ) as target:
                            while True:
                                chunk = (
                                    source.read(
                                        1024
                                        * 1024
                                    )
                                )

                                if not chunk:
                                    break

                                target.write(
                                    chunk
                                )

                    component = (
                        _discover_csv(
                            csv_path=(
                                temp_csv
                            ),
                            source_zip=(
                                path.name
                            ),
                            declared_asset=(
                                asset
                            ),
                        )
                    )

                    component[
                        "source_csv"
                    ] = original_name

                    zip_components.append(
                        component
                    )

                    component_records.append(
                        component
                    )

                    records_total += int(
                        component[
                            "row_count"
                        ]
                    )

                    all_dates.update(
                        component[
                            "dates"
                        ]
                    )

                    period_starts.append(
                        component[
                            "timestamp_min"
                        ]
                    )

                    period_ends.append(
                        component[
                            "timestamp_max"
                        ]
                    )

        source_records.append(
            {
                "name": (
                    path.name
                ),
                "source_sha256": (
                    source_hash
                ),
                "components_total": (
                    len(
                        zip_components
                    )
                ),
                "records_total": sum(
                    int(
                        item[
                            "row_count"
                        ]
                    )
                    for item
                    in zip_components
                ),
                "sessions": sorted(
                    {
                        date
                        for item
                        in zip_components
                        for date
                        in item[
                            "dates"
                        ]
                    }
                ),
            }
        )

    if not component_records:
        raise DatasetDiscoveryError(
            "DATASET_DISCOVERY_ERROR: "
            "no valid source components "
            "were discovered."
        )

    period_start = min(
        period_starts
    )

    period_end = max(
        period_ends
    )

    normalized_hashes = sorted(
        set(
            source_hashes
        )
    )

    identifier = dataset_id(
        market=market,
        asset=asset,
        source_sha256=(
            normalized_hashes
        ),
        period_start=(
            period_start
        ),
        period_end=(
            period_end
        ),
        dataset_version=(
            dataset_version
        ),
    )

    #
    # Os registros dos arquivos individuais
    # já apontam para o Dataset agregado.
    #
    for source in source_records:
        source[
            "dataset_id"
        ] = identifier

    for component in component_records:
        component[
            "dataset_id"
        ] = identifier

    manifest = {
        "dataset_id": (
            identifier
        ),
        "dataset_version": int(
            dataset_version
        ),
        "market": market,
        "asset": asset,
        "provider": (
            provider_value
        ),
        "period_start": (
            period_start
        ),
        "period_end": (
            period_end
        ),
        "files_total": len(
            source_records
        ),
        "components_total": len(
            component_records
        ),
        "sessions_total": len(
            all_dates
        ),
        "records_total": int(
            records_total
        ),
        "source_files": [
            source[
                "name"
            ]
            for source in (
                source_records
            )
        ],
        "source_sha256": (
            normalized_hashes
        ),
        "sources": (
            source_records
        ),
        "components": (
            component_records
        ),
        "discovery_version": (
            DATASET_DISCOVERY_VERSION
        ),
    }

    return manifest
