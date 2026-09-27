from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.common import (
    key_value_panel,
    metric_cards,
    page_header,
    section_title,
    status_badge,
)
from app.formatting import (
    NA_TEXT,
    format_integer,
)
from operar_range.quantitative_models import (
    US_OPEN_BREAKOUT_V1_ID,
    default_quantitative_model,
)
from operar_range.research_workspace import (
    DEFAULT_COMPOSITE_WEIGHTS,
    create_research,
    estimate_research,
    execute_research,
    list_available_datasets,
    load_research_manifest,
)


RUNNER_RULES = [
    "CANDLE_BREAK_M5",
]


def _text(
    value: Any,
) -> str:
    if value is None:
        return NA_TEXT

    return str(value)


def _number_or_none(
    value: float,
    enabled: bool,
) -> float | None:
    if not enabled:
        return None

    return float(
        value
    )


def _int_or_none(
    value: int,
    enabled: bool,
) -> int | None:
    if not enabled:
        return None

    return int(
        value
    )


def _parameter_definition_from_ui(
    *,
    stop_values: list[float],
    partial_1_values: list[float],
    partial_1_pct_values: list[float],
) -> dict[str, dict[str, Any]]:
    return {
        "stop_points": {
            "values": [
                float(
                    value
                )
                for value
                in stop_values
            ]
        },
        "partial_1_points": {
            "values": [
                float(
                    value
                )
                for value
                in partial_1_values
            ]
        },
        "partial_1_pct": {
            "values": [
                float(
                    value
                )
                for value
                in partial_1_pct_values
            ]
        },
    }


def _prepared_datasets() -> list[
    dict[str, Any]
]:
    return [
        row
        for row in list_available_datasets()
        if row.get(
            "prepared_for_research"
        )
    ]


def _dataset_label(
    row: dict[str, Any],
) -> str:
    ticker = (
        row.get(
            "ticker"
        )
        or "Dataset histórico"
    )

    start = (
        row.get(
            "period_start"
        )
        or "N/A"
    )

    end = (
        row.get(
            "period_end"
        )
        or "N/A"
    )

    return (
        f"{ticker} | "
        f"{start} → {end}"
    )


def _find_dataset(
    dataset_key: str,
) -> dict[str, Any] | None:
    for row in _prepared_datasets():
        if (
            str(
                row.get(
                    "dataset_key"
                )
            )
            == str(
                dataset_key
            )
        ):
            return row

    return None


def _build_definition(
    *,
    research_name: str,
    description: str,
    model: dict[str, Any],
    dataset: dict[str, Any],
    period_start: str,
    period_end: str,
    stop_values: list[float],
    partial_1_values: list[float],
    partial_1_pct_values: list[float],
    partial_2_enabled: bool,
    partial_2_points: float,
    partial_2_pct: float,
    partial_3_enabled: bool,
    partial_3_points: float,
    partial_3_pct: float,
    break_even_enabled: bool,
    break_even_after_partial: int,
    runner_enabled: bool,
    runner_pct: float,
    runner_rule: str,
    final_target_enabled: bool,
    final_target_points: float,
) -> dict[str, Any]:
    internal = model[
        "internal"
    ]

    base_config = {
        "stop_points": None,

        "partial_1_points": None,
        "partial_1_pct": None,

        "partial_2_points": (
            _number_or_none(
                partial_2_points,
                partial_2_enabled,
            )
        ),
        "partial_2_pct": (
            _number_or_none(
                partial_2_pct,
                partial_2_enabled,
            )
        ),

        "partial_3_points": (
            _number_or_none(
                partial_3_points,
                partial_3_enabled,
            )
        ),
        "partial_3_pct": (
            _number_or_none(
                partial_3_pct,
                partial_3_enabled,
            )
        ),

        "break_even_enabled": bool(
            break_even_enabled
        ),
        "break_even_after_partial": (
            _int_or_none(
                break_even_after_partial,
                break_even_enabled,
            )
        ),

        "runner_enabled": bool(
            runner_enabled
        ),
        "runner_pct": (
            _number_or_none(
                runner_pct,
                runner_enabled,
            )
        ),
        "runner_rule": (
            runner_rule
            if runner_enabled
            else None
        ),

        "final_target_points": (
            _number_or_none(
                final_target_points,
                final_target_enabled,
            )
        ),
    }

    return {
        "research_name": (
            research_name.strip()
        ),
        "description": (
            description.strip()
            or None
        ),
        "model_id": (
            model[
                "model_id"
            ]
        ),
        "model_name": (
            model[
                "name"
            ]
        ),
        "model_version": (
            model[
                "version"
            ]
        ),
        "hypothesis": (
            model[
                "hypothesis"
            ]
        ),
        "dataset_key": (
            dataset.get(
                "dataset_key"
            )
        ),
        "dataset_id": (
            dataset.get(
                "dataset_id"
            )
        ),
        "dataset_version": (
            dataset.get(
                "dataset_version"
            )
        ),
        "dataset_source_sha256": (
            dataset.get(
                "source_sha256"
            )
        ),
        "strategy": (
            model[
                "strategy"
            ]
        ),
        "family": (
            internal[
                "family"
            ]
        ),
        "generation": int(
            internal[
                "generation"
            ]
        ),
        "period_start": (
            period_start
        ),
        "period_end": (
            period_end
        ),
        "rules_version": (
            internal[
                "rules_version"
            ]
        ),
        "batch_size": int(
            internal[
                "batch_size"
            ]
        ),
        "base_config": (
            base_config
        ),
        "parameter_definition": (
            _parameter_definition_from_ui(
                stop_values=(
                    stop_values
                ),
                partial_1_values=(
                    partial_1_values
                ),
                partial_1_pct_values=(
                    partial_1_pct_values
                ),
            )
        ),
        "composite_weights": dict(
            DEFAULT_COMPOSITE_WEIGHTS
        ),
    }


def _render_model_explanation(
    model: dict[str, Any],
) -> None:
    section_title(
        "Modelo quantitativo"
    )

    key_value_panel(
        [
            (
                "Modelo",
                model[
                    "name"
                ],
            ),
            (
                "Hipótese",
                model[
                    "hypothesis"
                ],
            ),
            (
                "Estratégia atual",
                "Trade 1",
            ),
        ],
    )

    active = []

    development = []

    for component in model[
        "components"
    ]:
        if (
            component[
                "status"
            ]
            == "ACTIVE"
        ):
            active.append(
                component[
                    "name"
                ]
            )
        else:
            development.append(
                component[
                    "name"
                ]
            )

    st.markdown(
        "**Componentes atualmente pesquisados:** "
        + ", ".join(
            active
        )
    )

    if development:
        st.info(
            (
                ", ".join(
                    development
                )
                + " — Em desenvolvimento"
            )
        )


def _render_steps(
    current: int,
) -> None:
    labels = [
        "1. Pesquisa",
        "2. Período",
        "3. Parâmetros",
        "4. Resumo",
    ]

    columns = st.columns(
        len(
            labels
        )
    )

    for index, label in enumerate(
        labels,
        start=1,
    ):
        with columns[
            index - 1
        ]:
            if (
                index
                == current
            ):
                st.success(
                    label
                )

            elif (
                index
                < current
            ):
                st.caption(
                    "✓ "
                    + label
                )

            else:
                st.caption(
                    label
                )


def _navigation(
    *,
    step: int,
    can_continue: bool,
) -> None:
    left, right = st.columns(
        2
    )

    with left:
        if (
            step > 1
            and st.button(
                "← VOLTAR",
                use_container_width=True,
                key=(
                    f"stage185_back_{step}"
                ),
            )
        ):
            st.session_state[
                "stage185_research_step"
            ] = (
                step - 1
            )

            st.rerun()

    with right:
        if (
            step < 4
            and st.button(
                "CONTINUAR →",
                type="primary",
                use_container_width=True,
                disabled=(
                    not can_continue
                ),
                key=(
                    f"stage185_next_{step}"
                ),
            )
        ):
            st.session_state[
                "stage185_research_step"
            ] = (
                step + 1
            )

            st.rerun()


def _progress_callback(
    progress_bar,
    status_box,
    detail_box,
):
    labels = {
        "PREPARING": "Preparando pesquisa",
        "EXPERIMENT_GENERATOR": (
            "Gerando experimentos"
        ),
        "CONSTRAINT_ENGINE": (
            "Validando configurações"
        ),
        "BATCH_PLANNER": (
            "Preparando execução"
        ),
        "DISTRIBUTED_EXECUTOR": (
            "Executando pesquisa"
        ),
        "LINEAGE_ADAPTER": (
            "Preservando lineage"
        ),
        "ANALYTICS": (
            "Calculando Analytics"
        ),
        "RANKING": (
            "Gerando Rankings"
        ),
        "COMPLETED": "Concluída",
        "FAILED": "Falhou",
    }

    def callback(
        stage: str,
        fraction: float,
        details: dict[str, Any],
    ) -> None:
        progress_bar.progress(
            int(
                max(
                    0.0,
                    min(
                        1.0,
                        fraction,
                    ),
                )
                * 100
            )
        )

        status_box.info(
            labels.get(
                stage,
                stage,
            )
        )

        parts = []

        completed = details.get(
            "completed_batches"
        )

        total = details.get(
            "total_batches"
        )

        if (
            completed is not None
            and total is not None
        ):
            parts.append(
                (
                    f"Batches: "
                    f"{completed}/{total}"
                )
            )

        units = details.get(
            "execution_units_total"
        )

        if units is not None:
            parts.append(
                (
                    "Execution Units: "
                    f"{units}"
                )
            )

        if parts:
            detail_box.caption(
                " | ".join(
                    parts
                )
            )
        else:
            detail_box.empty()

    return callback


def _step_one(
    *,
    model: dict[str, Any],
    datasets: list[
        dict[str, Any]
    ],
) -> None:
    section_title(
        "Etapa 1 — Pesquisa",
        (
            "Identifique a pesquisa, o modelo "
            "e o dataset que será estudado."
        ),
    )

    research_name = st.text_input(
        "Nome da pesquisa",
        value=st.session_state.get(
            "stage185_research_name",
            "",
        ),
        placeholder=(
            "Ex.: Trade 1 — Stop 170"
        ),
        key=(
            "stage185_research_name"
        ),
    )

    st.text_input(
        "Modelo",
        value=model[
            "name"
        ],
        disabled=True,
        key=(
            "stage185_model_name"
        ),
    )

    options = [
        str(
            row[
                "dataset_key"
            ]
        )
        for row in datasets
    ]

    labels = {
        str(
            row[
                "dataset_key"
            ]
        ): _dataset_label(
            row
        )
        for row in datasets
    }

    selected_key = st.selectbox(
        "Dataset",
        options=options,
        format_func=lambda value: (
            labels.get(
                value,
                value,
            )
        ),
        key=(
            "stage185_dataset_key"
        ),
    )

    description = st.text_area(
        "Descrição opcional",
        value=st.session_state.get(
            "stage185_description",
            "",
        ),
        placeholder=(
            "Objetivo ou observação "
            "sobre esta pesquisa."
        ),
        key=(
            "stage185_description"
        ),
    )

    selected = _find_dataset(
        selected_key
    )

    if selected is not None:
        metric_cards(
            [
                (
                    "Pregões",
                    format_integer(
                        selected.get(
                            "sessions_total"
                        )
                    ),
                ),
                (
                    "Período",
                    (
                        f"{_text(selected.get('period_start'))}"
                        " → "
                        f"{_text(selected.get('period_end'))}"
                    ),
                ),
                (
                    "Status",
                    _text(
                        selected.get(
                            "quality_status"
                        )
                    ),
                ),
            ],
            columns=3,
        )

    st.divider()

    _render_model_explanation(
        model
    )

    can_continue = bool(
        research_name.strip()
        and selected is not None
    )

    _navigation(
        step=1,
        can_continue=(
            can_continue
        ),
    )


def _step_two(
    *,
    dataset: dict[str, Any],
) -> None:
    section_title(
        "Etapa 2 — Período",
        (
            "Defina o intervalo temporal "
            "da pesquisa."
        ),
    )

    minimum = dataset[
        "period_start"
    ]

    maximum = dataset[
        "period_end"
    ]

    start_date = st.date_input(
        "Data inicial",
        value=(
            st.session_state.get(
                "stage185_period_start",
                minimum,
            )
        ),
        min_value=minimum,
        max_value=maximum,
        key=(
            "stage185_period_start"
        ),
    )

    end_date = st.date_input(
        "Data final",
        value=(
            st.session_state.get(
                "stage185_period_end",
                maximum,
            )
        ),
        min_value=minimum,
        max_value=maximum,
        key=(
            "stage185_period_end"
        ),
    )

    start_text = (
        start_date.isoformat()
        if hasattr(
            start_date,
            "isoformat",
        )
        else str(
            start_date
        )
    )

    end_text = (
        end_date.isoformat()
        if hasattr(
            end_date,
            "isoformat",
        )
        else str(
            end_date
        )
    )

    sessions = int(
        dataset.get(
            "sessions_total"
        )
        or 0
    )

    if (
        start_text
        == dataset.get(
            "period_start"
        )
        and end_text
        == dataset.get(
            "period_end"
        )
    ):
        sessions_found = sessions
    else:
        #
        # O número oficial será calculado
        # pelo estimate_research antes da
        # execução. Aqui não inferimos
        # proporcionalmente.
        #
        sessions_found = None

    metric_cards(
        [
            (
                "Pregões no dataset",
                format_integer(
                    sessions
                ),
            ),
            (
                "Pregões encontrados",
                (
                    format_integer(
                        sessions_found
                    )
                    if sessions_found
                    is not None
                    else "Calculado no resumo"
                ),
            ),
            (
                "Período disponível",
                (
                    f"{minimum} → {maximum}"
                ),
            ),
        ],
        columns=3,
    )

    valid = (
        start_text
        <= end_text
    )

    if not valid:
        st.error(
            (
                "A data inicial não pode "
                "ser posterior à data final."
            )
        )

    _navigation(
        step=2,
        can_continue=(
            valid
        ),
    )


def _step_three() -> None:
    section_title(
        "Etapa 3 — Parâmetros quantitativos",
        (
            "Parâmetros já suportados pelos "
            "motores homologados."
        ),
    )

    with st.expander(
        "Trade 1",
        expanded=True,
    ):
        stop_values = st.multiselect(
            "Stops a testar",
            options=[
                100.0,
                125.0,
                150.0,
                165.0,
                170.0,
                175.0,
                200.0,
            ],
            default=st.session_state.get(
                "stage185_stop_values",
                [
                    170.0,
                ],
            ),
            key=(
                "stage185_stop_values"
            ),
        )

    with st.expander(
        "Gestão",
        expanded=True,
    ):
        col_a, col_b = st.columns(
            2
        )

        with col_a:
            partial_1_values = (
                st.multiselect(
                    "Pontos da Parcial 1",
                    options=[
                        100.0,
                        125.0,
                        150.0,
                        175.0,
                        200.0,
                    ],
                    default=(
                        st.session_state.get(
                            "stage185_partial1_values",
                            [
                                125.0,
                            ],
                        )
                    ),
                    key=(
                        "stage185_partial1_values"
                    ),
                )
            )

        with col_b:
            partial_1_pct_values = (
                st.multiselect(
                    "% da Parcial 1",
                    options=[
                        10.0,
                        15.0,
                        20.0,
                        25.0,
                        30.0,
                        40.0,
                        50.0,
                        60.0,
                        70.0,
                    ],
                    default=(
                        st.session_state.get(
                            "stage185_partial1_pct_values",
                            [
                                70.0,
                            ],
                        )
                    ),
                    key=(
                        "stage185_partial1_pct_values"
                    ),
                )
            )

        partial_2_enabled = (
            st.checkbox(
                "Ativar Parcial 2",
                value=st.session_state.get(
                    "stage185_partial2_enabled",
                    False,
                ),
                key=(
                    "stage185_partial2_enabled"
                ),
            )
        )

        p2a, p2b = st.columns(
            2
        )

        with p2a:
            st.number_input(
                "Pontos Parcial 2",
                min_value=1.0,
                value=float(
                    st.session_state.get(
                        "stage185_partial2_points",
                        175.0,
                    )
                ),
                step=5.0,
                disabled=(
                    not partial_2_enabled
                ),
                key=(
                    "stage185_partial2_points"
                ),
            )

        with p2b:
            st.number_input(
                "% Parcial 2",
                min_value=1.0,
                max_value=100.0,
                value=float(
                    st.session_state.get(
                        "stage185_partial2_pct",
                        30.0,
                    )
                ),
                step=5.0,
                disabled=(
                    not partial_2_enabled
                ),
                key=(
                    "stage185_partial2_pct"
                ),
            )

        partial_3_enabled = (
            st.checkbox(
                "Ativar Parcial 3",
                value=st.session_state.get(
                    "stage185_partial3_enabled",
                    False,
                ),
                key=(
                    "stage185_partial3_enabled"
                ),
            )
        )

        p3a, p3b = st.columns(
            2
        )

        with p3a:
            st.number_input(
                "Pontos Parcial 3",
                min_value=1.0,
                value=float(
                    st.session_state.get(
                        "stage185_partial3_points",
                        200.0,
                    )
                ),
                step=5.0,
                disabled=(
                    not partial_3_enabled
                ),
                key=(
                    "stage185_partial3_points"
                ),
            )

        with p3b:
            st.number_input(
                "% Parcial 3",
                min_value=1.0,
                max_value=100.0,
                value=float(
                    st.session_state.get(
                        "stage185_partial3_pct",
                        15.0,
                    )
                ),
                step=5.0,
                disabled=(
                    not partial_3_enabled
                ),
                key=(
                    "stage185_partial3_pct"
                ),
            )

        break_even_enabled = (
            st.checkbox(
                "Ativar Break-even",
                value=st.session_state.get(
                    "stage185_be_enabled",
                    True,
                ),
                key=(
                    "stage185_be_enabled"
                ),
            )
        )

        st.selectbox(
            "Aplicar BE após qual parcial?",
            options=[
                1,
                2,
                3,
            ],
            index=0,
            disabled=(
                not break_even_enabled
            ),
            key=(
                "stage185_be_after"
            ),
        )

        final_target_enabled = (
            st.checkbox(
                "Ativar Target final",
                value=st.session_state.get(
                    "stage185_target_enabled",
                    True,
                ),
                key=(
                    "stage185_target_enabled"
                ),
            )
        )

        st.number_input(
            "Target final em pontos",
            min_value=1.0,
            value=float(
                st.session_state.get(
                    "stage185_target_points",
                    400.0,
                )
            ),
            step=25.0,
            disabled=(
                not final_target_enabled
            ),
            key=(
                "stage185_target_points"
            ),
        )

    with st.expander(
        "Runner",
        expanded=True,
    ):
        runner_enabled = (
            st.checkbox(
                "Ativar Runner",
                value=st.session_state.get(
                    "stage185_runner_enabled",
                    False,
                ),
                key=(
                    "stage185_runner_enabled"
                ),
            )
        )

        runner_a, runner_b = (
            st.columns(
                2
            )
        )

        with runner_a:
            st.number_input(
                "% Runner",
                min_value=1.0,
                max_value=100.0,
                value=float(
                    st.session_state.get(
                        "stage185_runner_pct",
                        30.0,
                    )
                ),
                step=5.0,
                disabled=(
                    not runner_enabled
                ),
                key=(
                    "stage185_runner_pct"
                ),
            )

        with runner_b:
            st.selectbox(
                "Regra do Runner",
                options=(
                    RUNNER_RULES
                ),
                index=0,
                disabled=(
                    not runner_enabled
                ),
                key=(
                    "stage185_runner_rule"
                ),
            )

    errors = []

    if not stop_values:
        errors.append(
            "Selecione pelo menos um Stop."
        )

    if not partial_1_values:
        errors.append(
            (
                "Selecione pelo menos um "
                "valor de Parcial 1."
            )
        )

    if not partial_1_pct_values:
        errors.append(
            (
                "Selecione pelo menos um "
                "percentual de Parcial 1."
            )
        )

    be_after = st.session_state.get(
        "stage185_be_after",
        1,
    )

    if (
        break_even_enabled
        and be_after == 2
        and not partial_2_enabled
    ):
        errors.append(
            (
                "Break-even após Parcial 2 "
                "exige Parcial 2 ativa."
            )
        )

    if (
        break_even_enabled
        and be_after == 3
        and not partial_3_enabled
    ):
        errors.append(
            (
                "Break-even após Parcial 3 "
                "exige Parcial 3 ativa."
            )
        )

    for error in errors:
        st.error(
            error
        )

    _navigation(
        step=3,
        can_continue=(
            not errors
        ),
    )


def _definition_from_state(
    *,
    model: dict[str, Any],
    dataset: dict[str, Any],
) -> dict[str, Any]:
    start_value = (
        st.session_state[
            "stage185_period_start"
        ]
    )

    end_value = (
        st.session_state[
            "stage185_period_end"
        ]
    )

    start_text = (
        start_value.isoformat()
        if hasattr(
            start_value,
            "isoformat",
        )
        else str(
            start_value
        )
    )

    end_text = (
        end_value.isoformat()
        if hasattr(
            end_value,
            "isoformat",
        )
        else str(
            end_value
        )
    )

    return _build_definition(
        research_name=(
            st.session_state[
                "stage185_research_name"
            ]
        ),
        description=(
            st.session_state.get(
                "stage185_description",
                "",
            )
        ),
        model=model,
        dataset=dataset,
        period_start=(
            start_text
        ),
        period_end=(
            end_text
        ),
        stop_values=list(
            st.session_state[
                "stage185_stop_values"
            ]
        ),
        partial_1_values=list(
            st.session_state[
                "stage185_partial1_values"
            ]
        ),
        partial_1_pct_values=list(
            st.session_state[
                "stage185_partial1_pct_values"
            ]
        ),
        partial_2_enabled=bool(
            st.session_state.get(
                "stage185_partial2_enabled",
                False,
            )
        ),
        partial_2_points=float(
            st.session_state.get(
                "stage185_partial2_points",
                175.0,
            )
        ),
        partial_2_pct=float(
            st.session_state.get(
                "stage185_partial2_pct",
                30.0,
            )
        ),
        partial_3_enabled=bool(
            st.session_state.get(
                "stage185_partial3_enabled",
                False,
            )
        ),
        partial_3_points=float(
            st.session_state.get(
                "stage185_partial3_points",
                200.0,
            )
        ),
        partial_3_pct=float(
            st.session_state.get(
                "stage185_partial3_pct",
                15.0,
            )
        ),
        break_even_enabled=bool(
            st.session_state.get(
                "stage185_be_enabled",
                True,
            )
        ),
        break_even_after_partial=int(
            st.session_state.get(
                "stage185_be_after",
                1,
            )
        ),
        runner_enabled=bool(
            st.session_state.get(
                "stage185_runner_enabled",
                False,
            )
        ),
        runner_pct=float(
            st.session_state.get(
                "stage185_runner_pct",
                30.0,
            )
        ),
        runner_rule=str(
            st.session_state.get(
                "stage185_runner_rule",
                RUNNER_RULES[0],
            )
        ),
        final_target_enabled=bool(
            st.session_state.get(
                "stage185_target_enabled",
                True,
            )
        ),
        final_target_points=float(
            st.session_state.get(
                "stage185_target_points",
                400.0,
            )
        ),
    )


def _step_four(
    *,
    model: dict[str, Any],
    dataset: dict[str, Any],
) -> None:
    section_title(
        "Etapa 4 — Resumo",
        (
            "Revise o tamanho e a definição "
            "da pesquisa antes de executar."
        ),
    )

    try:
        definition = (
            _definition_from_state(
                model=model,
                dataset=dataset,
            )
        )

        estimate = (
            estimate_research(
                definition
            )
        )

    except Exception:
        st.error(
            (
                "Não foi possível calcular "
                "o resumo da pesquisa."
            )
        )

        st.info(
            (
                "Volte aos passos anteriores "
                "e revise a configuração."
            )
        )

        _navigation(
            step=4,
            can_continue=False,
        )

        return

    metric_cards(
        [
            (
                "Modelo",
                model[
                    "name"
                ],
            ),
            (
                "Pregões",
                format_integer(
                    estimate.get(
                        "sessions_total"
                    )
                ),
            ),
            (
                "Experimentos estimados",
                format_integer(
                    estimate.get(
                        "generated_configurations"
                    )
                ),
            ),
            (
                "Configurações válidas",
                format_integer(
                    estimate.get(
                        "valid_configurations"
                    )
                ),
            ),
            (
                "Execution Units",
                format_integer(
                    estimate.get(
                        "execution_units_estimated"
                    )
                ),
            ),
            (
                "Batches",
                format_integer(
                    estimate.get(
                        "batches_estimated"
                    )
                ),
            ),
            (
                "Tempo estimado",
                "N/A",
            ),
        ],
        columns=4,
    )

    st.caption(
        (
            "Tempo estimado: sem baseline "
            "oficial suficiente para projeção. "
            "Nenhuma duração é inventada."
        )
    )

    st.divider()

    key_value_panel(
        [
            (
                "Pesquisa",
                definition[
                    "research_name"
                ],
            ),
            (
                "Modelo",
                definition[
                    "model_name"
                ],
            ),
            (
                "Hipótese",
                definition[
                    "hypothesis"
                ],
            ),
            (
                "Dataset",
                _dataset_label(
                    dataset
                ),
            ),
            (
                "Período",
                (
                    f"{definition['period_start']} "
                    f"→ {definition['period_end']}"
                ),
            ),
            (
                "Estratégia",
                "Trade 1",
            ),
        ],
    )

    valid_count = int(
        estimate.get(
            "valid_configurations"
        )
        or 0
    )

    invalid_count = int(
        estimate.get(
            "invalid_configurations"
        )
        or 0
    )

    if valid_count <= 0:
        status_badge(
            "Pesquisa",
            "INVALID",
        )

        st.error(
            (
                "Nenhuma configuração válida "
                "foi encontrada."
            )
        )

        return

    if invalid_count:
        st.warning(
            (
                f"{invalid_count} configuração(ões) "
                "serão rejeitadas pelo "
                "Rule Engine."
            )
        )

    st.divider()

    left, right = st.columns(
        2
    )

    with left:
        if st.button(
            "← VOLTAR",
            use_container_width=True,
            key=(
                "stage185_back_4"
            ),
        ):
            st.session_state[
                "stage185_research_step"
            ] = 3

            st.rerun()

    with right:
        execute_clicked = st.button(
            "EXECUTAR PESQUISA",
            type="primary",
            use_container_width=True,
            key=(
                "stage185_execute"
            ),
        )

    if not execute_clicked:
        return

    created = None

    try:
        created = (
            create_research(
                definition
            )
        )

        research_id = (
            created[
                "research_id"
            ]
        )

        st.session_state[
            "active_research_id"
        ] = research_id

        st.session_state[
            "stage18_current_research_id"
        ] = research_id

        st.success(
            (
                "Pesquisa criada: "
                f"{research_id}"
            )
        )

        progress_bar = st.progress(
            0
        )

        status_box = st.empty()
        detail_box = st.empty()

        callback = (
            _progress_callback(
                progress_bar,
                status_box,
                detail_box,
            )
        )

        result = execute_research(
            research_id,
            progress_callback=(
                callback
            ),
        )

        progress_bar.progress(
            100
        )

        status_box.success(
            "Pesquisa concluída."
        )

        manifest = (
            load_research_manifest(
                research_id
            )
        )

        metric_cards(
            [
                (
                    "Research ID",
                    research_id,
                ),
                (
                    "Experimentos",
                    format_integer(
                        manifest.get(
                            "experiments_valid"
                        )
                    ),
                ),
                (
                    "Execution Units",
                    format_integer(
                        manifest.get(
                            "execution_units_total"
                        )
                    ),
                ),
                (
                    "Batches",
                    format_integer(
                        manifest.get(
                            "batches_total"
                        )
                    ),
                ),
            ],
            columns=4,
        )

        status_badge(
            "LINEAGE_MATCH",
            (
                "TRUE"
                if result.get(
                    "lineage_match"
                )
                else "FALSE"
            ),
        )

        st.session_state[
            "requested_terminal_page"
        ] = "Overview"

        st.success(
            (
                "A pesquisa foi concluída "
                "e definida como pesquisa ativa."
            )
        )

        if st.button(
            "ABRIR RESULTADO",
            type="primary",
            use_container_width=True,
            key=(
                "stage185_open_result"
            ),
        ):
            st.switch_page(
                "main.py"
            )

    except Exception as exc:
        if created is not None:
            st.error(
                (
                    "A pesquisa foi criada, "
                    "mas não foi concluída. "
                    "O erro foi preservado "
                    "no histórico."
                )
            )
        else:
            st.error(
                (
                    "Não foi possível criar "
                    "a pesquisa."
                )
            )

        st.caption(
            (
                "Erro técnico: "
                f"{type(exc).__name__}"
            )
        )


def render() -> None:
    page_header(
        "Nova Pesquisa",
        (
            "Crie uma pesquisa quantitativa "
            "a partir de um modelo oficial "
            "do Operar Range."
        ),
    )

    model = (
        default_quantitative_model()
    )

    if (
        model[
            "model_id"
        ]
        != US_OPEN_BREAKOUT_V1_ID
    ):
        st.error(
            "Modelo quantitativo indisponível."
        )
        return

    datasets = (
        _prepared_datasets()
    )

    if not datasets:
        st.error(
            (
                "Nenhum dataset preparado "
                "para pesquisa está disponível."
            )
        )

        st.info(
            (
                "Utilize o Data Manager antes "
                "de criar uma pesquisa."
            )
        )

        return

    step = int(
        st.session_state.get(
            "stage185_research_step",
            1,
        )
    )

    if step not in {
        1,
        2,
        3,
        4,
    }:
        step = 1

        st.session_state[
            "stage185_research_step"
        ] = 1

    _render_steps(
        step
    )

    st.divider()

    if step == 1:
        _step_one(
            model=model,
            datasets=datasets,
        )

        return

    dataset_key = (
        st.session_state.get(
            "stage185_dataset_key"
        )
    )

    dataset = (
        _find_dataset(
            str(
                dataset_key
            )
        )
        if dataset_key
        else None
    )

    if dataset is None:
        st.error(
            (
                "O dataset selecionado não "
                "está mais disponível."
            )
        )

        st.session_state[
            "stage185_research_step"
        ] = 1

        return

    if step == 2:
        _step_two(
            dataset=dataset
        )
        return

    if step == 3:
        _step_three()
        return

    _step_four(
        model=model,
        dataset=dataset,
    )


if __name__ == "__main__":
    render()
