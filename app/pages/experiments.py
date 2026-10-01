from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.common import (
    apply_multiselect_filter,
    dataframe_view,
    filter_multiselect,
    formatted_config_rows,
    formatted_identity_rows,
    key_value_panel,
    page_header,
    search_dataframe,
    section_title,
)
from app.data_access import (
    available_columns,
    experiment_detail,
    experiments_table,
)
from app.formatting import (
    NA_TEXT,
    as_text,
    format_boolean,
    format_float,
    format_hash,
    format_integer,
    format_percent,
    format_points,
    metric_value_or_status,
)


METRIC_FIELDS = [
    (
        "Total weighted points",
        "total_weighted_points",
        None,
        format_points,
    ),
    (
        "Expectancy",
        "expectancy_points_per_trade",
        None,
        format_points,
    ),
    (
        "Profit Factor",
        "profit_factor",
        "profit_factor_status",
        format_float,
    ),
    (
        "Payoff",
        "payoff_ratio",
        "payoff_ratio_status",
        format_float,
    ),
    (
        "Win rate",
        "win_rate_pct",
        None,
        format_percent,
    ),
    (
        "Trades",
        "trade1_count",
        None,
        format_integer,
    ),
    (
        "Max drawdown",
        "max_drawdown_points",
        None,
        format_points,
    ),
    (
        "Average trade",
        "average_weighted_points",
        None,
        format_points,
    ),
    (
        "Best trade",
        "best_trade_points",
        None,
        format_points,
    ),
    (
        "Worst trade",
        "worst_trade_points",
        None,
        format_points,
    ),
    (
        "Max consecutive wins",
        "max_consecutive_wins",
        None,
        format_integer,
    ),
    (
        "Max consecutive losses",
        "max_consecutive_losses",
        None,
        format_integer,
    ),
]


def _format_table_boolean(
    value,
) -> str:
    return format_boolean(
        value
    )


def _filter_stop(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    if (
        dataframe.empty
        or "stop_points"
        not in dataframe.columns
    ):
        return dataframe

    numeric = pd.to_numeric(
        dataframe[
            "stop_points"
        ],
        errors="coerce",
    )

    valid = numeric.dropna()

    if valid.empty:
        return dataframe

    minimum = float(
        valid.min()
    )

    maximum = float(
        valid.max()
    )

    if minimum == maximum:
        st.caption(
            f"Stop disponível: {minimum:g}"
        )
        return dataframe

    selected = st.slider(
        "Stop",
        min_value=minimum,
        max_value=maximum,
        value=(
            minimum,
            maximum,
        ),
        key=(
            "experiments_stop"
        ),
    )

    mask = (
        numeric
        >= selected[0]
    ) & (
        numeric
        <= selected[1]
    )

    return dataframe[
        mask.fillna(
            False
        )
    ].copy()


def _boolean_filter(
    dataframe: pd.DataFrame,
    *,
    column: str,
    label: str,
    key: str,
) -> pd.DataFrame:
    if (
        dataframe.empty
        or column
        not in dataframe.columns
    ):
        return dataframe

    selection = st.selectbox(
        label,
        options=[
            "ALL",
            "ON",
            "OFF",
        ],
        key=key,
    )

    if selection == "ALL":
        return dataframe

    target = (
        selection == "ON"
    )

    normalized = dataframe[
        column
    ].map(
        lambda value: (
            bool(value)
            if not pd.isna(
                value
            )
            else None
        )
    )

    return dataframe[
        normalized
        == target
    ].copy()


def _display_experiment_table(
    dataframe: pd.DataFrame,
) -> None:
    if dataframe.empty:
        st.info(
            "Nenhum experimento corresponde "
            "aos filtros atuais."
        )
        return

    display = dataframe.copy()

    if (
        "break_even_enabled"
        in display.columns
    ):
        display[
            "break_even_enabled"
        ] = display[
            "break_even_enabled"
        ].map(
            _format_table_boolean
        )

    if (
        "runner_enabled"
        in display.columns
    ):
        display[
            "runner_enabled"
        ] = display[
            "runner_enabled"
        ].map(
            _format_table_boolean
        )

    preferred = [
        "experiment_id",
        "experiment_name",
        "family",
        "generation",
        "status",
        "stop_points",
        "partial_1_points",
        "partial_1_pct",
        "partial_2_points",
        "partial_2_pct",
        "partial_3_points",
        "partial_3_pct",
        "break_even_enabled",
        "break_even_after_partial",
        "runner_enabled",
        "runner_pct",
        "runner_rule",
        "final_target_points",
    ]

    visible = (
        available_columns(
            display,
            preferred,
        )
    )

    dataframe_view(
        display[
            visible
        ],
        height=470,
    )


def _render_metrics(
    metrics: dict | None,
) -> None:
    section_title(
        "Métricas OVERALL"
    )

    if not metrics:
        st.info(
            "Métricas ainda não produzidas "
            "para este experimento."
        )
        return

    items = []

    for (
        label,
        value_field,
        status_field,
        formatter,
    ) in METRIC_FIELDS:
        value = metrics.get(
            value_field
        )

        status = (
            metrics.get(
                status_field
            )
            if status_field
            else None
        )

        items.append(
            (
                label,
                metric_value_or_status(
                    value=value,
                    status=status,
                    formatter=formatter,
                ),
            )
        )

    key_value_panel(
        items
    )


def _render_trade_lifecycle(
    results: list[dict],
) -> None:
    section_title(
        "Trade Lifecycle",
        (
            "Resultados do Trade 1, Trade 2 "
            "e ciclo operacional completo."
        ),
    )

    if not results:
        st.info(
            (
                "Resultados por sessão "
                "indisponíveis para este "
                "experimento."
            )
        )
        return

    rows = []

    for row in results:
        trade1_result = row.get(
            "trade1_result_points"
        )

        #
        # Compatibilidade com pesquisas
        # anteriores à Etapa 19.
        #
        if (
            trade1_result is None
            and row.get(
                "total_weighted_points"
            )
            is not None
        ):
            trade1_result = row.get(
                "total_weighted_points"
            )

        trade2_result = row.get(
            "trade2_result_points"
        )

        consolidated = row.get(
            "consolidated_result_points"
        )

        if (
            consolidated is None
            and trade1_result is not None
        ):
            consolidated = trade1_result

        rows.append(
            {
                "Pregão": (
                    as_text(
                        row.get(
                            "date"
                        )
                    )
                ),
                "Trade 1": (
                    format_points(
                        trade1_result
                    )
                    if trade1_result
                    is not None
                    else NA_TEXT
                ),
                "Trade 2 elegível": (
                    format_boolean(
                        row.get(
                            "trade2_eligible"
                        )
                    )
                    if row.get(
                        "trade2_eligible"
                    )
                    is not None
                    else NA_TEXT
                ),
                "Trade 2 ocorreu": (
                    format_boolean(
                        row.get(
                            "trade2_occurred"
                        )
                    )
                    if row.get(
                        "trade2_occurred"
                    )
                    is not None
                    else NA_TEXT
                ),
                "Trade 2": (
                    format_points(
                        trade2_result
                    )
                    if trade2_result
                    is not None
                    else NA_TEXT
                ),
                "Resultado consolidado": (
                    format_points(
                        consolidated
                    )
                    if consolidated
                    is not None
                    else NA_TEXT
                ),
                "Saída Trade 2": (
                    as_text(
                        row.get(
                            "trade2_final_reason"
                        )
                    )
                ),
            }
        )

    dataframe_view(
        pd.DataFrame(
            rows
        ),
        height=360,
    )


def _render_experiment_detail(
    experiment_id: str,
) -> None:
    detail = experiment_detail(
        experiment_id
    )

    experiment = detail.get(
        "experiment"
    )

    metrics = detail.get(
        "metrics"
    )

    results = detail.get(
        "results"
    ) or []

    st.divider()

    section_title(
        "Detalhes do experimento"
    )

    if not experiment:
        st.info(
            "Definição do experimento "
            "indisponível."
        )
        return

    left, right = st.columns(
        [1, 1]
    )

    with left:
        key_value_panel(
            formatted_identity_rows(
                experiment
            ),
            title="Experimento",
        )

    with right:
        key_value_panel(
            formatted_config_rows(
                experiment
            ),
            title="Configuração",
        )

    _render_metrics(
        metrics
    )

    st.divider()

    _render_trade_lifecycle(
        results
    )



def render() -> None:
    page_header(
        "Experimentos",
        (
            "Laboratório científico da pesquisa: "
            "hipótese, configuração, resultado "
            "e métricas principais."
        ),
    )

    dataframe = (
        experiments_table()
    )

    if dataframe.empty:
        st.info(
            "Dataset de experimentos "
            "indisponível."
        )
        return

    section_title(
        "Filtros"
    )

    search = st.text_input(
        "Buscar experimento",
        key="experiments_search",
    )

    filtered = (
        search_dataframe(
            dataframe,
            query=search,
            columns=[
                "experiment_id",
                "experiment_name",
            ],
        )
    )

    row_1 = st.columns(
        3
    )

    with row_1[0]:
        families = (
            filter_multiselect(
                label="Family",
                dataframe=filtered,
                column="family",
                key=(
                    "experiments_family"
                ),
            )
        )

    with row_1[1]:
        generations = (
            filter_multiselect(
                label="Generation",
                dataframe=filtered,
                column="generation",
                key=(
                    "experiments_generation"
                ),
            )
        )

    with row_1[2]:
        statuses = (
            filter_multiselect(
                label="Status",
                dataframe=filtered,
                column="status",
                key=(
                    "experiments_status"
                ),
            )
        )

    filtered = (
        apply_multiselect_filter(
            filtered,
            column="family",
            values=families,
        )
    )

    filtered = (
        apply_multiselect_filter(
            filtered,
            column="generation",
            values=generations,
        )
    )

    filtered = (
        apply_multiselect_filter(
            filtered,
            column="status",
            values=statuses,
        )
    )

    row_2 = st.columns(
        3
    )

    with row_2[0]:
        filtered = _filter_stop(
            filtered
        )

    with row_2[1]:
        filtered = (
            _boolean_filter(
                filtered,
                column=(
                    "runner_enabled"
                ),
                label="Runner",
                key=(
                    "experiments_runner"
                ),
            )
        )

    with row_2[2]:
        filtered = (
            _boolean_filter(
                filtered,
                column=(
                    "break_even_enabled"
                ),
                label="Break-even",
                key=(
                    "experiments_be"
                ),
            )
        )

    st.caption(
        (
            f"{len(filtered)} experimento(s) "
            "visível(is)."
        )
    )

    _display_experiment_table(
        filtered
    )

    if filtered.empty:
        return

    experiment_options = (
        filtered[
            "experiment_id"
        ]
        .astype(str)
        .tolist()
    )

    selected = st.selectbox(
        "Selecionar experimento para detalhe",
        options=(
            experiment_options
        ),
        key=(
            "experiments_selected"
        ),
    )

    if selected:
        _render_experiment_detail(
            selected
        )


if __name__ == "__main__":
    render()