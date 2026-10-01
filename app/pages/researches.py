from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from app.pages.research_result import (
    render_research_result,
)

from app.components.common import (
    dataframe_view,
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
from operar_range.distributed_executor import (
    distributed_status,
)
from operar_range.research_workspace import (
    list_researches,
    load_research_definition,
    load_research_manifest,
    research_paths,
    research_result_paths,
)


def _missing(
    value: Any,
) -> bool:
    if value is None:
        return True

    if isinstance(
        value,
        float,
    ):
        return math.isnan(
            value
        )

    try:
        result = pd.isna(
            value
        )

        if isinstance(
            result,
            bool,
        ):
            return result

    except Exception:
        pass

    return False


def _as_text(
    value: Any,
) -> str:
    if _missing(
        value
    ):
        return NA_TEXT

    text = str(
        value
    ).strip()

    if text.lower() in {
        "nan",
        "none",
        "nat",
        "",
    }:
        return NA_TEXT

    return text


def _duration_text(
    seconds: Any,
) -> str:
    if _missing(
        seconds
    ):
        return NA_TEXT

    try:
        value = float(
            seconds
        )
    except (
        TypeError,
        ValueError,
    ):
        return NA_TEXT

    if not math.isfinite(
        value
    ):
        return NA_TEXT

    if value < 0:
        return NA_TEXT

    if value < 60:
        return (
            f"{value:.2f}s"
        )

    minutes = int(
        value // 60
    )

    remaining = int(
        value % 60
    )

    if minutes < 60:
        return (
            f"{minutes}m "
            f"{remaining}s"
        )

    hours = (
        minutes // 60
    )

    remaining_minutes = (
        minutes % 60
    )

    return (
        f"{hours}h "
        f"{remaining_minutes}m"
    )


def _format_datetime(
    value: Any,
) -> str:
    if _missing(
        value
    ):
        return NA_TEXT

    try:
        parsed = datetime.fromisoformat(
            str(
                value
            ).replace(
                "Z",
                "+00:00",
            )
        )

        return parsed.strftime(
            "%d/%m/%Y %H:%M"
        )

    except Exception:
        return _as_text(
            value
        )


def _research_name(
    row: dict[str, Any],
) -> str:
    value = row.get(
        "research_name"
    )

    if not _missing(
        value
    ):
        return str(
            value
        )

    return (
        "Pesquisa anterior à Etapa 18.5"
    )


def _model_name(
    row: dict[str, Any],
) -> str:
    value = row.get(
        "model_name"
    )

    if _missing(
        value
    ):
        return "NÃO REGISTRADO"

    return str(
        value
    )


def _dataset_name(
    row: dict[str, Any],
) -> str:
    dataset_id = row.get(
        "dataset_id"
    )

    if not _missing(
        dataset_id
    ):
        return str(
            dataset_id
        )

    dataset_key = row.get(
        "dataset_key"
    )

    if not _missing(
        dataset_key
    ):
        return str(
            dataset_key
        )

    return "NÃO REGISTRADO"


def _elapsed_seconds(
    started_at: Any,
) -> float | None:
    if not started_at:
        return None

    try:
        started = (
            datetime.fromisoformat(
                str(
                    started_at
                ).replace(
                    "Z",
                    "+00:00",
                )
            )
        )

        if started.tzinfo is None:
            started = (
                started.replace(
                    tzinfo=timezone.utc
                )
            )

        now = datetime.now(
            timezone.utc
        )

        return max(
            0.0,
            (
                now
                - started.astimezone(
                    timezone.utc
                )
            ).total_seconds(),
        )

    except Exception:
        return None


def _discover_distributed_run_id(
    research_id: str,
    manifest: dict[str, Any],
) -> str | None:
    recorded = manifest.get(
        "distributed_run_id"
    )

    if recorded:
        return str(
            recorded
        )

    paths = research_paths(
        research_id
    )

    root = paths[
        "distributed_root"
    ]

    if not root.exists():
        return None

    candidates = []

    for path in root.iterdir():
        if not path.is_dir():
            continue

        run_manifest = (
            path
            / "distributed_run_manifest.json"
        )

        if run_manifest.exists():
            candidates.append(
                path.name
            )

    if len(
        candidates
    ) != 1:
        return None

    return candidates[0]


def _distributed_monitor(
    research_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    run_id = (
        _discover_distributed_run_id(
            research_id,
            manifest,
        )
    )

    if not run_id:
        return {
            "available": False,
            "run_id": None,
            "batches_total": (
                manifest.get(
                    "batches_total"
                )
            ),
            "completed": None,
            "remaining": None,
            "execution_units_total": (
                manifest.get(
                    "execution_units_total"
                )
            ),
            "failed_final": None,
            "retries": None,
            "workers_total": None,
        }

    paths = research_paths(
        research_id
    )

    try:
        status = distributed_status(
            distributed_root=(
                paths[
                    "distributed_root"
                ]
            ),
            run_id=run_id,
        )

    except Exception:
        return {
            "available": False,
            "run_id": run_id,
            "batches_total": (
                manifest.get(
                    "batches_total"
                )
            ),
            "completed": None,
            "remaining": None,
            "execution_units_total": (
                manifest.get(
                    "execution_units_total"
                )
            ),
            "failed_final": None,
            "retries": None,
            "workers_total": None,
        }

    batches_total = status.get(
        "batches_total"
    )

    completed = status.get(
        "completed"
    )

    remaining = None

    if (
        batches_total is not None
        and completed is not None
    ):
        remaining = max(
            0,
            int(
                batches_total
            )
            - int(
                completed
            ),
        )

    return {
        "available": True,
        "run_id": run_id,
        "batches_total": (
            batches_total
        ),
        "completed": (
            completed
        ),
        "remaining": (
            remaining
        ),
        "execution_units_total": (
            status.get(
                "execution_units_total"
            )
        ),
        "failed_final": (
            status.get(
                "failed_final"
            )
        ),
        "retries": (
            status.get(
                "retries"
            )
        ),
        "workers_total": (
            status.get(
                "workers_total"
            )
        ),
    }


def _eta_seconds(
    *,
    elapsed_seconds: float | None,
    completed: Any,
    total: Any,
) -> float | None:
    if elapsed_seconds is None:
        return None

    try:
        completed_value = int(
            completed
        )

        total_value = int(
            total
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if (
        completed_value <= 0
        or total_value <= 0
        or completed_value >= total_value
    ):
        return None

    rate = (
        elapsed_seconds
        / completed_value
    )

    remaining = (
        total_value
        - completed_value
    )

    return (
        rate
        * remaining
    )


def _history_frame(
    rows: list[
        dict[str, Any]
    ],
) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()

    active_id = st.session_state.get(
        "active_research_id"
    )

    output = []

    for row in rows:
        research_id = str(
            row.get(
                "research_id"
            )
            or ""
        )

        output.append(
            {
                "Pesquisa": (
                    _research_name(
                        row
                    )
                ),
                "Research ID": (
                    research_id
                ),
                "Modelo": (
                    _model_name(
                        row
                    )
                ),
                "Período": (
                    f"{_as_text(row.get('period_start'))}"
                    " → "
                    f"{_as_text(row.get('period_end'))}"
                ),
                "Status": (
                    _as_text(
                        row.get(
                            "status"
                        )
                    )
                ),
                "Experimentos": (
                    row.get(
                        "experiments_valid"
                    )
                ),
                "Duração": (
                    _duration_text(
                        row.get(
                            "duration_seconds"
                        )
                    )
                ),
                "Criada em": (
                    _format_datetime(
                        row.get(
                            "created_at"
                        )
                    )
                ),
                "Ativa": (
                    "SIM"
                    if research_id
                    == str(
                        active_id
                        or ""
                    )
                    else ""
                ),
            }
        )

    dataframe = pd.DataFrame(
        output
    )

    return dataframe.fillna(
        NA_TEXT
    )


def _render_status_counts(
    rows: list[
        dict[str, Any]
    ],
) -> None:
    running = sum(
        1
        for row in rows
        if row.get(
            "status"
        )
        == "RUNNING"
    )

    completed = sum(
        1
        for row in rows
        if row.get(
            "status"
        )
        == "COMPLETED"
    )

    failed = sum(
        1
        for row in rows
        if row.get(
            "status"
        )
        == "FAILED"
    )

    created = sum(
        1
        for row in rows
        if row.get(
            "status"
        )
        == "CREATED"
    )

    metric_cards(
        [
            (
                "Pesquisas",
                format_integer(
                    len(
                        rows
                    )
                ),
            ),
            (
                "Em andamento",
                format_integer(
                    running
                ),
            ),
            (
                "Concluídas",
                format_integer(
                    completed
                ),
            ),
            (
                "Falhadas",
                format_integer(
                    failed
                ),
            ),
            (
                "Criadas",
                format_integer(
                    created
                ),
            ),
        ],
        columns=5,
    )


def _render_monitor(
    research_id: str,
    manifest: dict[str, Any],
) -> None:
    section_title(
        "Execução",
        (
            "Acompanhamento da pesquisa "
            "selecionada."
        ),
    )

    status = (
        manifest.get(
            "status"
        )
        or NA_TEXT
    )

    status_badge(
        "Status da pesquisa",
        status,
    )

    monitor = (
        _distributed_monitor(
            research_id,
            manifest,
        )
    )

    elapsed = None

    if status == "RUNNING":
        elapsed = _elapsed_seconds(
            manifest.get(
                "started_at"
            )
        )

    elif (
        manifest.get(
            "duration_seconds"
        )
        is not None
    ):
        try:
            elapsed = float(
                manifest[
                    "duration_seconds"
                ]
            )
        except (
            TypeError,
            ValueError,
        ):
            elapsed = None

    eta = _eta_seconds(
        elapsed_seconds=(
            elapsed
        ),
        completed=(
            monitor.get(
                "completed"
            )
        ),
        total=(
            monitor.get(
                "batches_total"
            )
        ),
    )

    metric_cards(
        [
            (
                "Batches concluídos",
                format_integer(
                    monitor.get(
                        "completed"
                    )
                ),
            ),
            (
                "Batches restantes",
                format_integer(
                    monitor.get(
                        "remaining"
                    )
                ),
            ),
            (
                "Execution Units",
                format_integer(
                    monitor.get(
                        "execution_units_total"
                    )
                ),
            ),
            (
                "Tempo decorrido",
                _duration_text(
                    elapsed
                ),
            ),
            (
                "ETA",
                _duration_text(
                    eta
                ),
            ),
        ],
        columns=5,
    )

    current_stage = (
        manifest.get(
            "current_stage"
        )
    )

    if current_stage:
        st.info(
            (
                "Etapa atual: "
                f"{current_stage}"
            )
        )

    if status == "FAILED":
        st.error(
            (
                "A pesquisa não foi concluída. "
                "O registro da falha foi "
                "preservado para análise."
            )
        )


def _render_definition(
    research_id: str,
) -> dict[str, Any]:
    try:
        definition = (
            load_research_definition(
                research_id
            )
        )

    except Exception:
        st.info(
            (
                "A definição desta pesquisa "
                "não está disponível."
            )
        )

        return {}

    section_title(
        "Pesquisa"
    )

    research_name = (
        definition.get(
            "research_name"
        )
        or "Pesquisa anterior à Etapa 18.5"
    )

    model_name = (
        definition.get(
            "model_name"
        )
        or "NÃO REGISTRADO"
    )

    dataset_name = (
        definition.get(
            "dataset_id"
        )
        or definition.get(
            "dataset_key"
        )
        or "NÃO REGISTRADO"
    )

    hypothesis = (
        definition.get(
            "hypothesis"
        )
        or "NÃO REGISTRADA"
    )

    key_value_panel(
        [
            (
                "Nome",
                research_name,
            ),
            (
                "Modelo",
                model_name,
            ),
            (
                "Hipótese",
                hypothesis,
            ),
            (
                "Dataset",
                dataset_name,
            ),
            (
                "Período",
                (
                    f"{_as_text(definition.get('period_start'))}"
                    " → "
                    f"{_as_text(definition.get('period_end'))}"
                ),
            ),
            (
                "Estratégia",
                (
                    "Trade 1"
                    if definition.get(
                        "strategy"
                    )
                    == "TRADE_1"
                    else _as_text(
                        definition.get(
                            "strategy"
                        )
                    )
                ),
            ),
            (
                "Descrição",
                _as_text(
                    definition.get(
                        "description"
                    )
                ),
            ),
        ],
    )

    return definition


def _render_technical_details(
    research_id: str,
    manifest: dict[str, Any],
    definition: dict[str, Any],
) -> None:
    with st.expander(
        "Detalhes técnicos",
        expanded=False,
    ):
        lineage = manifest.get(
            "lineage_match"
        )

        status_badge(
            "LINEAGE_MATCH",
            (
                "TRUE"
                if lineage is True
                else (
                    "FALSE"
                    if lineage is False
                    else "N/A"
                )
            ),
        )

        key_value_panel(
            [
                (
                    "Motor version",
                    _as_text(
                        manifest.get(
                            "motor_version"
                        )
                    ),
                ),
                (
                    "Rules version",
                    _as_text(
                        manifest.get(
                            "rules_version"
                        )
                    ),
                ),
                (
                    "Research definition SHA-256",
                    _as_text(
                        manifest.get(
                            "research_definition_sha256"
                        )
                    ),
                ),
                (
                    "Experiment manifest SHA-256",
                    _as_text(
                        manifest.get(
                            "experiment_manifest_sha256"
                        )
                    ),
                ),
                (
                    "Distributed results SHA-256",
                    _as_text(
                        manifest.get(
                            "distributed_results_sha256"
                        )
                    ),
                ),
            ],
        )

        paths = research_result_paths(
            research_id
        )

        artifact_rows = []

        for name, value in paths.items():
            path = Path(
                value
            )

            artifact_rows.append(
                {
                    "Recurso": name,
                    "Status": (
                        "DISPONÍVEL"
                        if path.exists()
                        else "AUSENTE"
                    ),
                    "Caminho": value,
                }
            )

        if artifact_rows:
            dataframe_view(
                pd.DataFrame(
                    artifact_rows
                ),
                height=300,
            )

        with st.expander(
            "Definição completa",
            expanded=False,
        ):
            st.json(
                definition
            )


def _open_result_button(
    research_id: str,
    manifest: dict[str, Any],
) -> None:
    if (
        manifest.get(
            "status"
        )
        != "COMPLETED"
    ):
        st.info(
            (
                "O resultado poderá ser aberto "
                "quando a pesquisa estiver "
                "concluída."
            )
        )
        return

    paths = research_paths(
        research_id
    )

    required = [
        paths[
            "metrics"
        ],
        paths[
            "rankings"
        ],
        paths[
            "experiment_manifest"
        ],
        paths[
            "distributed_results"
        ],
    ]

    missing = [
        path.name
        for path in required
        if not path.exists()
    ]

    if missing:
        st.error(
            (
                "Esta pesquisa está marcada "
                "como concluída, mas os "
                "resultados necessários não "
                "estão disponíveis."
            )
        )
        return

    active_id = st.session_state.get(
        "active_research_id"
    )

    if (
        str(
            active_id
            or ""
        )
        == research_id
    ):
        st.success(
            "Esta é a pesquisa ativa."
        )

    if st.button(
        "ABRIR RESULTADO",
        type="primary",
        use_container_width=True,
        key=(
            "stage185_open_result_"
            + research_id
        ),
    ):
        st.session_state[
            "active_research_id"
        ] = research_id

        st.session_state[
            "stage18_current_research_id"
        ] = research_id

        st.session_state[
            "requested_terminal_page"
        ] = "Overview"

        st.switch_page(
            "main.py"
        )


def render() -> None:
    page_header(
        "Pesquisas",
        (
            "Histórico, acompanhamento e "
            "resultados das pesquisas "
            "quantitativas."
        ),
    )

    rows = list_researches()

    _render_status_counts(
        rows
    )

    active_id = st.session_state.get(
        "active_research_id"
    )

    st.divider()

    if active_id:
        active_row = next(
            (
                row
                for row in rows
                if str(
                    row.get(
                        "research_id"
                    )
                )
                == str(
                    active_id
                )
            ),
            None,
        )

        if active_row is not None:
            st.success(
                (
                    "Pesquisa ativa: "
                    f"{_research_name(active_row)} "
                    f"({active_id})"
                )
            )
        else:
            st.info(
                (
                    "Existe um Research ID ativo, "
                    "mas ele não foi encontrado "
                    "no histórico atual."
                )
            )

    else:
        st.info(
            "Nenhuma pesquisa ativa."
        )

    st.divider()

    section_title(
        "Histórico de pesquisas",
        (
            "Pesquisas criadas pelo "
            "Research Workspace."
        ),
    )

    if not rows:
        st.info(
            (
                "Nenhuma pesquisa foi criada "
                "até o momento."
            )
        )
        return

    history = _history_frame(
        rows
    )

    if not history.empty:
        dataframe_view(
            history,
            height=360,
        )

    research_ids = [
        str(
            row[
                "research_id"
            ]
        )
        for row in rows
        if row.get(
            "research_id"
        )
    ]

    default_id = (
        str(
            active_id
        )
        if active_id
        and str(
            active_id
        )
        in research_ids
        else research_ids[
            0
        ]
    )

    selected = st.selectbox(
        "Selecionar pesquisa",
        options=(
            research_ids
        ),
        index=(
            research_ids.index(
                default_id
            )
        ),
        format_func=lambda value: (
            (
                _research_name(
                    next(
                        row
                        for row in rows
                        if str(
                            row.get(
                                "research_id"
                            )
                        )
                        == value
                    )
                )
                + " — "
                + value
            )
        ),
        key=(
            "stage185_history_selection"
        ),
    )

    if not selected:
        return

    try:
        manifest = load_research_manifest(
            selected
        )

    except Exception:
        st.error(
            (
                "Não foi possível carregar "
                "esta pesquisa."
            )
        )
        return

    selected_row = next(
        (
            row
            for row in rows
            if str(
                row.get(
                    "research_id"
                )
            )
            == selected
        ),
        {},
    )

    st.divider()

    metric_cards(
        [
            (
                "Pesquisa",
                _research_name(
                    selected_row
                ),
            ),
            (
                "Status",
                _as_text(
                    manifest.get(
                        "status"
                    )
                ),
            ),
            (
                "Modelo",
                _model_name(
                    selected_row
                ),
            ),
            (
                "Pregões",
                format_integer(
                    manifest.get(
                        "sessions_total"
                    )
                ),
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
                "Duração",
                _duration_text(
                    manifest.get(
                        "duration_seconds"
                    )
                ),
            ),
        ],
        columns=4,
    )

    st.divider()

    _render_monitor(
        selected,
        manifest,
    )

    st.divider()

    definition = _render_definition(
        selected
    )

    st.divider()

    section_title(
        "Projeto de pesquisa",
        (
            "Hipótese, Resultados, Experimentos, "
            "Analytics, Comparações e Descobertas "
            "centralizados em uma única pesquisa."
        ),
    )

    project_tab_result, project_tab_navigation = (
        st.tabs(
            [
                "Resultado",
                "Explorar",
            ]
        )
    )

    with project_tab_result:
        render_research_result(
            selected
        )

    with project_tab_navigation:
        st.markdown(
            "### Continuar a investigação"
        )

        st.caption(
            (
                "Abra a área adequada sem "
                "expor estruturas internas "
                "da plataforma."
            )
        )

        col_a, col_b, col_c = st.columns(
            3
        )

        with col_a:
            if st.button(
                "Abrir Experimentos",
                key=(
                    "research_open_experiments"
                ),
                use_container_width=True,
            ):
                st.session_state[
                    "active_research_id"
                ] = selected

                st.session_state[
                    "requested_terminal_page"
                ] = "Experimentos"

                st.rerun()

        with col_b:
            if st.button(
                "Abrir Analytics",
                key=(
                    "research_open_analytics"
                ),
                use_container_width=True,
            ):
                st.session_state[
                    "active_research_id"
                ] = selected

                st.session_state[
                    "requested_terminal_page"
                ] = "Analytics"

                st.rerun()

        with col_c:
            if st.button(
                "Abrir Comparações",
                key=(
                    "research_open_comparisons"
                ),
                use_container_width=True,
            ):
                st.session_state[
                    "active_research_id"
                ] = selected

                st.session_state[
                    "requested_terminal_page"
                ] = "Comparações"

                st.rerun()

        st.info(
            (
                "Informações técnicas, hashes, "
                "manifests, runtime e auditoria "
                "foram removidos desta visão e "
                "permanecem disponíveis somente "
                "em Administração."
            )
        )


if __name__ == "__main__":
    render()
