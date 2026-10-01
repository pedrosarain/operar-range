from __future__ import annotations

import streamlit as st

from app.components.common import (
    page_header,
)
from app.pages import path_aggregation
from app.pages import path_analysis
from app.pages import path_query
from app.pages import rankings
from app.pages import trade_lifecycle_analytics


def render() -> None:
    page_header(
        "Analytics",
        (
            "Central estatística das pesquisas "
            "e experimentos."
        ),
    )

    st.caption(
        (
            "As capacidades quantitativas abaixo "
            "são somente apresentadas aqui. "
            "Nenhum motor é reexecutado ou alterado."
        )
    )

    tabs = st.tabs(
        [
            "Performance",
            "Risco",
            "Path",
            "Gestão",
            "Drill-down",
        ]
    )

    with tabs[0]:
        st.markdown(
            "### Performance"
        )

        st.caption(
            (
                "Expectancy, Profit Factor, Win Rate "
                "e demais métricas produzidas pelos "
                "artifacts existentes."
            )
        )

        rankings.render()

    with tabs[1]:
        st.markdown(
            "### Risco"
        )

        st.caption(
            (
                "Drawdown, MFE, MAE, stops e demais "
                "evidências de risco disponíveis."
            )
        )

        path_analysis.render()

    with tabs[2]:
        st.markdown(
            "### Path"
        )

        st.caption(
            (
                "Targets, stops, zero a zero e "
                "relações quantitativas do caminho "
                "dos trades."
            )
        )

        path_aggregation.render()

    with tabs[3]:
        st.markdown(
            "### Gestão"
        )

        trade_lifecycle_analytics.render()

    with tabs[4]:
        st.markdown(
            "### Ver pregões"
        )

        st.caption(
            (
                "Drill-down dos pregões que compõem "
                "os resultados quantitativos."
            )
        )

        path_query.render()
