from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

SRC_ROOT = (
    PROJECT_ROOT
    / "src"
)

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(SRC_ROOT),
    )

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from app.components.common import (  # noqa: E402
    apply_terminal_theme,
)

#
# UX-01 — páginas principais.
#
from app.pages import administration  # noqa: E402
from app.pages import analytics  # noqa: E402
from app.pages import comparisons  # noqa: E402
from app.pages import dashboard  # noqa: E402
from app.pages import experiments  # noqa: E402
from app.pages import researches  # noqa: E402
from app.pages import strategies  # noqa: E402

#
# Rotas históricas.
#
# Permanecem registradas para compatibilidade
# interna e com contratos homologados anteriores,
# mas NÃO aparecem na navegação principal.
#
from app.pages import compare  # noqa: E402
from app.pages import data  # noqa: E402
from app.pages import new_research  # noqa: E402
from app.pages import overview  # noqa: E402
from app.pages import path_aggregation  # noqa: E402
from app.pages import path_analysis  # noqa: E402
from app.pages import path_query  # noqa: E402
from app.pages import query  # noqa: E402
from app.pages import rankings  # noqa: E402
from app.pages import research_comparison  # noqa: E402
from app.pages import sessions  # noqa: E402
from app.pages import system  # noqa: E402
from app.pages import trade_lifecycle_analytics  # noqa: E402


APP_TITLE = (
    "Operar Range — Research Workspace"
)


#
# ÚNICA navegação principal visível da UX-01.
#
PRIMARY_PAGES = {
    "Dashboard": dashboard.render,
    "Pesquisas": researches.render,
    "Estratégias": strategies.render,
    "Experimentos": experiments.render,
    "Analytics": analytics.render,
    "Comparações": comparisons.render,
    "Administração": administration.render,
}


#
# Registro público completo.
#
# PAGES continua preservando rotas homologadas
# por stages anteriores. Isso não significa que
# essas páginas façam parte do menu principal.
#
PAGES = {
    **PRIMARY_PAGES,

    "Overview": overview.render,
    "Path Analysis": path_analysis.render,
    "Path Aggregation": path_aggregation.render,
    "Path Query": path_query.render,
    "Data": data.render,
    "Nova Pesquisa": new_research.render,
    "Experiments": experiments.render,
    "Trade Lifecycle Analytics": (
        trade_lifecycle_analytics.render
    ),
    "Rankings": rankings.render,
    "Query": query.render,
    "Research Comparison": (
        research_comparison.render
    ),
    "Compare": compare.render,
    "Sessions": sessions.render,
    "System": system.render,
}


#
# Rotas antigas que eventualmente sejam
# solicitadas pela própria Presentation Layer
# são redirecionadas para o novo hub equivalente.
#
LEGACY_PAGE_REDIRECTS = {
    "Overview": "Dashboard",
    "Path Analysis": "Analytics",
    "Path Aggregation": "Analytics",
    "Path Query": "Analytics",
    "Data": "Administração",
    "Nova Pesquisa": "Pesquisas",
    "Experiments": "Experimentos",
    "Trade Lifecycle Analytics": "Analytics",
    "Rankings": "Analytics",
    "Query": "Administração",
    "Research Comparison": "Comparações",
    "Compare": "Comparações",
    "Sessions": "Administração",
    "System": "Administração",
}


def configure_page() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📊",
        layout="wide",
        initial_sidebar_state=(
            "expanded"
        ),
    )


def _consume_requested_page() -> None:
    requested = (
        st.session_state.pop(
            "requested_terminal_page",
            None,
        )
    )

    if requested is None:
        return

    if requested in PRIMARY_PAGES:
        st.session_state[
            "research_workspace_page"
        ] = requested
        return

    redirected = (
        LEGACY_PAGE_REDIRECTS.get(
            requested
        )
    )

    if redirected is not None:
        st.session_state[
            "research_workspace_page"
        ] = redirected


def render_sidebar() -> str:
    _consume_requested_page()

    active_research_id = (
        st.session_state.get(
            "active_research_id"
        )
    )

    with st.sidebar:
        st.markdown(
            "## OPERAR RANGE"
        )

        st.caption(
            "Research Workspace"
        )

        if active_research_id:
            st.success(
                "PESQUISA ATIVA"
            )

            st.caption(
                str(
                    active_research_id
                )
            )

        else:
            st.info(
                "Nenhuma pesquisa ativa"
            )

        st.divider()

        current = st.session_state.get(
            "research_workspace_page"
        )

        if current not in PRIMARY_PAGES:
            st.session_state[
                "research_workspace_page"
            ] = "Dashboard"

        selected_page = (
            st.radio(
                "Navegação",
                options=list(
                    PRIMARY_PAGES.keys()
                ),
                index=0,
                key=(
                    "research_workspace_page"
                ),
            )
        )

        st.divider()

        st.caption(
            "LABORATÓRIO QUANTITATIVO"
        )

        st.caption(
            (
                "A interface apresenta respostas "
                "da pesquisa. Estruturas técnicas "
                "permanecem em Administração."
            )
        )

    return selected_page


def main() -> None:
    configure_page()

    apply_terminal_theme()

    selected_page = (
        render_sidebar()
    )

    renderer = PRIMARY_PAGES.get(
        selected_page
    )

    if renderer is None:
        st.error(
            "Página indisponível."
        )
        return

    try:
        renderer()

    except FileNotFoundError:
        st.error(
            "Dataset indisponível."
        )

    except KeyError as exc:
        st.error(
            (
                "Informação necessária "
                "não está disponível no "
                "dataset atual."
            )
        )

        st.caption(
            str(
                exc
            )
        )

    except Exception as exc:
        st.error(
            (
                "Não foi possível renderizar "
                "esta página com os dados "
                "atuais."
            )
        )

        st.caption(
            (
                "Tipo do erro: "
                f"{type(exc).__name__}"
            )
        )

        st.caption(
            str(
                exc
            )
        )


if __name__ == "__main__":
    main()
