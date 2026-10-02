from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
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
    research_paths,
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
    return str(
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


def _strategy_name(
    row: dict[str, Any],
) -> str:
    return str(
        row.get(
            "strategy"
        )
        or row.get(
            "model_name"
        )
        or "Não disponível"
    )


def _research_label(
    row: dict[str, Any],
) -> str:
    name = _research_name(
        row
    )

    strategy = _strategy_name(
        row
    )

    market = str(
        row.get(
            "market"
        )
        or "—"
    )

    asset = str(
        row.get(
            "asset"
        )
        or "—"
    )

    status = str(
        row.get(
            "status"
        )
        or "—"
    )

    return (
        name
        + " · "
        + strategy
        + " · "
        + market
        + "/"
        + asset
        + " · "
        + status
    )


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
        "Selecionar pesquisa",
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


def _read_manifest(
    research_id: str,
) -> pl.DataFrame:
    try:
        paths = research_paths(
            research_id
        )

        path_value = paths.get(
            "experiment_manifest"
        )

        if path_value is None:
            return pl.DataFrame()

        path = Path(
            path_value
        )

        if not path.exists():
            return pl.DataFrame()

        return pl.read_parquet(
            path
        )

    except Exception:
        return pl.DataFrame()


def _session_count(
    row: dict[str, Any],
) -> Any:
    value = row.get(
        "sessions_total"
    )

    if value is not None:
        return value

    research_id = _research_id(
        row
    )

    try:
        paths = research_paths(
            research_id
        )

        metrics_path = paths.get(
            "metrics"
        )

        if (
            metrics_path is None
            or not Path(
                metrics_path
            ).exists()
        ):
            return None

        frame = pl.read_parquet(
            metrics_path
        )

        if (
            frame.is_empty()
            or "sessions_total"
            not in frame.columns
        ):
            return None

        return frame[
            "sessions_total"
        ][0]

    except Exception:
        return None


def _experiment_count(
    row: dict[str, Any],
) -> Any:
    direct = (
        row.get(
            "experiments_valid"
        )
        or row.get(
            "experiments_generated"
        )
    )

    if direct is not None:
        return direct

    manifest = _read_manifest(
        _research_id(
            row
        )
    )

    if manifest.is_empty():
        return None

    if (
        "experiment_id"
        not in manifest.columns
    ):
        return manifest.height

    return (
        manifest[
            "experiment_id"
        ]
        .drop_nulls()
        .n_unique()
    )


def _render_identity(
    row: dict[str, Any],
) -> None:
    st.caption(
        "Nome"
    )

    st.markdown(
        "## "
        + _research_name(
            row
        )
    )

    st.caption(
        (
            "Projeto científico quantitativo"
        )
    )

    c1, c2, c3, c4 = st.columns(
        4
    )

    with c1:
        st.metric(
            "Estratégia",
            _strategy_name(
                row
            ),
        )

    with c2:
        st.metric(
            "Mercado",
            str(
                row.get(
                    "market"
                )
                or "—"
            ),
        )

    with c3:
        st.metric(
            "Ativo",
            str(
                row.get(
                    "asset"
                )
                or "—"
            ),
        )

    with c4:
        st.metric(
            "Status",
            str(
                row.get(
                    "status"
                )
                or "—"
            ),
        )

    c1, c2, c3 = st.columns(
        3
    )

    period = (
        str(
            row.get(
                "period_start"
            )
            or "—"
        )
        + " → "
        + str(
            row.get(
                "period_end"
            )
            or "—"
        )
    )

    with c1:
        st.metric(
            "Período",
            period,
        )

    with c2:
        sessions = _session_count(
            row
        )

        st.metric(
            "Pregões",
            (
                sessions
                if sessions is not None
                else "—"
            ),
        )

    with c3:
        experiments = (
            _experiment_count(
                row
            )
        )

        st.metric(
            "Experimentos",
            (
                experiments
                if experiments is not None
                else "—"
            ),
        )

    research_id = _research_id(
        row
    )

    if research_id:
        st.caption(
            "ID interno: "
            + research_id
        )


def _render_summary(
    row: dict[str, Any],
) -> None:
    st.subheader(
        "Resumo"
    )

    hypothesis = row.get(
        "hypothesis"
    )

    description = row.get(
        "description"
    )

    if description:
        st.markdown(
            "#### Sobre esta pesquisa"
        )

        st.write(
            str(
                description
            )
        )

    if hypothesis:
        st.markdown(
            "#### Hipótese registrada"
        )

        st.write(
            str(
                hypothesis
            )
        )

    if (
        not description
        and not hypothesis
    ):
        st.info(
            (
                "Esta pesquisa não possui "
                "descrição ou hipótese textual "
                "registrada."
            )
        )


def render() -> None:
    page_title(
        "Pesquisas",
        (
            "Cada pesquisa é um projeto "
            "científico quantitativo."
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

    st.divider()

    _render_identity(
        row
    )

    st.divider()

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
