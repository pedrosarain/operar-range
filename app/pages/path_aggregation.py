from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.common import (
    dataframe_view,
    page_header,
    section_title,
)
from operar_range.path_aggregation_engine import (
    load_path_stop_analytics,
    load_path_target_analytics,
    load_path_target_stop_matrix,
    load_path_trade2_analytics,
)


def _active_research_id() -> str | None:
    value = st.session_state.get(
        "active_research_id"
    )

    if not value:
        return None

    return str(
        value
    )


def _load_or_empty(
    loader,
    research_id: str,
) -> pd.DataFrame:
    try:
        dataframe = loader(
            research_id
        )
    except FileNotFoundError:
        return pd.DataFrame()

    return dataframe.to_pandas()


def _render_targets(
    dataframe: pd.DataFrame,
) -> None:
    section_title(
        "Targets",
        (
            "Agregação factual dos eventos "
            "de target e primeiro retorno ao zero."
        ),
    )

    if dataframe.empty:
        st.info(
            "Path Target Analytics indisponível."
        )
        return

    columns = [
        column
        for column in [
            "experiment_id",
            "trade",
            "target_points",
            "sessions_total",
            "valid_trade_sessions",
            "target_reached_count",
            "target_reached_pct",
            "target_before_first_zero_count",
            "target_before_first_zero_pct",
            "target_after_first_zero_count",
            "target_after_first_zero_pct",
            "target_then_zero_count",
            "target_then_zero_pct",
        ]
        if column
        in dataframe.columns
    ]

    dataframe_view(
        dataframe[
            columns
        ],
        height=470,
    )


def _render_matrix(
    dataframe: pd.DataFrame,
) -> None:
    section_title(
        "Target × Stop",
        (
            "Contagem de stops ocorridos "
            "depois de cada target."
        ),
    )

    if dataframe.empty:
        st.info(
            "Path Target × Stop Matrix "
            "indisponível."
        )
        return

    required = {
        "target_points",
        "stop_points",
        "stop_after_target_count",
    }

    if not required.issubset(
        set(
            dataframe.columns
        )
    ):
        dataframe_view(
            dataframe,
            height=470,
        )
        return

    matrix = (
        dataframe
        .pivot_table(
            index="target_points",
            columns="stop_points",
            values=(
                "stop_after_target_count"
            ),
            aggfunc="first",
        )
        .sort_index()
    )

    dataframe_view(
        matrix.reset_index(),
        height=470,
    )

    with st.expander(
        "Tabela completa — Target × Stop",
        expanded=False,
    ):
        dataframe_view(
            dataframe,
            height=500,
        )


def _render_stops(
    dataframe: pd.DataFrame,
) -> None:
    section_title(
        "Stops",
        (
            "Agregação factual dos eventos "
            "de stop."
        ),
    )

    if dataframe.empty:
        st.info(
            "Path Stop Analytics indisponível."
        )
        return

    dataframe_view(
        dataframe,
        height=360,
    )


def _render_trade2(
    dataframe: pd.DataFrame,
) -> None:
    section_title(
        "Trade 2",
        (
            "Agregação factual do Trade 2 "
            "já existente no Path Analysis."
        ),
    )

    if dataframe.empty:
        st.info(
            "Path Trade 2 Analytics "
            "indisponível."
        )
        return

    columns = [
        column
        for column in [
            "experiment_id",
            "trade1_stop_points",
            "trade1_stopped_count",
            "trade2_eligible_count",
            "trade2_occurred_count",
            "trade2_executed_count",
            "trade2_occurrence_pct",
            "trade2_return_to_entry_count",
            "trade2_target_points",
            "trade2_target_reached_count",
            "trade2_target_reached_pct",
            "trade2_stop_points",
            "trade2_stop_reached_count",
            "trade2_stop_reached_pct",
        ]
        if column
        in dataframe.columns
    ]

    dataframe_view(
        dataframe[
            columns
        ],
        height=500,
    )


def render() -> None:
    page_header(
        "Path Aggregation",
        (
            "Agregações read-only produzidas "
            "sobre os fatos da Stage 25."
        ),
    )

    research_id = (
        _active_research_id()
    )

    if research_id is None:
        st.info(
            "Selecione uma pesquisa ativa."
        )
        return

    targets = _load_or_empty(
        load_path_target_analytics,
        research_id,
    )

    matrix = _load_or_empty(
        load_path_target_stop_matrix,
        research_id,
    )

    stops = _load_or_empty(
        load_path_stop_analytics,
        research_id,
    )

    trade2 = _load_or_empty(
        load_path_trade2_analytics,
        research_id,
    )

    if (
        targets.empty
        and matrix.empty
        and stops.empty
        and trade2.empty
    ):
        st.info(
            (
                "Path Aggregation ainda não "
                "foi produzido para a "
                "pesquisa ativa."
            )
        )
        return

    _render_targets(
        targets
    )

    st.divider()

    _render_matrix(
        matrix
    )

    st.divider()

    _render_stops(
        stops
    )

    st.divider()

    _render_trade2(
        trade2
    )


if __name__ == "__main__":
    render()
