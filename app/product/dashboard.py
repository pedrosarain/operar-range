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
    load_research_definition,
    research_paths,
)


def _text(
    value: Any,
) -> str:
    if value in (
        None,
        "",
    ):
        return "Não disponível"

    return str(
        value
    )


def _number(
    value: Any,
) -> str:
    if value is None:
        return "Não disponível"

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
            f"{numeric:.2f}"
        )

    except Exception:
        return str(
            value
        )


def _percent(
    value: Any,
) -> str:
    if value is None:
        return "Não disponível"

    try:
        return (
            f"{float(value):.2f}%"
        )

    except Exception:
        return "Não disponível"


def _read_parquet(
    path: Any,
) -> pl.DataFrame:
    if not path:
        return pl.DataFrame()

    resolved = Path(
        path
    )

    if not resolved.exists():
        return pl.DataFrame()

    try:
        return pl.read_parquet(
            resolved
        )

    except Exception:
        return pl.DataFrame()


def _research_name(
    row: dict[str, Any],
) -> str:
    value = (
        row.get(
            "research_name"
        )
        or row.get(
            "model_name"
        )
        or row.get(
            "strategy"
        )
        or row.get(
            "research_id"
        )
    )

    return _text(
        value
    )


def _completed_researches(
    rows: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    return [
        row
        for row in rows
        if str(
            row.get(
                "status"
            )
            or ""
        ).upper()
        == "COMPLETED"
    ]


def _running_researches(
    rows: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    running_statuses = {
        "RUNNING",
        "EXECUTING",
        "IN_PROGRESS",
        "PENDING",
    }

    return [
        row
        for row in rows
        if str(
            row.get(
                "status"
            )
            or ""
        ).upper()
        in running_statuses
    ]


def _attention_researches(
    rows: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    attention_statuses = {
        "FAILED",
        "ERROR",
    }

    return [
        row
        for row in rows
        if str(
            row.get(
                "status"
            )
            or ""
        ).upper()
        in attention_statuses
    ]


def _latest_completed(
    rows: list[
        dict[str, Any]
    ],
) -> dict[str, Any] | None:
    completed = (
        _completed_researches(
            rows
        )
    )

    if not completed:
        return None

    def sort_key(
        row: dict[str, Any],
    ) -> str:
        return str(
            row.get(
                "completed_at"
            )
            or row.get(
                "created_at"
            )
            or ""
        )

    return sorted(
        completed,
        key=sort_key,
        reverse=True,
    )[0]


def _overall_rankings(
    research_id: str,
) -> pl.DataFrame:
    try:
        paths = research_paths(
            research_id
        )

        frame = _read_parquet(
            paths.get(
                "rankings"
            )
        )

    except Exception:
        return pl.DataFrame()

    if frame.is_empty():
        return frame

    if (
        "scope"
        in frame.columns
    ):
        overall = frame.filter(
            pl.col(
                "scope"
            )
            == "OVERALL"
        )

        if not overall.is_empty():
            frame = overall

    if (
        "ranking_status"
        in frame.columns
    ):
        ranked = frame.filter(
            pl.col(
                "ranking_status"
            )
            == "RANKED"
        )

        if not ranked.is_empty():
            frame = ranked

    return frame


def _leader_from_ranking(
    rankings: pl.DataFrame,
    ranking_types: tuple[
        str,
        ...,
    ],
) -> dict[str, Any] | None:
    if rankings.is_empty():
        return None

    if (
        "ranking_type"
        not in rankings.columns
        or "rank_position"
        not in rankings.columns
    ):
        return None

    for ranking_type in ranking_types:
        subset = rankings.filter(
            pl.col(
                "ranking_type"
            )
            == ranking_type
        )

        if subset.is_empty():
            continue

        subset = subset.sort(
            "rank_position"
        )

        return subset.row(
            0,
            named=True,
        )

    return None


def _metrics(
    research_id: str,
) -> pl.DataFrame:
    try:
        paths = research_paths(
            research_id
        )

        return _read_parquet(
            paths.get(
                "metrics"
            )
        )

    except Exception:
        return pl.DataFrame()


def _metric_row(
    metrics: pl.DataFrame,
    experiment_id: str,
) -> dict[str, Any] | None:
    if (
        metrics.is_empty()
        or "experiment_id"
        not in metrics.columns
    ):
        return None

    subset = metrics.filter(
        pl.col(
            "experiment_id"
        ).cast(
            pl.Utf8
        )
        == str(
            experiment_id
        )
    )

    if subset.is_empty():
        return None

    return subset.row(
        0,
        named=True,
    )


def _formal_research_statements(
    research_id: str,
) -> dict[str, Any]:
    try:
        definition = (
            load_research_definition(
                research_id
            )
        )

    except Exception:
        return {}

    keys = (
        "hypothesis_result",
        "hypothesis_status",
        "validation_result",
        "conclusion_status",
        "conclusion",
        "conclusions",
        "research_conclusions",
        "discoveries",
        "research_findings",
        "findings",
    )

    return {
        key: definition.get(
            key
        )
        for key in keys
        if definition.get(
            key
        )
        not in (
            None,
            "",
            [],
            {},
        )
    }


def _render_attention(
    rows: list[
        dict[str, Any]
    ],
) -> None:
    st.subheader(
        "Pesquisas que precisam de atenção"
    )

    failed = (
        _attention_researches(
            rows
        )
    )

    if not failed:
        st.success(
            "Nenhuma pesquisa com falha registrada."
        )
        return

    st.metric(
        "Pesquisas com falha",
        len(
            failed
        ),
    )

    display = []

    for row in failed[
        :10
    ]:
        display.append(
            {
                "Pesquisa": (
                    _research_name(
                        row
                    )
                ),
                "Status": (
                    _text(
                        row.get(
                            "status"
                        )
                    )
                ),
                "Mercado": (
                    _text(
                        row.get(
                            "market"
                        )
                    )
                ),
                "Ativo": (
                    _text(
                        row.get(
                            "asset"
                        )
                    )
                ),
                "Erro": (
                    _text(
                        row.get(
                            "error_message"
                        )
                    )
                ),
            }
        )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )


def render() -> None:
    page_title(
        "Dashboard",
        (
            "Estado factual do laboratório "
            "quantitativo."
        ),
    )

    rows = list_researches()

    running = (
        _running_researches(
            rows
        )
    )

    completed = (
        _completed_researches(
            rows
        )
    )

    attention = (
        _attention_researches(
            rows
        )
    )

    st.subheader(
        "Agora"
    )

    c1, c2, c3, c4 = st.columns(
        4
    )

    with c1:
        st.metric(
            "Pesquisa rodando",
            (
                "Sim"
                if running
                else "Não"
            ),
        )

    with c2:
        st.metric(
            "Pesquisas em execução",
            len(
                running
            ),
        )

    with c3:
        st.metric(
            "Pesquisas concluídas",
            len(
                completed
            ),
        )

    with c4:
        st.metric(
            "Precisam de atenção",
            len(
                attention
            ),
        )

    latest = _latest_completed(
        rows
    )

    st.divider()

    st.subheader(
        "Última pesquisa concluída"
    )

    if latest is None:
        st.info(
            "Nenhuma pesquisa concluída disponível."
        )
        _render_attention(
            rows
        )
        return

    research_id = str(
        latest.get(
            "research_id"
        )
        or ""
    )

    a, b, c, d = st.columns(
        4
    )

    with a:
        st.metric(
            "Pesquisa",
            _research_name(
                latest
            ),
        )

    with b:
        st.metric(
            "Mercado",
            _text(
                latest.get(
                    "market"
                )
            ),
        )

    with c:
        st.metric(
            "Ativo",
            _text(
                latest.get(
                    "asset"
                )
            ),
        )

    with d:
        st.metric(
            "Status",
            _text(
                latest.get(
                    "status"
                )
            ),
        )

    period_start = latest.get(
        "period_start"
    )

    period_end = latest.get(
        "period_end"
    )

    if (
        period_start
        or period_end
    ):
        st.caption(
            (
                "Período pesquisado: "
                f"{period_start or '—'}"
                " → "
                f"{period_end or '—'}"
            )
        )

    rankings = _overall_rankings(
        research_id
    )

    metrics = _metrics(
        research_id
    )

    composite = _leader_from_ranking(
        rankings,
        (
            "COMPOSITE_SCORE",
        ),
    )

    expectancy_rank = (
        _leader_from_ranking(
            rankings,
            (
                "EXPECTANCY",
                "EXPECTANCY_POINTS_PER_TRADE",
            ),
        )
    )

    profit_factor_rank = (
        _leader_from_ranking(
            rankings,
            (
                "PROFIT_FACTOR",
            ),
        )
    )

    st.divider()

    st.subheader(
        "Respostas quantitativas disponíveis"
    )

    if composite is not None:
        experiment_id = str(
            composite.get(
                "experiment_id"
            )
        )

        row = _metric_row(
            metrics,
            experiment_id,
        )

        st.markdown(
            "#### Experimento líder do ranking composto"
        )

        x1, x2, x3, x4 = st.columns(
            4
        )

        with x1:
            st.metric(
                "Experimento",
                experiment_id,
            )

        with x2:
            st.metric(
                "Expectancy",
                (
                    _number(
                        row.get(
                            "expectancy_points_per_trade"
                        )
                    )
                    if row
                    else "Não disponível"
                ),
            )

        with x3:
            if row:
                pf = row.get(
                    "profit_factor"
                )

                pf_status = row.get(
                    "profit_factor_status"
                )

                if pf is None:
                    pf_display = (
                        _text(
                            pf_status
                        )
                    )
                else:
                    pf_display = (
                        _number(
                            pf
                        )
                    )

            else:
                pf_display = (
                    "Não disponível"
                )

            st.metric(
                "Profit Factor",
                pf_display,
            )

        with x4:
            st.metric(
                "Win Rate",
                (
                    _percent(
                        row.get(
                            "win_rate_pct"
                        )
                    )
                    if row
                    else "Não disponível"
                ),
            )

        if row:
            st.caption(
                (
                    "Drawdown registrado: "
                    + _number(
                        row.get(
                            "max_drawdown_points"
                        )
                    )
                    + " pontos."
                )
            )

    else:
        st.info(
            (
                "A pesquisa não possui ranking "
                "composto disponível."
            )
        )

    left, right = st.columns(
        2
    )

    with left:
        st.markdown(
            "#### Maior Expectancy formalmente ranqueada"
        )

        if expectancy_rank is None:
            st.info(
                (
                    "Nenhum ranking específico de "
                    "Expectancy está disponível."
                )
            )

        else:
            st.metric(
                "Experimento",
                _text(
                    expectancy_rank.get(
                        "experiment_id"
                    )
                ),
            )

            st.metric(
                "Valor",
                _number(
                    expectancy_rank.get(
                        "metric_value"
                    )
                ),
            )

    with right:
        st.markdown(
            "#### Maior Profit Factor formalmente ranqueado"
        )

        if profit_factor_rank is None:
            st.info(
                (
                    "Nenhum ranking específico de "
                    "Profit Factor está disponível."
                )
            )

        else:
            st.metric(
                "Experimento",
                _text(
                    profit_factor_rank.get(
                        "experiment_id"
                    )
                ),
            )

            st.metric(
                "Valor",
                _number(
                    profit_factor_rank.get(
                        "metric_value"
                    )
                ),
            )

    st.divider()

    st.subheader(
        "Conclusões formais"
    )

    formal = (
        _formal_research_statements(
            research_id
        )
    )

    if not formal:
        st.info(
            (
                "Esta pesquisa não possui "
                "descoberta, validação de hipótese "
                "ou conclusão formal persistida. "
                "O Dashboard não irá inferi-las."
            )
        )

    else:
        for key, value in formal.items():
            st.markdown(
                f"**{key}**"
            )

            if isinstance(
                value,
                list,
            ):
                for item in value:
                    st.write(
                        f"- {item}"
                    )

            else:
                st.write(
                    value
                )

    st.divider()

    _render_attention(
        rows
    )
