from __future__ import annotations

from collections import defaultdict
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


def _strategy_key(
    row: dict[str, Any],
) -> str:
    for field in (
        "model_id",
        "model_name",
        "strategy",
        "family",
    ):
        value = row.get(
            field
        )

        if not _missing(
            value
        ):
            return str(
                value
            )

    return "Estratégia sem identificação"


def _strategy_label(
    rows: list[
        dict[str, Any]
    ],
) -> str:
    for row in rows:
        for field in (
            "model_name",
            "model_id",
            "strategy",
            "family",
        ):
            value = row.get(
                field
            )

            if not _missing(
                value
            ):
                return str(
                    value
                )

    return "Estratégia"


def _unique_values(
    rows: list[
        dict[str, Any]
    ],
    field: str,
) -> list[str]:
    return sorted(
        {
            str(
                row.get(
                    field
                )
            )
            for row in rows
            if not _missing(
                row.get(
                    field
                )
            )
        }
    )


def _research_experiment_count(
    rows: list[
        dict[str, Any]
    ],
) -> int:
    return sum(
        int(
            row.get(
                "experiments_valid"
            )
            or 0
        )
        for row in rows
    )


def _metric_summary(
    experiment_ids: set[str],
) -> dict[str, Any]:
    try:
        metrics = (
            experiment_metrics()
        )

    except Exception:
        return {}

    if (
        metrics.empty
        or "experiment_id"
        not in metrics.columns
        or not experiment_ids
    ):
        return {}

    frame = metrics[
        metrics[
            "experiment_id"
        ]
        .astype(
            str
        )
        .isin(
            experiment_ids
        )
    ].copy()

    if frame.empty:
        return {}

    result: dict[str, Any] = {}

    for column in (
        "expectancy_points_per_trade",
        "profit_factor",
        "win_rate_pct",
        "max_drawdown_points",
    ):
        if column not in frame.columns:
            continue

        numeric = pd.to_numeric(
            frame[
                column
            ],
            errors="coerce",
        )

        if not numeric.notna().any():
            continue

        if column == "max_drawdown_points":
            value = numeric.min()

        else:
            value = numeric.max()

        result[
            column
        ] = value

    return result


def _strategy_experiment_ids(
    rows: list[
        dict[str, Any]
    ],
) -> set[str]:
    try:
        experiments = (
            experiments_table()
        )

    except Exception:
        return set()

    if (
        experiments.empty
        or "experiment_id"
        not in experiments.columns
    ):
        return set()

    families = set(
        _unique_values(
            rows,
            "family",
        )
    )

    if (
        families
        and "family"
        in experiments.columns
    ):
        subset = experiments[
            experiments[
                "family"
            ]
            .astype(
                str
            )
            .isin(
                families
            )
        ]

    else:
        subset = experiments

    return {
        str(
            value
        )
        for value in subset[
            "experiment_id"
        ]
        .dropna()
        .tolist()
    }


def _format_metric(
    value: Any,
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
        f"{number:.2f}"
        .replace(
            ".",
            ",",
        )
    )


def render() -> None:
    page_header(
        "Estratégias",
        (
            "Biblioteca de conhecimento construída "
            "a partir das pesquisas já executadas."
        ),
    )

    try:
        researches = (
            list_researches()
        )

    except Exception:
        researches = []

    if not researches:
        st.info(
            (
                "Ainda não existem pesquisas "
                "suficientes para construir a "
                "biblioteca de estratégias."
            )
        )
        return

    grouped: dict[
        str,
        list[
            dict[str, Any]
        ],
    ] = defaultdict(
        list
    )

    for row in researches:
        grouped[
            _strategy_key(
                row
            )
        ].append(
            row
        )

    keys = sorted(
        grouped
    )

    section_title(
        "Biblioteca"
    )

    selected = st.selectbox(
        "Estratégia",
        options=keys,
        format_func=lambda value: (
            _strategy_label(
                grouped[
                    value
                ]
            )
        ),
    )

    rows = grouped[
        selected
    ]

    label = (
        _strategy_label(
            rows
        )
    )

    versions = (
        _unique_values(
            rows,
            "generation",
        )
    )

    statuses = (
        _unique_values(
            rows,
            "status",
        )
    )

    experiment_ids = (
        _strategy_experiment_ids(
            rows
        )
    )

    metrics = (
        _metric_summary(
            experiment_ids
        )
    )

    metric_cards(
        [
            (
                "Estratégia",
                label,
            ),
            (
                "Pesquisas",
                format_integer(
                    len(
                        rows
                    )
                ),
            ),
            (
                "Experimentos",
                format_integer(
                    _research_experiment_count(
                        rows
                    )
                ),
            ),
            (
                "Versões",
                (
                    ", ".join(
                        versions
                    )
                    if versions
                    else NA_TEXT
                ),
            ),
            (
                "Status",
                (
                    ", ".join(
                        statuses
                    )
                    if statuses
                    else NA_TEXT
                ),
            ),
        ],
        columns=5,
    )

    st.divider()

    left, right = st.columns(
        2
    )

    with left:
        section_title(
            "Objetivo e hipótese"
        )

        hypothesis = next(
            (
                row.get(
                    "hypothesis"
                )
                for row in rows
                if not _missing(
                    row.get(
                        "hypothesis"
                    )
                )
            ),
            None,
        )

        if hypothesis:
            st.markdown(
                f"**Hipótese:** {hypothesis}"
            )

        else:
            st.info(
                (
                    "Hipótese estruturada não "
                    "disponível para esta estratégia."
                )
            )

        models = (
            _unique_values(
                rows,
                "model_name",
            )
        )

        if models:
            st.markdown(
                (
                    "**Modelos pesquisados:** "
                    + ", ".join(
                        models
                    )
                )
            )

    with right:
        section_title(
            "Performance registrada"
        )

        metric_cards(
            [
                (
                    "Expectancy",
                    _format_metric(
                        metrics.get(
                            "expectancy_points_per_trade"
                        )
                    ),
                ),
                (
                    "Profit Factor",
                    _format_metric(
                        metrics.get(
                            "profit_factor"
                        )
                    ),
                ),
                (
                    "Win Rate",
                    _format_metric(
                        metrics.get(
                            "win_rate_pct"
                        )
                    ),
                ),
                (
                    "Drawdown",
                    _format_metric(
                        metrics.get(
                            "max_drawdown_points"
                        )
                    ),
                ),
            ],
            columns=2,
        )

    st.divider()

    section_title(
        "Histórico de pesquisas"
    )

    display_rows: list[
        dict[str, Any]
    ] = []

    for row in sorted(
        rows,
        key=lambda item: str(
            item.get(
                "created_at"
            )
            or ""
        ),
        reverse=True,
    ):
        display_rows.append(
            {
                "Pesquisa": (
                    row.get(
                        "research_name"
                    )
                    or row.get(
                        "research_id"
                    )
                ),
                "Período": (
                    f"{_text(row.get('period_start'))}"
                    " → "
                    f"{_text(row.get('period_end'))}"
                ),
                "Status": _text(
                    row.get(
                        "status"
                    )
                ),
                "Experimentos": (
                    row.get(
                        "experiments_valid"
                    )
                ),
                "Criada em": _text(
                    row.get(
                        "created_at"
                    )
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(
            display_rows
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    section_title(
        "Validações e descobertas"
    )

    st.info(
        (
            "Os artifacts atuais não possuem um "
            "registro estruturado de validações e "
            "descobertas por estratégia. A interface "
            "não cria conclusões que não estejam "
            "registradas pela plataforma."
        )
    )

    st.divider()

    section_title(
        "O que fazer agora?"
    )

    st.markdown(
        """
- Abra **Pesquisas** para analisar uma pesquisa específica.
- Abra **Experimentos** para investigar uma configuração.
- Use **Analytics** para aprofundar a evidência quantitativa.
- Use **Comparações** para verificar diferenças entre pesquisas ou experimentos.
"""
    )
