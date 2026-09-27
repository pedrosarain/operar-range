from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

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


def _as_text(
    value: Any,
) -> str:
    if value is None:
        return NA_TEXT

    return str(value)


def _duration_text(
    seconds: Any,
) -> str:
    if seconds is None:
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
        status = (
            distributed_status(
                distributed_root=(
                    paths[
                        "distributed_root"
                    ]
                ),
                run_id=run_id,
            )
        )

    except Exception:
        return {
            "available": False,
            "run_id": (
                run_id
            ),
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

    batches_total = (
        status.get(
            "batches_total"
        )
    )

    completed = (
        status.get(
            "completed"
        )
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

    dataframe = pd.DataFrame(
        rows
    )

    preferred = [
        "research_id",
        "status",
        "current_stage",
        "created_at",
        "period_start",
        "period_end",
        "family",
        "generation",
        "experiments_valid",
        "execution_units_total",
        "batches_total",
        "duration_seconds",
        "lineage_match",
    ]

    visible = [
        column
        for column in preferred
        if column
        in dataframe.columns
    ]

    display = dataframe[
        visible
    ].copy()

    if (
        "duration_seconds"
        in display.columns
    ):
        display[
            "duration"
        ] = display[
            "duration_seconds"
        ].map(
            _duration_text
        )

        display = (
            display.drop(
                columns=[
                    "duration_seconds"
                ]
            )
        )

    return display


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
        "Run Monitor",
        (
            "Estado persistido da execução "
            "selecionada."
        ),
    )

    status = (
        manifest.get(
            "status"
        )
        or "N/A"
    )

    status_badge(
        "Research status",
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
        elapsed = (
            _elapsed_seconds(
                manifest.get(
                    "started_at"
                )
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

    eta = (
        _eta_seconds(
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
                "Batches total",
                format_integer(
                    monitor.get(
                        "batches_total"
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
                "Workers",
                format_integer(
                    monitor.get(
                        "workers_total"
                    )
                ),
            ),
            (
                "Retries",
                format_integer(
                    monitor.get(
                        "retries"
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
        columns=4,
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

    if (
        monitor.get(
            "failed_final"
        )
        is not None
        and int(
            monitor[
                "failed_final"
            ]
        )
        > 0
    ):
        st.error(
            (
                "A execução distribuída "
                "possui falhas finais."
            )
        )

    if status == "FAILED":
        st.error(
            (
                f"{manifest.get('error_type') or 'ERROR'}: "
                f"{manifest.get('error_message') or 'N/A'}"
            )
        )


def _render_lineage(
    manifest: dict[str, Any],
) -> None:
    section_title(
        "Lineage",
        (
            "Hashes e identificação da "
            "execução preservados no "
            "Research ID."
        ),
    )

    lineage = (
        manifest.get(
            "lineage_match"
        )
    )

    if lineage is True:
        lineage_text = "TRUE"

    elif lineage is False:
        lineage_text = "FALSE"

    else:
        lineage_text = "N/A"

    status_badge(
        "LINEAGE_MATCH",
        lineage_text,
    )

    repeated = (
        manifest.get(
            "quantitative_execution_repeated"
        )
    )

    if repeated is False:
        repeated_text = "FALSE"

    elif repeated is True:
        repeated_text = "TRUE"

    else:
        repeated_text = "N/A"

    status_badge(
        "Quantitative execution repeated",
        repeated_text,
    )

    key_value_panel(
        [
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
            (
                "Valid experiments SHA-256",
                _as_text(
                    manifest.get(
                        "source_valid_experiments_sha256"
                    )
                ),
            ),
            (
                "Trajectory manifest SHA-256",
                _as_text(
                    manifest.get(
                        "trajectory_manifest_sha256"
                    )
                ),
            ),
            (
                "Rule Set SHA-256",
                _as_text(
                    manifest.get(
                        "rule_set_sha256"
                    )
                ),
            ),
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
        ],
    )


def _render_artifacts(
    research_id: str,
) -> None:
    section_title(
        "Artifacts",
        (
            "Recursos isolados desta "
            "pesquisa."
        ),
    )

    paths = (
        research_result_paths(
            research_id
        )
    )

    rows = []

    for name, value in (
        paths.items()
    ):
        path = Path(
            value
        )

        rows.append(
            {
                "artifact": name,
                "exists": (
                    path.exists()
                ),
                "path": value,
                "size_bytes": (
                    path.stat().st_size
                    if path.exists()
                    and path.is_file()
                    else None
                ),
            }
        )

    dataframe = pd.DataFrame(
        rows
    )

    if not dataframe.empty:
        dataframe[
            "status"
        ] = dataframe[
            "exists"
        ].map(
            {
                True: "AVAILABLE",
                False: "MISSING",
            }
        )

        visible = [
            "artifact",
            "status",
            "size_bytes",
            "path",
        ]

        dataframe_view(
            dataframe[
                visible
            ],
            height=360,
        )


def _render_definition(
    research_id: str,
) -> None:
    try:
        definition = (
            load_research_definition(
                research_id
            )
        )
    except Exception:
        st.info(
            "Definição indisponível."
        )
        return

    section_title(
        "Research Definition"
    )

    key_value_panel(
        [
            (
                "Strategy",
                _as_text(
                    definition.get(
                        "strategy"
                    )
                ),
            ),
            (
                "Family",
                _as_text(
                    definition.get(
                        "family"
                    )
                ),
            ),
            (
                "Generation",
                _as_text(
                    definition.get(
                        "generation"
                    )
                ),
            ),
            (
                "Period start",
                _as_text(
                    definition.get(
                        "period_start"
                    )
                ),
            ),
            (
                "Period end",
                _as_text(
                    definition.get(
                        "period_end"
                    )
                ),
            ),
            (
                "Batch size",
                _as_text(
                    definition.get(
                        "batch_size"
                    )
                ),
            ),
        ],
    )

    with st.expander(
        "Parâmetros completos",
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
                "Abrir Resultado estará "
                "disponível após a pesquisa "
                "ser concluída."
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
                "Pesquisa marcada como "
                "COMPLETED, porém existem "
                "artifacts ausentes: "
                + ", ".join(
                    missing
                )
            )
        )
        return

    if st.button(
        "ABRIR RESULTADO",
        type="primary",
        use_container_width=True,
        key=(
            "stage18_open_result_"
            + research_id
        ),
    ):
        #
        # O Research Terminal continuará
        # sendo a área de resultados.
        #
        # O main.py consumirá essa intenção
        # antes de criar o widget de
        # navegação, evitando modificar um
        # widget depois da instanciação.
        #
        st.session_state[
            "active_research_id"
        ] = research_id

        st.session_state[
            "requested_terminal_page"
        ] = "Overview"

        st.success(
            (
                "Resultado selecionado. "
                "Abrindo Research Workspace..."
            )
        )

        st.switch_page(
            "main.py"
        )


def render() -> None:
    page_header(
        "Pesquisas",
        (
            "Run Monitor e histórico "
            "persistente das pesquisas "
            "criadas pelo Workspace."
        ),
    )

    rows = (
        list_researches()
    )

    _render_status_counts(
        rows
    )

    st.divider()

    section_title(
        "Research History",
        (
            "Cada pesquisa possui Research ID "
            "próprio e artifacts isolados."
        ),
    )

    if not rows:
        st.info(
            (
                "Nenhuma pesquisa foi criada "
                "pelo Workspace."
            )
        )
        return

    history = (
        _history_frame(
            rows
        )
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

    current_id = st.session_state.get(
        "stage18_current_research_id"
    )

    default_index = 0

    if (
        current_id
        and current_id
        in research_ids
    ):
        default_index = (
            research_ids.index(
                current_id
            )
        )

    selected = st.selectbox(
        "Abrir pesquisa",
        options=(
            research_ids
        ),
        index=(
            default_index
        ),
        key=(
            "stage18_history_selection"
        ),
    )

    if not selected:
        return

    try:
        manifest = (
            load_research_manifest(
                selected
            )
        )

    except Exception as exc:
        st.error(
            (
                "Não foi possível carregar "
                "o manifesto da pesquisa."
            )
        )

        st.caption(
            str(
                exc
            )
        )

        return

    st.divider()

    metric_cards(
        [
            (
                "Research ID",
                selected,
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
                "Experimentos gerados",
                format_integer(
                    manifest.get(
                        "experiments_generated"
                    )
                ),
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
                "Experimentos inválidos",
                format_integer(
                    manifest.get(
                        "experiments_invalid"
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

    _render_definition(
        selected
    )

    st.divider()

    _render_lineage(
        manifest
    )

    st.divider()

    _render_artifacts(
        selected
    )

    st.divider()

    _open_result_button(
        selected,
        manifest,
    )


if __name__ == "__main__":
    render()