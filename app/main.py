from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from app.components.common import (  # noqa: E402
    apply_terminal_theme,
)
from app.pages import compare  # noqa: E402
from app.pages import experiments  # noqa: E402
from app.pages import overview  # noqa: E402
from app.pages import rankings  # noqa: E402
from app.pages import sessions  # noqa: E402
from app.pages import system  # noqa: E402


APP_TITLE = "Operar Range — Research Terminal"


PAGES = {
    "Overview": overview.render,
    "Experiments": experiments.render,
    "Rankings": rankings.render,
    "Compare": compare.render,
    "Sessions": sessions.render,
    "System": system.render,
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


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            "## OPERAR RANGE"
        )

        st.caption(
            "Research Terminal V1"
        )

        st.divider()

        selected_page = (
            st.radio(
                "Navigation",
                options=list(
                    PAGES.keys()
                ),
                index=0,
                key=(
                    "research_terminal_page"
                ),
            )
        )

        st.divider()

        st.caption(
            "READ ONLY"
        )

        st.caption(
            (
                "Esta interface consulta "
                "outputs homologados da "
                "plataforma. Nenhuma alteração "
                "de experimentos, regras ou "
                "resultados é realizada pela UI."
            )
        )

    return selected_page


def main() -> None:
    configure_page()

    apply_terminal_theme()

    selected_page = (
        render_sidebar()
    )

    renderer = PAGES.get(
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
            str(exc)
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


if __name__ == "__main__":
    main()