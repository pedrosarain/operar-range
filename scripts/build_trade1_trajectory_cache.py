from datetime import date
from pathlib import Path

from operar_range.trade1 import reconstruct_trade1
from operar_range.trajectory import (
    write_trajectory_parquet,
    write_trajectory_metadata,
    read_trajectory_parquet,
)

CASES = [
    (
        date(2026, 8, 18),
        Path("data/normalized/winv26_ticks_20260818_enriched.parquet"),
    ),
    (
        date(2026, 8, 19),
        Path("data/normalized/winv26_ticks_20260819_enriched.parquet"),
    ),
]

for session_date, parquet in CASES:

    report = reconstruct_trade1(
        parquet_path=parquet,
        session_date=session_date,
    )

    trajectory = report["trajectory"]

    trajectory_file = Path(
        f"data/trajectories/winv26_trade1_{session_date:%Y%m%d}.parquet"
    )

    metadata_file = Path(
        f"data/reports/winv26_trade1_{session_date:%Y%m%d}.json"
    )

    write_trajectory_parquet(
        trajectory,
        trajectory_file,
    )

    metadata = write_trajectory_metadata(
        report,
        trajectory_file,
        metadata_file,
    )

    reload = read_trajectory_parquet(
        trajectory_file,
    )

    print("=" * 70)
    print(session_date)

    print(
        "ROW_COUNT_MATCH:",
        len(trajectory) == len(reload),
    )

    print(
        "FIRST_ROW_MATCH:",
        trajectory[0] == reload[0],
    )

    print(
        "LAST_ROW_MATCH:",
        trajectory[-1] == reload[-1],
    )

    print(
        "MFE_MATCH:",
        max(x["favorable_excursion"] for x in trajectory)
        ==
        max(x["favorable_excursion"] for x in reload),
    )

    print(
        "MAE_MATCH:",
        max(x["adverse_excursion"] for x in trajectory)
        ==
        max(x["adverse_excursion"] for x in reload),
    )

    print(
        "FILE_SIZE:",
        metadata["file_size_bytes"],
    )

    print(
        "SHA256:",
        metadata["sha256"],
    )