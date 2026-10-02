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

if str(
    SRC_ROOT
) not in sys.path:
    sys.path.insert(
        0,
        str(
            SRC_ROOT
        ),
    )

if str(
    PROJECT_ROOT
) not in sys.path:
    sys.path.insert(
        0,
        str(
            PROJECT_ROOT
        ),
    )


from app.components.common import (  # noqa: E402
    apply_terminal_theme,
)
from app.product import admin  # noqa: E402
from app.product import analytics  # noqa: E402
from app.product import dashboard  # noqa: E402
from app.product import research  # noqa: E402
from app.product import strategies  # noqa: E402
from app.product.navigation import (  # noqa: E402
    PUBLIC_ROUTE_LABELS,
    PUBLIC_ROUTE_SLUGS,
)


APP_TITLE = (
    "Operar Range — Research Workspace V2"
)


#
# PRODUCT-01 public contract.
#
# These are the ONLY public routes.
#
PUBLIC_ROUTES = {
    "/dashboard": (
        "Dashboard",
        dashboard.render,
    ),
    "/research": (
        "Pesquisas",
        research.render,
    ),
    "/strategies": (
        "Estratégias",
        strategies.render,
    ),
    "/analytics": (
        "Analytics",
        analytics.render,
    ),
    "/admin": (
        "Administração",
        admin.render,
    ),
}


#
# Public navigation and legacy internal compatibility
# are intentionally separate contracts.
#
# PUBLIC_ROUTES is the ONLY source used to render the
# Research Workspace public navigation.
#
# PAGES preserves historical imports used by legacy
# tests/internal modules without exposing those pages
# in the public interface.
#
from app.pages import query as _legacy_query
from app.pages import research_comparison as _legacy_research_comparison


PAGES = {
    **PUBLIC_ROUTES,
    "Query": _legacy_query.render,
    "Research Comparison": (
        _legacy_research_comparison.render
    ),
}


DEFAULT_ROUTE = (
    "/dashboard"
)


def configure_page() -> None:
    st.set_page_config(
        page_title=(
            APP_TITLE
        ),
        page_icon="📊",
        layout="wide",
        initial_sidebar_state=(
            "expanded"
        ),
    )


def _route_labels() -> dict[
    str,
    str,
]:
    return {
        slug: value[
            0
        ]
        for slug, value
        in PUBLIC_ROUTES.items()
    }


def _selected_route() -> str:
    current = (
        st.session_state.get(
            "product01_route"
        )
    )

    if (
        current
        not in PUBLIC_ROUTES
    ):
        current = (
            DEFAULT_ROUTE
        )

        st.session_state[
            "product01_route"
        ] = current

    return str(
        current
    )


def navigate(
    route: str,
) -> None:
    if (
        route
        not in PUBLIC_ROUTES
    ):
        raise ValueError(
            (
                "PRODUCT-01 public route "
                f"not available: {route}"
            )
        )

    st.session_state[
        "product01_route"
    ] = route


def render_sidebar() -> str:
    current = (
        _selected_route()
    )

    labels = (
        _route_labels()
    )

    route_options = list(
        PUBLIC_ROUTES.keys()
    )

    with st.sidebar:
        st.markdown(
            "## OPERAR RANGE"
        )

        st.caption(
            "Research Workspace V2"
        )

        st.divider()

        selected = st.radio(
            "Navegação",
            options=(
                route_options
            ),
            index=(
                route_options.index(
                    current
                )
            ),
            format_func=lambda route: (
                labels[
                    route
                ]
            ),
            key=(
                "product01_route"
            ),
        )

        st.divider()

        st.caption(
            "LABORATÓRIO DE PERGUNTAS"
        )

        st.caption(
            (
                "Formule uma pergunta, obtenha "
                "a resposta e audite os pregões "
                "que compõem o resultado."
            )
        )

    return str(
        selected
    )


def main() -> None:
    configure_page()

    apply_terminal_theme()

    route = (
        render_sidebar()
    )

    page = (
        PUBLIC_ROUTES.get(
            route
        )
    )

    if page is None:
        st.error(
            "Rota indisponível."
        )
        return

    _label, renderer = (
        page
    )

    try:
        renderer()

    except FileNotFoundError:
        st.error(
            (
                "Os dados necessários para "
                "esta resposta não estão "
                "disponíveis."
            )
        )

    except KeyError as exc:
        st.error(
            (
                "Uma informação necessária "
                "não está disponível para "
                "esta pesquisa."
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
                "Não foi possível apresentar "
                "esta área com os dados atuais."
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


#
# Contract guards.
#
assert tuple(
    PUBLIC_ROUTES.keys()
) == PUBLIC_ROUTE_SLUGS

assert tuple(
    value[
        0
    ]
    for value
    in PUBLIC_ROUTES.values()
) == PUBLIC_ROUTE_LABELS


if __name__ == "__main__":
    main()
