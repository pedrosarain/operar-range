from __future__ import annotations

from typing import Any

import streamlit as st

from app.product.questions import (
    render_questions,
)
from app.product.research_views import (
    render_conclusions,
    render_experiments,
    render_research_analytics,
    render_result,
)
from app.product.shared import (
    page_title,
)
from operar_range.research_workspace import (
    list_researches,
)


RESEARCH_TABS = (
    "Resumo",
    "Perguntas",
    "Resultado",
    "Experimentos",
    "Analytics",
    "Conclusões",
)


def _research_id(
    row: dict[str, Any],
) -> str:
    return str(
        row.get(
            "research_id"
        )
        or ""
    )


def _research_name(
    row: dict[str, Any],
) -> str:
    value = (
        row.get(
            "research_name"
        )
        or row.get(
            "model_name"
        )
        or row.get(
            "strategy"
        )
        or "Pesquisa"
    )

    return str(
        value
    )


def _research_label(
    row: dict[str, Any],
) -> str:
    research_id = _research_id(
        row
    )

    name = _research_name(
        row
    )

    status = str(
        row.get(
            "status"
        )
        or ""
    )

    label = (
        name
        + " — "
        + research_id
    )

    if status:
        label += (
            " — "
            + status
        )

    return label


def _researches() -> list[
    dict[str, Any]
]:
    rows = list_researches()

    return [
        row
        for row in rows
        if _research_id(
            row
        )
    ]


def _select_research(
    rows: list[
        dict[str, Any]
    ],
) -> str | None:
    if not rows:
        st.info(
            "Nenhuma pesquisa disponível."
        )
        return None

    by_id = {
        _research_id(
            row
        ): row
        for row in rows
    }

    research_ids = list(
        by_id.keys()
    )

    active = str(
        st.session_state.get(
            "active_research_id"
        )
        or ""
    )

    if active in by_id:
        default_index = (
            research_ids.index(
                active
            )
        )

    else:
        default_index = 0

    selected = st.selectbox(
        "Pesquisa",
        options=research_ids,
        index=default_index,
        format_func=lambda value: (
            _research_label(
                by_id[
                    value
                ]
            )
        ),
        key=(
            "product01_selected_research"
        ),
    )

    if not selected:
        return None

    st.session_state[
        "active_research_id"
    ] = str(
        selected
    )

    return str(
        selected
    )


def _selected_row(
    rows: list[
        dict[str, Any]
    ],
    research_id: str,
) -> dict[str, Any]:
    for row in rows:
        if (
            _research_id(
                row
            )
            == research_id
        ):
            return row

    return {}


def _render_summary(
    row: dict[str, Any],
) -> None:
    st.subheader(
        "Resumo"
    )

    col_a, col_b, col_c = (
        st.columns(
            3
        )
    )

    with col_a:
        st.metric(
            "Status",
            str(
                row.get(
                    "status"
                )
                or "—"
            ),
        )

    with col_b:
        st.metric(
            "Mercado",
            str(
                row.get(
                    "market"
                )
                or "—"
            ),
        )

    with col_c:
        st.metric(
            "Ativo",
            str(
                row.get(
                    "asset"
                )
                or "—"
            ),
        )

    hypothesis = row.get(
        "hypothesis"
    )

    if hypothesis:
        st.markdown(
            "#### Hipótese"
        )

        st.write(
            str(
                hypothesis
            )
        )

    period_start = row.get(
        "period_start"
    )

    period_end = row.get(
        "period_end"
    )

    if (
        period_start
        or period_end
    ):
        st.caption(
            (
                "Período: "
                f"{period_start or '—'}"
                " → "
                f"{period_end or '—'}"
            )
        )


def render() -> None:
    page_title(
        "Pesquisas",
        (
            "Cada pesquisa é um projeto "
            "quantitativo completo."
        ),
    )

    rows = _researches()

    research_id = (
        _select_research(
            rows
        )
    )

    if research_id is None:
        return

    row = _selected_row(
        rows,
        research_id,
    )

    tabs = st.tabs(
        list(
            RESEARCH_TABS
        )
    )

    with tabs[0]:
        _render_summary(
            row
        )

    with tabs[1]:
        render_questions(
            research_id
        )

    with tabs[2]:
        render_result(
            research_id
        )

    with tabs[3]:
        render_experiments(
            research_id
        )

    with tabs[4]:
        render_research_analytics(
            research_id
        )

    with tabs[5]:
        render_conclusions(
            research_id
        )
