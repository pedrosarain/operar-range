from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app.components.common import (
    metric_cards,
    page_header,
    section_title,
)
from app.data_access import (
    experiment_metrics,
    experiments_table,
    rankings_overall,
)
from app.formatting import (
    NA_TEXT,
    format_integer,
)
from operar_range.research_workspace import (
    list_researches,
)


def _missing(
    value: Any,
) -> bool:
    if value is None:
        return True

    try:
        return bool(
            pd.isna(
                value
            )
        )

    except Exception:
        return False


def _text(
    value: Any,
) -> str:
    if _missing(
        value
    ):
        return NA_TEXT

    return str(
        value
    )


def _number(
    value: Any,
    *,
    decimals: int = 2,
) -> str:
    if _missing(
        value
    ):
        return NA_TEXT

    try:
        number = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return _text(
            value
        )

    return (
        f"{number:,.{decimals}f}"
        .replace(
            ",",
            "_",
        )
        .replace(
            ".",
            ",",
        )
        .replace(
            "_",
            ".",
        )
    )


def _latest_research(
    rows: list[
        dict[str, Any]
    ],
) -> dict[str, Any] | None:
    if not rows:
        return None

    def key(
        row: dict[str, Any],
    ) -> str:
        return str(
            row.get(
                "created_at"
            )
            or ""
        )

    return max(
        rows,
        key=key,
    )


def _running_researches(
    rows: list[
        dict[str, Any]
    ],
) -> int:
    terminal = {
        "COMPLETED",
        "FAILED",
        "CANCELLED",
    }

    return sum(
        1
        for row in rows
        if str(
            row.get(
                "status"
            )
            or ""
        ).upper()
        not in terminal
    )


def _top_ranked_experiment() -> str:
    try:
        rankings = (
            rankings_overall()
        )

    except Exception:
        return NA_TEXT

    if rankings.empty:
        return NA_TEXT

    required = {
        "experiment_id",
        "rank_position",
    }

    if not required.issubset(
        rankings.columns
    ):
        return NA_TEXT

    frame = rankings[
        rankings[
            "rank_position"
        ]
        == 1
    ]

    if frame.empty:
        return NA_TEXT

    if (
        "ranking_type"
        in frame.columns
    ):
        overall = frame[
            frame[
                "ranking_type"
            ]
            .astype(
                str
            )
            .str.upper()
            .eq(
                "OVERALL"
            )
        ]

        if not overall.empty:
            frame = overall

    return _text(
        frame.iloc[
            0
        ].get(
            "experiment_id"
        )
    )


def _extreme_metric(
    column: str,
) -> tuple[
    str,
    str,
]:
    try:
        metrics = (
            experiment_metrics()
        )

    except Exception:
        return (
            NA_TEXT,
            NA_TEXT,
        )

    if (
        metrics.empty
        or column
        not in metrics.columns
    ):
        return (
            NA_TEXT,
            NA_TEXT,
        )

    frame = metrics.copy()

    numeric = pd.to_numeric(
        frame[
            column
        ],
        errors="coerce",
    )

    valid = numeric.notna()

    if not valid.any():
        return (
            NA_TEXT,
            NA_TEXT,
        )

    index = (
        numeric[
            valid
        ]
        .idxmax()
    )

    experiment_id = (
        frame.loc[
            index
        ].get(
            "experiment_id"
        )
    )

    value = numeric.loc[
        index
    ]

    return (
        _text(
            experiment_id
        ),
        _number(
            value
        ),
    )


def _leader_configuration(
    experiment_id: str,
) -> str:
    if (
        not experiment_id
        or experiment_id
        == NA_TEXT
    ):
        return NA_TEXT

    try:
        experiments = (
            experiments_table()
        )

    except Exception:
        return NA_TEXT

    if (
        experiments.empty
        or "experiment_id"
        not in experiments.columns
    ):
        return NA_TEXT

    frame = experiments[
        experiments[
            "experiment_id"
        ]
        .astype(
            str
        )
        == str(
            experiment_id
        )
    ]

    if frame.empty:
        return NA_TEXT

    row = frame.iloc[
        0
    ]

    parts: list[str] = []

    labels = (
        (
            "stop_points",
            "Stop",
        ),
        (
            "partial_1_points",
            "Parcial 1",
        ),
        (
            "partial_1_pct",
            "% Parcial 1",
        ),
        (
            "final_target_points",
            "Alvo final",
        ),
        (
            "runner_enabled",
            "Runner",
        ),
        (
            "break_even_enabled",
            "Break-even",
        ),
    )

    for column, label in labels:
        if (
            column
            not in frame.columns
        ):
            continue

        value = row.get(
            column
        )

        if _missing(
            value
        ):
            continue

        if isinstance(
            value,
            bool,
        ):
            text = (
                "Sim"
                if value
                else "Não"
            )

        else:
            text = _text(
                value
            )

        parts.append(
            f"{label}: {text}"
        )

    if not parts:
        return NA_TEXT

    return " · ".join(
        parts
    )


def render() -> None:
    page_header(
        "Dashboard",
        (
            "O estado atual do laboratório "
            "em respostas, não em estruturas."
        ),
    )

    try:
        researches = (
            list_researches()
        )

    except Exception:
        researches = []

    latest = (
        _latest_research(
            researches
        )
    )

    top_experiment = (
        _top_ranked_experiment()
    )

    (
        expectancy_experiment,
        expectancy_value,
    ) = _extreme_metric(
        "expectancy_points_per_trade"
    )

    (
        pf_experiment,
        pf_value,
    ) = _extreme_metric(
        "profit_factor"
    )

    section_title(
        "Agora"
    )

    metric_cards(
        [
            (
                "Pesquisas",
                format_integer(
                    len(
                        researches
                    )
                ),
            ),
            (
                "Rodando agora",
                format_integer(
                    _running_researches(
                        researches
                    )
                ),
            ),
            (
                "Última pesquisa",
                (
                    _text(
                        latest.get(
                            "research_name"
                        )
                    )
                    if latest
                    else NA_TEXT
                ),
            ),
            (
                "Status da última",
                (
                    _text(
                        latest.get(
                            "status"
                        )
                    )
                    if latest
                    else NA_TEXT
                ),
            ),
        ],
        columns=4,
    )

    st.divider()

    section_title(
        "Onde está o melhor resultado registrado?"
    )

    metric_cards(
        [
            (
                "Experimento líder",
                top_experiment,
            ),
            (
                "Maior Expectancy",
                expectancy_value,
            ),
            (
                "Experimento — Expectancy",
                expectancy_experiment,
            ),
            (
                "Maior Profit Factor",
                pf_value,
            ),
            (
                "Experimento — Profit Factor",
                pf_experiment,
            ),
        ],
        columns=5,
    )

    st.caption(
        (
            "Os destaques acima são apenas uma "
            "apresentação de métricas e rankings "
            "já materializados pelos motores."
        )
    )

    st.divider()

    section_title(
        "Configuração do experimento líder"
    )

    leader_config = (
        _leader_configuration(
            top_experiment
        )
    )

    if leader_config == NA_TEXT:
        st.info(
            (
                "Não há configuração validada "
                "disponível para o experimento "
                "líder atual."
            )
        )

    else:
        st.success(
            leader_config
        )

    st.divider()

    section_title(
        "Descobertas e hipóteses"
    )

    left, right = st.columns(
        2
    )

    with left:
        st.markdown(
            "#### Última descoberta"
        )

        st.info(
            (
                "Nenhuma descoberta estruturada "
                "foi localizada nos artifacts "
                "atuais."
            )
        )

    with right:
        st.markdown(
            "#### Hipótese confirmada"
        )

        st.info(
            (
                "Nenhum campo estruturado de "
                "confirmação de hipótese está "
                "disponível no inventário atual."
            )
        )

    st.caption(
        (
            "O Dashboard não infere descobertas "
            "nem confirma hipóteses por conta "
            "própria. Quando esses resultados "
            "existirem nos artifacts, serão "
            "apresentados aqui."
        )
    )

    st.divider()

    section_title(
        "O que fazer agora?"
    )

    st.markdown(
        """
- **Pesquisas:** abra o projeto quantitativo e veja seu resultado consolidado.
- **Experimentos:** investigue a configuração e as métricas de um experimento.
- **Analytics:** aprofunde performance, risco, path e gestão.
- **Comparações:** compare pesquisas ou experimentos já executados.
- **Estratégias:** consulte o conhecimento acumulado por modelo e família.
"""
    )
