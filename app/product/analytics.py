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


ANALYTICS_TABS = (
    "Geral",
    "Períodos",
    "Rankings",
    "Distribuições",
    "Correlações",
)


def _render_future_area(
    title: str,
) -> None:
    st.subheader(
        title
    )

    st.info(
        "Disponível em versão futura."
    )


def render() -> None:
    page_title(
        "Analytics",
        (
            "Central estatística do "
            "laboratório quantitativo."
        ),
    )

    st.caption(
        (
            "Esta área apresenta somente "
            "estatísticas e rankings já "
            "produzidos pelo backend."
        )
    )

    researches = (
        _completed_researches()
    )

    if not researches:
        st.info(
            "Nenhuma pesquisa concluída disponível."
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

    experiment_ids = _experiment_ids(
        metrics,
        rankings,
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
        list(
            ANALYTICS_TABS
        )
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
        _render_rankings(
            rankings,
            experiment_id,
        )

    with tabs[3]:
        _render_future_area(
            "Distribuições"
        )

    with tabs[4]:
        _render_future_area(
            "Correlações"
        )
