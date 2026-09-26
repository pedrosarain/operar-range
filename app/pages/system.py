from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.common import (
    dataframe_view,
    key_value_panel,
    metric_cards,
    page_header,
    section_title,
    status_badge,
)
from app.data_access import (
    DATASETS,
    REPORTS,
    dataset,
    dataset_inventory,
    detected_versions,
    regression_status,
    report,
    report_inventory,
)
from app.formatting import (
    NA_TEXT,
    as_text,
    format_bytes,
    format_integer,
)


def _count_rows(
    dataset_name: str,
) -> int | None:
    try:
        dataframe = dataset(
            dataset_name
        )
    except Exception:
        return None

    if dataframe.empty:
        return 0

    return len(
        dataframe
    )


def _batch_summary() -> dict[str, int | None]:
    plan = dataset(
        "batch_execution_plan"
    )

    if plan.empty:
        return {
            "batches": None,
            "execution_units": None,
            "completed": None,
            "failed": None,
            "skipped": None,
            "pending": None,
        }

    batches = None

    if "batch_id" in plan.columns:
        batches = (
            plan[
                "batch_id"
            ]
            .dropna()
            .nunique()
        )

    execution_units = len(
        plan
    )

    counts = {}

    if (
        "execution_status"
        in plan.columns
    ):
        counts = (
            plan[
                "execution_status"
            ]
            .fillna(
                "UNKNOWN"
            )
            .astype(str)
            .value_counts()
            .to_dict()
        )

    return {
        "batches": (
            int(batches)
            if batches is not None
            else None
        ),
        "execution_units": (
            int(
                execution_units
            )
        ),
        "completed": int(
            counts.get(
                "COMPLETED",
                0,
            )
        ),
        "failed": int(
            counts.get(
                "FAILED",
                0,
            )
        ),
        "skipped": int(
            counts.get(
                "SKIPPED_NO_TRADE",
                0,
            )
        ),
        "pending": int(
            counts.get(
                "PENDING",
                0,
            )
        ),
    }


def _lineage_status() -> dict[str, str]:
    ranking_summary = report(
        "ranking_summary"
    )

    constraint_summary = report(
        "constraint_engine_summary"
    )

    ranking_rule_status = (
        ranking_summary.get(
            "rule_set_hash_status"
        )
        if ranking_summary
        else None
    )

    ranking_rule_hash = (
        ranking_summary.get(
            "rule_set_hash"
        )
        if ranking_summary
        else None
    )

    constraint_rule_hash = (
        constraint_summary.get(
            "rule_set_sha256"
        )
        if constraint_summary
        else None
    )

    return {
        "ranking_rule_set_hash": (
            as_text(
                ranking_rule_hash
            )
        ),
        "ranking_rule_set_status": (
            as_text(
                ranking_rule_status
            )
        ),
        "constraint_rule_set_hash": (
            as_text(
                constraint_rule_hash
            )
        ),
    }


def _render_dataset_inventory() -> None:
    section_title(
        "Datasets",
        (
            "Arquivos principais encontrados "
            "pela interface."
        ),
    )

    inventory = (
        dataset_inventory()
    )

    if inventory.empty:
        st.info(
            "Inventário indisponível."
        )
        return

    display = inventory.copy()

    display[
        "status"
    ] = display[
        "exists"
    ].map(
        {
            True: "AVAILABLE",
            False: "MISSING",
        }
    )

    if (
        "size_bytes"
        in display.columns
    ):
        display[
            "size"
        ] = display[
            "size_bytes"
        ].map(
            format_bytes
        )

    preferred = [
        "dataset",
        "status",
        "rows",
        "columns",
        "size",
        "sha256",
        "modified_at",
        "path",
    ]

    visible = [
        column
        for column in preferred
        if column
        in display.columns
    ]

    dataframe_view(
        display[
            visible
        ],
        height=460,
    )


def _render_report_inventory() -> None:
    section_title(
        "Reports / manifests"
    )

    inventory = (
        report_inventory()
    )

    if inventory.empty:
        st.info(
            "Inventário de reports "
            "indisponível."
        )
        return

    display = inventory.copy()

    display[
        "status"
    ] = display[
        "exists"
    ].map(
        {
            True: "AVAILABLE",
            False: "MISSING",
        }
    )

    if (
        "size_bytes"
        in display.columns
    ):
        display[
            "size"
        ] = display[
            "size_bytes"
        ].map(
            format_bytes
        )

    preferred = [
        "report",
        "status",
        "size",
        "sha256",
        "modified_at",
        "path",
    ]

    visible = [
        column
        for column in preferred
        if column
        in display.columns
    ]

    dataframe_view(
        display[
            visible
        ],
        height=300,
    )


def _render_regression_status() -> None:
    section_title(
        "Regression"
    )

    status = (
        regression_status()
    )

    if not status.get(
        "available"
    ):
        status_badge(
            "Regression status",
            "N/A",
        )

        st.caption(
            (
                "A Full Regression Suite "
                "não possui, no momento, "
                "fonte persistida homologada. "
                "O resultado do terminal não "
                "é hardcoded pela interface."
            )
        )

        return

    metric_cards(
        [
            (
                "Total tests",
                format_integer(
                    status.get(
                        "total_tests"
                    )
                ),
            ),
            (
                "Passed",
                format_integer(
                    status.get(
                        "passed"
                    )
                ),
            ),
            (
                "Failed",
                format_integer(
                    status.get(
                        "failed"
                    )
                ),
            ),
            (
                "Errors",
                format_integer(
                    status.get(
                        "errors"
                    )
                ),
            ),
        ],
        columns=4,
    )

    status_badge(
        "Regression status",
        status.get(
            "status"
        ),
    )


def render() -> None:
    page_header(
        "System",
        (
            "Integridade técnica e lineage "
            "dos recursos consumidos pelo "
            "Research Terminal."
        ),
    )

    versions = detected_versions()
    registry_rows = (
        _count_rows(
            "experiment_registry"
        )
    )

    batch = (
        _batch_summary()
    )

    metric_cards(
        [
            (
                "Registry rows",
                format_integer(
                    registry_rows
                ),
            ),
            (
                "Batches",
                format_integer(
                    batch.get(
                        "batches"
                    )
                ),
            ),
            (
                "Execution units",
                format_integer(
                    batch.get(
                        "execution_units"
                    )
                ),
            ),
            (
                "Completed",
                format_integer(
                    batch.get(
                        "completed"
                    )
                ),
            ),
            (
                "Skipped",
                format_integer(
                    batch.get(
                        "skipped"
                    )
                ),
            ),
            (
                "Failed",
                format_integer(
                    batch.get(
                        "failed"
                    )
                ),
            ),
            (
                "Pending",
                format_integer(
                    batch.get(
                        "pending"
                    )
                ),
            ),
        ],
        columns=4,
    )

    st.divider()

    left, right = st.columns(
        2
    )

    with left:
        key_value_panel(
            [
                (
                    "Motor version",
                    as_text(
                        versions.get(
                            "motor_version"
                        )
                    ),
                ),
                (
                    "Rules version",
                    as_text(
                        versions.get(
                            "rules_version"
                        )
                    ),
                ),
            ],
            title="Runtime versions",
        )

    with right:
        lineage = (
            _lineage_status()
        )

        key_value_panel(
            [
                (
                    "Ranking rule_set_hash",
                    lineage[
                        "ranking_rule_set_hash"
                    ],
                ),
                (
                    "Ranking lineage status",
                    lineage[
                        "ranking_rule_set_status"
                    ],
                ),
                (
                    "Constraint rule_set_hash",
                    lineage[
                        "constraint_rule_set_hash"
                    ],
                ),
            ],
            title="Lineage",
        )

    st.divider()

    _render_dataset_inventory()

    st.divider()

    _render_report_inventory()

    st.divider()

    _render_regression_status()


if __name__ == "__main__":
    render()