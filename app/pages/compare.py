from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.common import (
    dataframe_view,
    key_value_panel,
    page_header,
    section_title,
)
from app.data_access import (
    compare_experiments,
    experiments_table,
)
from app.formatting import (
    NA_TEXT,
    as_text,
    format_boolean,
    format_float,
    format_integer,
    format_percent,
    format_points,
    metric_value_or_status,
    numeric_difference,
)


CONFIG_COMPARISON_FIELDS = [
    (
        "Stop",
        "stop_points",
        format_points,
    ),
    (
        "Partial 1",
        "partial_1_points",
        format_points,
    ),
    (
        "Partial 1 %",
        "partial_1_pct",
        format_percent,
    ),
    (
        "Partial 2",
        "partial_2_points",
        format_points,
    ),
    (
        "Partial 2 %",
        "partial_2_pct",
        format_percent,
    ),
    (
        "Partial 3",
        "partial_3_points",
        format_points,
    ),
    (
        "Partial 3 %",
        "partial_3_pct",
        format_percent,
    ),
    (
        "Break-even",
        "break_even_enabled",
        format_boolean,
    ),
    (
        "BE after partial",
        "break_even_after_partial",
        as_text,
    ),
    (
        "Runner",
        "runner_enabled",
        format_boolean,
    ),
    (
        "Runner %",
        "runner_pct",
        format_percent,
    ),
    (
        "Runner rule",
        "runner_rule",
        as_text,
    ),
    (
        "Final target",
        "final_target_points",
        format_points,
    ),
]


METRIC_COMPARISON_FIELDS = [
    {
        "label": "Result",
        "field": "total_weighted_points",
        "status_field": None,
        "formatter": format_points,
        "difference_formatter": format_points,
    },
    {
        "label": "Expectancy",
        "field": "expectancy_points_per_trade",
        "status_field": None,
        "formatter": format_points,
        "difference_formatter": format_points,
    },
    {
        "label": "Profit Factor",
        "field": "profit_factor",
        "status_field": "profit_factor_status",
        "formatter": format_float,
        "difference_formatter": format_float,
    },
    {
        "label": "Win rate",
        "field": "win_rate_pct",
        "status_field": None,
        "formatter": format_percent,
        "difference_formatter": format_percent,
    },
    {
        "label": "Max drawdown",
        "field": "max_drawdown_points",
        "status_field": None,
        "formatter": format_points,
        "difference_formatter": format_points,
    },
    {
        "label": "Payoff",
        "field": "payoff_ratio",
        "status_field": "payoff_ratio_status",
        "formatter": format_float,
        "difference_formatter": format_float,
    },
    {
        "label": "Trades",
        "field": "trade1_count",
        "status_field": None,
        "formatter": format_integer,
        "difference_formatter": format_integer,
    },
    {
        "label": "Frequency",
        "field": "trade_frequency_pct",
        "status_field": None,
        "formatter": format_percent,
        "difference_formatter": format_percent,
    },
]


def _experiment_label(
    row: pd.Series,
) -> str:
    experiment_id = str(
        row.get(
            "experiment_id",
            "",
        )
    )

    experiment_name = row.get(
        "experiment_name"
    )

    if (
        experiment_name is not None
        and not pd.isna(
            experiment_name
        )
        and str(
            experiment_name
        ).strip()
    ):
        return (
            f"{experiment_id} — "
            f"{experiment_name}"
        )

    return experiment_id


def _experiment_options(
    dataframe: pd.DataFrame,
) -> list[str]:
    if (
        dataframe.empty
        or "experiment_id"
        not in dataframe.columns
    ):
        return []

    return (
        dataframe[
            "experiment_id"
        ]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .sort_values()
        .tolist()
    )


def _identity_panel(
    *,
    title: str,
    experiment: dict | None,
) -> None:
    if not experiment:
        st.info(
            "Definição do experimento "
            "indisponível."
        )
        return

    key_value_panel(
        [
            (
                "Experiment ID",
                as_text(
                    experiment.get(
                        "experiment_id"
                    )
                ),
            ),
            (
                "Experiment name",
                as_text(
                    experiment.get(
                        "experiment_name"
                    )
                ),
            ),
            (
                "Family",
                as_text(
                    experiment.get(
                        "family"
                    )
                ),
            ),
            (
                "Generation",
                as_text(
                    experiment.get(
                        "generation"
                    )
                ),
            ),
            (
                "Status",
                as_text(
                    experiment.get(
                        "status"
                    )
                ),
            ),
            (
                "Config SHA-256",
                as_text(
                    experiment.get(
                        "config_sha256"
                    )
                ),
            ),
        ],
        title=title,
    )


def _config_comparison_table(
    experiment_a: dict | None,
    experiment_b: dict | None,
) -> pd.DataFrame:
    if (
        not experiment_a
        or not experiment_b
    ):
        return pd.DataFrame()

    rows = []

    for (
        label,
        field,
        formatter,
    ) in CONFIG_COMPARISON_FIELDS:
        left = experiment_a.get(
            field
        )

        right = experiment_b.get(
            field
        )

        rows.append(
            {
                "Field": label,
                "Experiment A": (
                    formatter(
                        left
                    )
                ),
                "Experiment B": (
                    formatter(
                        right
                    )
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def _metric_display(
    metrics: dict | None,
    field: str,
    status_field: str | None,
    formatter,
) -> str:
    if not metrics:
        return NA_TEXT

    status = (
        metrics.get(
            status_field
        )
        if status_field
        else None
    )

    return metric_value_or_status(
        value=metrics.get(
            field
        ),
        status=status,
        formatter=formatter,
    )


def _metric_difference(
    metrics_a: dict | None,
    metrics_b: dict | None,
    *,
    field: str,
    formatter,
) -> str:
    if (
        not metrics_a
        or not metrics_b
    ):
        return NA_TEXT

    difference = numeric_difference(
        metrics_a.get(
            field
        ),
        metrics_b.get(
            field
        ),
    )

    if difference is None:
        return NA_TEXT

    return formatter(
        difference
    )


def _metric_comparison_table(
    metrics_a: dict | None,
    metrics_b: dict | None,
) -> pd.DataFrame:
    rows = []

    for definition in (
        METRIC_COMPARISON_FIELDS
    ):
        rows.append(
            {
                "Metric": (
                    definition[
                        "label"
                    ]
                ),
                "Experiment A": (
                    _metric_display(
                        metrics_a,
                        definition[
                            "field"
                        ],
                        definition[
                            "status_field"
                        ],
                        definition[
                            "formatter"
                        ],
                    )
                ),
                "Experiment B": (
                    _metric_display(
                        metrics_b,
                        definition[
                            "field"
                        ],
                        definition[
                            "status_field"
                        ],
                        definition[
                            "formatter"
                        ],
                    )
                ),
                "A - B": (
                    _metric_difference(
                        metrics_a,
                        metrics_b,
                        field=(
                            definition[
                                "field"
                            ]
                        ),
                        formatter=(
                            definition[
                                "difference_formatter"
                            ]
                        ),
                    )
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def render() -> None:
    page_header(
        "Compare",
        (
            "Comparação lado a lado entre "
            "dois experimentos, sem declarar "
            "vencedor."
        ),
    )

    experiments = (
        experiments_table()
    )

    if experiments.empty:
        st.info(
            "Dataset de experimentos "
            "indisponível."
        )
        return

    options = (
        _experiment_options(
            experiments
        )
    )

    if len(options) < 2:
        st.info(
            "São necessários pelo menos "
            "dois experimentos para comparação."
        )
        return

    selector_columns = (
        st.columns(
            2
        )
    )

    with selector_columns[0]:
        experiment_a = (
            st.selectbox(
                "Experiment A",
                options=options,
                index=0,
                key=(
                    "compare_a"
                ),
            )
        )

    remaining_for_b = [
        experiment_id
        for experiment_id in options
        if experiment_id
        != experiment_a
    ]

    with selector_columns[1]:
        experiment_b = (
            st.selectbox(
                "Experiment B",
                options=(
                    remaining_for_b
                ),
                index=0,
                key=(
                    "compare_b"
                ),
            )
        )

    comparison = (
        compare_experiments(
            experiment_a,
            experiment_b,
        )
    )

    detail_a = comparison[
        "a"
    ]

    detail_b = comparison[
        "b"
    ]

    experiment_data_a = (
        detail_a.get(
            "experiment"
        )
    )

    experiment_data_b = (
        detail_b.get(
            "experiment"
        )
    )

    metrics_a = detail_a.get(
        "metrics"
    )

    metrics_b = detail_b.get(
        "metrics"
    )

    st.divider()

    section_title(
        "Identidade"
    )

    left, right = st.columns(
        2
    )

    with left:
        _identity_panel(
            title=(
                "Experiment A"
            ),
            experiment=(
                experiment_data_a
            ),
        )

    with right:
        _identity_panel(
            title=(
                "Experiment B"
            ),
            experiment=(
                experiment_data_b
            ),
        )

    st.divider()

    section_title(
        "Configuração"
    )

    config_table = (
        _config_comparison_table(
            experiment_data_a,
            experiment_data_b,
        )
    )

    dataframe_view(
        config_table,
        height=500,
    )

    st.divider()

    section_title(
        "Métricas OVERALL",
        (
            "A coluna A - B mostra somente "
            "a diferença numérica quando "
            "ambos os valores são comparáveis."
        ),
    )

    metrics_table = (
        _metric_comparison_table(
            metrics_a,
            metrics_b,
        )
    )

    dataframe_view(
        metrics_table,
        height=430,
    )

    st.caption(
        (
            "A comparação é descritiva. "
            "O Research Terminal não declara "
            "winner, best strategy ou optimal."
        )
    )


if __name__ == "__main__":
    render()