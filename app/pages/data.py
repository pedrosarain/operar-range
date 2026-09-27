from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app.components.common import (
    dataframe_view,
    metric_cards,
    page_header,
    section_title,
    status_badge,
)
from app.formatting import (
    format_bytes,
    format_integer,
)
from operar_range.research_workspace import (
    available_dataset_period,
    list_inbox_files,
    process_datasets,
    validate_inbox_selection,
)


def _inventory_frame() -> pd.DataFrame:
    rows = list_inbox_files()

    if not rows:
        return pd.DataFrame()

    dataframe = pd.DataFrame(
        rows
    )

    if (
        "size_bytes"
        in dataframe.columns
    ):
        dataframe[
            "size"
        ] = dataframe[
            "size_bytes"
        ].map(
            format_bytes
        )

    preferred = [
        "name",
        "status",
        "size",
        "modified_at",
        "sha256",
        "error",
    ]

    visible = [
        column
        for column in preferred
        if column
        in dataframe.columns
    ]

    return dataframe[
        visible
    ].copy()


def _render_dataset_period() -> None:
    period = (
        available_dataset_period()
    )

    st.divider()

    section_title(
        "Dataset processado",
        (
            "Período atualmente disponível "
            "para pesquisas Trade 1."
        ),
    )

    if not period.get(
        "available"
    ):
        status_badge(
            "Dataset",
            "N/A",
        )

        st.info(
            (
                "Nenhum dataset processado "
                "está disponível."
            )
        )

        return

    metric_cards(
        [
            (
                "Pregões disponíveis",
                format_integer(
                    period.get(
                        "sessions_total"
                    )
                ),
            ),
            (
                "Período inicial",
                str(
                    period.get(
                        "period_start"
                    )
                    or "N/A"
                ),
            ),
            (
                "Período final",
                str(
                    period.get(
                        "period_end"
                    )
                    or "N/A"
                ),
            ),
        ],
        columns=3,
    )


def _progress_callback(
    progress_bar,
    status_box,
):
    def callback(
        stage: str,
        fraction: float,
        details: dict,
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

        detail_parts = []

        if details:
            for key in (
                "file",
                "imported_reports",
                "completed_batches",
                "total_batches",
                "remaining_batches",
                "worker_id",
                "batch_id",
                "status",
            ):
                if (
                    key in details
                    and details[
                        key
                    ]
                    is not None
                ):
                    detail_parts.append(
                        (
                            f"{key}="
                            f"{details[key]}"
                        )
                    )

        detail_text = (
            " | ".join(
                detail_parts
            )
        )

        message = stage

        if detail_text:
            message = (
                f"{stage} — "
                f"{detail_text}"
            )

        status_box.info(
            message
        )

    return callback


def render() -> None:
    page_header(
        "Data",
        (
            "Entrada e processamento oficial "
            "de novos datasets do Operar Range."
        ),
    )

    st.caption(
        (
            "Nesta V1 os arquivos são "
            "copiados manualmente para "
            "`data/inbox/`. A interface "
            "valida e processa os arquivos "
            "encontrados nessa pasta."
        )
    )

    inventory_rows = (
        list_inbox_files()
    )

    new_count = sum(
        1
        for row in inventory_rows
        if row.get(
            "status"
        )
        == "NEW"
    )

    processed_count = sum(
        1
        for row in inventory_rows
        if row.get(
            "status"
        )
        == "PROCESSED"
    )

    error_count = sum(
        1
        for row in inventory_rows
        if row.get(
            "status"
        )
        == "ERROR"
    )

    metric_cards(
        [
            (
                "Arquivos encontrados",
                format_integer(
                    len(
                        inventory_rows
                    )
                ),
            ),
            (
                "Novos",
                format_integer(
                    new_count
                ),
            ),
            (
                "Processados",
                format_integer(
                    processed_count
                ),
            ),
            (
                "Com erro",
                format_integer(
                    error_count
                ),
            ),
        ],
        columns=4,
    )

    st.divider()

    section_title(
        "Inbox",
        (
            "Arquivos disponíveis em "
            "`data/inbox/`."
        ),
    )

    display = (
        _inventory_frame()
    )

    if display.empty:
        st.info(
            (
                "Nenhum arquivo encontrado "
                "em data/inbox/."
            )
        )

        _render_dataset_period()
        return

    dataframe_view(
        display,
        height=320,
    )

    selectable = [
        row[
            "name"
        ]
        for row in inventory_rows
        if row.get(
            "status"
        )
        in {
            "NEW",
            "PROCESSED",
        }
        and row.get(
            "extension"
        )
        == ".zip"
    ]

    st.divider()

    section_title(
        "Selecionar datasets",
        (
            "Nenhum processamento é iniciado "
            "até a validação completa da "
            "seleção."
        ),
    )

    if not selectable:
        st.warning(
            (
                "Não há arquivos ZIP válidos "
                "disponíveis para seleção."
            )
        )

        _render_dataset_period()
        return

    selected = st.multiselect(
        "Arquivos",
        options=selectable,
        default=[
            name
            for name in selectable
            if next(
                (
                    row.get(
                        "status"
                    )
                    for row
                    in inventory_rows
                    if row.get(
                        "name"
                    )
                    == name
                ),
                None,
            )
            == "NEW"
        ],
        key=(
            "stage18_data_files"
        ),
    )

    validation = (
        validate_inbox_selection(
            selected
        )
    )

    if selected:
        if validation[
            "valid"
        ]:
            status_badge(
                "Validação",
                "VALID",
            )

            st.success(
                (
                    "Seleção válida. "
                    "O processamento pode "
                    "ser iniciado."
                )
            )

        else:
            status_badge(
                "Validação",
                "ERROR",
            )

            for error in validation[
                "errors"
            ]:
                st.error(
                    error
                )

    else:
        status_badge(
            "Validação",
            "PENDING",
        )

    st.divider()

    section_title(
        "Pipeline",
        (
            "O botão abaixo reutiliza os "
            "motores homologados. A interface "
            "não recalcula a lógica."
        ),
    )

    st.markdown(
        """
1. **Validação**
2. **Normalização**
3. **Scanner**
4. **Trade Database**
5. **Trajectory Cache**
6. **Analytics** — executado posteriormente dentro da pesquisa
"""
    )

    process_disabled = (
        not selected
        or not validation[
            "valid"
        ]
    )

    if st.button(
        "PROCESSAR DATASET",
        type="primary",
        disabled=(
            process_disabled
        ),
        use_container_width=True,
        key=(
            "stage18_process_dataset"
        ),
    ):
        progress_bar = (
            st.progress(
                0
            )
        )

        status_box = (
            st.empty()
        )

        callback = (
            _progress_callback(
                progress_bar,
                status_box,
            )
        )

        try:
            result = (
                process_datasets(
                    selected,
                    progress_callback=(
                        callback
                    ),
                )
            )

        except Exception as exc:
            progress_bar.empty()

            status_box.error(
                (
                    "Processamento falhou."
                )
            )

            st.error(
                str(
                    exc
                )
            )

            return

        progress_bar.progress(
            100
        )

        status_box.success(
            "Processamento concluído."
        )

        scanner = result.get(
            "scanner"
        ) or {}

        trajectory = result.get(
            "trajectory_cache"
        ) or {}

        scanner_summary = (
            scanner.get(
                "summary"
            )
            if isinstance(
                scanner,
                dict,
            )
            else {}
        ) or {}

        metric_cards(
            [
                (
                    "Arquivos importados",
                    format_integer(
                        len(
                            result.get(
                                "imports",
                                [],
                            )
                        )
                    ),
                ),
                (
                    "Pregões analisados",
                    format_integer(
                        scanner_summary.get(
                            "pregoes_analisados"
                        )
                    ),
                ),
                (
                    "Trade 1",
                    format_integer(
                        scanner_summary.get(
                            "trade1_count"
                        )
                    ),
                ),
                (
                    "Sem Trade 1",
                    format_integer(
                        scanner_summary.get(
                            "sem_trade1_count"
                        )
                    ),
                ),
            ],
            columns=4,
        )

        st.success(
            (
                "Dataset preparado para "
                "utilização no Research "
                "Builder."
            )
        )

        st.caption(
            (
                "Analytics permanece "
                f"{result.get('analytics_status', 'N/A')} "
                "até existir uma pesquisa "
                "executada."
            )
        )

        st.cache_data.clear()

    _render_dataset_period()


if __name__ == "__main__":
    render()