from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq


TRAJECTORY_SCHEMA = pa.schema(
    [
        (
            "timestamp",
            pa.timestamp(
                "us",
                tz="America/Sao_Paulo",
            ),
        ),
        ("trade_number", pa.int64()),
        ("price", pa.float64()),
        ("points_from_entry", pa.float64()),
        ("favorable_excursion", pa.float64()),
        ("adverse_excursion", pa.float64()),
    ]
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _trajectory_to_table(
    trajectory: list[dict[str, Any]],
) -> pa.Table:
    timezone = ZoneInfo("America/Sao_Paulo")

    timestamps = [
        datetime.fromisoformat(
            row["timestamp"]
        ).astimezone(timezone)
        for row in trajectory
    ]

    return pa.Table.from_arrays(
        [
            pa.array(
                timestamps,
                type=TRAJECTORY_SCHEMA.field(
                    "timestamp"
                ).type,
            ),
            pa.array(
                [
                    int(row["trade_number"])
                    for row in trajectory
                ],
                type=pa.int64(),
            ),
            pa.array(
                [
                    float(row["price"])
                    for row in trajectory
                ],
                type=pa.float64(),
            ),
            pa.array(
                [
                    float(
                        row["points_from_entry"]
                    )
                    for row in trajectory
                ],
                type=pa.float64(),
            ),
            pa.array(
                [
                    float(
                        row[
                            "favorable_excursion"
                        ]
                    )
                    for row in trajectory
                ],
                type=pa.float64(),
            ),
            pa.array(
                [
                    float(
                        row[
                            "adverse_excursion"
                        ]
                    )
                    for row in trajectory
                ],
                type=pa.float64(),
            ),
        ],
        schema=TRAJECTORY_SCHEMA,
    )


def write_trajectory_parquet(
    trajectory: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = _trajectory_to_table(
        trajectory
    )

    pq.write_table(
        table,
        output_path,
        compression="zstd",
    )

    return output_path


def read_trajectory_parquet(
    parquet_path: str | Path,
) -> list[dict[str, Any]]:
    parquet_path = Path(parquet_path)

    table = pq.read_table(
        parquet_path
    )

    rows = table.to_pylist()

    return [
        {
            "timestamp": (
                row["timestamp"].isoformat()
            ),
            "trade_number": int(
                row["trade_number"]
            ),
            "price": float(
                row["price"]
            ),
            "points_from_entry": float(
                row["points_from_entry"]
            ),
            "favorable_excursion": float(
                row["favorable_excursion"]
            ),
            "adverse_excursion": float(
                row["adverse_excursion"]
            ),
        }
        for row in rows
    ]


def write_trajectory_metadata(
    report: dict[str, Any],
    trajectory_path: str | Path,
    metadata_path: str | Path,
) -> dict[str, Any]:
    trajectory_path = Path(
        trajectory_path
    )
    metadata_path = Path(
        metadata_path
    )

    trajectory = report["trajectory"]

    metadata = {
        "date": report["date"],
        "direction": report["direction"],
        "entry_price": (
            report["entry_trigger_level"]
        ),
        "row_count": len(trajectory),
        "first_timestamp": (
            trajectory[0]["timestamp"]
            if trajectory
            else None
        ),
        "last_timestamp": (
            trajectory[-1]["timestamp"]
            if trajectory
            else None
        ),
        "mfe": report["mfe_points"],
        "mae": report["mae_points"],
        "file_size_bytes": (
            trajectory_path.stat().st_size
        ),
        "sha256": _sha256(
            trajectory_path
        ),
        "trajectory_file": (
            str(trajectory_path)
        ),
    }

    metadata_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return metadata