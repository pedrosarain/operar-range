from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.common import (
    dataframe_view,
    page_header,
    section_title,
)
from operar_range.path_analysis_engine import (
    PATH_ANALYSIS_ENGINE_VERSION,
    load_research_path_analysis,
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


def render() -> None:
    page_header(
        "Path Analysis",
        (
            "Eventos cronológicos observados "
            "nas trajectories persistidas. "
            "READ ONLY."
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

    try:
        dataframe = (
            load_research_path_analysis(
                research_id
            )
        )

    except FileNotFoundError:
        st.info(
            (
                "O artifact Path Analysis "
                "ainda não foi produzido "
                "para esta pesquisa."
            )
        )
        return

    if dataframe.is_empty():
        st.info(
            "Path Analysis sem registros."
        )
        return

    st.caption(
        (
            f"Research ID: {research_id} | "
            f"Engine: "
            f"{PATH_ANALYSIS_ENGINE_VERSION}"
        )
    )

    section_title(
        "Artifact"
    )

    pandas_frame = (
        dataframe.to_pandas()
    )

    dataframe_view(
        pandas_frame,
        height=650,
    )


if __name__ == "__main__":
    render()
