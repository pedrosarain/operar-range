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
    list_available_datasets,
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


def _research_name(
    row: dict[str, Any],
) -> str:
    return str(
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


def _status(
    row: dict[str, Any],
) -> str:
    return str(
        row.get(
            "status"
        )
        or ""
    ).upper()


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
        if _status(
            row
        )
        == "COMPLETED"
    ]


def _running_researches(
    rows: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    running = {
        "RUNNING",
        "EXECUTING",
        "IN_PROGRESS",
    }

    return [
        row
        for row in rows
        if _status(
            row
        )
        in running
    ]


def _waiting_researches(
    rows: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    waiting = {
        "PENDING",
        "QUEUED",
        "CREATED",
        "READY",
    }

    return [
        row
        for row in rows
        if _status(
            row
        )
        in waiting
    ]


def _failed_researches(
    rows: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    failed = {
        "FAILED",
        "ERROR",
    }

    return [
        row
        for row in rows
        if _status(
            row
        )
        in failed
    ]


def _incomplete_researches(
    rows: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    known = {
        "COMPLETED",
        "FAILED",
        "ERROR",
        "RUNNING",
        "EXECUTING",
        "IN_PROGRESS",
        "PENDING",
        "QUEUED",
        "CREATED",
        "READY",
    }

    return [
        row
        for row in rows
        if (
            _status(
                row
            )
            and _status(
                row
            )
            not in known
        )
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


def _read_parquet(
    value: Any,
) -> pl.DataFrame:
    if not value:
        return pl.DataFrame()

    path = Path(
        value
    )

    if not path.exists():
        return pl.DataFrame()

    try:
        return pl.read_parquet(
            path
        )

    except Exception:
        return pl.DataFrame()


def _artifact(
    research_id: str,
    key: str,
) -> pl.DataFrame:
    try:
        paths = research_paths(
            research_id
        )

        return _read_parquet(
            paths.get(
                key
            )
        )

    except Exception:
        return pl.DataFrame()


def _experiment_count(
    rows: list[
        dict[str, Any]
    ],
) -> int:
    experiment_ids: set[str] = set()

    for row in rows:
        research_id = str(
            row.get(
                "research_id"
            )
            or ""
        )

        if not research_id:
            continue

        frame = _artifact(
            research_id,
            "experiment_manifest",
        )

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
            experiment_ids.add(
                str(
                    value
                )
            )

    return len(
        experiment_ids
    )


def _strategy_count() -> int:
    #
    # PRODUCT-02 apresenta apenas estratégias
    # formalmente existentes.
    #
    models = [
        US_OPEN_BREAKOUT_V1,
    ]

    return sum(
        1
        for model in models
        if isinstance(
            model,
            dict,
        )
        and model.get(
            "model_id"
        )
    )


def _active_dataset(
    latest: dict[str, Any] | None,
) -> str:
    if latest is not None:
        dataset_id = latest.get(
            "dataset_id"
        )

        if dataset_id:
            return str(
                dataset_id
            )

    try:
        datasets = list(
            list_available_datasets()
        )

    except Exception:
        return "Não disponível"

    ready = [
        row
        for row in datasets
        if bool(
            row.get(
                "research_ready"
            )
            or row.get(
                "prepared_for_research"
            )
        )
    ]

    if not ready:
        return "Não disponível"

    ready = sorted(
        ready,
        key=lambda row: str(
            row.get(
                "imported_at"
            )
            or ""
        ),
        reverse=True,
    )

    selected = ready[0]

    return str(
        selected.get(
            "dataset_id"
        )
        or selected.get(
            "dataset_key"
        )
        or "Não disponível"
    )


def _ranking_leader(
    research_id: str,
) -> dict[str, Any] | None:
    rankings = _artifact(
        research_id,
        "rankings",
    )

    if rankings.is_empty():
        return None

    frame = rankings

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

    if (
        "ranking_type"
        in frame.columns
    ):
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

    if frame.is_empty():
        return None

    return frame.row(
        0,
        named=True,
    )


def _metric_row(
    research_id: str,
    experiment_id: str | None,
) -> dict[str, Any] | None:
    metrics = _artifact(
        research_id,
        "metrics",
    )

    if metrics.is_empty():
        return None

    frame = metrics

    if (
        experiment_id
        and "experiment_id"
        in frame.columns
    ):
        selected = frame.filter(
            pl.col(
                "experiment_id"
            ).cast(
                pl.Utf8
            )
            == str(
                experiment_id
            )
        )

        if not selected.is_empty():
            frame = selected

    if frame.is_empty():
        return None

    return frame.row(
        0,
        named=True,
    )


def _latest_research_facts(
    latest: dict[str, Any],
) -> tuple[
    dict[str, Any] | None,
    str | None,
]:
    research_id = str(
        latest.get(
            "research_id"
        )
        or ""
    )

    if not research_id:
        return None, None

    leader = _ranking_leader(
        research_id
    )

    experiment_id = None

    if leader is not None:
        value = leader.get(
            "experiment_id"
        )

        if value is not None:
            experiment_id = str(
                value
            )

    metrics = _metric_row(
        research_id,
        experiment_id,
    )

    return metrics, experiment_id


def _render_attention(
    rows: list[
        dict[str, Any]
    ],
) -> None:
    st.subheader(
        "O que merece atenção"
    )

    failed = _failed_researches(
        rows
    )

    incomplete = _incomplete_researches(
        rows
    )

    waiting = _waiting_researches(
        rows
    )

    groups = [
        (
            "Pesquisas falhadas",
            failed,
        ),
        (
            "Pesquisas incompletas",
            incomplete,
        ),
        (
            "Pesquisas aguardando conclusão",
            waiting,
        ),
    ]

    existing = [
        (
            label,
            values,
        )
        for label, values
        in groups
        if values
    ]

    if not existing:
        st.success(
            (
                "Nenhuma pesquisa requer "
                "atenção neste momento."
            )
        )
        return

    for label, values in existing:
        st.markdown(
            f"#### {label}"
        )

        display = []

        for row in values[
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
                    "Mensagem": (
                        _text(
                            row.get(
                                "error_message"
                            )
                        )
                        if row.get(
                            "error_message"
                        )
                        else ""
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
        "Como está meu laboratório?",
    )

    rows = list(
        list_researches()
    )

    running = _running_researches(
        rows
    )

    latest = _latest_completed(
        rows
    )

    st.subheader(
        "Estado do laboratório"
    )

    c1, c2, c3 = st.columns(
        3
    )

    with c1:
        st.metric(
            "Pesquisa em execução",
            (
                _research_name(
                    running[0]
                )
                if running
                else "Nenhuma"
            ),
        )

    with c2:
        st.metric(
            "Quantidade de pesquisas",
            len(
                rows
            ),
        )

    with c3:
        st.metric(
            "Quantidade de estratégias",
            _strategy_count(),
        )

    c4, c5, c6 = st.columns(
        3
    )

    with c4:
        st.metric(
            "Quantidade de experimentos",
            _experiment_count(
                rows
            ),
        )

    with c5:
        st.metric(
            "Dataset ativo",
            _active_dataset(
                latest
            ),
        )

    with c6:
        st.metric(
            "Última pesquisa concluída",
            (
                _research_name(
                    latest
                )
                if latest is not None
                else "Nenhuma"
            ),
        )

    st.divider()

    st.subheader(
        "Resumo da última pesquisa"
    )

    if latest is None:
        st.info(
            "Nenhuma pesquisa concluída disponível."
        )

        st.divider()

        _render_attention(
            rows
        )

        return

    metrics, experiment_id = (
        _latest_research_facts(
            latest
        )
    )

    a, b, c, d = st.columns(
        4
    )

    with a:
        st.metric(
            "Estratégia pesquisada",
            _text(
                latest.get(
                    "strategy"
                )
                or latest.get(
                    "model_name"
                )
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

    period = (
        str(
            latest.get(
                "period_start"
            )
            or "—"
        )
        + " → "
        + str(
            latest.get(
                "period_end"
            )
            or "—"
        )
    )

    a, b, c = st.columns(
        3
    )

    with a:
        st.metric(
            "Período",
            period,
        )

    with b:
        sessions = (
            metrics.get(
                "sessions_total"
            )
            if metrics
            else latest.get(
                "sessions_total"
            )
        )

        st.metric(
            "Pregões analisados",
            _number(
                sessions
            ),
        )

    with c:
        experiments = (
            latest.get(
                "experiments_valid"
            )
            or latest.get(
                "experiments_generated"
            )
        )

        st.metric(
            "Experimentos executados",
            _number(
                experiments
            ),
        )

    a, b, c = st.columns(
        3
    )

    with a:
        st.metric(
            "Win Rate",
            (
                _percent(
                    metrics.get(
                        "win_rate_pct"
                    )
                )
                if metrics
                else "Não disponível"
            ),
        )

    with b:
        st.metric(
            "Expectancy",
            (
                _number(
                    metrics.get(
                        "expectancy_points_per_trade"
                    )
                )
                if metrics
                else "Não disponível"
            ),
        )

    with c:
        if metrics:
            pf = metrics.get(
                "profit_factor"
            )

            if pf is None:
                pf_display = _text(
                    metrics.get(
                        "profit_factor_status"
                    )
                )

            else:
                pf_display = _number(
                    pf
                )

        else:
            pf_display = (
                "Não disponível"
            )

        st.metric(
            "Profit Factor",
            pf_display,
        )

    if experiment_id:
        st.caption(
            (
                "Métricas apresentadas a partir "
                "do experimento de referência "
                "formalmente disponível na última "
                "pesquisa."
            )
        )

    st.divider()

    _render_attention(
        rows
    )
