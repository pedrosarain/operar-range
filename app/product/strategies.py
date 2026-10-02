from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
import streamlit as st

from app.product.shared import (
    page_title,
)
from operar_range.quantitative_models import (
    US_OPEN_BREAKOUT_V1,
)
from operar_range.research_workspace import (
    list_researches,
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


def _model_id() -> str:
    return str(
        US_OPEN_BREAKOUT_V1.get(
            "model_id"
        )
        or "US_OPEN_BREAKOUT_V1"
    )


def _model_name() -> str:
    return str(
        US_OPEN_BREAKOUT_V1.get(
            "model_name"
        )
        or US_OPEN_BREAKOUT_V1.get(
            "name"
        )
        or "US OPEN BREAKOUT V1"
    )


def _model_strategy() -> str:
    return str(
        US_OPEN_BREAKOUT_V1.get(
            "strategy"
        )
        or ""
    )


def _related_researches() -> list[
    dict[str, Any]
]:
    rows = list_researches()

    model_id = _model_id()

    strategy = _model_strategy()

    related = []

    for row in rows:
        row_model = str(
            row.get(
                "model_id"
            )
            or ""
        )

        row_strategy = str(
            row.get(
                "strategy"
            )
            or ""
        )

        if (
            row_model
            and row_model
            == model_id
        ):
            related.append(
                row
            )
            continue

        #
        # Researches históricas anteriores ao
        # preenchimento formal do model_id podem
        # estar relacionadas pela estratégia
        # persistida.
        #
        if (
            not row_model
            and strategy
            and row_strategy
            == strategy
        ):
            related.append(
                row
            )

    return related


def _latest_completed(
    rows: list[
        dict[str, Any]
    ],
) -> dict[str, Any] | None:
    completed = [
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

    if not completed:
        return None

    return sorted(
        completed,
        key=lambda row: str(
            row.get(
                "completed_at"
            )
            or row.get(
                "created_at"
            )
            or ""
        ),
        reverse=True,
    )[0]


def _latest_metrics(
    research_id: str,
) -> dict[str, Any] | None:
    try:
        paths = research_paths(
            research_id
        )

        metrics = _read_parquet(
            paths.get(
                "metrics"
            )
        )

    except Exception:
        return None

    if metrics.is_empty():
        return None

    rankings = _read_parquet(
        paths.get(
            "rankings"
        )
    )

    experiment_id = None

    if not rankings.is_empty():
        ranked = rankings

        if (
            "scope"
            in ranked.columns
        ):
            overall = ranked.filter(
                pl.col(
                    "scope"
                )
                == "OVERALL"
            )

            if not overall.is_empty():
                ranked = overall

        if (
            "ranking_type"
            in ranked.columns
        ):
            composite = ranked.filter(
                pl.col(
                    "ranking_type"
                )
                == "COMPOSITE_SCORE"
            )

            if not composite.is_empty():
                ranked = composite

        if (
            "rank_position"
            in ranked.columns
        ):
            ranked = ranked.sort(
                "rank_position"
            )

        if (
            not ranked.is_empty()
            and "experiment_id"
            in ranked.columns
        ):
            experiment_id = str(
                ranked[
                    "experiment_id"
                ][0]
            )

    if (
        experiment_id
        and "experiment_id"
        in metrics.columns
    ):
        selected = metrics.filter(
            pl.col(
                "experiment_id"
            ).cast(
                pl.Utf8
            )
            == experiment_id
        )

        if not selected.is_empty():
            return selected.row(
                0,
                named=True,
            )

    return metrics.row(
        0,
        named=True,
    )


def _formal_model_sections() -> list[
    tuple[str, Any]
]:
    ignored = {
        "model_id",
        "model_name",
        "name",
        "strategy",
    }

    preferred = (
        "description",
        "hypothesis",
        "market",
        "asset",
        "reference_candle",
        "reference_time",
        "entry_rule",
        "entry_offset",
        "rules",
    )

    rows = []

    for key in preferred:
        value = US_OPEN_BREAKOUT_V1.get(
            key
        )

        if value not in (
            None,
            "",
            [],
            {},
        ):
            rows.append(
                (
                    key,
                    value,
                )
            )

    for key, value in (
        US_OPEN_BREAKOUT_V1.items()
    ):
        if (
            key in ignored
            or key in preferred
            or value
            in (
                None,
                "",
                [],
                {},
            )
        ):
            continue

        rows.append(
            (
                key,
                value,
            )
        )

    return rows


def _render_description() -> None:
    st.subheader(
        "Descrição"
    )

    description = (
        US_OPEN_BREAKOUT_V1.get(
            "description"
        )
    )

    if description:
        st.write(
            description
        )

    else:
        st.info(
            (
                "Não existe descrição textual "
                "formal persistida para este modelo."
            )
        )

    c1, c2 = st.columns(
        2
    )

    with c1:
        st.metric(
            "Modelo",
            _model_name(),
        )

    with c2:
        st.metric(
            "Estratégia",
            _text(
                US_OPEN_BREAKOUT_V1.get(
                    "strategy"
                )
            ),
        )


def _render_hypothesis() -> None:
    st.subheader(
        "Hipótese"
    )

    hypothesis = (
        US_OPEN_BREAKOUT_V1.get(
            "hypothesis"
        )
    )

    if hypothesis:
        st.write(
            hypothesis
        )

    else:
        st.info(
            (
                "Nenhuma hipótese textual formal "
                "está registrada no contrato "
                "do modelo."
            )
        )


def _render_validation(
    rows: list[
        dict[str, Any]
    ],
) -> None:
    st.subheader(
        "Validação"
    )

    completed = [
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

    failed = [
        row
        for row in rows
        if str(
            row.get(
                "status"
            )
            or ""
        ).upper()
        == "FAILED"
    ]

    c1, c2, c3 = st.columns(
        3
    )

    with c1:
        st.metric(
            "Pesquisas relacionadas",
            len(
                rows
            ),
        )

    with c2:
        st.metric(
            "Concluídas",
            len(
                completed
            ),
        )

    with c3:
        st.metric(
            "Falhas registradas",
            len(
                failed
            ),
        )

    st.caption(
        (
            "Esses números descrevem apenas "
            "execuções registradas. Eles não "
            "significam que a hipótese esteja "
            "confirmada ou rejeitada."
        )
    )


def _render_history(
    rows: list[
        dict[str, Any]
    ],
) -> None:
    st.subheader(
        "Histórico"
    )

    if not rows:
        st.info(
            "Nenhuma pesquisa relacionada registrada."
        )
        return

    history = []

    for row in rows:
        history.append(
            {
                "Pesquisa": (
                    row.get(
                        "research_name"
                    )
                    or row.get(
                        "research_id"
                    )
                ),
                "Status": (
                    row.get(
                        "status"
                    )
                ),
                "Mercado": (
                    row.get(
                        "market"
                    )
                ),
                "Ativo": (
                    row.get(
                        "asset"
                    )
                ),
                "Início": (
                    row.get(
                        "period_start"
                    )
                ),
                "Fim": (
                    row.get(
                        "period_end"
                    )
                ),
            }
        )

    st.dataframe(
        history,
        use_container_width=True,
        hide_index=True,
    )


def _render_performance(
    rows: list[
        dict[str, Any]
    ],
) -> None:
    st.subheader(
        "Performance"
    )

    latest = _latest_completed(
        rows
    )

    if latest is None:
        st.info(
            (
                "Nenhuma pesquisa concluída possui "
                "performance disponível."
            )
        )
        return

    research_id = str(
        latest.get(
            "research_id"
        )
        or ""
    )

    metrics = _latest_metrics(
        research_id
    )

    if not metrics:
        st.info(
            (
                "A última pesquisa concluída não "
                "possui métricas disponíveis."
            )
        )
        return

    st.caption(
        (
            "Métricas da pesquisa concluída mais "
            "recente relacionada ao modelo."
        )
    )

    c1, c2, c3, c4 = st.columns(
        4
    )

    with c1:
        st.metric(
            "Win Rate",
            _percent(
                metrics.get(
                    "win_rate_pct"
                )
            ),
        )

    with c2:
        st.metric(
            "Expectancy",
            _number(
                metrics.get(
                    "expectancy_points_per_trade"
                )
            ),
        )

    with c3:
        profit_factor = (
            metrics.get(
                "profit_factor"
            )
        )

        if profit_factor is None:
            pf_display = _text(
                metrics.get(
                    "profit_factor_status"
                )
            )

        else:
            pf_display = _number(
                profit_factor
            )

        st.metric(
            "Profit Factor",
            pf_display,
        )

    with c4:
        st.metric(
            "Drawdown",
            _number(
                metrics.get(
                    "max_drawdown_points"
                )
            ),
        )

    st.caption(
        (
            "Pesquisa: "
            + research_id
        )
    )


def _render_discoveries() -> None:
    st.subheader(
        "Descobertas"
    )

    formal_keys = (
        "discoveries",
        "findings",
        "conclusions",
        "validation_result",
        "hypothesis_result",
    )

    found = {
        key: (
            US_OPEN_BREAKOUT_V1.get(
                key
            )
        )
        for key in formal_keys
        if US_OPEN_BREAKOUT_V1.get(
            key
        )
        not in (
            None,
            "",
            [],
            {},
        )
    }

    if not found:
        st.info(
            (
                "Nenhuma descoberta ou conclusão "
                "formal está registrada no contrato "
                "do modelo."
            )
        )
        return

    for key, value in found.items():
        st.markdown(
            f"**{key}**"
        )

        st.write(
            value
        )


def _render_versions() -> None:
    st.subheader(
        "Versões"
    )

    version_keys = (
        "version",
        "model_version",
        "rules_version",
    )

    found = {
        key: (
            US_OPEN_BREAKOUT_V1.get(
                key
            )
        )
        for key in version_keys
        if US_OPEN_BREAKOUT_V1.get(
            key
        )
        not in (
            None,
            "",
        )
    }

    if not found:
        st.info(
            (
                "Nenhuma versão adicional está "
                "formalmente registrada no contrato "
                "do modelo."
            )
        )
        return

    for key, value in found.items():
        st.write(
            f"{key}: {value}"
        )


def _render_evolution() -> None:
    st.subheader(
        "Evolução"
    )

    evolution = (
        US_OPEN_BREAKOUT_V1.get(
            "evolution"
        )
        or US_OPEN_BREAKOUT_V1.get(
            "history"
        )
    )

    if evolution:
        st.write(
            evolution
        )

    else:
        st.info(
            (
                "Nenhuma evolução formal do modelo "
                "está registrada ainda."
            )
        )


def render() -> None:
    page_title(
        "Estratégias",
        (
            "Biblioteca de conhecimento do "
            "laboratório quantitativo."
        ),
    )

    st.caption(
        (
            "Esta área organiza o conhecimento "
            "já produzido sobre cada estratégia. "
            "Pesquisas são executadas na área "
            "Pesquisas."
        )
    )

    st.divider()

    st.markdown(
        "## "
        + _model_name()
    )

    model = US_OPEN_BREAKOUT_V1

    c1, c2, c3 = st.columns(
        3
    )

    with c1:
        st.metric(
            "Estratégia",
            _model_strategy()
            or "Não disponível",
        )

    with c2:
        st.metric(
            "Status",
            _text(
                model.get(
                    "status"
                )
            ),
        )

    with c3:
        st.metric(
            "Versão",
            _text(
                model.get(
                    "version"
                )
            ),
        )

    st.caption(
        (
            "Identificador interno: "
            + _model_id()
        )
    )

    rows = _related_researches()

    st.divider()

    tabs = st.tabs(
        [
            "Descrição",
            "Hipótese",
            "Validação",
            "Histórico",
            "Performance",
            "Descobertas",
            "Versões",
            "Evolução",
        ]
    )

    with tabs[0]:
        _render_description()

    with tabs[1]:
        _render_hypothesis()

    with tabs[2]:
        _render_validation(
            rows
        )

    with tabs[3]:
        _render_history(
            rows
        )

    with tabs[4]:
        _render_performance(
            rows
        )

    with tabs[5]:
        _render_discoveries()

    with tabs[6]:
        _render_versions()

    with tabs[7]:
        _render_evolution()
