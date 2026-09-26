from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.scanner import (
    MOTOR_VERSION,
    _extract_session_date,
    discover_normalized_parquets,
)
from operar_range.trade1 import reconstruct_trade1
from operar_range.trajectory import (
    read_trajectory_parquet,
    write_trajectory_parquet,
)


MANIFEST_SCHEMA = pa.schema(
    [
        ("date", pa.string()),
        ("source_parquet", pa.string()),
        ("trade1_status", pa.string()),
        ("direction", pa.string()),
        ("entry_price", pa.float64()),
        ("entry_timestamp", pa.string()),
        ("trajectory_exists", pa.bool_()),
        ("trajectory_path", pa.string()),
        ("trajectory_rows", pa.int64()),
        ("mfe_points", pa.float64()),
        ("mae_points", pa.float64()),
        ("first_timestamp", pa.string()),
        ("last_timestamp", pa.string()),
        ("file_size_bytes", pa.int64()),
        ("sha256", pa.string()),
        ("motor_version", pa.string()),
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


def _trajectory_output_path(
    session_date,
    trajectory_dir: Path,
) -> Path:
    return (
        trajectory_dir
        / (
            "winv26_trade1_"
            f"{session_date.strftime('%Y%m%d')}.parquet"
        )
    )


def _mfe_from_trajectory(
    trajectory: list[dict[str, Any]],
) -> float | None:
    if not trajectory:
        return None

    return max(
        float(row["favorable_excursion"])
        for row in trajectory
    )


def _mae_from_trajectory(
    trajectory: list[dict[str, Any]],
) -> float | None:
    if not trajectory:
        return None

    return max(
        float(row["adverse_excursion"])
        for row in trajectory
    )


def validate_trajectory_reload(
    original: list[dict[str, Any]],
    reloaded: list[dict[str, Any]],
    report: dict[str, Any],
) -> dict[str, bool]:
    row_count_match = (
        len(original) == len(reloaded)
    )

    first_row_match = (
        bool(original)
        and bool(reloaded)
        and original[0] == reloaded[0]
    )

    last_row_match = (
        bool(original)
        and bool(reloaded)
        and original[-1] == reloaded[-1]
    )

    mfe_match = (
        _mfe_from_trajectory(reloaded)
        == float(report["mfe_points"])
    )

    mae_match = (
        _mae_from_trajectory(reloaded)
        == float(report["mae_points"])
    )

    first_timestamp_match = (
        bool(original)
        and bool(reloaded)
        and original[0]["timestamp"]
        == reloaded[0]["timestamp"]
    )

    last_timestamp_match = (
        bool(original)
        and bool(reloaded)
        and original[-1]["timestamp"]
        == reloaded[-1]["timestamp"]
    )

    return {
        "row_count_match": row_count_match,
        "first_row_match": first_row_match,
        "last_row_match": last_row_match,
        "mfe_match": mfe_match,
        "mae_match": mae_match,
        "first_timestamp_match": first_timestamp_match,
        "last_timestamp_match": last_timestamp_match,
    }


def _assert_integrity(
    checks: dict[str, bool],
    session_date,
) -> None:
    failed = [
        name
        for name, value in checks.items()
        if value is not True
    ]

    if failed:
        raise RuntimeError(
            "Trajectory integrity failure for "
            f"{session_date.isoformat()}: "
            + ", ".join(failed)
        )


def build_manifest_record(
    parquet_path: Path,
    trajectory_dir: Path,
) -> tuple[
    dict[str, Any],
    dict[str, bool] | None,
]:
    session_date = _extract_session_date(
        parquet_path
    )

    report = reconstruct_trade1(
        parquet_path=parquet_path,
        session_date=session_date,
    )

    entry_found = bool(
        report.get("entry_found")
    )

    trajectory_path = (
        _trajectory_output_path(
            session_date,
            trajectory_dir,
        )
    )

    if not entry_found:
        # Remove eventual cache antigo/stale criado
        # antes da ADR-004.
        if trajectory_path.exists():
            trajectory_path.unlink()

        record = {
            "date": session_date.isoformat(),
            "source_parquet": parquet_path.name,
            "trade1_status": "NO_TRADE_1",
            "direction": None,
            "entry_price": None,
            "entry_timestamp": None,
            "trajectory_exists": False,
            "trajectory_path": None,
            "trajectory_rows": None,
            "mfe_points": None,
            "mae_points": None,
            "first_timestamp": None,
            "last_timestamp": None,
            "file_size_bytes": None,
            "sha256": None,
            "motor_version": MOTOR_VERSION,
        }

        return record, None

    trajectory = report.get(
        "trajectory"
    )

    if not trajectory:
        raise RuntimeError(
            "Trade 1 exists but trajectory is empty "
            f"for {session_date.isoformat()}."
        )

    write_trajectory_parquet(
        trajectory=trajectory,
        output_path=trajectory_path,
    )

    reloaded = read_trajectory_parquet(
        trajectory_path
    )

    checks = validate_trajectory_reload(
        original=trajectory,
        reloaded=reloaded,
        report=report,
    )

    _assert_integrity(
        checks,
        session_date,
    )

    record = {
        "date": session_date.isoformat(),
        "source_parquet": parquet_path.name,
        "trade1_status": "TRADE_1",
        "direction": report["direction"],
        "entry_price": float(
            report["entry_trigger_level"]
        ),
        "entry_timestamp": report[
            "entry_timestamp"
        ],
        "trajectory_exists": True,
        "trajectory_path": str(
            trajectory_path
        ),
        "trajectory_rows": len(
            reloaded
        ),
        "mfe_points": float(
            report["mfe_points"]
        ),
        "mae_points": float(
            report["mae_points"]
        ),
        "first_timestamp": (
            reloaded[0]["timestamp"]
        ),
        "last_timestamp": (
            reloaded[-1]["timestamp"]
        ),
        "file_size_bytes": (
            trajectory_path.stat().st_size
        ),
        "sha256": _sha256(
            trajectory_path
        ),
        "motor_version": MOTOR_VERSION,
    }

    return record, checks


def write_manifest(
    records: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ordered = sorted(
        records,
        key=lambda row: (
            row["date"],
            row["source_parquet"],
        ),
    )

    table = pa.Table.from_pylist(
        ordered,
        schema=MANIFEST_SCHEMA,
    )

    pq.write_table(
        table,
        output_path,
        compression="zstd",
    )

    return output_path


def run_trajectory_cache(
    normalized_dir: str | Path = "data/normalized",
    trajectory_dir: str | Path = "data/trajectories",
    manifest_path: str | Path = (
        "data/research/"
        "trade1_trajectory_manifest.parquet"
    ),
) -> dict[str, Any]:
    normalized_dir = Path(
        normalized_dir
    )
    trajectory_dir = Path(
        trajectory_dir
    )
    manifest_path = Path(
        manifest_path
    )

    trajectory_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    parquet_files = (
        discover_normalized_parquets(
            normalized_dir
        )
    )

    records = []
    validations = {}

    for parquet_path in parquet_files:
        record, checks = (
            build_manifest_record(
                parquet_path,
                trajectory_dir,
            )
        )

        records.append(record)

        validations[
            record["date"]
        ] = checks

    records = sorted(
        records,
        key=lambda row: (
            row["date"],
            row["source_parquet"],
        ),
    )

    write_manifest(
        records,
        manifest_path,
    )

    return {
        "records": records,
        "validations": validations,
        "manifest_path": str(
            manifest_path
        ),
    }