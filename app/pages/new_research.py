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
    format_integer,
)
from operar_range.research_workspace import (
    DEFAULT_COMPOSITE_WEIGHTS,
    available_dataset_period,
    create_research,
    estimate_research,
    execute_research,
    load_research_manifest,
)


DEFAULT_RULES_VERSION = (
    "ADR-004+STAGE10"
)


RUNNER_RULES = [
    "CANDLE_BREAK_M5",
]


def _number_or_none(
    value: float,
    enabled: bool,
) -> float | None:
    if not enabled:
        return None

    return float(value)


def _int_or_none(
    value: int,
    enabled: bool,
) -> int | None:
    if not enabled:
        return None

    return int(value)


def _parameter_definition_from_ui(
    *,
    stop_values: list[float],
    partial_1_values: list[float],
    partial_1_pct_values: list[float],
) -> dict[str, dict[str, Any]]:
    return {
        "stop_points": {
            "values": [
                float(value)
                for value
                in stop_values
            ]
        },
        "partial_1_points": {
            "values": [
                float(value)
                for value
                in partial_1_values
            ]
        },
        "partial_1_pct": {
            "values": [
                float(value)
                for value
                in partial_1_pct_values
            ]
        },
    }


def _build_definition(
    *,
    family: str,
    generation: int,
    period_start: str,
    period_end: str,
    batch_size: int,
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

        "break_even_enabled": (
            bool(
                break_even_enabled
            )
        ),
        "break_even_after_partial": (
            _int_or_none(
                break_even_after_partial,
                break_even_enabled,
            )
        ),

        "runner_enabled": (
            bool(
                runner_enabled
            )
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
        "strategy": "TRADE_1",
        "family": (
            family.strip()
        ),
        "generation": (
            int(
                generation
            )
        ),
        "period_start": (
            period_start
        ),
        "period_end": (
            period_end
        ),
        "rules_version": (
            DEFAULT_RULES_VERSION
        ),
        "batch_size": (
            int(
                batch_size
            )
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


def _render_progress_callback(
    progress_bar,
    status_box,
    detail_box,
):
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
            (
                f"Etapa atual: "
                f"{stage}"
            )
        )

        details_to_show = []

        for key in (
            "completed_batches",
            "total_batches",
            "remaining_batches",
            "execution_units_total",
            "worker_id",
            "batch_id",
            "duration_seconds",
        ):
            value = details.get(
                key
            )

            if value is None:
                continue

            details_to_show.append(
                (
                    f"**{key}:** "
                    f"{value}"
                )
            )

        if details_to_show:
            detail_box.markdown(
                "  \n".join(
                    details_to_show
                )
            )
        else:
            detail_box.empty()

    return callback


def _render_estimate(
    estimate: dict[str, Any],
) -> None:
    st.divider()

    section_title(
        "Estimativa da pesquisa",
        (
            "Pré-validação realizada sem "
            "executar nenhum Trade 1."
        ),
    )

    metric_cards(
        [
            (
                "Pregões encontrados",
                format_integer(
                    estimate.get(
                        "sessions_total"
                    )
                ),
            ),
            (
                "Configurações geradas",
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
                "Configurações inválidas",
                format_integer(
                    estimate.get(
                        "invalid_configurations"
                    )
                ),
            ),
            (
                "Execution Units previstas",
                format_integer(
                    estimate.get(
                        "execution_units_estimated"
                    )
                ),
            ),
            (
                "Batches previstos",
                format_integer(
                    estimate.get(
                        "batches_estimated"
                    )
                ),
            ),
        ],
        columns=3,
    )

    valid_count = (
        estimate.get(
            "valid_configurations"
        )
        or 0
    )

    invalid_count = (
        estimate.get(
            "invalid_configurations"
        )
        or 0
    )

    if (
        valid_count > 0
        and invalid_count == 0
    ):
        status_badge(
            "Pré-validação",
            "VALID",
        )

    elif valid_count > 0:
        status_badge(
            "Pré-validação",
            "PARTIAL",
        )

        st.warning(
            (
                f"{invalid_count} configuração(ões) "
                "serão rejeitadas pelo Rule Engine "
                "na execução oficial."
            )
        )

    else:
        status_badge(
            "Pré-validação",
            "INVALID",
        )

        st.error(
            (
                "Nenhuma configuração válida "
                "foi encontrada."
            )
        )


def render() -> None:
    page_header(
        "Nova Pesquisa",
        (
            "Construa, estime e execute uma "
            "pesquisa quantitativa Trade 1."
        ),
    )

    st.caption(
        (
            "A interface apenas coordena "
            "os motores homologados. "
            "Nenhuma lógica quantitativa "
            "é implementada nesta tela."
        )
    )

    dataset_period = (
        available_dataset_period()
    )

    if not dataset_period.get(
        "available"
    ):
        st.error(
            (
                "Nenhum dataset processado "
                "está disponível."
            )
        )

        st.info(
            (
                "Utilize primeiro a página "
                "Data para preparar os dados."
            )
        )

        return

    metric_cards(
        [
            (
                "Pregões disponíveis",
                format_integer(
                    dataset_period.get(
                        "sessions_total"
                    )
                ),
            ),
            (
                "Início disponível",
                str(
                    dataset_period.get(
                        "period_start"
                    )
                ),
            ),
            (
                "Fim disponível",
                str(
                    dataset_period.get(
                        "period_end"
                    )
                ),
            ),
        ],
        columns=3,
    )

    st.divider()

    section_title(
        "Pesquisa",
        (
            "Identificação e universo "
            "temporal."
        ),
    )

    col_a, col_b, col_c = (
        st.columns(
            [2, 1, 1]
        )
    )

    with col_a:
        family = st.text_input(
            "Family",
            value=(
                "TRADE1_WORKSPACE"
            ),
            key=(
                "stage18_family"
            ),
        )

    with col_b:
        generation = (
            st.number_input(
                "Generation",
                min_value=1,
                value=1,
                step=1,
                key=(
                    "stage18_generation"
                ),
            )
        )

    with col_c:
        batch_size = (
            st.number_input(
                "Batch size",
                min_value=1,
                value=1000,
                step=1,
                key=(
                    "stage18_batch_size"
                ),
            )
        )

    period_a, period_b = (
        st.columns(2)
    )

    with period_a:
        start_date = (
            st.date_input(
                "Início",
                value=(
                    dataset_period[
                        "period_start"
                    ]
                ),
                min_value=(
                    dataset_period[
                        "period_start"
                    ]
                ),
                max_value=(
                    dataset_period[
                        "period_end"
                    ]
                ),
                key=(
                    "stage18_period_start"
                ),
            )
        )

    with period_b:
        end_date = (
            st.date_input(
                "Fim",
                value=(
                    dataset_period[
                        "period_end"
                    ]
                ),
                min_value=(
                    dataset_period[
                        "period_start"
                    ]
                ),
                max_value=(
                    dataset_period[
                        "period_end"
                    ]
                ),
                key=(
                    "stage18_period_end"
                ),
            )
        )

    st.divider()

    section_title(
        "Gestão",
        (
            "Parâmetros suportados pelo "
            "Management Engine homologado."
        ),
    )

    st.markdown(
        "#### Stop"
    )

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
        default=[
            170.0,
        ],
        key=(
            "stage18_stop_values"
        ),
    )

    st.markdown(
        "#### Parcial 1"
    )

    partial_1_a, partial_1_b = (
        st.columns(2)
    )

    with partial_1_a:
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
                default=[
                    125.0,
                ],
                key=(
                    "stage18_partial1_values"
                ),
            )
        )

    with partial_1_b:
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
                default=[
                    70.0,
                ],
                key=(
                    "stage18_partial1_pct_values"
                ),
            )
        )

    st.markdown(
        "#### Parcial 2"
    )

    partial_2_enabled = (
        st.checkbox(
            "Ativar Parcial 2",
            value=False,
            key=(
                "stage18_partial2_enabled"
            ),
        )
    )

    partial_2_a, partial_2_b = (
        st.columns(2)
    )

    with partial_2_a:
        partial_2_points = (
            st.number_input(
                "Pontos Parcial 2",
                min_value=1.0,
                value=175.0,
                step=5.0,
                disabled=(
                    not partial_2_enabled
                ),
                key=(
                    "stage18_partial2_points"
                ),
            )
        )

    with partial_2_b:
        partial_2_pct = (
            st.number_input(
                "% Parcial 2",
                min_value=1.0,
                max_value=100.0,
                value=30.0,
                step=5.0,
                disabled=(
                    not partial_2_enabled
                ),
                key=(
                    "stage18_partial2_pct"
                ),
            )
        )

    st.markdown(
        "#### Parcial 3"
    )

    partial_3_enabled = (
        st.checkbox(
            "Ativar Parcial 3",
            value=False,
            key=(
                "stage18_partial3_enabled"
            ),
        )
    )

    partial_3_a, partial_3_b = (
        st.columns(2)
    )

    with partial_3_a:
        partial_3_points = (
            st.number_input(
                "Pontos Parcial 3",
                min_value=1.0,
                value=200.0,
                step=5.0,
                disabled=(
                    not partial_3_enabled
                ),
                key=(
                    "stage18_partial3_points"
                ),
            )
        )

    with partial_3_b:
        partial_3_pct = (
            st.number_input(
                "% Parcial 3",
                min_value=1.0,
                max_value=100.0,
                value=15.0,
                step=5.0,
                disabled=(
                    not partial_3_enabled
                ),
                key=(
                    "stage18_partial3_pct"
                ),
            )
        )

    st.markdown(
        "#### Break-even"
    )

    break_even_enabled = (
        st.checkbox(
            "Ativar Break-even",
            value=True,
            key=(
                "stage18_be_enabled"
            ),
        )
    )

    break_even_after_partial = (
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
                "stage18_be_after"
            ),
        )
    )

    st.markdown(
        "#### Runner"
    )

    runner_enabled = (
        st.checkbox(
            "Ativar Runner",
            value=False,
            key=(
                "stage18_runner_enabled"
            ),
        )
    )

    runner_a, runner_b = (
        st.columns(2)
    )

    with runner_a:
        runner_pct = (
            st.number_input(
                "% Runner",
                min_value=1.0,
                max_value=100.0,
                value=30.0,
                step=5.0,
                disabled=(
                    not runner_enabled
                ),
                key=(
                    "stage18_runner_pct"
                ),
            )
        )

    with runner_b:
        runner_rule = (
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
                    "stage18_runner_rule"
                ),
            )
        )

    st.markdown(
        "#### Target final"
    )

    final_target_enabled = (
        st.checkbox(
            "Ativar Target final",
            value=True,
            key=(
                "stage18_target_enabled"
            ),
        )
    )

    final_target_points = (
        st.number_input(
            "Target final em pontos",
            min_value=1.0,
            value=400.0,
            step=25.0,
            disabled=(
                not final_target_enabled
            ),
            key=(
                "stage18_target_points"
            ),
        )
    )

    validation_errors = []

    if not family.strip():
        validation_errors.append(
            "Family é obrigatória."
        )

    if not stop_values:
        validation_errors.append(
            (
                "Selecione pelo menos "
                "um Stop."
            )
        )

    if not partial_1_values:
        validation_errors.append(
            (
                "Selecione pelo menos "
                "um valor de Parcial 1."
            )
        )

    if not partial_1_pct_values:
        validation_errors.append(
            (
                "Selecione pelo menos "
                "um percentual de "
                "Parcial 1."
            )
        )

    if (
        break_even_enabled
        and break_even_after_partial == 2
        and not partial_2_enabled
    ):
        validation_errors.append(
            (
                "Break-even após Parcial 2 "
                "exige Parcial 2 ativa."
            )
        )

    if (
        break_even_enabled
        and break_even_after_partial == 3
        and not partial_3_enabled
    ):
        validation_errors.append(
            (
                "Break-even após Parcial 3 "
                "exige Parcial 3 ativa."
            )
        )

    if (
        runner_enabled
        and final_target_enabled
    ):
        st.caption(
            (
                "Runner + Target final será "
                "validado pelo Rule Engine. "
                "Configurações incompatíveis "
                "serão classificadas como "
                "inválidas."
            )
        )

    definition = None
    estimate = None

    if not validation_errors:
        definition = (
            _build_definition(
                family=family,
                generation=int(
                    generation
                ),
                period_start=(
                    start_date.isoformat()
                    if hasattr(
                        start_date,
                        "isoformat",
                    )
                    else str(
                        start_date
                    )
                ),
                period_end=(
                    end_date.isoformat()
                    if hasattr(
                        end_date,
                        "isoformat",
                    )
                    else str(
                        end_date
                    )
                ),
                batch_size=int(
                    batch_size
                ),
                stop_values=(
                    stop_values
                ),
                partial_1_values=(
                    partial_1_values
                ),
                partial_1_pct_values=(
                    partial_1_pct_values
                ),
                partial_2_enabled=(
                    partial_2_enabled
                ),
                partial_2_points=float(
                    partial_2_points
                ),
                partial_2_pct=float(
                    partial_2_pct
                ),
                partial_3_enabled=(
                    partial_3_enabled
                ),
                partial_3_points=float(
                    partial_3_points
                ),
                partial_3_pct=float(
                    partial_3_pct
                ),
                break_even_enabled=(
                    break_even_enabled
                ),
                break_even_after_partial=int(
                    break_even_after_partial
                ),
                runner_enabled=(
                    runner_enabled
                ),
                runner_pct=float(
                    runner_pct
                ),
                runner_rule=(
                    runner_rule
                ),
                final_target_enabled=(
                    final_target_enabled
                ),
                final_target_points=float(
                    final_target_points
                ),
            )
        )

        try:
            estimate = (
                estimate_research(
                    definition
                )
            )

        except Exception as exc:
            validation_errors.append(
                str(
                    exc
                )
            )

    if validation_errors:
        st.divider()

        status_badge(
            "Configuração",
            "INVALID",
        )

        for message in (
            validation_errors
        ):
            st.error(
                message
            )

        return

    if estimate is None:
        return

    _render_estimate(
        estimate
    )

    st.divider()

    section_title(
        "Definição",
        (
            "Resumo da pesquisa antes "
            "da criação do Research ID."
        ),
    )

    key_value_panel(
        [
            (
                "Strategy",
                "TRADE_1",
            ),
            (
                "Family",
                family,
            ),
            (
                "Generation",
                str(
                    generation
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
                "Batch size",
                str(
                    batch_size
                ),
            ),
            (
                "Rules version",
                DEFAULT_RULES_VERSION,
            ),
        ],
    )

    can_execute = (
        (
            estimate.get(
                "valid_configurations"
            )
            or 0
        )
        > 0
    )

    if not can_execute:
        st.error(
            (
                "A pesquisa não pode ser "
                "executada porque não há "
                "configurações válidas."
            )
        )

        return

    st.divider()

    section_title(
        "Execução",
        (
            "Uma nova execução cria um "
            "Research ID próprio e não "
            "sobrescreve pesquisas anteriores."
        ),
    )

    st.warning(
        (
            "Após iniciar, os motores "
            "Generator → Rule Engine → "
            "Batch Planner → Distributed "
            "Executor → Lineage Adapter → "
            "Analytics → Ranking serão "
            "executados nessa ordem."
        )
    )

    execute_clicked = (
        st.button(
            "EXECUTAR PESQUISA",
            type="primary",
            use_container_width=True,
            key=(
                "stage18_execute_research"
            ),
        )
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
            "stage18_current_research_id"
        ] = research_id

        st.success(
            (
                "Research ID criado: "
                f"{research_id}"
            )
        )

        progress_bar = (
            st.progress(
                0
            )
        )

        status_box = (
            st.empty()
        )

        detail_box = (
            st.empty()
        )

        callback = (
            _render_progress_callback(
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
                    "Experimentos válidos",
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

        status_badge(
            "Quantitative execution repeated",
            (
                "FALSE"
                if not result.get(
                    "quantitative_execution_repeated"
                )
                else "TRUE"
            ),
        )

        st.session_state[
            "stage18_open_result_research_id"
        ] = research_id

        st.success(
            (
                "A pesquisa já está disponível "
                "no histórico e pode ser aberta "
                "no Research Terminal."
            )
        )

    except Exception as exc:
        if created is not None:
            st.error(
                (
                    "A pesquisa foi criada, "
                    "mas a execução falhou. "
                    "O Research ID e o erro "
                    "foram preservados no "
                    "histórico."
                )
            )

        else:
            st.error(
                (
                    "Não foi possível criar "
                    "a pesquisa."
                )
            )

        st.error(
            str(
                exc
            )
        )


if __name__ == "__main__":
    render()