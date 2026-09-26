from __future__ import annotations

import hashlib
from pathlib import Path

import pyarrow.parquet as pq

from operar_range.scanner import run_scanner


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
    result = run_scanner()

    database_path = Path(
        result["database_path"]
    )

    summary_path = Path(
        result["summary_path"]
    )

    table = pq.read_table(
        database_path
    )

    print("=" * 70)
    print("ETAPA 7 — SCANNER DE PREGÕES")
    print("=" * 70)

    print(
        "PREGOES_ANALISADOS:",
        result["summary"][
            "pregoes_analisados"
        ],
    )

    print(
        "TRADE1_COUNT:",
        result["summary"][
            "trade1_count"
        ],
    )

    print(
        "SEM_TRADE1_COUNT:",
        result["summary"][
            "sem_trade1_count"
        ],
    )

    print(
        "PERIODO_INICIAL:",
        result["summary"][
            "periodo_inicial"
        ],
    )

    print(
        "PERIODO_FINAL:",
        result["summary"][
            "periodo_final"
        ],
    )

    print(
        "MOTOR_VERSION:",
        result["summary"][
            "motor_version"
        ],
    )

    print(
        "DATABASE_ROWS:",
        table.num_rows,
    )

    print(
        "DATABASE_COLUMNS:",
        table.num_columns,
    )

    print(
        "DATABASE_PATH:",
        database_path,
    )

    print(
        "DATABASE_SIZE_BYTES:",
        database_path.stat().st_size,
    )

    print(
        "DATABASE_SHA256:",
        sha256_file(
            database_path
        ),
    )

    print(
        "SUMMARY_PATH:",
        summary_path,
    )

    print("\nREGISTROS")

    for row in table.to_pylist():
        print("-" * 70)
        print("date:", row["date"])
        print(
            "source_parquet:",
            row["source_parquet"],
        )
        print(
            "entry_found:",
            row["entry_found"],
        )
        print(
            "trade1_status:",
            row["trade1_status"],
        )
        print(
            "direction:",
            row["direction"],
        )
        print(
            "entry_timestamp:",
            row["entry_timestamp"],
        )
        print(
            "mfe_points:",
            row["mfe_points"],
        )
        print(
            "mae_points:",
            row["mae_points"],
        )


if __name__ == "__main__":
    main()