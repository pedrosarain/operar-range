from __future__ import annotations

import streamlit as st

from app.components.common import (
    dataframe_view,
    key_value_panel,
    metric_cards,
    page_header,
    section_title,
)
from app.data_access import (
    dataset_inventory,
    detected_versions,
    latest_dataset,
    overview_counts,
)
from app.formatting import (
    NA_TEXT,
    as_text,
    format_date,
    format_integer,
)


def _display_value(
    value,
) -> str:
    if value is None:
        return NA_TEXT

    return str(value)


def render() -> None:
    page_header(
        "Overview",
        (
            "Estado geral da plataforma "
            "Operar Range."
        ),
    )

    counts = overview_counts()
    versions = detected_versions()
    latest = latest_dataset()

    metric_cards(
        [
            (
                "Pregões analisados",
                format_integer(
                    counts.get(
                        "sessions_total"
                    )
                ),
            ),
            (
                "Com Trade 1",
                format_integer(
                    counts.get(
                        "trade1_count"
                    )
                ),
            ),
            (
                "Sem Trade 1",
                format_integer(
                    counts.get(
                        "no_trade1_count"
                    )
                ),
            ),
            (
                "Experimentos registrados",
                format_integer(
                    counts.get(
                        "registry_total"
                    )
                ),
            ),
            (
                "ACTIVE",
                format_integer(
                    counts.get(
                        "registry_active"
                    )
                ),
            ),
            (
                "FROZEN",
                format_integer(
                    counts.get(
                        "registry_frozen"
                    )
                ),
            ),
            (
                "Configurações válidas",
                format_integer(
                    counts.get(
                        "valid_experiments"
                    )
                ),
            ),
            (
                "Execuções existentes",
                format_integer(
                    counts.get(
                        "execution_rows"
                    )
                ),
            ),
            (
                "Rankings disponíveis",
                format_integer(
                    counts.get(
                        "ranking_types"
                    )
                ),
            ),
            (
                "Período inicial",
                format_date(
                    counts.get(
                        "period_start"
                    )
                ),
            ),
            (
                "Período final",
                format_date(
                    counts.get(
                        "period_end"
                    )
                ),
            ),
        ],
        columns=4,
    )

    st.divider()

    left, right = st.columns(
        [1, 1]
    )

    with left:
        section_title(
            "Runtime",
            (
                "Versões detectadas nos "
                "datasets homologados."
            ),
        )

        key_value_panel(
            [
                (
                    "Current Motor Version",
                    as_text(
                        versions.get(
                            "motor_version"
                        )
                    ),
                ),
                (
                    "Rules Version",
                    as_text(
                        versions.get(
                            "rules_version"
                        )
                    ),
                ),
            ],
        )

    with right:
        section_title(
            "Último dataset disponível",
            (
                "Arquivo mais recentemente "
                "modificado entre os datasets "
                "monitorados pela interface."
            ),
        )

        if latest is None:
            key_value_panel(
                [
                    (
                        "Dataset",
                        NA_TEXT,
                    ),
                    (
                        "Modified at",
                        NA_TEXT,
                    ),
                    (
                        "SHA-256",
                        NA_TEXT,
                    ),
                ],
            )

        else:
            key_value_panel(
                [
                    (
                        "Dataset",
                        as_text(
                            latest.get(
                                "name"
                            )
                        ),
                    ),
                    (
                        "Modified at",
                        as_text(
                            latest.get(
                                "modified_at"
                            )
                        ),
                    ),
                    (
                        "SHA-256",
                        as_text(
                            latest.get(
                                "sha256"
                            )
                        ),
                    ),
                ],
            )

    st.divider()

    section_title(
        "Datasets",
        (
            "Inventário read-only dos "
            "principais datasets consumidos "
            "pelo Research Terminal."
        ),
    )

    inventory = (
        dataset_inventory()
    )

    if inventory.empty:
        st.info(
            "Nenhum dataset disponível."
        )
        return

    display = inventory.copy()

    if "exists" in display.columns:
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

    preferred_columns = [
        "dataset",
        "status",
        "rows",
        "columns",
        "size_bytes",
        "modified_at",
        "sha256",
        "path",
    ]

    visible_columns = [
        column
        for column in preferred_columns
        if column
        in display.columns
    ]

    display = display[
        visible_columns
    ]

    dataframe_view(
        display,
        height=440,
    )


if __name__ == "__main__":
    render()