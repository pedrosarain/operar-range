from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
import streamlit as st

from app.product.shared import (
    page_title,
)
from operar_range.research_workspace import (
    list_researches,
    research_paths,
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


def _research_label(
    row: dict[str, Any],
) -> str:
    name = (
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

    return (
        str(
            name
        )
        + " — "
        + _research_id(
            row
        )
    )


def _completed_researches() -> list[
    dict[str, Any]
]:
    rows = list_researches()

    return [
        row
        for row in rows
        if (
            _research_id(
                row
            )
            and str(
                row.get(
                    "status"
                )
                or ""
            ).upper()
            == "COMPLETED"
        )
    ]


def _read_parquet(
    research_id: str,
    key: str,
) -> pl.DataFrame:
    try:
        paths = research_paths(
            research_id
        )

        value = paths.get(
            key
        )

        if value is None:
            return pl.DataFrame()

        path = Path(
            value
        )

        if not path.exists():
            return pl.DataFrame()

        return pl.read_parquet(
            path
        )

    except Exception:
        return pl.DataFrame()


def _number(
    value: Any,
    decimals: int = 2,
) -> str:
    if value is None:
        return "—"

    try:
        numeric = float(
            value
        )

        if numeric.is_integer():
            return str(
                int(
                    numeric
                )
            )

        return (
            f"{numeric:.{decimals}f}"
        )

    except Exception:
        return str(
            value
        )


def _percent(
    value: Any,
) -> str:
    if value is None:
        return "—"

    try:
        return (
            f"{float(value):.2f}%"
        )

    except Exception:
        return "—"


def _first_row(
    frame: pl.DataFrame,
    *,
    experiment_id: str | None = None,
) -> dict[str, Any] | None:
    if frame.is_empty():
        return None

    selected = frame

    if (
        experiment_id
        and "experiment_id"
        in selected.columns
    ):
        filtered = selected.filter(
            pl.col(
                "experiment_id"
            )
            == experiment_id
        )

        if not filtered.is_empty():
            selected = filtered

    if selected.is_empty():
        return None

    return selected.row(
        0,
        named=True,
    )


def _experiment_ids(
    *frames: pl.DataFrame,
) -> list[str]:
    values: set[str] = set()

    for frame in frames:
        if (
            frame.is_empty()
            or "experiment_id"
            not in frame.columns
        ):
            continue

        for value in (
            frame[
                "experiment_id"
            ]
            .drop_nulls()
            .unique()
            .to_list()
        ):
            values.add(
                str(
                    value
                )
            )

    return sorted(
        values
    )


def _safe_columns(
    frame: pl.DataFrame,
    columns: list[str],
) -> pl.DataFrame:
    available = [
        column
        for column in columns
        if column in frame.columns
    ]

    if not available:
        return pl.DataFrame()

    return frame.select(
        available
    )


def _render_overall(
    metrics: pl.DataFrame,
    experiment_id: str | None,
) -> None:
    st.subheader(
        "Visão geral"
    )

    row = _first_row(
        metrics,
        experiment_id=(
            experiment_id
        ),
    )

    if row is None:
        st.info(
            "Métricas gerais indisponíveis."
        )
        return

    c1, c2, c3, c4 = st.columns(
        4
    )

    with c1:
        st.metric(
            "Win Rate",
            _percent(
                row.get(
                    "win_rate_pct"
                )
            ),
        )

    with c2:
        st.metric(
            "Expectancy",
            _number(
                row.get(
                    "expectancy_points_per_trade"
                )
            ),
        )

    with c3:
        profit_factor = row.get(
            "profit_factor"
        )

        if profit_factor is None:
            profit_factor = row.get(
                "profit_factor_status"
            )

        st.metric(
            "Profit Factor",
            _number(
                profit_factor
            ),
        )

    with c4:
        st.metric(
            "Max Drawdown",
            _number(
                row.get(
                    "max_drawdown_points"
                )
            ),
        )

    c1, c2, c3, c4 = st.columns(
        4
    )

    with c1:
        st.metric(
            "Trades",
            _number(
                row.get(
                    "trade1_count"
                )
            ),
        )

    with c2:
        st.metric(
            "Dias positivos",
            _number(
                row.get(
                    "positive_days"
                )
            ),
        )

    with c3:
        st.metric(
            "Dias negativos",
            _number(
                row.get(
                    "negative_days"
                )
            ),
        )

    with c4:
        st.metric(
            "Resultado total",
            _number(
                row.get(
                    "total_weighted_points"
                )
            ),
        )

    st.caption(
        (
            "Valores apresentados diretamente "
            "dos artifacts quantitativos da Research."
        )
    )


def _render_periods(
    monthly: pl.DataFrame,
    yearly: pl.DataFrame,
    experiment_id: str | None,
) -> None:
    st.subheader(
        "Períodos"
    )

    period_tabs = st.tabs(
        [
            "Mensal",
            "Anual",
        ]
    )

    with period_tabs[0]:
        frame = monthly

        if (
            experiment_id
            and not frame.is_empty()
            and "experiment_id"
            in frame.columns
        ):
            frame = frame.filter(
                pl.col(
                    "experiment_id"
                )
                == experiment_id
            )

        if frame.is_empty():
            st.info(
                "Analytics mensal indisponível."
            )

        else:
            visible = _safe_columns(
                frame,
                [
                    "year",
                    "month",
                    "sessions_total",
                    "trade1_count",
                    "winning_trades",
                    "losing_trades",
                    "win_rate_pct",
                    "expectancy_points_per_trade",
                    "profit_factor",
                    "max_drawdown_points",
                    "total_weighted_points",
                    "positive_days",
                    "negative_days",
                ],
            )

            st.dataframe(
                visible.to_pandas(),
                use_container_width=True,
                hide_index=True,
            )

    with period_tabs[1]:
        frame = yearly

        if (
            experiment_id
            and not frame.is_empty()
            and "experiment_id"
            in frame.columns
        ):
            frame = frame.filter(
                pl.col(
                    "experiment_id"
                )
                == experiment_id
            )

        if frame.is_empty():
            st.info(
                "Analytics anual indisponível."
            )

        else:
            visible = _safe_columns(
                frame,
                [
                    "year",
                    "sessions_total",
                    "trade1_count",
                    "winning_trades",
                    "losing_trades",
                    "win_rate_pct",
                    "expectancy_points_per_trade",
                    "profit_factor",
                    "max_drawdown_points",
                    "total_weighted_points",
                    "positive_days",
                    "negative_days",
                ],
            )

            st.dataframe(
                visible.to_pandas(),
                use_container_width=True,
                hide_index=True,
            )


def _render_trade2(
    trade2: pl.DataFrame,
    consolidated: pl.DataFrame,
    comparison: pl.DataFrame,
    experiment_id: str | None,
) -> None:
    st.subheader(
        "Trade 2"
    )

    trade2_row = _first_row(
        trade2,
        experiment_id=(
            experiment_id
        ),
    )

    if trade2_row is None:
        st.info(
            "Analytics de Trade 2 indisponível."
        )

    else:
        c1, c2, c3, c4 = st.columns(
            4
        )

        with c1:
            st.metric(
                "Elegíveis",
                _number(
                    trade2_row.get(
                        "trade2_eligible_count"
                    )
                ),
            )

        with c2:
            st.metric(
                "Novo rompimento",
                _number(
                    trade2_row.get(
                        "trade2_occurred_count"
                    )
                ),
            )

        with c3:
            st.metric(
                "Executados",
                _number(
                    trade2_row.get(
                        "trade2_executed_count"
                    )
                ),
            )

        with c4:
            st.metric(
                "Resultado Trade 2",
                _number(
                    trade2_row.get(
                        "trade2_weighted_result_points"
                    )
                ),
            )

        c1, c2, c3 = st.columns(
            3
        )

        with c1:
            st.metric(
                "Positivos",
                _number(
                    trade2_row.get(
                        "trade2_winning_count"
                    )
                ),
            )

        with c2:
            st.metric(
                "Negativos",
                _number(
                    trade2_row.get(
                        "trade2_losing_count"
                    )
                ),
            )

        with c3:
            st.metric(
                "Break-even",
                _number(
                    trade2_row.get(
                        "trade2_breakeven_count"
                    )
                ),
            )

    consolidated_row = _first_row(
        consolidated,
        experiment_id=(
            experiment_id
        ),
    )

    if consolidated_row is not None:
        st.markdown(
            "#### Ciclo consolidado"
        )

        c1, c2, c3, c4 = st.columns(
            4
        )

        with c1:
            st.metric(
                "Ciclos",
                _number(
                    consolidated_row.get(
                        "total_cycles"
                    )
                ),
            )

        with c2:
            st.metric(
                "Ciclos com Trade 2",
                _number(
                    consolidated_row.get(
                        "cycles_with_trade2"
                    )
                ),
            )

        with c3:
            st.metric(
                "Ciclos recuperados",
                _number(
                    consolidated_row.get(
                        "recovered_cycle_count"
                    )
                ),
            )

        with c4:
            st.metric(
                "Resultado consolidado",
                _number(
                    consolidated_row.get(
                        "total_result_points"
                    )
                ),
            )

    comparison_row = _first_row(
        comparison,
        experiment_id=(
            experiment_id
        ),
    )

    if comparison_row is not None:
        st.markdown(
            "#### Trade 1 × ciclo completo"
        )

        visible = {
            "Trade 1": {
                "Resultado": (
                    comparison_row.get(
                        "trade1_total_result_points"
                    )
                ),
                "Expectancy": (
                    comparison_row.get(
                        "trade1_expectancy_points"
                    )
                ),
                "Profit Factor": (
                    comparison_row.get(
                        "trade1_profit_factor"
                    )
                ),
                "Drawdown": (
                    comparison_row.get(
                        "trade1_max_drawdown_points"
                    )
                ),
                "Win Rate": (
                    comparison_row.get(
                        "trade1_win_rate_pct"
                    )
                ),
            },
            "Trade 1 + Trade 2": {
                "Resultado": (
                    comparison_row.get(
                        "consolidated_total_result_points"
                    )
                ),
                "Expectancy": (
                    comparison_row.get(
                        "consolidated_expectancy_points"
                    )
                ),
                "Profit Factor": (
                    comparison_row.get(
                        "consolidated_profit_factor"
                    )
                ),
                "Drawdown": (
                    comparison_row.get(
                        "consolidated_max_drawdown_points"
                    )
                ),
                "Win Rate": (
                    comparison_row.get(
                        "consolidated_win_rate_pct"
                    )
                ),
            },
        }

        table = pl.DataFrame(
            [
                {
                    "Escopo": scope,
                    **values,
                }
                for scope, values
                in visible.items()
            ]
        )

        st.dataframe(
            table.to_pandas(),
            use_container_width=True,
            hide_index=True,
        )


def _render_rankings(
    rankings: pl.DataFrame,
    experiment_id: str | None,
) -> None:
    st.subheader(
        "Rankings existentes"
    )

    if rankings.is_empty():
        st.info(
            "Nenhum ranking disponível."
        )
        return

    frame = rankings

    if (
        experiment_id
        and "experiment_id"
        in frame.columns
    ):
        filtered = frame.filter(
            pl.col(
                "experiment_id"
            )
            == experiment_id
        )

        if not filtered.is_empty():
            frame = filtered

    if "scope" in frame.columns:
        overall = frame.filter(
            pl.col(
                "scope"
            )
            == "OVERALL"
        )

        if not overall.is_empty():
            frame = overall

    visible = _safe_columns(
        frame,
        [
            "ranking_type",
            "rank_position",
            "experiment_id",
            "metric_name",
            "metric_value",
            "trade_count",
            "sessions_total",
            "max_drawdown_points",
        ],
    )

    if visible.is_empty():
        st.info(
            "Ranking disponível, mas sem campos "
            "de apresentação compatíveis."
        )
        return

    st.dataframe(
        visible.to_pandas(),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        (
            "A interface apenas apresenta rankings "
            "já produzidos pelo backend. Nenhum novo "
            "critério de ranking é calculado aqui."
        )
    )


def render() -> None:
    page_title(
        "Analytics",
        (
            "Toda estatística quantitativa da "
            "Research fica centralizada aqui."
        ),
    )

    researches = (
        _completed_researches()
    )

    if not researches:
        st.info(
            "Nenhuma Research concluída disponível."
        )
        return

    by_id = {
        _research_id(
            row
        ): row
        for row in researches
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
        index = research_ids.index(
            active
        )

    else:
        index = 0

    research_id = st.selectbox(
        "Pesquisa",
        options=research_ids,
        index=index,
        format_func=lambda value: (
            _research_label(
                by_id[
                    value
                ]
            )
        ),
        key=(
            "product01_analytics_research"
        ),
    )

    if not research_id:
        return

    st.session_state[
        "active_research_id"
    ] = str(
        research_id
    )

    metrics = _read_parquet(
        research_id,
        "metrics",
    )

    monthly = _read_parquet(
        research_id,
        "metrics_monthly",
    )

    yearly = _read_parquet(
        research_id,
        "metrics_yearly",
    )

    rankings = _read_parquet(
        research_id,
        "rankings",
    )

    trade2 = _read_parquet(
        research_id,
        "trade2_analytics",
    )

    consolidated = _read_parquet(
        research_id,
        "consolidated_analytics",
    )

    comparison = _read_parquet(
        research_id,
        "lifecycle_comparison",
    )

    experiment_ids = _experiment_ids(
        metrics,
        rankings,
        trade2,
        consolidated,
        comparison,
    )

    experiment_id = None

    if experiment_ids:
        experiment_id = st.selectbox(
            "Experimento",
            options=experiment_ids,
            key=(
                "product01_analytics_experiment"
            ),
        )

    tabs = st.tabs(
        [
            "Geral",
            "Períodos",
            "Trade 2",
            "Rankings",
        ]
    )

    with tabs[0]:
        _render_overall(
            metrics,
            experiment_id,
        )

    with tabs[1]:
        _render_periods(
            monthly,
            yearly,
            experiment_id,
        )

    with tabs[2]:
        _render_trade2(
            trade2,
            consolidated,
            comparison,
            experiment_id,
        )

    with tabs[3]:
        _render_rankings(
            rankings,
            experiment_id,
        )
