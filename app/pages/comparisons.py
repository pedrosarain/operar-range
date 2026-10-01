from __future__ import annotations

import streamlit as st

from app.components.common import (
    page_header,
)
from app.pages import compare
from app.pages import research_comparison


def render() -> None:
    page_header(
        "Comparações",
        (
            "Comparação factual entre pesquisas "
            "e experimentos existentes."
        ),
    )

    tabs = st.tabs(
        [
            "Pesquisas",
            "Experimentos",
        ]
    )

    with tabs[0]:
        research_comparison.render()

    with tabs[1]:
        compare.render()
