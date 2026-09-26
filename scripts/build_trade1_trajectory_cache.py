from __future__ import annotations

import hashlib
from pathlib import Path

import pyarrow.parquet as pq

from operar_range.trajectory_cache import run_trajectory_cache


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def main():
    result = run_trajectory_cache()

    manifest_path = Path(
        result["manifest_path"]
    )

    manifest = pq.read_table(
        manifest_path
    )

    rows = manifest.to_pylist()

    print("=" * 72)
    print("ETAPA 8 — CACHE DE TRAJETÓRIAS EM ESCALA")
    print("=" * 72)

    print(
        "PREGOES_ANALISADOS:",
        len(rows),
    )

    print(
        "TRAJECTORIES_CREATED:",
        sum(
            1
            for row in rows
            if row["trajectory_exists"]
        ),
    )

    print(
        "NO_TRADE_1_COUNT:",
        sum(
            1
            for row in rows
            if not row["trajectory_exists"]
        ),
    )

    print(
        "MANIFEST_ROWS:",
        manifest.num_rows,
    )

    print(
        "MANIFEST_COLUMNS:",
        manifest.num_columns,
    )

    print(
        "MANIFEST_PATH:",
        manifest_path,
    )

    print(
        "MANIFEST_SIZE_BYTES:",
        manifest_path.stat().st_size,
    )

    print(
        "MANIFEST_SHA256:",
        sha256_file(
            manifest_path
        ),
    )

    for row in rows:
        print("-" * 72)

        date_value = row["date"]

        print("DATE:", date_value)
        print(
            "SOURCE_PARQUET:",
            row["source_parquet"],
        )
        print(
            "TRADE1_STATUS:",
            row["trade1_status"],
        )
        print(
            "DIRECTION:",
            row["direction"],
        )
        print(
            "ENTRY_PRICE:",
            row["entry_price"],
        )
        print(
            "ENTRY_TIMESTAMP:",
            row["entry_timestamp"],
        )
        print(
            "TRAJECTORY_EXISTS:",
            row["trajectory_exists"],
        )
        print(
            "TRAJECTORY_PATH:",
            row["trajectory_path"],
        )
        print(
            "TRAJECTORY_ROWS:",
            row["trajectory_rows"],
        )
        print(
            "MFE_POINTS:",
            row["mfe_points"],
        )
        print(
            "MAE_POINTS:",
            row["mae_points"],
        )
        print(
            "FIRST_TIMESTAMP:",
            row["first_timestamp"],
        )
        print(
            "LAST_TIMESTAMP:",
            row["last_timestamp"],
        )
        print(
            "FILE_SIZE_BYTES:",
            row["file_size_bytes"],
        )
        print(
            "SHA256:",
            row["sha256"],
        )

        checks = result[
            "validations"
        ].get(date_value)

        if checks is None:
            print("ROW_COUNT_MATCH: N/A")
            print("FIRST_ROW_MATCH: N/A")
            print("LAST_ROW_MATCH: N/A")
            print("MFE_MATCH: N/A")
            print("MAE_MATCH: N/A")
            print("FIRST_TIMESTAMP_MATCH: N/A")
            print("LAST_TIMESTAMP_MATCH: N/A")

        else:
            print(
                "ROW_COUNT_MATCH:",
                checks["row_count_match"],
            )
            print(
                "FIRST_ROW_MATCH:",
                checks["first_row_match"],
            )
            print(
                "LAST_ROW_MATCH:",
                checks["last_row_match"],
            )
            print(
                "MFE_MATCH:",
                checks["mfe_match"],
            )
            print(
                "MAE_MATCH:",
                checks["mae_match"],
            )
            print(
                "FIRST_TIMESTAMP_MATCH:",
                checks["first_timestamp_match"],
            )
            print(
                "LAST_TIMESTAMP_MATCH:",
                checks["last_timestamp_match"],
            )


if __name__ == "__main__":
    main()
