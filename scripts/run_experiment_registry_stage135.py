from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

from operar_range.experiment_registry import (
    migrate_registry,
    sha256_file,
)


REGISTRY = Path(
    "data/research/"
    "experiment_registry.parquet"
)

SOURCES = [
    Path(
        "data/research/"
        "experiment_manifest.parquet"
    ),
    Path(
        "data/research/"
        "generated_experiments.parquet"
    ),
]


def duplicate_count(
    values,
):
    values = [
        value
        for value in values
        if value is not None
    ]

    return (
        len(values)
        - len(set(values))
    )


def main():
    first = migrate_registry(
        registry_path=REGISTRY,
        source_paths=SOURCES,
    )

    first_hash = sha256_file(
        REGISTRY
    )

    first_rows = pq.read_table(
        REGISTRY
    ).to_pylist()

    second = migrate_registry(
        registry_path=REGISTRY,
        source_paths=SOURCES,
    )

    second_hash = sha256_file(
        REGISTRY
    )

    second_rows = pq.read_table(
        REGISTRY
    ).to_pylist()

    ids = [
        row["experiment_id"]
        for row in second_rows
    ]

    configs = [
        row["config_sha256"]
        for row in second_rows
    ]

    print("=" * 80)
    print(
        "ETAPA 13.5 — "
        "EXPERIMENT REGISTRY"
    )
    print("=" * 80)

    print(
        "REGISTRY_ROWS:",
        len(second_rows),
    )

    print(
        "DUPLICATE_IDS:",
        duplicate_count(ids),
    )

    print(
        "DUPLICATE_CONFIGS_INCORRETAS:",
        duplicate_count(
            configs
        ),
    )

    print(
        "FIRST_ID:",
        (
            second_rows[0][
                "experiment_id"
            ]
            if second_rows
            else None
        ),
    )

    print(
        "LAST_ID:",
        (
            second_rows[-1][
                "experiment_id"
            ]
            if second_rows
            else None
        ),
    )

    print(
        "NEXT_AVAILABLE_ID:",
        second[
            "next_available_id"
        ],
    )

    print(
        "NEW_EXPERIMENTS_FIRST_RUN:",
        first[
            "new_experiments"
        ],
    )

    print(
        "NEW_EXPERIMENTS_SECOND_RUN:",
        second[
            "new_experiments"
        ],
    )

    print(
        "REGISTRY_UNCHANGED:",
        (
            first_rows
            == second_rows
            and first_hash
            == second_hash
        ),
    )

    print(
        "REGISTRY_PATH:",
        REGISTRY,
    )

    print(
        "REGISTRY_SHA256:",
        second_hash,
    )

    print("\nSOURCES")

    for source in SOURCES:
        print(
            source,
            "| EXISTS:",
            source.exists(),
            "| SHA256:",
            (
                sha256_file(
                    source
                )
                if source.exists()
                else None
            ),
        )


if __name__ == "__main__":
    main()