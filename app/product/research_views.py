from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl
import streamlit as st

from app.product.shared import (
    answer_card,
    section,
)
from operar_range.research_workspace import (
    load_research_definition,
    research_paths,
)


def _read_parquet(
    path: Path | str | None,
) -> pl.DataFrame:
    if path is None:
        return pl.DataFrame()

    try:
        resolved = Path(
            path
        )

        if not resolved.exists():
            return pl.DataFrame()

        return pl.read_parquet(
            resolved
        )

    except Exception:
        return pl.DataFrame()


def _paths(
    research_id: str,
) -> dict[str, Path]:
    try:
        return research_paths(
            research_id
        )

    except Exception:
        return {}


def _artifact(
    research_id: str,
    key: str,
) -> pl.DataFrame:
    paths = _paths(
        research_id
    )

    return _read_parquet(
        paths.get(
            key
        )
    )


def _safe_value(
    row: dict[str, Any] | None,
    key: str,
) -> Any:
    if not row:
        return None

    return row.get(
        key
    )


def _number(
    value: Any,
    *,
    decimals: int = 2,
) -> str:
    if value is None:
        return "—"

    try:
        number = float(
            value
        )

        if number.is_integer():
            return str(
                int(
                    number
                )
            )

        return (
            f"{number:.{decimals}f}"
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


def _points(
    value: Any,
) -> str:
    if value is None:
        return "—"

    return (
        _number(
            value
        )
        + " pts"
    )


def _bool_text(
    value: Any,
) -> str:
    if value is True:
        return "Sim"

    if value is False:
        return "Não"

    return "—"


def _first_row(
    frame: pl.DataFrame,
) -> dict[str, Any] | None:
    if frame.is_empty():
        return None

    return frame.row(
        0,
        named=True,
    )


def _experiment_row(
    frame: pl.DataFrame,
    experiment_id: str | None,
) -> dict[str, Any] | None:
    if (
        frame.is_empty()
        or not experiment_id
        or "experiment_id"
        not in frame.columns
    ):
        return None

    filtered = frame.filter(
        pl.col(
            "experiment_id"
        ).cast(
            pl.Utf8
        )
        == str(
            experiment_id
        )
    )

    return _first_row(
        filtered
    )


def _ranking_leader(
    rankings: pl.DataFrame,
) -> dict[str, Any] | None:
    if rankings.is_empty():
        return None

    frame = rankings

    if "scope" in frame.columns:
        overall = frame.filter(
            pl.col(
                "scope"
            )
            == "OVERALL"
        )

        if not overall.is_empty():
            frame = overall

    if "ranking_status" in frame.columns:
        ranked = frame.filter(
            pl.col(
                "ranking_status"
            )
            == "RANKED"
        )

        if not ranked.is_empty():
            frame = ranked

    if "ranking_type" in frame.columns:
        composite = frame.filter(
            pl.col(
                "ranking_type"
            )
            == "COMPOSITE_SCORE"
        )

        if not composite.is_empty():
            frame = composite

    if (
        "rank_position"
        in frame.columns
    ):
        frame = frame.sort(
            "rank_position"
        )

    return _first_row(
        frame
    )


def _experiment_name(
    row: dict[str, Any] | None,
) -> str:
    if not row:
        return "—"

    return str(
        row.get(
            "experiment_name"
        )
        or row.get(
            "name"
        )
        or row.get(
            "experiment_id"
        )
        or "—"
    )


def _formal_hypothesis(
    research_id: str,
) -> str | None:
    try:
        definition = (
            load_research_definition(
                research_id
            )
        )

    except Exception:
        return None

    value = (
        definition.get(
            "hypothesis"
        )
        or definition.get(
            "research_hypothesis"
        )
    )

    if not value:
        return None

    return str(
        value
    )


def _configuration_panel(
    experiment: dict[str, Any] | None,
) -> None:
    if not experiment:
        st.info(
            "Configuração do experimento indisponível."
        )
        return

    st.markdown(
        "#### Configuração avaliada"
    )

    left, right, third = st.columns(
        3
    )

    with left:
        answer_card(
            "Stop",
            _points(
                experiment.get(
                    "stop_points"
                )
            ),
        )

        answer_card(
            "Parcial 1",
            _points(
                experiment.get(
                    "partial_1_points"
                )
            ),
        )

    with right:
        partial_pct = (
            experiment.get(
                "partial_1_pct"
            )
        )

        answer_card(
            "% Parcial 1",
            _percent(
                partial_pct
            ),
        )

        answer_card(
            "Alvo final",
            _points(
                experiment.get(
                    "final_target_points"
                )
            ),
        )

    with third:
        answer_card(
            "Runner",
            _bool_text(
                experiment.get(
                    "runner_enabled"
                )
            ),
        )

        answer_card(
            "Break-even",
            _bool_text(
                experiment.get(
                    "break_even_enabled"
                )
            ),
        )


def _negative_months(
    frame: pl.DataFrame,
) -> pl.DataFrame:
    if (
        frame.is_empty()
        or "total_weighted_points"
        not in frame.columns
    ):
        return pl.DataFrame()

    return frame.filter(
        pl.col(
            "total_weighted_points"
        )
        < 0
    )


def _negative_days(
    frame: pl.DataFrame,
) -> pl.DataFrame:
    if (
        frame.is_empty()
        or "total_weighted_points"
        not in frame.columns
    ):
        return pl.DataFrame()

    return frame.filter(
        pl.col(
            "total_weighted_points"
        ).is_not_null()
        & (
            pl.col(
                "total_weighted_points"
            )
            < 0
        )
    )


def _display_negative_periods(
    *,
    monthly: pl.DataFrame,
    distributed: pl.DataFrame,
) -> None:
    st.markdown(
        "#### Períodos negativos observados"
    )

    bad_months = _negative_months(
        monthly
    )

    bad_days = _negative_days(
        distributed
    )

    left, right = st.columns(
        2
    )

    with left:
        st.markdown(
            "**Meses com resultado negativo**"
        )

        if bad_months.is_empty():
            st.caption(
                (
                    "Nenhum mês negativo foi "
                    "observado nos artifacts "
                    "disponíveis desta Research."
                )
            )

        else:
            columns = [
                column
                for column in [
                    "year",
                    "month",
                    "trade1_count",
                    "total_weighted_points",
                    "expectancy_points_per_trade",
                    "max_drawdown_points",
                ]
                if column
                in bad_months.columns
            ]

            st.dataframe(
                bad_months.select(
                    columns
                ).to_pandas(),
                use_container_width=True,
                hide_index=True,
            )

    with right:
        st.markdown(
            "**Pregões com resultado negativo**"
        )

        if bad_days.is_empty():
            st.caption(
                (
                    "Nenhum pregão negativo foi "
                    "observado nos artifacts "
                    "disponíveis desta Research."
                )
            )

        else:
            columns = [
                column
                for column in [
                    "date",
                    "experiment_id",
                    "direction",
                    "trade1_result_points",
                    "trade2_result_points",
                    "consolidated_result_points",
                    "total_weighted_points",
                    "final_reason",
                ]
                if column
                in bad_days.columns
            ]

            st.dataframe(
                bad_days.select(
                    columns
                ).to_pandas(),
                use_container_width=True,
                hide_index=True,
            )


def render_result(
    research_id: str,
) -> None:
    section(
        "Resultado",
        (
            "Leitura factual dos artifacts "
            "produzidos por esta Research."
        ),
    )

    paths = _paths(
        research_id
    )

    rankings = _read_parquet(
        paths.get(
            "rankings"
        )
    )

    valid = _read_parquet(
        paths.get(
            "valid"
        )
    )

    metrics = _read_parquet(
        paths.get(
            "metrics"
        )
    )

    monthly = _read_parquet(
        paths.get(
            "metrics_monthly"
        )
    )

    distributed = _read_parquet(
        paths.get(
            "distributed_results"
        )
    )

    hypothesis = _formal_hypothesis(
        research_id
    )

    if hypothesis:
        st.markdown(
            "#### Hipótese registrada"
        )

        st.write(
            hypothesis
        )

    else:
        st.info(
            (
                "Esta Research não possui "
                "hipótese textual formal "
                "persistida."
            )
        )

    leader = _ranking_leader(
        rankings
    )

    leader_id = (
        str(
            leader.get(
                "experiment_id"
            )
        )
        if leader
        and leader.get(
            "experiment_id"
        )
        else None
    )

    experiment = _experiment_row(
        valid,
        leader_id,
    )

    metric = _experiment_row(
        metrics,
        leader_id,
    )

    if metric is None:
        metric = _first_row(
            metrics
        )

        if (
            metric
            and not leader_id
        ):
            leader_id = str(
                metric.get(
                    "experiment_id"
                )
                or ""
            )

            experiment = (
                _experiment_row(
                    valid,
                    leader_id,
                )
            )

    st.markdown(
        "#### Resposta quantitativa"
    )

    if leader:
        ranking_type = str(
            leader.get(
                "ranking_type"
            )
            or "Ranking"
        )

        st.caption(
            (
                "Experimento exibido abaixo: "
                "posição 1 do ranking "
                f"{ranking_type}. "
                "A interface não redefine "
                "o critério do ranking."
            )
        )

    elif leader_id:
        st.caption(
            (
                "Nenhum ranking formal foi "
                "resolvido. Exibindo métricas "
                "do experimento disponível."
            )
        )

    else:
        st.info(
            (
                "Não há experimento com métricas "
                "disponíveis para esta Research."
            )
        )

        return

    c1, c2, c3, c4 = st.columns(
        4
    )

    with c1:
        answer_card(
            "Experimento",
            (
                _experiment_name(
                    experiment
                )
                if experiment
                else leader_id
            ),
        )

    with c2:
        answer_card(
            "Win Rate",
            _percent(
                _safe_value(
                    metric,
                    "win_rate_pct",
                )
            ),
        )

    with c3:
        answer_card(
            "Expectancy",
            _points(
                _safe_value(
                    metric,
                    "expectancy_points_per_trade",
                )
            ),
        )

    with c4:
        pf = _safe_value(
            metric,
            "profit_factor",
        )

        pf_status = _safe_value(
            metric,
            "profit_factor_status",
        )

        answer_card(
            "Profit Factor",
            (
                _number(
                    pf
                )
                if pf is not None
                else (
                    str(
                        pf_status
                    )
                    if pf_status
                    else "—"
                )
            ),
        )

    c1, c2, c3, c4 = st.columns(
        4
    )

    with c1:
        answer_card(
            "Drawdown",
            _points(
                _safe_value(
                    metric,
                    "max_drawdown_points",
                )
            ),
        )

    with c2:
        answer_card(
            "Pregões",
            _number(
                _safe_value(
                    metric,
                    "sessions_total",
                )
            ),
        )

    with c3:
        answer_card(
            "Trades",
            _number(
                _safe_value(
                    metric,
                    "trade1_count",
                )
            ),
        )

    with c4:
        answer_card(
            "Resultado total",
            _points(
                _safe_value(
                    metric,
                    "total_weighted_points",
                )
            ),
        )

    _configuration_panel(
        experiment
    )

    st.markdown(
        "#### Conclusão formal"
    )

    st.info(
        (
            "Nenhuma conclusão metodológica é "
            "inferida a partir das métricas. "
            "Confirmação, rejeição, edge ou "
            "descoberta só aparecem quando "
            "existirem formalmente persistidos."
        )
    )

    _display_negative_periods(
        monthly=monthly,
        distributed=distributed,
    )

    st.markdown(
        "#### Resumo factual"
    )

    summary_parts = []

    if metric:
        sessions = metric.get(
            "sessions_total"
        )

        trades = metric.get(
            "trade1_count"
        )

        expectancy = metric.get(
            "expectancy_points_per_trade"
        )

        drawdown = metric.get(
            "max_drawdown_points"
        )

        if sessions is not None:
            summary_parts.append(
                (
                    "Pregões analisados: "
                    + _number(
                        sessions
                    )
                )
            )

        if trades is not None:
            summary_parts.append(
                (
                    "Trades executados: "
                    + _number(
                        trades
                    )
                )
            )

        if expectancy is not None:
            summary_parts.append(
                (
                    "Expectancy observada: "
                    + _points(
                        expectancy
                    )
                )
            )

        if drawdown is not None:
            summary_parts.append(
                (
                    "Drawdown observado: "
                    + _points(
                        drawdown
                    )
                )
            )

    if summary_parts:
        for item in summary_parts:
            st.write(
                "• " + item
            )

    else:
        st.caption(
            "Resumo factual indisponível."
        )

    st.markdown(
        "#### Próximas perguntas"
    )

    st.write(
        (
            "• O resultado muda por target e stop?\n"
            "• O retorno ao zero altera a distribuição dos alvos?\n"
            "• Quais pregões compõem cada grupo?\n"
            "• O Trade 2 altera o resultado consolidado?\n"
            "• Como MFE e MAE se distribuem nos ciclos?"
        )
    )

    st.caption(
        (
            "Estas são perguntas de investigação, "
            "não conclusões quantitativas."
        )
    )


def _experiment_metrics_map(
    metrics: pl.DataFrame,
) -> dict[str, dict[str, Any]]:
    if (
        metrics.is_empty()
        or "experiment_id"
        not in metrics.columns
    ):
        return {}

    result = {}

    for row in metrics.iter_rows(
        named=True
    ):
        experiment_id = str(
            row.get(
                "experiment_id"
            )
            or ""
        )

        if experiment_id:
            result[
                experiment_id
            ] = row

    return result


def render_experiments(
    research_id: str,
) -> None:
    section(
        "Experimentos",
        (
            "Cada experimento é apresentado "
            "como uma hipótese/configuração "
            "quantitativa testada."
        ),
    )

    valid = _artifact(
        research_id,
        "valid",
    )

    metrics = _artifact(
        research_id,
        "metrics",
    )

    if valid.is_empty():
        st.info(
            (
                "Nenhum experimento válido "
                "disponível nesta Research."
            )
        )

        return

    metrics_by_id = (
        _experiment_metrics_map(
            metrics
        )
    )

    for experiment in valid.iter_rows(
        named=True
    ):
        experiment_id = str(
            experiment.get(
                "experiment_id"
            )
            or ""
        )

        name = _experiment_name(
            experiment
        )

        metric = (
            metrics_by_id.get(
                experiment_id
            )
        )

        with st.expander(
            (
                name
                + (
                    " — "
                    + experiment_id
                    if experiment_id
                    else ""
                )
            ),
            expanded=False,
        ):
            st.markdown(
                "#### Hipótese / configuração"
            )

            st.caption(
                (
                    "A configuração abaixo é o "
                    "objeto efetivamente testado. "
                    "Nenhuma hipótese textual é "
                    "inventada pela interface."
                )
            )

            _configuration_panel(
                experiment
            )

            st.markdown(
                "#### Resultado observado"
            )

            if metric is None:
                st.info(
                    (
                        "Métricas ainda não "
                        "disponíveis."
                    )
                )

                continue

            c1, c2, c3, c4 = st.columns(
                4
            )

            with c1:
                answer_card(
                    "Win Rate",
                    _percent(
                        metric.get(
                            "win_rate_pct"
                        )
                    ),
                )

            with c2:
                answer_card(
                    "Expectancy",
                    _points(
                        metric.get(
                            "expectancy_points_per_trade"
                        )
                    ),
                )

            with c3:
                value = metric.get(
                    "profit_factor"
                )

                status = metric.get(
                    "profit_factor_status"
                )

                answer_card(
                    "Profit Factor",
                    (
                        _number(
                            value
                        )
                        if value is not None
                        else (
                            str(
                                status
                            )
                            if status
                            else "—"
                        )
                    ),
                )

            with c4:
                answer_card(
                    "Drawdown",
                    _points(
                        metric.get(
                            "max_drawdown_points"
                        )
                    ),
                )

            st.caption(
                (
                    "Status quantitativo acima "
                    "vem dos artifacts existentes. "
                    "A Presentation Layer não "
                    "classifica o experimento como "
                    "confirmado ou rejeitado."
                )
            )


def render_research_analytics(
    research_id: str,
) -> None:
    section(
        "Analytics",
        (
            "Estatísticas contextuais desta "
            "Research. Nenhum motor é reexecutado."
        ),
    )

    paths = _paths(
        research_id
    )

    metrics = _read_parquet(
        paths.get(
            "metrics"
        )
    )

    monthly = _read_parquet(
        paths.get(
            "metrics_monthly"
        )
    )

    yearly = _read_parquet(
        paths.get(
            "metrics_yearly"
        )
    )

    trade2 = _read_parquet(
        paths.get(
            "trade2_analytics"
        )
    )

    consolidated = _read_parquet(
        paths.get(
            "consolidated_analytics"
        )
    )

    comparison = _read_parquet(
        paths.get(
            "lifecycle_comparison"
        )
    )

    tabs = st.tabs(
        [
            "Performance",
            "Mensal",
            "Anual",
            "Trade 2",
            "Ciclo",
        ]
    )

    with tabs[0]:
        if metrics.is_empty():
            st.info(
                "Métricas gerais indisponíveis."
            )

        else:
            visible = [
                column
                for column in [
                    "experiment_id",
                    "sessions_total",
                    "trade1_count",
                    "trade_frequency_pct",
                    "total_weighted_points",
                    "average_weighted_points",
                    "win_rate_pct",
                    "profit_factor",
                    "profit_factor_status",
                    "expectancy_points_per_trade",
                    "max_drawdown_points",
                    "max_consecutive_losses",
                    "max_consecutive_wins",
                ]
                if column
                in metrics.columns
            ]

            st.dataframe(
                metrics.select(
                    visible
                ).to_pandas(),
                use_container_width=True,
                hide_index=True,
            )

    with tabs[1]:
        if monthly.is_empty():
            st.info(
                "Métricas mensais indisponíveis."
            )

        else:
            visible = [
                column
                for column in [
                    "experiment_id",
                    "year",
                    "month",
                    "sessions_total",
                    "trade1_count",
                    "total_weighted_points",
                    "win_rate_pct",
                    "profit_factor",
                    "expectancy_points_per_trade",
                    "max_drawdown_points",
                ]
                if column
                in monthly.columns
            ]

            st.dataframe(
                monthly.select(
                    visible
                ).to_pandas(),
                use_container_width=True,
                hide_index=True,
            )

    with tabs[2]:
        if yearly.is_empty():
            st.info(
                "Métricas anuais indisponíveis."
            )

        else:
            visible = [
                column
                for column in [
                    "experiment_id",
                    "year",
                    "sessions_total",
                    "trade1_count",
                    "total_weighted_points",
                    "win_rate_pct",
                    "profit_factor",
                    "expectancy_points_per_trade",
                    "max_drawdown_points",
                ]
                if column
                in yearly.columns
            ]

            st.dataframe(
                yearly.select(
                    visible
                ).to_pandas(),
                use_container_width=True,
                hide_index=True,
            )

    with tabs[3]:
        if trade2.is_empty():
            st.info(
                "Analytics de Trade 2 indisponível."
            )

        else:
            visible = [
                column
                for column in [
                    "experiment_id",
                    "sessions_total",
                    "trade2_eligible_count",
                    "trade2_occurred_count",
                    "trade2_executed_count",
                    "trade2_winning_count",
                    "trade2_losing_count",
                    "trade2_breakeven_count",
                    "trade2_runner_count",
                    "trade2_weighted_result_points",
                    "trade2_total_position_points",
                ]
                if column
                in trade2.columns
            ]

            st.dataframe(
                trade2.select(
                    visible
                ).to_pandas(),
                use_container_width=True,
                hide_index=True,
            )

    with tabs[4]:
        if consolidated.is_empty():
            st.info(
                (
                    "Analytics consolidado "
                    "indisponível."
                )
            )

        else:
            visible = [
                column
                for column in [
                    "experiment_id",
                    "total_cycles",
                    "cycles_with_trade2",
                    "recovered_cycle_count",
                    "recovery_pct",
                    "total_result_points",
                    "expectancy_points_per_cycle",
                    "win_rate_pct",
                    "profit_factor",
                    "profit_factor_status",
                    "max_drawdown_points",
                ]
                if column
                in consolidated.columns
            ]

            st.markdown(
                "#### Resultado consolidado"
            )

            st.dataframe(
                consolidated.select(
                    visible
                ).to_pandas(),
                use_container_width=True,
                hide_index=True,
            )

        if not comparison.is_empty():
            visible = [
                column
                for column in [
                    "experiment_id",
                    "trade1_total_result_points",
                    "consolidated_total_result_points",
                    "difference_total_result_points",
                    "trade1_expectancy_points",
                    "consolidated_expectancy_points",
                    "difference_expectancy_points",
                    "trade1_profit_factor",
                    "consolidated_profit_factor",
                    "difference_profit_factor",
                    "trade1_max_drawdown_points",
                    "consolidated_max_drawdown_points",
                    "difference_max_drawdown_points",
                    "trade1_win_rate_pct",
                    "consolidated_win_rate_pct",
                    "difference_win_rate_pct",
                ]
                if column
                in comparison.columns
            ]

            st.markdown(
                "#### Trade 1 × ciclo consolidado"
            )

            st.dataframe(
                comparison.select(
                    visible
                ).to_pandas(),
                use_container_width=True,
                hide_index=True,
            )


def _formal_text_values(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        text = value.strip()

        if not text:
            return []

        try:
            parsed = json.loads(
                text
            )

            if isinstance(
                parsed,
                list,
            ):
                return [
                    str(
                        item
                    )
                    for item in parsed
                    if str(
                        item
                    ).strip()
                ]

        except Exception:
            pass

        return [
            text
        ]

    if isinstance(
        value,
        list,
    ):
        return [
            str(
                item
            )
            for item in value
            if str(
                item
            ).strip()
        ]

    return []


def render_conclusions(
    research_id: str,
) -> None:
    section(
        "Conclusões",
        (
            "Somente conclusões, validações "
            "ou descobertas formalmente "
            "persistidas são exibidas."
        ),
    )

    try:
        definition = (
            load_research_definition(
                research_id
            )
        )

    except Exception:
        definition = {}

    candidate_keys = [
        "conclusion",
        "conclusions",
        "research_conclusions",
        "findings",
        "research_findings",
        "discoveries",
        "validation_result",
        "hypothesis_result",
        "hypothesis_status",
        "conclusion_status",
    ]

    found: list[
        tuple[str, str]
    ] = []

    for key in candidate_keys:
        if key not in definition:
            continue

        values = _formal_text_values(
            definition.get(
                key
            )
        )

        for value in values:
            found.append(
                (
                    key,
                    value,
                )
            )

    if not found:
        st.info(
            (
                "Nenhuma conclusão formal, "
                "confirmação, rejeição, descoberta "
                "ou validação textual está "
                "persistida nesta Research."
            )
        )

        st.caption(
            (
                "A interface não converte métricas "
                "automaticamente em conclusões "
                "metodológicas."
            )
        )

        return

    for key, value in found:
        st.markdown(
            (
                "**"
                + key
                + "**"
            )
        )

        st.write(
            value
        )
