from __future__ import annotations

import streamlit as st

from app.components.common import (
    page_header,
)
from app.pages import data
from app.pages import query
from app.pages import sessions
from app.pages import system


def render() -> None:
    page_header(
        "Administração",
        (
            "Auditoria técnica, dados, runtime "
            "e estruturas internas da plataforma."
        ),
    )

    st.warning(
        (
            "Área técnica. As informações aqui "
            "existem para auditoria e operação da "
            "plataforma, não para interpretação "
            "quantitativa dos resultados."
        )
    )

    tabs = st.tabs(
        [
            "Datasets",
            "Auditoria",
            "Sessões",
            "System",
        ]
    )

    with tabs[0]:
        data.render()

    with tabs[1]:
        query.render()

    with tabs[2]:
        sessions.render()

    with tabs[3]:
        system.render()
