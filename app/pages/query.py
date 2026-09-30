from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from operar_range.research_query_engine import (
    ResearchQuery,
    execute_query,
)
from operar_range.research_workspace import (
    list_researches,
)


def _research_ids() -> list[str]:
    rows = list_researches()

    values: list[str] = []

    for row in rows:
        research_id = row.get(
            "research_id"
        )

        if not research_id:
            continue

        values.append(
            str(
                research_id
            )
        )

    return sorted(
        set(
            values
        ),
        reverse=True,
    )


def _default_research_index(
    research_ids: list[str],
) -> int:
    active = st.session_state.get(
        "active_research_id"
    )

    if (
        active is not None
        and str(
            active
        )
        in research_ids
    ):
        return research_ids.index(
            str(
                active
            )
        )

    return 0


def _optional_text(
    value: str,
) -> str | None:
    normalized = value.strip()

    if not normalized:
        return None

    return normalized


def _optional_int(
    value: str,
) -> int | None:
    normalized = value.strip()

    if not normalized:
        return None

    return int(
        normalized
    )


def _tri_state(
    label: str,
    *,
    key: str,
) -> bool | None:
    selected = st.selectbox(
        label,
        options=[
            "QUALQUER",
            "SIM",
            "NÃO",
        ],
        key=key,
    )

    if selected == "SIM":
        return True

    if selected == "NÃO":
        return False

    return None


def _optional_choice(
    label: str,
    options: list[str],
    *,
    key: str,
) -> str | None:
    selected = st.selectbox(
        label,
        options=[
            "QUALQUER",
            *options,
        ],
        key=key,
    )

    if selected == "QUALQUER":
        return None

    return selected


def _build_query(
    *,
    research_id: str,
    experiment_id: str,
    exact_date_enabled: bool,
    exact_date: date,
    year: str,
    month: str,
    trade1_outcome: str | None,
    trade2_enabled: bool | None,
    trade2_eligible: bool | None,
    trade2_executed: bool | None,
    trade2_winner: bool | None,
    trade2_loser: bool | None,
    trade2_breakeven: bool | None,
    direction: str | None,
    result_sign: str | None,
    runner_occurred: bool | None,
) -> ResearchQuery:
    month_value = (
        None
        if month == "QUALQUER"
        else int(
            month
        )
    )

    return ResearchQuery(
        research_id=research_id,
        experiment_id=(
            _optional_text(
                experiment_id
            )
        ),
        date=(
            exact_date.isoformat()
            if exact_date_enabled
            else None
        ),
        year=_optional_int(
            year
        ),
        month=month_value,
        trade1_outcome=(
            trade1_outcome
        ),
        trade2_enabled=(
            trade2_enabled
        ),
        trade2_eligible=(
            trade2_eligible
        ),
        trade2_executed=(
            trade2_executed
        ),
        trade2_winner=(
            trade2_winner
        ),
        trade2_loser=(
            trade2_loser
        ),
        trade2_breakeven=(
            trade2_breakeven
        ),
        direction=direction,
        result_sign=(
            result_sign
        ),
        runner_occurred=(
            runner_occurred
        ),
    )


def _render_summary(
    result: dict[str, Any],
) -> None:
    columns = st.columns(
        4
    )

    columns[0].metric(
        "Sessões",
        result[
            "sessions"
        ],
    )

    columns[1].metric(
        "Experimentos",
        result[
            "experiments"
        ],
    )

    columns[2].metric(
        "Linhas",
        result[
            "rows_found"
        ],
    )

    columns[3].metric(
        "Dataset",
        (
            result.get(
                "dataset_id"
            )
            or "-"
        ),
    )

    st.caption(
        (
            "Research: "
            f"{result['research_id']}"
        )
    )


def render() -> None:
    st.title(
        "Query"
    )

    st.caption(
        (
            "Research Query Engine V1 — "
            "consulta read-only sobre "
            "artifacts de uma Research."
        )
    )

    research_ids = (
        _research_ids()
    )

    if not research_ids:
        st.warning(
            "Nenhuma Research disponível."
        )
        return

    selected_research = (
        st.selectbox(
            "Research ID",
            options=research_ids,
            index=(
                _default_research_index(
                    research_ids
                )
            ),
            key=(
                "query_research_id"
            ),
        )
    )

    st.divider()

    st.subheader(
        "Filtros"
    )

    experiment_id = (
        st.text_input(
            "Experiment ID",
            value="",
            placeholder=(
                "Ex.: EXP-000047"
            ),
            key=(
                "query_experiment_id"
            ),
        )
    )

    date_col_1, date_col_2 = (
        st.columns(
            2
        )
    )

    with date_col_1:
        year = st.text_input(
            "Ano",
            value="",
            placeholder="Ex.: 2026",
            key="query_year",
        )

        month = st.selectbox(
            "Mês",
            options=[
                "QUALQUER",
                *[
                    str(
                        month_number
                    )
                    for month_number
                    in range(
                        1,
                        13,
                    )
                ],
            ],
            key="query_month",
        )

    with date_col_2:
        exact_date_enabled = (
            st.checkbox(
                "Filtrar data exata",
                value=False,
                key=(
                    "query_exact_date_enabled"
                ),
            )
        )

        exact_date = st.date_input(
            "Data",
            key="query_exact_date",
            disabled=(
                not exact_date_enabled
            ),
        )

    trade_col_1, trade_col_2 = (
        st.columns(
            2
        )
    )

    with trade_col_1:
        trade1_outcome = (
            _optional_choice(
                "Trade 1",
                [
                    "WIN",
                    "LOSS",
                    "BREAK_EVEN",
                    "NO_TRADE",
                ],
                key=(
                    "query_trade1_outcome"
                ),
            )
        )

        direction = (
            _optional_choice(
                "Direção",
                [
                    "LONG",
                    "SHORT",
                ],
                key=(
                    "query_direction"
                ),
            )
        )

        result_sign = (
            _optional_choice(
                "Resultado consolidado",
                [
                    "POSITIVE",
                    "NEGATIVE",
                    "ZERO",
                ],
                key=(
                    "query_result_sign"
                ),
            )
        )

        runner_occurred = (
            _tri_state(
                "Runner ocorreu",
                key=(
                    "query_runner_occurred"
                ),
            )
        )

    with trade_col_2:
        trade2_enabled = (
            _tri_state(
                "Trade 2 habilitado",
                key=(
                    "query_trade2_enabled"
                ),
            )
        )

        trade2_eligible = (
            _tri_state(
                "Trade 2 elegível",
                key=(
                    "query_trade2_eligible"
                ),
            )
        )

        trade2_executed = (
            _tri_state(
                "Trade 2 executado",
                key=(
                    "query_trade2_executed"
                ),
            )
        )

        trade2_winner = (
            _tri_state(
                "Trade 2 vencedor",
                key=(
                    "query_trade2_winner"
                ),
            )
        )

        trade2_loser = (
            _tri_state(
                "Trade 2 perdedor",
                key=(
                    "query_trade2_loser"
                ),
            )
        )

        trade2_breakeven = (
            _tri_state(
                "Trade 2 break-even",
                key=(
                    "query_trade2_breakeven"
                ),
            )
        )

    st.divider()

    execute = st.button(
        "Executar consulta",
        type="primary",
        key="query_execute",
    )

    if not execute:
        st.info(
            (
                "Configure os filtros e "
                "execute a consulta."
            )
        )
        return

    try:
        query = _build_query(
            research_id=(
                selected_research
            ),
            experiment_id=(
                experiment_id
            ),
            exact_date_enabled=(
                exact_date_enabled
            ),
            exact_date=exact_date,
            year=year,
            month=month,
            trade1_outcome=(
                trade1_outcome
            ),
            trade2_enabled=(
                trade2_enabled
            ),
            trade2_eligible=(
                trade2_eligible
            ),
            trade2_executed=(
                trade2_executed
            ),
            trade2_winner=(
                trade2_winner
            ),
            trade2_loser=(
                trade2_loser
            ),
            trade2_breakeven=(
                trade2_breakeven
            ),
            direction=direction,
            result_sign=(
                result_sign
            ),
            runner_occurred=(
                runner_occurred
            ),
        )

        result = execute_query(
            query
        )

    except (
        ValueError,
        FileNotFoundError,
    ) as exc:
        st.error(
            str(
                exc
            )
        )
        return

    _render_summary(
        result
    )

    rows = result[
        "rows"
    ]

    if rows.is_empty():
        st.warning(
            (
                "A consulta não encontrou "
                "linhas."
            )
        )
        return

    st.subheader(
        "Resultado"
    )

    st.dataframe(
        rows.to_pandas(),
        use_container_width=True,
        hide_index=True,
    )
