from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
import streamlit as st

from operar_range.path_aggregation_engine import (
    load_path_stop_analytics,
    load_path_target_analytics,
    load_path_target_stop_matrix,
    load_path_trade2_analytics,
)
from operar_range.path_analysis_engine import (
    load_research_path_analysis,
)
from operar_range.path_query_engine import (
    PathQuery,
    execute_path_query,
    get_session_detail,
    resolve_trajectory,
)
from operar_range.research_workspace import (
    create_research_stage22,
    estimate_research,
    load_research_definition,
    research_paths,
)


def _safe_load(
    loader,
    research_id: str,
) -> pl.DataFrame:
    try:
        frame = loader(
            research_id
        )

        if frame is None:
            return pl.DataFrame()

        return frame

    except Exception:
        return pl.DataFrame()


def _distributed_results(
    research_id: str,
) -> pl.DataFrame:
    try:
        path = research_paths(
            research_id
        )[
            "distributed_results"
        ]

        if not Path(
            path
        ).exists():
            return pl.DataFrame()

        return pl.read_parquet(
            path
        )

    except Exception:
        return pl.DataFrame()


def _available_values(
    frame: pl.DataFrame,
    column: str,
) -> list[int]:
    if (
        frame.is_empty()
        or column not in frame.columns
    ):
        return []

    values = (
        frame[
            column
        ]
        .drop_nulls()
        .unique()
        .sort()
        .to_list()
    )

    return [
        int(
            value
        )
        for value in values
    ]


def _percentage_text(
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


def _number_text(
    value: Any,
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
            f"{numeric:.2f}"
        )

    except Exception:
        return str(
            value
        )


def _metric_answer(
    *,
    title: str,
    count: Any,
    denominator: Any,
    pct: Any,
) -> None:
    left, middle, right = st.columns(
        3
    )

    with left:
        st.metric(
            title,
            _number_text(
                count
            ),
        )

    with middle:
        st.metric(
            "Denominador",
            _number_text(
                denominator
            ),
        )

    with right:
        st.metric(
            "Percentual",
            _percentage_text(
                pct
            ),
        )


def _single_row(
    frame: pl.DataFrame,
    **filters: Any,
) -> dict[str, Any] | None:
    if frame.is_empty():
        return None

    filtered = frame

    for column, value in filters.items():
        if column not in filtered.columns:
            return None

        filtered = filtered.filter(
            pl.col(
                column
            )
            == value
        )

    if filtered.is_empty():
        return None

    return filtered.row(
        0,
        named=True,
    )


def _research_grid(
    path_analysis: pl.DataFrame,
) -> tuple[
    list[int],
    list[int],
    list[int],
    list[int],
]:
    if path_analysis.is_empty():
        return (
            [],
            [],
            [],
            [],
        )

    trade1 = path_analysis.filter(
        pl.col(
            "trade"
        )
        == "TRADE_1"
    )

    trade2 = path_analysis.filter(
        pl.col(
            "trade"
        )
        == "TRADE_2"
    )

    trade1_targets = _available_values(
        trade1,
        "target_points",
    )

    trade1_stops = _available_values(
        trade1,
        "stop_points",
    )

    trade2_targets = _available_values(
        trade2,
        "target_points",
    )

    trade2_stops = _available_values(
        trade2,
        "stop_points",
    )

    return (
        trade1_targets,
        trade1_stops,
        trade2_targets,
        trade2_stops,
    )


def _grid_unavailable(
    *,
    kind: str,
    value: int,
    available: list[int],
) -> None:
    st.warning(
        (
            f"{kind} {value} não pertence ao "
            "universo paramétrico desta Research."
        )
    )

    st.caption(
        (
            "Uma Research concluída é imutável. "
            "Para pesquisar esse valor, será "
            "necessário criar uma nova Research "
            "com outro grid."
        )
    )

    if available:
        st.caption(
            (
                "Valores disponíveis nesta "
                f"Research: {available}"
            )
        )

    st.session_state[
        "product01_requested_grid_change"
    ] = True


def _query_sessions(
    query: PathQuery,
) -> dict[str, Any]:
    try:
        result = execute_path_query(
            query
        )

        if not isinstance(
            result,
            dict,
        ):
            return {
                "sessions_found": 0,
                "sessions": [],
            }

        return result

    except Exception:
        return {
            "sessions_found": 0,
            "sessions": [],
        }


def _render_session_detail(
    *,
    research_id: str,
    experiment_id: str,
    session_date: str,
) -> None:
    try:
        detail = get_session_detail(
            research_id=research_id,
            experiment_id=experiment_id,
            session_date=session_date,
        )

    except Exception as exc:
        st.error(
            (
                "Não foi possível abrir o "
                "detalhe deste pregão."
            )
        )

        st.caption(
            str(
                exc
            )
        )
        return

    if not detail.get(
        "found"
    ):
        st.info(
            "Detalhe do pregão indisponível."
        )
        return

    trades = detail.get(
        "trades"
    ) or []

    st.markdown(
        f"### Pregão {session_date}"
    )

    for trade in trades:
        trade_name = str(
            trade.get(
                "trade"
            )
            or "Trade"
        )

        st.markdown(
            f"#### {trade_name}"
        )

        c1, c2, c3, c4 = st.columns(
            4
        )

        with c1:
            st.metric(
                "Direção",
                str(
                    trade.get(
                        "direction"
                    )
                    or "—"
                ),
            )

        with c2:
            st.metric(
                "Entrada",
                _number_text(
                    trade.get(
                        "entry_price"
                    )
                ),
            )

        with c3:
            st.metric(
                "Retorno ao zero",
                (
                    "Sim"
                    if trade.get(
                        "first_zero_return_occurred"
                    )
                    else "Não"
                ),
            )

        with c4:
            st.metric(
                "Trade 2",
                (
                    "Executado"
                    if trade.get(
                        "trade2_executed"
                    )
                    else "Não executado"
                ),
            )

        if trade.get(
            "first_zero_return_timestamp"
        ):
            st.caption(
                (
                    "Primeiro retorno ao zero: "
                    f"{trade.get('first_zero_return_timestamp')}"
                )
            )

        targets = trade.get(
            "targets"
        ) or []

        stops = trade.get(
            "stops"
        ) or []

        left, right = st.columns(
            2
        )

        with left:
            st.markdown(
                "**Targets atingidos**"
            )

            reached_targets = [
                row
                for row in targets
                if row.get(
                    "target_reached"
                )
            ]

            if not reached_targets:
                st.caption(
                    "Nenhum target registrado."
                )

            else:
                for row in reached_targets:
                    label = row.get(
                        "target_label"
                    )

                    relation = row.get(
                        "target_zero_relation"
                    )

                    st.write(
                        (
                            f"{label} pts — "
                            f"{relation or 'sem relação registrada'}"
                        )
                    )

        with right:
            st.markdown(
                "**Stops atingidos**"
            )

            reached_stops = [
                row
                for row in stops
                if row.get(
                    "stop_reached"
                )
            ]

            if not reached_stops:
                st.caption(
                    "Nenhum stop registrado."
                )

            else:
                for row in reached_stops:
                    st.write(
                        (
                            f"{row.get('stop_points')} pts — "
                            f"{row.get('stop_timestamp')}"
                        )
                    )

    st.divider()

    st.markdown(
        "### Linha do tempo / Trajectory"
    )

    try:
        trajectory_info = resolve_trajectory(
            research_id=research_id,
            session_date=session_date,
        )

    except Exception as exc:
        st.info(
            "Trajectory indisponível."
        )

        st.caption(
            str(
                exc
            )
        )
        return

    if not trajectory_info.get(
        "trajectory_exists"
    ):
        st.info(
            "Trajectory não existe para este pregão."
        )
        return

    trajectory_path = trajectory_info.get(
        "trajectory_path"
    )

    st.caption(
        (
            f"{trajectory_info.get('trajectory_rows', 0)} "
            "mudanças de preço registradas."
        )
    )

    if not trajectory_path:
        return

    path = Path(
        str(
            trajectory_path
        )
    )

    if not path.exists():
        st.info(
            "Arquivo de trajectory não encontrado."
        )
        return

    try:
        trajectory = pl.read_parquet(
            path
        )

    except Exception as exc:
        st.info(
            "Não foi possível ler a trajectory."
        )

        st.caption(
            str(
                exc
            )
        )
        return

    preferred = [
        column
        for column in [
            "timestamp",
            "trade_number",
            "price",
            "points",
            "points_vs_entry",
            "excursion_favoravel",
            "excursion_contraria",
        ]
        if column
        in trajectory.columns
    ]

    if preferred:
        preview = (
            trajectory
            .select(
                preferred
            )
            .head(
                5000
            )
        )

        st.dataframe(
            preview.to_pandas(),
            use_container_width=True,
            hide_index=True,
            height=420,
        )

    else:
        st.caption(
            (
                "Trajectory disponível, mas sem "
                "colunas reconhecidas para preview."
            )
        )


def _render_session_list(
    *,
    research_id: str,
    result: dict[str, Any],
    key_prefix: str,
) -> None:
    sessions = result.get(
        "sessions"
    ) or []

    if not sessions:
        st.info(
            "Nenhum pregão corresponde à pergunta."
        )
        return

    st.markdown(
        "### Pregões"
    )

    st.caption(
        (
            f"{len(sessions)} pregão(ões) "
            "no resultado."
        )
    )

    options: list[
        tuple[str, str]
    ] = []

    records = result.get(
        "records"
    ) or result.get(
        "rows"
    ) or []

    experiment_by_session: dict[
        str,
        str,
    ] = {}

    for row in records:
        date_value = row.get(
            "session_date"
        )

        experiment_value = row.get(
            "experiment_id"
        )

        if (
            date_value is not None
            and experiment_value is not None
        ):
            experiment_by_session.setdefault(
                str(
                    date_value
                ),
                str(
                    experiment_value
                ),
            )

    for session_date in sessions:
        date_text = str(
            session_date
        )

        experiment_id = (
            experiment_by_session.get(
                date_text
            )
        )

        if experiment_id is not None:
            options.append(
                (
                    date_text,
                    experiment_id,
                )
            )

    if not options:
        st.caption(
            (
                "A lista foi encontrada, mas não "
                "há Experiment ID disponível para "
                "abrir o detalhe."
            )
        )
        return

    labels = [
        item[
            0
        ]
        for item in options
    ]

    selected_date = st.selectbox(
        "Abrir pregão",
        options=labels,
        key=(
            f"{key_prefix}_session"
        ),
    )

    selected = next(
        (
            item
            for item in options
            if item[
                0
            ]
            == selected_date
        ),
        None,
    )

    if selected is None:
        return

    if st.button(
        "Abrir detalhe e trajetória",
        key=(
            f"{key_prefix}_open"
        ),
    ):
        st.session_state[
            f"{key_prefix}_opened"
        ] = selected

    opened = st.session_state.get(
        f"{key_prefix}_opened"
    )

    if opened:
        _render_session_detail(
            research_id=research_id,
            experiment_id=str(
                opened[
                    1
                ]
            ),
            session_date=str(
                opened[
                    0
                ]
            ),
        )


def _render_targets(
    *,
    research_id: str,
    target_analytics: pl.DataFrame,
    targets: list[int],
) -> None:
    st.markdown(
        "## Alvos"
    )

    st.caption(
        (
            "Pergunte o que aconteceu quando o "
            "trade alcançou determinado alvo."
        )
    )

    if not targets:
        st.info(
            "Analytics de alvos indisponível."
        )
        return

    target = st.selectbox(
        "Alvo",
        options=targets,
        key="product01_target_value",
    )

    row = _single_row(
        target_analytics,
        trade="TRADE_1",
        target_points=target,
    )

    if row is None:
        st.info(
            "Resposta agregada indisponível."
        )
        return

    st.markdown(
        "### Quantos atingiram?"
    )

    _metric_answer(
        title="Pregões",
        count=row.get(
            "target_reached_count"
        ),
        denominator=row.get(
            "target_reached_denominator"
        ),
        pct=row.get(
            "target_reached_pct"
        ),
    )

    st.markdown(
        "### Antes do primeiro retorno ao zero"
    )

    _metric_answer(
        title="Pregões",
        count=row.get(
            "target_before_first_zero_count"
        ),
        denominator=row.get(
            "target_before_first_zero_denominator"
        ),
        pct=row.get(
            "target_before_first_zero_pct"
        ),
    )

    before_result = _query_sessions(
        PathQuery(
            research_id=research_id,
            trade="TRADE_1",
            target_points=target,
            target_reached=True,
            target_before_first_zero=True,
        )
    )

    with st.expander(
        "Ver pregões — antes do zero"
    ):
        _render_session_list(
            research_id=research_id,
            result=before_result,
            key_prefix=(
                f"target_{target}_before_zero"
            ),
        )

    st.markdown(
        "### Depois do primeiro retorno ao zero"
    )

    _metric_answer(
        title="Pregões",
        count=row.get(
            "target_after_first_zero_count"
        ),
        denominator=row.get(
            "target_after_first_zero_denominator"
        ),
        pct=row.get(
            "target_after_first_zero_pct"
        ),
    )

    after_result = _query_sessions(
        PathQuery(
            research_id=research_id,
            trade="TRADE_1",
            target_points=target,
            target_reached=True,
            target_after_first_zero=True,
        )
    )

    with st.expander(
        "Ver pregões — depois do zero"
    ):
        _render_session_list(
            research_id=research_id,
            result=after_result,
            key_prefix=(
                f"target_{target}_after_zero"
            ),
        )

    st.markdown(
        "### Atingiram o alvo e depois voltaram ao zero"
    )

    _metric_answer(
        title="Pregões",
        count=row.get(
            "target_then_zero_count"
        ),
        denominator=row.get(
            "target_then_zero_denominator"
        ),
        pct=row.get(
            "target_then_zero_pct"
        ),
    )

    then_zero_result = _query_sessions(
        PathQuery(
            research_id=research_id,
            trade="TRADE_1",
            target_points=target,
            target_reached=True,
            target_then_zero=True,
        )
    )

    with st.expander(
        "Ver pregões — alvo e depois zero"
    ):
        _render_session_list(
            research_id=research_id,
            result=then_zero_result,
            key_prefix=(
                f"target_{target}_then_zero"
            ),
        )


def _render_target_stop(
    *,
    research_id: str,
    matrix: pl.DataFrame,
    targets: list[int],
    stops: list[int],
) -> None:
    st.markdown(
        "## Target × Stop"
    )

    if (
        not targets
        or not stops
    ):
        st.info(
            "Matriz Target × Stop indisponível."
        )
        return

    left, right = st.columns(
        2
    )

    with left:
        target = st.number_input(
            "Target",
            min_value=1,
            step=5,
            value=(
                200
                if 200 in targets
                else targets[
                    0
                ]
            ),
            key="product01_matrix_target",
        )

    with right:
        stop = st.number_input(
            "Stop",
            min_value=1,
            step=5,
            value=(
                170
                if 170 in stops
                else stops[
                    0
                ]
            ),
            key="product01_matrix_stop",
        )

    target = int(
        target
    )

    stop = int(
        stop
    )

    if target not in targets:
        _grid_unavailable(
            kind="Target",
            value=target,
            available=targets,
        )
        return

    if stop not in stops:
        _grid_unavailable(
            kind="Stop",
            value=stop,
            available=stops,
        )
        return

    row = _single_row(
        matrix,
        trade="TRADE_1",
        target_points=target,
        stop_points=stop,
    )

    if row is None:
        st.info(
            "Combinação não encontrada."
        )
        return

    st.markdown(
        "### Target antes do Stop"
    )

    stop_before_target = int(
        row.get(
            "stop_before_target_count"
        )
        or 0
    )

    valid = int(
        row.get(
            "valid_trade_sessions"
        )
        or 0
    )

    target_before_stop = max(
        valid
        - stop_before_target,
        0,
    )

    target_before_stop_pct = (
        (
            target_before_stop
            / valid
        )
        * 100
        if valid
        else None
    )

    _metric_answer(
        title="Pregões",
        count=target_before_stop,
        denominator=valid,
        pct=target_before_stop_pct,
    )

    st.markdown(
        "### Target atingido e depois Stop"
    )

    _metric_answer(
        title="Pregões",
        count=row.get(
            "stop_after_target_count"
        ),
        denominator=row.get(
            "stop_after_target_denominator"
        ),
        pct=row.get(
            "stop_after_target_pct"
        ),
    )

    after_result = _query_sessions(
        PathQuery(
            research_id=research_id,
            trade="TRADE_1",
            target_points=target,
            target_reached=True,
            stop_points=stop,
            stop_reached=True,
            stop_after_target=True,
        )
    )

    with st.expander(
        "Ver pregões — target e depois stop"
    ):
        _render_session_list(
            research_id=research_id,
            result=after_result,
            key_prefix=(
                f"matrix_{target}_{stop}_after"
            ),
        )

    st.markdown(
        "### Stop antes do Target"
    )

    _metric_answer(
        title="Pregões",
        count=row.get(
            "stop_before_target_count"
        ),
        denominator=row.get(
            "stop_before_target_denominator"
        ),
        pct=row.get(
            "stop_before_target_pct"
        ),
    )

    before_result = _query_sessions(
        PathQuery(
            research_id=research_id,
            trade="TRADE_1",
            target_points=target,
            stop_points=stop,
            stop_reached=True,
            stop_before_target=True,
        )
    )

    with st.expander(
        "Ver pregões — stop antes do target"
    ):
        _render_session_list(
            research_id=research_id,
            result=before_result,
            key_prefix=(
                f"matrix_{target}_{stop}_before"
            ),
        )


def _render_stops(
    *,
    research_id: str,
    stop_analytics: pl.DataFrame,
    stops: list[int],
) -> None:
    st.markdown(
        "## Stops"
    )

    if not stops:
        st.info(
            "Analytics de stops indisponível."
        )
        return

    stop = int(
        st.number_input(
            "Stop a investigar",
            min_value=1,
            step=5,
            value=(
                170
                if 170 in stops
                else stops[
                    0
                ]
            ),
            key="product01_stop_value",
        )
    )

    if stop not in stops:
        _grid_unavailable(
            kind="Stop",
            value=stop,
            available=stops,
        )
        return

    row = _single_row(
        stop_analytics,
        trade="TRADE_1",
        stop_points=stop,
    )

    if row is None:
        st.info(
            "Resposta de stop indisponível."
        )
        return

    st.markdown(
        "### Quantos atingiram o stop?"
    )

    _metric_answer(
        title="Pregões",
        count=row.get(
            "stop_reached_count"
        ),
        denominator=row.get(
            "stop_reached_denominator"
        ),
        pct=row.get(
            "stop_reached_pct"
        ),
    )

    st.markdown(
        "### Stop antes de qualquer target"
    )

    _metric_answer(
        title="Pregões",
        count=row.get(
            "stop_before_any_target_count"
        ),
        denominator=row.get(
            "stop_before_any_target_denominator"
        ),
        pct=row.get(
            "stop_before_any_target_pct"
        ),
    )

    result = _query_sessions(
        PathQuery(
            research_id=research_id,
            trade="TRADE_1",
            stop_points=stop,
            stop_reached=True,
            stop_before_any_target=True,
        )
    )

    with st.expander(
        "Ver pregões — stop antes de qualquer target"
    ):
        _render_session_list(
            research_id=research_id,
            result=result,
            key_prefix=(
                f"stop_{stop}_before_any"
            ),
        )


def _render_trade2(
    *,
    research_id: str,
    trade2_analytics: pl.DataFrame,
    distributed: pl.DataFrame,
    trade1_stops: list[int],
    trade2_targets: list[int],
    trade2_stops: list[int],
) -> None:
    st.markdown(
        "## Trade 2 / Reentrada"
    )

    st.caption(
        (
            "Funil apresentado exatamente como "
            "persistido pelo motor: STOP no Trade 1 "
            "→ elegível → novo rompimento do mesmo "
            "gatilho ocorreu → Trade 2 executado."
        )
    )

    if distributed.is_empty():
        st.info(
            "Resultados de execução indisponíveis."
        )
        return

    eligible_count = (
        distributed
        .filter(
            pl.col(
                "trade2_eligible"
            )
            .fill_null(
                False
            )
        )
        .height
        if "trade2_eligible"
        in distributed.columns
        else 0
    )

    occurred_count = (
        distributed
        .filter(
            pl.col(
                "trade2_occurred"
            )
            .fill_null(
                False
            )
        )
        .height
        if "trade2_occurred"
        in distributed.columns
        else 0
    )

    executed_count = (
        distributed
        .filter(
            pl.col(
                "trade2_executed"
            )
            .fill_null(
                False
            )
        )
        .height
        if "trade2_executed"
        in distributed.columns
        else 0
    )

    stopped_trade1_count = (
        distributed
        .filter(
            pl.col(
                "final_reason"
            )
            == "STOP"
        )
        .height
        if "final_reason"
        in distributed.columns
        else None
    )

    c1, c2, c3, c4 = st.columns(
        4
    )

    with c1:
        st.metric(
            "Trade 1 com STOP",
            _number_text(
                stopped_trade1_count
            ),
        )

    with c2:
        st.metric(
            "Trade 2 elegíveis",
            _number_text(
                eligible_count
            ),
        )

    with c3:
        st.metric(
            "Novo rompimento ocorreu",
            _number_text(
                occurred_count
            ),
        )

    with c4:
        st.metric(
            "Trade 2 executados",
            _number_text(
                executed_count
            ),
        )

    if executed_count == 0:
        st.info(
            (
                "Esta Research não possui Trade 2 "
                "executado. Nenhum resultado de "
                "reentrada será inferido."
            )
        )
        return

    executed = distributed.filter(
        pl.col(
            "trade2_executed"
        )
        .fill_null(
            False
        )
    )

    filter_columns = st.columns(
        3
    )

    with filter_columns[0]:
        selected_t1_stop = (
            st.selectbox(
                "Stop do Trade 1",
                options=(
                    ["Todos"]
                    + trade1_stops
                ),
                key="product01_t2_t1_stop",
            )
        )

    with filter_columns[1]:
        selected_t2_target = (
            st.selectbox(
                "Target do Trade 2",
                options=(
                    ["Todos"]
                    + trade2_targets
                ),
                key="product01_t2_target",
            )
        )

    with filter_columns[2]:
        selected_t2_stop = (
            st.selectbox(
                "Stop do Trade 2",
                options=(
                    ["Todos"]
                    + trade2_stops
                ),
                key="product01_t2_stop",
            )
        )

    if (
        selected_t1_stop
        != "Todos"
        and "stop_points"
        in executed.columns
    ):
        executed = executed.filter(
            pl.col(
                "stop_points"
            )
            == float(
                selected_t1_stop
            )
        )

    display_columns = [
        column
        for column in [
            "date",
            "experiment_id",
            "trade2_mfe",
            "trade2_mae",
            "trade2_result_points",
            "consolidated_result_points",
            "trade2_final_reason",
        ]
        if column
        in executed.columns
    ]

    if display_columns:
        display = (
            executed
            .select(
                display_columns
            )
            .rename(
                {
                    "date": "Data",
                    "experiment_id": "Experimento",
                    "trade2_mfe": "MFE Trade 2",
                    "trade2_mae": "MAE Trade 2",
                    "trade2_result_points": (
                        "Resultado Trade 2"
                    ),
                    "consolidated_result_points": (
                        "Resultado consolidado T1 + T2"
                    ),
                    "trade2_final_reason": (
                        "Final reason"
                    ),
                }
            )
        )

        st.dataframe(
            display.to_pandas(),
            use_container_width=True,
            hide_index=True,
        )

    if (
        "trade2_winner"
        in executed.columns
    ):
        positives = (
            executed
            .filter(
                pl.col(
                    "trade2_winner"
                )
                .fill_null(
                    False
                )
            )
            .height
        )

    else:
        positives = None

    if (
        "trade2_loser"
        in executed.columns
    ):
        negatives = (
            executed
            .filter(
                pl.col(
                    "trade2_loser"
                )
                .fill_null(
                    False
                )
            )
            .height
        )

    else:
        negatives = None

    if (
        "trade2_breakeven"
        in executed.columns
    ):
        breakevens = (
            executed
            .filter(
                pl.col(
                    "trade2_breakeven"
                )
                .fill_null(
                    False
                )
            )
            .height
        )

    else:
        breakevens = None

    c1, c2, c3 = st.columns(
        3
    )

    with c1:
        st.metric(
            "Trade 2 positivos",
            _number_text(
                positives
            ),
        )

    with c2:
        st.metric(
            "Trade 2 negativos",
            _number_text(
                negatives
            ),
        )

    with c3:
        st.metric(
            "Trade 2 break-even",
            _number_text(
                breakevens
            ),
        )

    if (
        "consolidated_result_points"
        in executed.columns
    ):
        recovered = (
            executed
            .filter(
                pl.col(
                    "consolidated_result_points"
                )
                >= 0
            )
            .height
        )

        st.metric(
            "Ciclos recuperados integralmente",
            recovered,
        )

    if (
        not trade2_analytics.is_empty()
        and selected_t1_stop
        != "Todos"
        and selected_t2_target
        != "Todos"
        and selected_t2_stop
        != "Todos"
    ):
        analytics_row = _single_row(
            trade2_analytics,
            trade1_stop_points=int(
                selected_t1_stop
            ),
            trade2_target_points=int(
                selected_t2_target
            ),
            trade2_stop_points=int(
                selected_t2_stop
            ),
        )

        if analytics_row is not None:
            st.markdown(
                "### Resposta agregada do grid selecionado"
            )

            st.write(
                {
                    "Trade 1 stopados": (
                        analytics_row.get(
                            "trade1_stopped_count"
                        )
                    ),
                    "Trade 2 elegíveis": (
                        analytics_row.get(
                            "trade2_eligible_count"
                        )
                    ),
                    "Novo rompimento ocorreu": (
                        analytics_row.get(
                            "trade2_occurred_count"
                        )
                    ),
                    "Trade 2 executados": (
                        analytics_row.get(
                            "trade2_executed_count"
                        )
                    ),
                }
            )




def _parse_grid_list(
    value: Any,
) -> list[int]:
    if value is None:
        return []

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        raw_values = list(
            value
        )

    else:
        raw_values = [
            item.strip()
            for item in str(
                value
            ).split(
                ","
            )
            if item.strip()
        ]

    result: list[int] = []

    for raw in raw_values:
        numeric = int(
            float(
                raw
            )
        )

        if numeric <= 0:
            raise ValueError(
                (
                    "Valores do grid devem "
                    "ser positivos."
                )
            )

        result.append(
            numeric
        )

    return sorted(
        set(
            result
        )
    )


def _candidate_path_parameters(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    mode = str(
        candidate.get(
            "mode"
        )
        or ""
    )

    parameters: dict[
        str,
        Any,
    ] = {}

    if mode == "Intervalo":
        parameters.update(
            {
                "target_start": int(
                    candidate[
                        "target_start"
                    ]
                ),
                "target_end": int(
                    candidate[
                        "target_end"
                    ]
                ),
                "target_step": int(
                    candidate[
                        "target_step"
                    ]
                ),
                "stop_start": int(
                    candidate[
                        "stop_start"
                    ]
                ),
                "stop_end": int(
                    candidate[
                        "stop_end"
                    ]
                ),
                "stop_step": int(
                    candidate[
                        "stop_step"
                    ]
                ),
            }
        )

    elif mode == "Lista explícita":
        parameters[
            "target_values"
        ] = _parse_grid_list(
            candidate.get(
                "target_values"
            )
        )

        parameters[
            "stop_values"
        ] = _parse_grid_list(
            candidate.get(
                "stop_values"
            )
        )

    else:
        raise ValueError(
            "Formato de grid não suportado."
        )

    trade2_mode = str(
        candidate.get(
            "trade2_mode"
        )
        or ""
    )

    if (
        trade2_mode
        == "Configurar separadamente"
    ):
        trade2_targets = (
            _parse_grid_list(
                candidate.get(
                    "trade2_target_values"
                )
            )
        )

        trade2_stops = (
            _parse_grid_list(
                candidate.get(
                    "trade2_stop_values"
                )
            )
        )

        if trade2_targets:
            parameters[
                "trade2_target_values"
            ] = trade2_targets

        if trade2_stops:
            parameters[
                "trade2_stop_values"
            ] = trade2_stops

    return parameters


def _derived_research_definition(
    *,
    source_research_id: str,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    source = load_research_definition(
        source_research_id
    )

    derived = dict(
        source
    )

    derived[
        "path_parameters"
    ] = (
        _candidate_path_parameters(
            candidate
        )
    )

    #
    # A definição derivada é apenas uma proposta
    # em memória neste ponto.
    #
    # Nenhum Research ID é criado aqui.
    #
    derived.pop(
        "research_id",
        None,
    )

    derived.pop(
        "research_definition_sha256",
        None,
    )

    return derived


def _create_derived_research(
    *,
    source_research_id: str,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    #
    # A criação utiliza exclusivamente o
    # contrato homologado de criação de Research.
    #
    # A Research de origem nunca é alterada.
    #
    definition = (
        _derived_research_definition(
            source_research_id=(
                source_research_id
            ),
            candidate=(
                candidate
            ),
        )
    )

    result = create_research_stage22(
        definition
    )

    research_id = str(
        result.get(
            "research_id"
        )
        or ""
    ).strip()

    if not research_id:
        raise RuntimeError(
            "A criação da nova Research não "
            "retornou um Research ID."
        )

    return {
        "research_id": (
            research_id
        ),
        "definition": (
            definition
        ),
        "result": (
            result
        ),
    }


def _render_derived_research_estimate(
    research_id: str,
) -> None:
    requested = bool(
        st.session_state.get(
            "product01_branch_requested",
            False,
        )
    )

    source_id = str(
        st.session_state.get(
            "product01_branch_from_research_id"
        )
        or ""
    )

    candidate = (
        st.session_state.get(
            "product01_candidate_grid"
        )
    )

    if (
        not requested
        or source_id != research_id
        or not isinstance(
            candidate,
            dict,
        )
    ):
        return

    st.divider()

    st.markdown(
        "#### Estimativa da nova Research"
    )

    st.caption(
        (
            "Esta é apenas uma simulação da "
            "Research derivada. Nenhum Research ID "
            "foi criado e a Research atual "
            "permanece intacta."
        )
    )

    try:
        definition = (
            _derived_research_definition(
                source_research_id=(
                    research_id
                ),
                candidate=(
                    candidate
                ),
            )
        )

        path_parameters = dict(
            definition.get(
                "path_parameters"
            )
            or {}
        )

        estimate = estimate_research(
            definition
        )

    except Exception as exc:
        st.error(
            (
                "Não foi possível estimar "
                "o novo universo."
            )
        )

        st.caption(
            str(
                exc
            )
        )

        return

    st.session_state[
        "product01_derived_definition"
    ] = definition

    st.session_state[
        "product01_derived_estimate"
    ] = estimate

    st.markdown(
        "**Novo universo proposto**"
    )

    st.json(
        path_parameters,
        expanded=False,
    )

    generated = estimate.get(
        "generated_configurations"
    )

    valid = estimate.get(
        "valid_configurations"
    )

    invalid = estimate.get(
        "invalid_configurations"
    )

    sessions = estimate.get(
        "sessions_total"
    )

    units = estimate.get(
        "execution_units_estimated"
    )

    batches = estimate.get(
        "batches_estimated"
    )

    c1, c2, c3 = st.columns(
        3
    )

    with c1:
        st.metric(
            "Configurações geradas",
            _number_text(
                generated
            ),
        )

        st.metric(
            "Configurações válidas",
            _number_text(
                valid
            ),
        )

    with c2:
        st.metric(
            "Configurações inválidas",
            _number_text(
                invalid
            ),
        )

        st.metric(
            "Pregões",
            _number_text(
                sessions
            ),
        )

    with c3:
        st.metric(
            "Unidades estimadas",
            _number_text(
                units
            ),
        )

        st.metric(
            "Batches estimados",
            _number_text(
                batches
            ),
        )

    st.success(
        (
            "Estimativa concluída. "
            "A Research atual permanece "
            "inalterada."
        )
    )

    st.warning(
        (
            "A ação abaixo cria uma NOVA "
            "Research com identidade e lineage "
            "próprios."
        )
    )

    if st.button(
        "Criar nova Research a partir deste grid",
        type="primary",
        key=(
            "product01_create_derived_research_"
            + research_id
        ),
    ):
        try:
            created = (
                _create_derived_research(
                    source_research_id=(
                        research_id
                    ),
                    candidate=(
                        candidate
                    ),
                )
            )

        except Exception as exc:
            st.error(
                (
                    "Não foi possível criar "
                    "a nova Research."
                )
            )

            st.caption(
                str(
                    exc
                )
            )

            return

        new_research_id = str(
            created[
                "research_id"
            ]
        )

        #
        # A origem continua selecionada nesta
        # renderização. Registramos a nova Research
        # para o próximo contexto da interface,
        # sem reexecutá-la automaticamente.
        #
        st.session_state[
            "product01_created_research_id"
        ] = new_research_id

        st.session_state[
            "active_research_id"
        ] = new_research_id

        st.session_state[
            "product01_branch_requested"
        ] = False

        st.session_state.pop(
            "product01_derived_definition",
            None,
        )

        st.session_state.pop(
            "product01_derived_estimate",
            None,
        )

        st.success(
            (
                "Nova Research criada: "
                + new_research_id
            )
        )

        st.caption(
            (
                "A Research de origem "
                + research_id
                + " permaneceu intacta. "
                "A nova Research ainda não foi "
                "executada automaticamente."
            )
        )


def _format_grid_values(
    values: list[int],
) -> str:
    if not values:
        return "Não disponível"

    return ", ".join(
        str(
            value
        )
        for value in values
    )


def _render_grid_identity(
    *,
    research_id: str,
    trade1_targets: list[int],
    trade1_stops: list[int],
    trade2_targets: list[int],
    trade2_stops: list[int],
) -> None:
    st.markdown(
        "### Universo desta Research"
    )

    st.caption(
        (
            "Este universo paramétrico pertence "
            "à identidade desta Research. "
            "As perguntas abaixo consultam somente "
            "os níveis já calculados para ela."
        )
    )

    c1, c2, c3, c4 = st.columns(
        4
    )

    with c1:
        st.caption(
            "Targets Trade 1"
        )

        st.write(
            _format_grid_values(
                trade1_targets
            )
        )

    with c2:
        st.caption(
            "Stops Trade 1"
        )

        st.write(
            _format_grid_values(
                trade1_stops
            )
        )

    with c3:
        st.caption(
            "Targets Trade 2"
        )

        st.write(
            _format_grid_values(
                trade2_targets
            )
        )

    with c4:
        st.caption(
            "Stops Trade 2"
        )

        st.write(
            _format_grid_values(
                trade2_stops
            )
        )

    st.info(
        (
            "A Research atual é imutável. "
            "Alterar targets ou stops exige "
            "uma nova Research com identidade "
            "e lineage próprios."
        )
    )

    with st.expander(
        "Quero investigar outro grid",
        expanded=False,
    ):
        st.markdown(
            "#### Configurar novo universo"
        )

        st.caption(
            (
                "Esta configuração NÃO modifica "
                "a Research atual."
            )
        )

        mode = st.radio(
            "Formato do novo grid",
            [
                "Intervalo",
                "Lista explícita",
            ],
            horizontal=True,
            key=(
                "product01_grid_mode_"
                + research_id
            ),
        )

        if mode == "Intervalo":
            st.markdown(
                "**Targets — Trade 1**"
            )

            a, b, c = st.columns(
                3
            )

            with a:
                target_start = (
                    st.number_input(
                        "Target inicial",
                        min_value=1,
                        value=(
                            trade1_targets[0]
                            if trade1_targets
                            else 100
                        ),
                        step=5,
                        key=(
                            "product01_target_start_"
                            + research_id
                        ),
                    )
                )

            with b:
                target_end = (
                    st.number_input(
                        "Target final",
                        min_value=1,
                        value=(
                            trade1_targets[-1]
                            if trade1_targets
                            else 1000
                        ),
                        step=5,
                        key=(
                            "product01_target_end_"
                            + research_id
                        ),
                    )
                )

            with c:
                target_step = (
                    st.number_input(
                        "Passo do target",
                        min_value=1,
                        value=25,
                        step=1,
                        key=(
                            "product01_target_step_"
                            + research_id
                        ),
                    )
                )

            st.markdown(
                "**Stops — Trade 1**"
            )

            a, b, c = st.columns(
                3
            )

            with a:
                stop_start = (
                    st.number_input(
                        "Stop inicial",
                        min_value=1,
                        value=(
                            trade1_stops[0]
                            if trade1_stops
                            else 100
                        ),
                        step=5,
                        key=(
                            "product01_stop_start_"
                            + research_id
                        ),
                    )
                )

            with b:
                stop_end = (
                    st.number_input(
                        "Stop final",
                        min_value=1,
                        value=(
                            trade1_stops[-1]
                            if trade1_stops
                            else 250
                        ),
                        step=5,
                        key=(
                            "product01_stop_end_"
                            + research_id
                        ),
                    )
                )

            with c:
                stop_step = (
                    st.number_input(
                        "Passo do stop",
                        min_value=1,
                        value=5,
                        step=1,
                        key=(
                            "product01_stop_step_"
                            + research_id
                        ),
                    )
                )

            st.markdown(
                "**Trade 2**"
            )

            trade2_mode = st.radio(
                "Grid do Trade 2",
                [
                    "Herdar Trade 1",
                    "Configurar separadamente",
                ],
                horizontal=True,
                key=(
                    "product01_trade2_grid_mode_"
                    + research_id
                ),
            )

            candidate = {
                "target_start": int(
                    target_start
                ),
                "target_end": int(
                    target_end
                ),
                "target_step": int(
                    target_step
                ),
                "stop_start": int(
                    stop_start
                ),
                "stop_end": int(
                    stop_end
                ),
                "stop_step": int(
                    stop_step
                ),
                "trade2_mode": (
                    trade2_mode
                ),
            }

            if (
                trade2_mode
                == "Configurar separadamente"
            ):
                st.caption(
                    (
                        "A configuração detalhada "
                        "do grid do Trade 2 será "
                        "aplicada na criação da "
                        "nova Research."
                    )
                )

                t2_target_text = (
                    st.text_input(
                        "Targets Trade 2",
                        value=",".join(
                            str(
                                value
                            )
                            for value
                            in trade2_targets
                        ),
                        key=(
                            "product01_t2_targets_"
                            + research_id
                        ),
                    )
                )

                t2_stop_text = (
                    st.text_input(
                        "Stops Trade 2",
                        value=",".join(
                            str(
                                value
                            )
                            for value
                            in trade2_stops
                        ),
                        key=(
                            "product01_t2_stops_"
                            + research_id
                        ),
                    )
                )

                candidate[
                    "trade2_target_values"
                ] = t2_target_text

                candidate[
                    "trade2_stop_values"
                ] = t2_stop_text

        else:
            target_text = (
                st.text_input(
                    "Targets Trade 1",
                    value=",".join(
                        str(
                            value
                        )
                        for value
                        in trade1_targets
                    ),
                    key=(
                        "product01_target_values_"
                        + research_id
                    ),
                )
            )

            stop_text = (
                st.text_input(
                    "Stops Trade 1",
                    value=",".join(
                        str(
                            value
                        )
                        for value
                        in trade1_stops
                    ),
                    key=(
                        "product01_stop_values_"
                        + research_id
                    ),
                )
            )

            t2_target_text = (
                st.text_input(
                    "Targets Trade 2",
                    value=",".join(
                        str(
                            value
                        )
                        for value
                        in trade2_targets
                    ),
                    key=(
                        "product01_t2_target_values_"
                        + research_id
                    ),
                )
            )

            t2_stop_text = (
                st.text_input(
                    "Stops Trade 2",
                    value=",".join(
                        str(
                            value
                        )
                        for value
                        in trade2_stops
                    ),
                    key=(
                        "product01_t2_stop_values_"
                        + research_id
                    ),
                )
            )

            candidate = {
                "target_values": (
                    target_text
                ),
                "stop_values": (
                    stop_text
                ),
                "trade2_target_values": (
                    t2_target_text
                ),
                "trade2_stop_values": (
                    t2_stop_text
                ),
                "trade2_mode": (
                    "Configurar separadamente"
                ),
            }

        st.session_state[
            "product01_candidate_grid"
        ] = {
            "source_research_id": (
                research_id
            ),
            "mode": mode,
            **candidate,
        }

        st.warning(
            (
                "Confirmar este fluxo criará "
                "uma NOVA Research. "
                "A atual continuará intacta."
            )
        )

        if st.button(
            "Estimar nova pesquisa com este grid",
            type="primary",
            key=(
                "product01_branch_grid_"
                + research_id
            ),
        ):
            st.session_state[
                "product01_branch_from_research_id"
            ] = research_id

            st.session_state[
                "product01_branch_requested"
            ] = True

            st.success(
                (
                    "Novo universo preparado para "
                    "estimativa. Nenhuma Research "
                    "foi criada ou modificada "
                    "neste passo."
                )
            )


def render_questions(
    research_id: str,
) -> None:
    st.markdown(
        "# Perguntas"
    )

    st.caption(
        (
            "Formule perguntas quantitativas "
            "sobre esta Research. A interface "
            "consulta somente artifacts e motores "
            "já existentes."
        )
    )

    path_analysis = _safe_load(
        load_research_path_analysis,
        research_id,
    )

    target_analytics = _safe_load(
        load_path_target_analytics,
        research_id,
    )

    target_stop_matrix = _safe_load(
        load_path_target_stop_matrix,
        research_id,
    )

    stop_analytics = _safe_load(
        load_path_stop_analytics,
        research_id,
    )

    trade2_analytics = _safe_load(
        load_path_trade2_analytics,
        research_id,
    )

    distributed = _distributed_results(
        research_id
    )

    (
        trade1_targets,
        trade1_stops,
        trade2_targets,
        trade2_stops,
    ) = _research_grid(
        path_analysis
    )

    _render_grid_identity(
        research_id=research_id,
        trade1_targets=(
            trade1_targets
        ),
        trade1_stops=(
            trade1_stops
        ),
        trade2_targets=(
            trade2_targets
        ),
        trade2_stops=(
            trade2_stops
        ),
    )

    _render_derived_research_estimate(
        research_id
    )

    tabs = st.tabs(
        [
            "Alvos",
            "Retorno ao Zero",
            "Stops",
            "Target × Stop",
            "Trade 2",
            "Gestão",
        ]
    )

    with tabs[0]:
        _render_targets(
            research_id=research_id,
            target_analytics=(
                target_analytics
            ),
            targets=trade1_targets,
        )

    with tabs[1]:
        st.markdown(
            "## Retorno ao Zero"
        )

        st.caption(
            (
                "Use a análise de Alvos para "
                "comparar antes do zero, depois "
                "do zero e alvo seguido de retorno."
            )
        )

        _render_targets(
            research_id=research_id,
            target_analytics=(
                target_analytics
            ),
            targets=trade1_targets,
        )

    with tabs[2]:
        _render_stops(
            research_id=research_id,
            stop_analytics=(
                stop_analytics
            ),
            stops=trade1_stops,
        )

    with tabs[3]:
        _render_target_stop(
            research_id=research_id,
            matrix=(
                target_stop_matrix
            ),
            targets=trade1_targets,
            stops=trade1_stops,
        )

    with tabs[4]:
        _render_trade2(
            research_id=research_id,
            trade2_analytics=(
                trade2_analytics
            ),
            distributed=distributed,
            trade1_stops=trade1_stops,
            trade2_targets=trade2_targets,
            trade2_stops=trade2_stops,
        )

    with tabs[5]:
        st.markdown(
            "## Gestão"
        )

        st.caption(
            (
                "A camada de perguntas de gestão "
                "será construída exclusivamente "
                "sobre métricas já produzidas pelos "
                "artifacts existentes."
            )
        )

        st.info(
            (
                "Nenhuma nova regra de gestão é "
                "calculada nesta interface."
            )
        )
