from __future__ import annotations

from typing import Any, Iterable

import pandas as pd
import streamlit as st

from app.formatting import (
    NA_TEXT,
    as_text,
    format_boolean,
    format_float,
    format_hash,
    format_integer,
    format_percent,
    format_points,
)


def apply_terminal_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(
                    circle at top left,
                    rgba(20, 31, 51, 0.55),
                    rgba(6, 10, 17, 1) 38%
                );
            color: #e5e7eb;
        }

        [data-testid="stSidebar"] {
            background-color: #0b111c;
            border-right: 1px solid #1f2937;
        }

        [data-testid="stMetric"] {
            background: #0f1724;
            border: 1px solid #243041;
            border-radius: 10px;
            padding: 10px 12px;
        }

        [data-testid="stMetricLabel"] {
            color: #9ca3af;
        }

        [data-testid="stMetricValue"] {
            color: #f8fafc;
        }

        .terminal-card {
            border: 1px solid #243041;
            border-radius: 10px;
            padding: 14px 16px;
            background: #0f1724;
            margin-bottom: 12px;
        }

        .terminal-section-title {
            color: #f8fafc;
            font-weight: 700;
            font-size: 1rem;
            margin-bottom: 8px;
        }

        .terminal-muted {
            color: #94a3b8;
            font-size: 0.88rem;
        }

        .terminal-kv {
            display: grid;
            grid-template-columns: minmax(180px, 0.8fr) minmax(0, 1.2fr);
            gap: 7px 16px;
            font-size: 0.92rem;
        }

        .terminal-kv-key {
            color: #94a3b8;
        }

        .terminal-kv-value {
            color: #f8fafc;
            overflow-wrap: anywhere;
        }

        .status-ok {
            color: #86efac;
            font-weight: 600;
        }

        .status-warning {
            color: #fde68a;
            font-weight: 600;
        }

        .status-na {
            color: #94a3b8;
            font-weight: 600;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid #1f2937;
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(
    title: str,
    subtitle: str | None = None,
) -> None:
    st.title(
        title
    )

    if subtitle:
        st.caption(
            subtitle
        )


def section_title(
    title: str,
    subtitle: str | None = None,
) -> None:
    st.subheader(
        title
    )

    if subtitle:
        st.caption(
            subtitle
        )


def info_message(
    message: str,
) -> None:
    st.info(
        message
    )


def warning_message(
    message: str,
) -> None:
    st.warning(
        message
    )


def empty_dataset(
    label: str = "Dataset",
) -> None:
    st.info(
        f"{label} indisponível."
    )


def metric_cards(
    items: Iterable[
        tuple[str, Any]
    ],
    columns: int = 4,
) -> None:
    items = list(
        items
    )

    if not items:
        return

    for start in range(
        0,
        len(items),
        columns,
    ):
        chunk = items[
            start:
            start + columns
        ]

        cols = st.columns(
            columns
        )

        for index, (
            label,
            value,
        ) in enumerate(
            chunk
        ):
            cols[index].metric(
                label,
                (
                    NA_TEXT
                    if value is None
                    else str(value)
                ),
            )


def dataframe_view(
    dataframe: pd.DataFrame,
    *,
    height: int = 420,
    use_container_width: bool = True,
    hide_index: bool = True,
) -> None:
    if dataframe.empty:
        empty_dataset(
            "Tabela"
        )
        return

    st.dataframe(
        dataframe,
        height=height,
        use_container_width=(
            use_container_width
        ),
        hide_index=(
            hide_index
        ),
    )


def key_value_panel(
    values: Iterable[
        tuple[str, Any]
    ],
    *,
    title: str | None = None,
) -> None:
    if title:
        st.markdown(
            (
                '<div class="terminal-section-title">'
                f"{title}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    lines = []

    for label, value in values:
        text = (
            NA_TEXT
            if value is None
            else str(value)
        )

        lines.append(
            (
                '<div class="terminal-kv-key">'
                f"{label}"
                "</div>"
                '<div class="terminal-kv-value">'
                f"{text}"
                "</div>"
            )
        )

    st.markdown(
        (
            '<div class="terminal-card">'
            '<div class="terminal-kv">'
            + "".join(
                lines
            )
            + "</div>"
            + "</div>"
        ),
        unsafe_allow_html=True,
    )


def formatted_config_rows(
    row: dict[str, Any],
) -> list[
    tuple[str, str]
]:
    return [
        (
            "Stop",
            format_points(
                row.get(
                    "stop_points"
                )
            ),
        ),
        (
            "Partial 1",
            format_points(
                row.get(
                    "partial_1_points"
                )
            ),
        ),
        (
            "Partial 1 %",
            format_percent(
                row.get(
                    "partial_1_pct"
                )
            ),
        ),
        (
            "Partial 2",
            format_points(
                row.get(
                    "partial_2_points"
                )
            ),
        ),
        (
            "Partial 2 %",
            format_percent(
                row.get(
                    "partial_2_pct"
                )
            ),
        ),
        (
            "Partial 3",
            format_points(
                row.get(
                    "partial_3_points"
                )
            ),
        ),
        (
            "Partial 3 %",
            format_percent(
                row.get(
                    "partial_3_pct"
                )
            ),
        ),
        (
            "Break-even",
            format_boolean(
                row.get(
                    "break_even_enabled"
                )
            ),
        ),
        (
            "BE after partial",
            as_text(
                row.get(
                    "break_even_after_partial"
                )
            ),
        ),
        (
            "Runner",
            format_boolean(
                row.get(
                    "runner_enabled"
                )
            ),
        ),
        (
            "Runner %",
            format_percent(
                row.get(
                    "runner_pct"
                )
            ),
        ),
        (
            "Runner rule",
            as_text(
                row.get(
                    "runner_rule"
                )
            ),
        ),
        (
            "Final target",
            format_points(
                row.get(
                    "final_target_points"
                )
            ),
        ),
    ]


def formatted_identity_rows(
    row: dict[str, Any],
) -> list[
    tuple[str, str]
]:
    return [
        (
            "Experiment ID",
            as_text(
                row.get(
                    "experiment_id"
                )
            ),
        ),
        (
            "Experiment name",
            as_text(
                row.get(
                    "experiment_name"
                )
            ),
        ),
        (
            "Family",
            as_text(
                row.get(
                    "family"
                )
            ),
        ),
        (
            "Generation",
            format_integer(
                row.get(
                    "generation"
                )
            ),
        ),
        (
            "Status",
            as_text(
                row.get(
                    "status"
                )
            ),
        ),
        (
            "Config SHA-256",
            as_text(
                row.get(
                    "config_sha256"
                )
            ),
        ),
        (
            "Definition SHA-256",
            as_text(
                row.get(
                    "definition_sha256"
                )
            ),
        ),
        (
            "Engine version",
            as_text(
                row.get(
                    "engine_version"
                )
            ),
        ),
        (
            "Rules version",
            as_text(
                row.get(
                    "rules_version"
                )
            ),
        ),
    ]


def compact_hash(
    value: Any,
) -> str:
    return format_hash(
        value,
        visible=16,
    )


def filter_multiselect(
    *,
    label: str,
    dataframe: pd.DataFrame,
    column: str,
    key: str,
) -> list[Any]:
    if (
        dataframe.empty
        or column
        not in dataframe.columns
    ):
        return []

    values = (
        dataframe[
            column
        ]
        .dropna()
        .unique()
        .tolist()
    )

    values = sorted(
        values,
        key=lambda item: str(
            item
        ),
    )

    return st.multiselect(
        label,
        options=values,
        default=[],
        key=key,
    )


def apply_multiselect_filter(
    dataframe: pd.DataFrame,
    *,
    column: str,
    values: list[Any],
) -> pd.DataFrame:
    if (
        not values
        or dataframe.empty
        or column
        not in dataframe.columns
    ):
        return dataframe

    return dataframe[
        dataframe[
            column
        ].isin(
            values
        )
    ].copy()


def search_dataframe(
    dataframe: pd.DataFrame,
    *,
    query: str,
    columns: list[str],
) -> pd.DataFrame:
    if (
        dataframe.empty
        or not query.strip()
    ):
        return dataframe

    query = (
        query.strip()
        .lower()
    )

    mask = pd.Series(
        False,
        index=dataframe.index,
    )

    for column in columns:
        if column not in dataframe.columns:
            continue

        values = (
            dataframe[
                column
            ]
            .fillna("")
            .astype(str)
            .str.lower()
        )

        mask = (
            mask
            | values.str.contains(
                query,
                regex=False,
            )
        )

    return dataframe[
        mask
    ].copy()


def status_badge(
    label: str,
    value: str | None,
) -> None:
    if value is None:
        css_class = (
            "status-na"
        )
        value = NA_TEXT

    elif value in {
        "AVAILABLE",
        "ACTIVE",
        "COMPLETED",
        "CLEAN",
        "VALID",
        "RANKED",
    }:
        css_class = (
            "status-ok"
        )

    elif value in {
        "UNAVAILABLE",
        "NOT_RANKABLE",
        "N/A",
        "NOT_APPLICABLE_LEGACY_DATASET",
    }:
        css_class = (
            "status-na"
        )

    else:
        css_class = (
            "status-warning"
        )

    st.markdown(
        (
            f"**{label}:** "
            f'<span class="{css_class}">'
            f"{value}"
            "</span>"
        ),
        unsafe_allow_html=True,
    )