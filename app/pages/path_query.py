from __future__ import annotations

import polars as pl
import streamlit as st

from operar_range.path_query_engine import (
    PathQuery,
    execute_path_query,
    get_session_detail,
)
from operar_range.research_workspace import (
    research_paths,
)


def _research_ids() -> list[str]:
    root = (
        research_paths(
            "__probe__"
        )["root"]
        .parent
    )

    if not root.exists():
        return []

    return sorted(
        [
            item.name
            for item in root.iterdir()
            if (
                item.is_dir()
                and item.name.startswith(
                    "RES-"
                )
            )
        ]
    )


def _experiment_ids(
    research_id: str,
) -> list[str]:
    paths = research_paths(
        research_id
    )

    candidates = [
        paths.get(
            "distributed_results"
        ),
        paths.get(
            "experiment_manifest"
        ),
        paths.get(
            "valid"
        ),
    ]

    for candidate in candidates:
        if (
            candidate is None
            or not candidate.exists()
        ):
            continue

        frame = pl.read_parquet(
            candidate
        )

        if (
            "experiment_id"
            not in frame.columns
        ):
            continue

        return sorted(
            [
                str(value)
                for value in (
                    frame[
                        "experiment_id"
                    ]
                    .drop_nulls()
                    .unique()
                    .to_list()
                )
            ]
        )

    return []


def _tristate(
    value: str,
) -> bool | None:
    if value == "TRUE":
        return True

    if value == "FALSE":
        return False

    return None


def render() -> None:
    st.header(
        "Path Query"
    )

    st.caption(
        "READ ONLY — Stage 27"
    )

    research_ids = (
        _research_ids()
    )

    if not research_ids:
        st.info(
            "Nenhuma Research disponível."
        )
        return

    active_research_id = (
        st.session_state.get(
            "active_research_id"
        )
    )

    research_index = 0

    if (
        active_research_id
        in research_ids
    ):
        research_index = (
            research_ids.index(
                active_research_id
            )
        )

    research_id = st.selectbox(
        "Research",
        research_ids,
        index=research_index,
    )

    experiment_ids = (
        _experiment_ids(
            research_id
        )
    )

    if not experiment_ids:
        st.info(
            "Nenhum experimento disponível."
        )
        return

    experiment_id = st.selectbox(
        "Experiment",
        experiment_ids,
    )

    trade = st.selectbox(
        "Trade",
        [
            "TRADE_1",
            "TRADE_2",
        ],
    )

    direction_choice = (
        st.selectbox(
            "Direction",
            [
                "ANY",
                "LONG",
                "SHORT",
            ],
        )
    )

    left, right = st.columns(
        2
    )

    with left:
        target_points_raw = (
            st.selectbox(
                "Target",
                [
                    "ANY",
                    "100",
                    "125",
                    "150",
                    "175",
                    "200",
                    "250",
                    "300",
                    "350",
                    "400",
                    "500",
                    "600",
                    "800",
                    "1000",
                ],
            )
        )

        target_reached_raw = (
            st.selectbox(
                "Target reached",
                [
                    "ANY",
                    "TRUE",
                    "FALSE",
                ],
            )
        )

        zero_relation = (
            st.selectbox(
                "Target / Zero",
                [
                    "ANY",
                    "BEFORE_ZERO",
                    "AFTER_ZERO",
                    "THEN_ZERO",
                ],
            )
        )

    with right:
        stop_points_raw = (
            st.selectbox(
                "Stop",
                [
                    "ANY",
                    "100",
                    "125",
                    "150",
                    "175",
                    "200",
                ],
            )
        )

        stop_reached_raw = (
            st.selectbox(
                "Stop reached",
                [
                    "ANY",
                    "TRUE",
                    "FALSE",
                ],
            )
        )

        stop_relation = (
            st.selectbox(
                "Stop / Target",
                [
                    "ANY",
                    "BEFORE_TARGET",
                    "AFTER_TARGET",
                ],
            )
        )

    if trade == "TRADE_2":
        st.subheader(
            "Trade 2"
        )

        trade2_eligible_raw = (
            st.selectbox(
                "Trade 2 eligible",
                [
                    "ANY",
                    "TRUE",
                    "FALSE",
                ],
            )
        )

        trade2_occurred_raw = (
            st.selectbox(
                "Trade 2 occurred",
                [
                    "ANY",
                    "TRUE",
                    "FALSE",
                ],
            )
        )

        trade2_executed_raw = (
            st.selectbox(
                "Trade 2 executed",
                [
                    "ANY",
                    "TRUE",
                    "FALSE",
                ],
            )
        )

    else:
        trade2_eligible_raw = "ANY"
        trade2_occurred_raw = "ANY"
        trade2_executed_raw = "ANY"

    if not st.button(
        "Executar Query",
        type="primary",
    ):
        return

    target_points = (
        None
        if target_points_raw
        == "ANY"
        else int(
            target_points_raw
        )
    )

    stop_points = (
        None
        if stop_points_raw
        == "ANY"
        else int(
            stop_points_raw
        )
    )

    query = PathQuery(
        research_id=research_id,
        experiment_id=experiment_id,
        trade=trade,
        direction=(
            None
            if direction_choice
            == "ANY"
            else direction_choice
        ),
        target_points=(
            target_points
        ),
        target_reached=(
            _tristate(
                target_reached_raw
            )
        ),
        target_before_first_zero=(
            True
            if zero_relation
            == "BEFORE_ZERO"
            else None
        ),
        target_after_first_zero=(
            True
            if zero_relation
            == "AFTER_ZERO"
            else None
        ),
        target_then_zero=(
            True
            if zero_relation
            == "THEN_ZERO"
            else None
        ),
        stop_points=(
            stop_points
        ),
        stop_reached=(
            _tristate(
                stop_reached_raw
            )
        ),
        stop_before_target=(
            True
            if stop_relation
            == "BEFORE_TARGET"
            else None
        ),
        stop_after_target=(
            True
            if stop_relation
            == "AFTER_TARGET"
            else None
        ),
        trade2_eligible=(
            _tristate(
                trade2_eligible_raw
            )
        ),
        trade2_occurred=(
            _tristate(
                trade2_occurred_raw
            )
        ),
        trade2_executed=(
            _tristate(
                trade2_executed_raw
            )
        ),
    )

    result = (
        execute_path_query(
            query
        )
    )

    c1, c2 = st.columns(
        2
    )

    c1.metric(
        "Sessions found",
        result[
            "sessions_found"
        ],
    )

    c2.metric(
        "Rows found",
        result[
            "rows_found"
        ],
    )

    records = result.get(
        "records",
        [],
    )

    if not records:
        st.info(
            "Nenhum pregão encontrado."
        )
        return

    st.dataframe(
        records,
        use_container_width=True,
    )

    sessions = result.get(
        "sessions",
        [],
    )

    if not sessions:
        return

    session_date = st.selectbox(
        "Session detail",
        sessions,
    )

    detail = (
        get_session_detail(
            research_id=(
                research_id
            ),
            experiment_id=(
                experiment_id
            ),
            session_date=(
                session_date
            ),
        )
    )

    st.subheader(
        "Session Detail"
    )

    st.json(
        detail
    )
