from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from app.components.common import (
    dataframe_view,
    key_value_panel,
    page_header,
    section_title,
    status_badge,
)
from app.data_access import (
    MONTHLY_SCOPE,
    OVERALL_SCOPE,
    YEARLY_SCOPE,
    available_months,
    available_years,
    experiment_metrics,
    experiments_table,
    ranking_manifest_for_scope,
    rankings_for_scope,
)
from app.formatting import (
    NA_TEXT,
    display_metric_name,
    format_float,
    format_integer,
    format_percent,
    format_points,
    format_ranking_metric,
)


DISPLAYABLE_RANKING_TYPES = [
    "PROFIT_FACTOR",
    "EXPECTANCY",
    "NET_POINTS",
    "WIN_RATE",
    "AVERAGE_TRADE",
    "MAX_DRAWDOWN",
    "PAYOFF",
    "NUMBER_OF_TRADES",
    "FREQUENCY",
    "COMPOSITE_SCORE",
    "CAGR",
    "RECOVERY_FACTOR",
]


def _scope_selector() -> tuple[
    str,
    int | None,
    int | None,
]:
    scope = st.selectbox(
        "Scope",
        options=[
            OVERALL_SCOPE,
            YEARLY_SCOPE,
            MONTHLY_SCOPE,
        ],
        key="rankings_scope",
    )

    year = None
    month = None

    if scope == YEARLY_SCOPE:
        years = available_years()

        if not years:
            st.info(
                "Nenhum ano disponível."
            )
            return (
                scope,
                None,
                None,
            )

        year = st.selectbox(
            "Ano",
            options=years,
            key="rankings_year",
        )

    elif scope == MONTHLY_SCOPE:
        years = available_years()

        if not years:
            st.info(
                "Nenhum ano disponível."
            )
            return (
                scope,
                None,
                None,
            )

        year = st.selectbox(
            "Ano",
            options=years,
            key="rankings_monthly_year",
        )

        months = available_months(
            int(year)
        )

        if not months:
            st.info(
                "Nenhum mês disponível "
                "para o ano selecionado."
            )
            return (
                scope,
                int(year),
                None,
            )

        month = st.selectbox(
            "Mês",
            options=months,
            format_func=lambda value: (
                f"{int(value):02d}"
            ),
            key="rankings_month",
        )

    return (
        scope,
        (
            int(year)
            if year is not None
            else None
        ),
        (
            int(month)
            if month is not None
            else None
        ),
    )


def _available_ranking_types(
    manifest: pd.DataFrame,
) -> list[str]:
    if (
        manifest.empty
        or "ranking_type"
        not in manifest.columns
    ):
        return []

    existing = (
        manifest[
            "ranking_type"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    ordered = [
        ranking_type
        for ranking_type
        in DISPLAYABLE_RANKING_TYPES
        if ranking_type in existing
    ]

    extras = sorted(
        set(existing)
        - set(ordered)
    )

    return [
        *ordered,
        *extras,
    ]


def _ranking_manifest_row(
    manifest: pd.DataFrame,
    ranking_type: str,
) -> dict | None:
    if (
        manifest.empty
        or "ranking_type"
        not in manifest.columns
    ):
        return None

    subset = manifest[
        manifest[
            "ranking_type"
        ].astype(str)
        == str(
            ranking_type
        )
    ]

    if subset.empty:
        return None

    return (
        subset.iloc[0]
        .to_dict()
    )


def _join_supporting_metrics(
    rankings: pd.DataFrame,
) -> pd.DataFrame:
    if rankings.empty:
        return rankings

    experiments = (
        experiments_table()
    )

    metrics = (
        experiment_metrics()
    )

    result = rankings.copy()

    if (
        not experiments.empty
        and "experiment_id"
        in experiments.columns
    ):
        columns = [
            "experiment_id",
            "experiment_name",
            "family",
            "generation",
        ]

        columns = [
            column
            for column in columns
            if column
            in experiments.columns
        ]

        experiment_info = (
            experiments[
                columns
            ]
            .drop_duplicates(
                subset=[
                    "experiment_id"
                ]
            )
        )

        result = result.merge(
            experiment_info,
            on="experiment_id",
            how="left",
            suffixes=(
                "",
                "_registry",
            ),
        )

    if (
        not metrics.empty
        and "experiment_id"
        in metrics.columns
    ):
        columns = [
            "experiment_id",
            "expectancy_points_per_trade",
            "win_rate_pct",
        ]

        columns = [
            column
            for column in columns
            if column
            in metrics.columns
        ]

        supporting = (
            metrics[
                columns
            ]
            .drop_duplicates(
                subset=[
                    "experiment_id"
                ]
            )
        )

        result = result.merge(
            supporting,
            on="experiment_id",
            how="left",
            suffixes=(
                "",
                "_metric",
            ),
        )

    return result


def _ranking_table(
    dataframe: pd.DataFrame,
    ranking_type: str,
) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe

    result = (
        _join_supporting_metrics(
            dataframe
        )
    )

    result = result.copy()

    if "rank_position" in result.columns:
        result[
            "rank"
        ] = result[
            "rank_position"
        ]

    if "metric_value" in result.columns:
        result[
            "metric"
        ] = result.apply(
            lambda row: (
                format_ranking_metric(
                    ranking_type,
                    row.get(
                        "metric_value"
                    ),
                    row.get(
                        "ranking_status"
                    ),
                )
            ),
            axis=1,
        )

    if (
        "max_drawdown_points"
        in result.columns
    ):
        result[
            "drawdown"
        ] = result[
            "max_drawdown_points"
        ].map(
            format_points
        )

    if (
        "expectancy_points_per_trade"
        in result.columns
    ):
        result[
            "expectancy"
        ] = result[
            "expectancy_points_per_trade"
        ].map(
            format_points
        )

    if (
        "win_rate_pct"
        in result.columns
    ):
        result[
            "win_rate"
        ] = result[
            "win_rate_pct"
        ].map(
            format_percent
        )

    preferred = [
        "rank",
        "experiment_id",
        "experiment_name",
        "metric",
        "trade_count",
        "drawdown",
        "expectancy",
        "win_rate",
        "family",
        "generation",
        "ranking_status",
    ]

    visible = [
        column
        for column in preferred
        if column
        in result.columns
    ]

    return result[
        visible
    ]


def _render_composite_details(
    rankings: pd.DataFrame,
    manifest_row: dict,
) -> None:
    st.divider()

    section_title(
        "Composite Score",
        (
            "Score contextual. Os valores "
            "dependem dos pesos e do universo "
            "do ranking já produzido."
        ),
    )

    weights_json = (
        manifest_row.get(
            "weights_json"
        )
    )

    weights = {}

    if weights_json:
        try:
            weights = json.loads(
                str(
                    weights_json
                )
            )
        except Exception:
            weights = {}

    if weights:
        weight_rows = [
            {
                "metric": (
                    display_metric_name(
                        metric
                    )
                ),
                "weight": (
                    format_percent(
                        float(weight)
                        * 100.0
                    )
                ),
            }
            for metric, weight
            in sorted(
                weights.items()
            )
        ]

        dataframe_view(
            pd.DataFrame(
                weight_rows
            ),
            height=240,
        )

    if rankings.empty:
        return

    fields = [
        "rank_position",
        "experiment_id",
        "composite_score",
        "metrics_available_count",
        "metrics_missing_count",
        "effective_weight_sum",
        "missing_metrics",
    ]

    fields = [
        field
        for field in fields
        if field
        in rankings.columns
    ]

    display = rankings[
        fields
    ].copy()

    if (
        "effective_weight_sum"
        in display.columns
    ):
        display[
            "effective_weight_sum"
        ] = display[
            "effective_weight_sum"
        ].map(
            lambda value: (
                format_float(
                    value,
                    decimals=3,
                )
            )
        )

    dataframe_view(
        display,
        height=330,
    )


def render() -> None:
    page_header(
        "Rankings",
        (
            "Consulta dos rankings "
            "quantitativos produzidos "
            "pela Etapa 16."
        ),
    )

    scope, year, month = (
        _scope_selector()
    )

    if (
        scope == YEARLY_SCOPE
        and year is None
    ):
        return

    if (
        scope == MONTHLY_SCOPE
        and (
            year is None
            or month is None
        )
    ):
        return

    rankings = (
        rankings_for_scope(
            scope=scope,
            year=year,
            month=month,
        )
    )

    manifest = (
        ranking_manifest_for_scope(
            scope=scope,
            year=year,
            month=month,
        )
    )

    if manifest.empty:
        st.info(
            "Ranking manifest indisponível "
            "para o scope selecionado."
        )
        return

    ranking_types = (
        _available_ranking_types(
            manifest
        )
    )

    if not ranking_types:
        st.info(
            "Nenhum ranking disponível."
        )
        return

    ranking_type = st.selectbox(
        "Ranking Type",
        options=ranking_types,
        format_func=(
            display_metric_name
        ),
        key=(
            "ranking_type"
        ),
    )

    manifest_row = (
        _ranking_manifest_row(
            manifest,
            ranking_type,
        )
    )

    if manifest_row is None:
        st.info(
            "Manifest do ranking "
            "indisponível."
        )
        return

    status = str(
        manifest_row.get(
            "ranking_status"
        )
        or NA_TEXT
    )

    status_badge(
        "Ranking status",
        status,
    )

    left, right = st.columns(
        [1, 1]
    )

    with left:
        key_value_panel(
            [
                (
                    "Ranking ID",
                    manifest_row.get(
                        "ranking_id"
                    )
                    or NA_TEXT,
                ),
                (
                    "Scope",
                    scope,
                ),
                (
                    "Year",
                    year
                    if year
                    is not None
                    else NA_TEXT,
                ),
                (
                    "Month",
                    month
                    if month
                    is not None
                    else NA_TEXT,
                ),
            ],
            title="Identidade",
        )

    with right:
        key_value_panel(
            [
                (
                    "Candidates",
                    format_integer(
                        manifest_row.get(
                            "candidate_count"
                        )
                    ),
                ),
                (
                    "Rankable",
                    format_integer(
                        manifest_row.get(
                            "rankable_count"
                        )
                    ),
                ),
                (
                    "Not rankable",
                    format_integer(
                        manifest_row.get(
                            "not_rankable_count"
                        )
                    ),
                ),
                (
                    "Source hash",
                    manifest_row.get(
                        "source_hash"
                    )
                    or NA_TEXT,
                ),
            ],
            title="Universe",
        )

    if status == "UNAVAILABLE":
        st.info(
            (
                f"{display_metric_name(ranking_type)} "
                "está UNAVAILABLE nos dados "
                "homologados atuais."
            )
        )
        return

    if rankings.empty:
        st.info(
            "Dataset de rankings "
            "indisponível."
        )
        return

    subset = rankings[
        rankings[
            "ranking_type"
        ].astype(str)
        == str(
            ranking_type
        )
    ].copy()

    if subset.empty:
        st.info(
            "Nenhuma linha produzida para "
            "o ranking selecionado."
        )
        return

    if "rank_position" in subset.columns:
        subset = subset.sort_values(
            [
                "rank_position",
                "experiment_id",
            ],
            na_position="last",
        )

    section_title(
        display_metric_name(
            ranking_type
        )
    )

    table = _ranking_table(
        subset,
        ranking_type,
    )

    dataframe_view(
        table,
        height=470,
    )

    if (
        ranking_type
        == "COMPOSITE_SCORE"
    ):
        _render_composite_details(
            subset,
            manifest_row,
        )


if __name__ == "__main__":
    render()