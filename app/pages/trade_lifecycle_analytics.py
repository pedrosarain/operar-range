from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.common import (
    dataframe_view,
    metric_cards,
    page_header,
    section_title,
)
from app.data_access import (
    consolidated_analytics,
    lifecycle_comparison,
    trade2_analytics,
)
from app.formatting import (
    NA_TEXT,
    format_float,
    format_integer,
    format_percent,
    format_points,
)


def _value(
    row: dict,
    field: str,
    formatter,
) -> str:
    value = row.get(
        field
    )

    if value is None:
        return NA_TEXT

    return formatter(
        value
    )


def _first_row(
    dataframe: pd.DataFrame,
) -> dict | None:
    if dataframe.empty:
        return None

    return (
        dataframe.iloc[0]
        .to_dict()
    )


def _render_trade2(
    dataframe: pd.DataFrame,
) -> None:
    section_title(
        "Trade 2",
        (
            "Analytics específicos do "
            "segundo trade do ciclo."
        ),
    )

    row = _first_row(
        dataframe
    )

    if row is None:
        st.info(
            "Analytics do Trade 2 indisponíveis."
        )
        return

    metric_cards(
        [
            (
                "Elegíveis",
                _value(
                    row,
                    "trade2_eligible_count",
                    format_integer,
                ),
            ),
            (
                "Ocorreram",
                _value(
                    row,
                    "trade2_occurred_count",
                    format_integer,
                ),
            ),
            (
                "Executados",
                _value(
                    row,
                    "trade2_executed_count",
                    format_integer,
                ),
            ),
            (
                "Vencedores",
                _value(
                    row,
                    "trade2_winning_count",
                    format_integer,
                ),
            ),
            (
                "Perdedores",
                _value(
                    row,
                    "trade2_losing_count",
                    format_integer,
                ),
            ),
            (
                "Break-even",
                _value(
                    row,
                    "trade2_breakeven_count",
                    format_integer,
                ),
            ),
            (
                "Runner",
                _value(
                    row,
                    "trade2_runner_count",
                    format_integer,
                ),
            ),
            (
                "Resultado ponderado",
                _value(
                    row,
                    "trade2_weighted_result_points",
                    format_points,
                ),
            ),
        ],
        columns=4,
    )

    with st.expander(
        "Tabela completa — Trade 2",
        expanded=False,
    ):
        dataframe_view(
            dataframe,
            height=360,
        )


def _render_consolidated(
    dataframe: pd.DataFrame,
) -> None:
    section_title(
        "Consolidado",
        (
            "Estatísticas calculadas sobre "
            "consolidated_result_points."
        ),
    )

    row = _first_row(
        dataframe
    )

    if row is None:
        st.info(
            "Analytics consolidados indisponíveis."
        )
        return

    metric_cards(
        [
            (
                "Total de ciclos",
                _value(
                    row,
                    "total_cycles",
                    format_integer,
                ),
            ),
            (
                "Ciclos com Trade 2",
                _value(
                    row,
                    "cycles_with_trade2",
                    format_integer,
                ),
            ),
            (
                "Trade 2 %",
                _value(
                    row,
                    "trade2_pct",
                    format_percent,
                ),
            ),
            (
                "Ciclos recuperados",
                _value(
                    row,
                    "recovered_cycle_count",
                    format_integer,
                ),
            ),
            (
                "Recovery %",
                _value(
                    row,
                    "recovery_pct",
                    format_percent,
                ),
            ),
            (
                "Resultado total",
                _value(
                    row,
                    "total_result_points",
                    format_points,
                ),
            ),
            (
                "Expectancy",
                _value(
                    row,
                    "expectancy_points_per_cycle",
                    format_points,
                ),
            ),
            (
                "Average cycle",
                _value(
                    row,
                    "average_cycle_points",
                    format_points,
                ),
            ),
            (
                "Median",
                _value(
                    row,
                    "median_cycle_points",
                    format_points,
                ),
            ),
            (
                "Melhor ciclo",
                _value(
                    row,
                    "best_cycle_points",
                    format_points,
                ),
            ),
            (
                "Pior ciclo",
                _value(
                    row,
                    "worst_cycle_points",
                    format_points,
                ),
            ),
            (
                "Profit Factor",
                _value(
                    row,
                    "profit_factor",
                    format_float,
                ),
            ),
            (
                "Payoff",
                _value(
                    row,
                    "payoff_ratio",
                    format_float,
                ),
            ),
            (
                "Win Rate",
                _value(
                    row,
                    "win_rate_pct",
                    format_percent,
                ),
            ),
            (
                "Loss Rate",
                _value(
                    row,
                    "loss_rate_pct",
                    format_percent,
                ),
            ),
            (
                "Breakeven Rate",
                _value(
                    row,
                    "breakeven_rate_pct",
                    format_percent,
                ),
            ),
            (
                "Drawdown",
                _value(
                    row,
                    "max_drawdown_points",
                    format_points,
                ),
            ),
            (
                "Máx. sequência vencedora",
                _value(
                    row,
                    "max_consecutive_wins",
                    format_integer,
                ),
            ),
            (
                "Máx. sequência perdedora",
                _value(
                    row,
                    "max_consecutive_losses",
                    format_integer,
                ),
            ),
        ],
        columns=4,
    )

    with st.expander(
        "Tabela completa — Consolidado",
        expanded=False,
    ):
        dataframe_view(
            dataframe,
            height=420,
        )


def _render_comparison(
    dataframe: pd.DataFrame,
) -> None:
    section_title(
        "Comparação",
        (
            "Trade 1 versus Trade 1 + Trade 2. "
            "Somente números; nenhuma conclusão "
            "é produzida pela plataforma."
        ),
    )

    row = _first_row(
        dataframe
    )

    if row is None:
        st.info(
            "Comparação indisponível."
        )
        return

    metric_cards(
        [
            (
                "Δ Resultado total",
                _value(
                    row,
                    "difference_total_result_points",
                    format_points,
                ),
            ),
            (
                "Δ Expectancy",
                _value(
                    row,
                    "difference_expectancy_points",
                    format_points,
                ),
            ),
            (
                "Δ Profit Factor",
                _value(
                    row,
                    "difference_profit_factor",
                    format_float,
                ),
            ),
            (
                "Δ Drawdown",
                _value(
                    row,
                    "difference_max_drawdown_points",
                    format_points,
                ),
            ),
            (
                "Δ Win Rate",
                _value(
                    row,
                    "difference_win_rate_pct",
                    format_percent,
                ),
            ),
        ],
        columns=5,
    )

    with st.expander(
        "Tabela completa — Comparação",
        expanded=False,
    ):
        dataframe_view(
            dataframe,
            height=360,
        )


def render() -> None:
    page_header(
        "Trade Lifecycle Analytics",
        (
            "Analytics read-only do Trade 2, "
            "ciclo consolidado e comparação "
            "com o Trade 1."
        ),
    )

    trade2 = trade2_analytics()
    consolidated = (
        consolidated_analytics()
    )
    comparison = (
        lifecycle_comparison()
    )

    if (
        trade2.empty
        and consolidated.empty
        and comparison.empty
    ):
        st.info(
            (
                "Trade Lifecycle Analytics "
                "ainda não foi produzido "
                "para a pesquisa ativa."
            )
        )
        return

    _render_trade2(
        trade2
    )

    st.divider()

    _render_consolidated(
        consolidated
    )

    st.divider()

    _render_comparison(
        comparison
    )


if __name__ == "__main__":
    render()
