from __future__ import annotations

from typing import Any

import streamlit as st


PRODUCT_NAME = "OPERAR RANGE"
PRODUCT_SUBTITLE = "Research Workspace V2"


def page_title(
    title: str,
    description: str | None = None,
) -> None:
    st.title(
        title
    )

    if description:
        st.caption(
            description
        )


def answer_card(
    label: str,
    value: Any,
    *,
    help_text: str | None = None,
) -> None:
    display = (
        "Não disponível"
        if value is None
        else str(
            value
        )
    )

    st.metric(
        label,
        display,
        help=help_text,
    )


def unavailable(
    message: str,
) -> None:
    st.info(
        message
    )


def section(
    title: str,
    description: str | None = None,
) -> None:
    st.subheader(
        title
    )

    if description:
        st.caption(
            description
        )
