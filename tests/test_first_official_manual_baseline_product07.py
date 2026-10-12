from __future__ import annotations

import hashlib
from pathlib import Path

from operar_range.manual_baseline_registry import (
    baseline_components_root,
    list_manual_baselines,
    load_manual_baseline,
)


EXPECTED_SOURCE_SHA = (
    "d83dfa42a7a3956301af112809ea02bb"
    "507176d312085f7c2788b3e089fdc33e"
)


def _sha256(
    path: Path,
) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def test_first_official_manual_baseline_registered():
    rows = list_manual_baselines()

    assert len(
        rows
    ) == 1

    row = rows[
        0
    ]

    assert (
        row[
            "name"
        ]
        == (
            "US OPEN BREAKOUT V1 "
            "Manual Baseline Oficial"
        )
    )

    assert (
        row[
            "strategy"
        ]
        == "US OPEN BREAKOUT V1"
    )

    assert (
        row[
            "market"
        ]
        == "B3"
    )

    assert (
        row[
            "asset"
        ]
        == "WINFUT"
    )

    assert (
        row[
            "period_start"
        ]
        == "2026-01-01"
    )

    assert (
        row[
            "period_end"
        ]
        == "2026-09-21"
    )

    assert (
        row[
            "session_count"
        ]
        == 164
    )

    assert (
        row[
            "version"
        ]
        == 1
    )

    assert (
        row[
            "status"
        ]
        == "OFFICIAL"
    )

    assert (
        row[
            "component_count"
        ]
        == 1
    )

    assert (
        row[
            "results"
        ]
        == []
    )


def test_official_component_is_preserved_byte_for_byte():
    row = list_manual_baselines()[
        0
    ]

    source = Path(
        "data/manual/candle18_manual.xlsx"
    )

    stored = (
        baseline_components_root(
            row[
                "baseline_id"
            ],
            row[
                "version"
            ],
        )
        / "candle18_manual.xlsx"
    )

    assert source.exists()
    assert stored.exists()

    assert (
        _sha256(
            source
        )
        == EXPECTED_SOURCE_SHA
    )

    assert (
        _sha256(
            stored
        )
        == EXPECTED_SOURCE_SHA
    )

    assert (
        source.read_bytes()
        == stored.read_bytes()
    )

    component = row[
        "components"
    ][
        0
    ]

    assert (
        component[
            "original_name"
        ]
        == "candle18_manual.xlsx"
    )

    assert (
        component[
            "stored_name"
        ]
        == "candle18_manual.xlsx"
    )

    assert (
        component[
            "sha256"
        ]
        == EXPECTED_SOURCE_SHA
    )


def test_official_baseline_version_is_loadable():
    row = list_manual_baselines()[
        0
    ]

    loaded = (
        load_manual_baseline(
            row[
                "baseline_id"
            ],
            1,
        )
    )

    assert loaded == row

    assert (
        loaded[
            "baseline_sha256"
        ]
    )

    assert (
        loaded[
            "components_sha256"
        ]
    )
