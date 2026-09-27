from __future__ import annotations

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
    format_bytes,
    format_integer,
)
from operar_range.research_workspace import (
    list_available_datasets,
    list_inbox_files,
    process_datasets,
    validate_inbox_selection,
)


def _text(
    value,
) -> str:
    if value is None:
        return NA_TEXT

    return str(value)


def _dataset_display_frame(
    rows: list[dict],
) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()

    dataframe = pd.DataFrame(
        rows
    )

    dataframe[
        "prepared"
    ] = dataframe[
        "prepared_for_research"
    ].map(
        {
            True: "SIM",
            False: "NÃO",
        }
    )

    dataframe[
        "version"
    ] = dataframe[
        "dataset_version"
    ].fillna(
        NA_TEXT
    )

    dataframe[
        "normalization"
    ] = dataframe[
        "normalization_version"
    ].fillna(
        NA_TEXT
    )

    dataframe[
        "imported"
    ] = dataframe.apply(
        lambda row: (
            row.get(
                "imported_at"
            )
            if row.get(
                "imported_at"
            )
            else "NÃO REGISTRADO"
        ),
        axis=1,
    )

    preferred = [
        "dataset_id",
        "ticker",
        "source",
        "sessions_total",
        "records_total",
        "period_start",
        "period_end",
        "quality_status",
        "version",
        "imported",
        "ingest_version",
        "normalization",
        "source_sha256",
        "prepared",
    ]

    visible = [
        column
        for column in preferred
        if column in dataframe.columns
    ]

    return dataframe[
        visible
    ].copy()


def _inbox_frame(
    rows: list[dict],
) -> pd.DataFrame:
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
        "sha256",
        "error",
    ]

    visible = [
        column
        for column in preferred
        if column in dataframe.columns
    ]

    return dataframe[
        visible
    ].copy()


def _progress_callback(
    progress_bar,
    status_box,
):
    labels = {
        "VALIDATION": "Validação",
        "NORMALIZATION": "Normalização",
        "SCANNER": "Scanner",
        "TRAJECTORY_CACHE": "Trajetórias",
        "ANALYTICS": "Analytics",
    }

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

        label = labels.get(
            stage,
            stage,
        )

        status_box.info(
            f"Etapa atual: {label}"
        )

    return callback


def _render_dataset_catalog() -> None:
    datasets = (
        list_available_datasets()
    )

    section_title(
        "Datasets disponíveis",
        (
            "Datasets preparados e reconhecidos "
            "pela plataforma para utilização "
            "em pesquisas quantitativas."
        ),
    )

    if not datasets:
        st.info(
            "Nenhum dataset disponível."
        )
        return

    ready_count = sum(
        1
        for row in datasets
        if row.get(
            "prepared_for_research"
        )
    )

    sessions_total = sum(
        int(
            row.get(
                "sessions_total"
            )
            or 0
        )
        for row in datasets
    )

    records_total = sum(
        int(
            row.get(
                "records_total"
            )
            or 0
        )
        for row in datasets
    )

    metric_cards(
        [
            (
                "Datasets",
                format_integer(
                    len(
                        datasets
                    )
                ),
            ),
            (
                "Preparados para pesquisa",
                format_integer(
                    ready_count
                ),
            ),
            (
                "Pregões",
                format_integer(
                    sessions_total
                ),
            ),
            (
                "Registros",
                format_integer(
                    records_total
                ),
            ),
        ],
        columns=4,
    )

    st.divider()

    frame = (
        _dataset_display_frame(
            datasets
        )
    )

    dataframe_view(
        frame,
        height=320,
    )

    options = [
        str(
            row.get(
                "dataset_key"
            )
        )
        for row in datasets
    ]

    selected_key = st.selectbox(
        "Dataset",
        options=options,
        key=(
            "stage185_dataset_selection"
        ),
    )

    selected = next(
        (
            row
            for row in datasets
            if str(
                row.get(
                    "dataset_key"
                )
            )
            == selected_key
        ),
        None,
    )

    if selected is None:
        return

    st.divider()

    section_title(
        "Detalhes do dataset"
    )

    imported_text = (
        selected.get(
            "imported_at"
        )
        or "NÃO REGISTRADO"
    )

    dataset_id_text = (
        selected.get(
            "dataset_id"
        )
        or "LEGACY DATASET"
    )

    prepared_text = (
        "SIM"
        if selected.get(
            "prepared_for_research"
        )
        else "NÃO"
    )

    key_value_panel(
        [
            (
                "Dataset ID",
                dataset_id_text,
            ),
            (
                "Versão",
                _text(
                    selected.get(
                        "dataset_version"
                    )
                ),
            ),
            (
                "Ativo",
                _text(
                    selected.get(
                        "ticker"
                    )
                ),
            ),
            (
                "Origem",
                _text(
                    selected.get(
                        "source"
                    )
                ),
            ),
            (
                "Fornecedor",
                _text(
                    selected.get(
                        "provider"
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
                "Pregões",
                format_integer(
                    selected.get(
                        "sessions_total"
                    )
                ),
            ),
            (
                "Registros",
                format_integer(
                    selected.get(
                        "records_total"
                    )
                ),
            ),
            (
                "Importado em",
                imported_text,
            ),
            (
                "Ingest Version",
                _text(
                    selected.get(
                        "ingest_version"
                    )
                ),
            ),
            (
                "Normalization Version",
                _text(
                    selected.get(
                        "normalization_version"
                    )
                ),
            ),
            (
                "Scanner Motor",
                _text(
                    selected.get(
                        "scanner_motor_version"
                    )
                ),
            ),
            (
                "SHA-256",
                _text(
                    selected.get(
                        "source_sha256"
                    )
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
            (
                "Preparado para pesquisa?",
                prepared_text,
            ),
        ],
    )

    if selected.get(
        "prepared_for_research"
    ):
        status_badge(
            "Dataset",
            "READY",
        )
    else:
        status_badge(
            "Dataset",
            "NOT READY",
        )


def _render_inbox() -> None:
    st.divider()

    section_title(
        "Entrada de novos dados",
        (
            "Nesta versão os arquivos são "
            "colocados manualmente em "
            "`data/inbox/`."
        ),
    )

    st.caption(
        (
            "Upload pelo navegador ainda não "
            "faz parte da Etapa 18.5."
        )
    )

    rows = (
        list_inbox_files()
    )

    if not rows:
        st.info(
            (
                "Nenhum arquivo encontrado "
                "para processamento."
            )
        )
        return

    frame = (
        _inbox_frame(
            rows
        )
    )

    dataframe_view(
        frame,
        height=260,
    )

    selectable = [
        row[
            "name"
        ]
        for row in rows
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

    if not selectable:
        return

    selected = st.multiselect(
        "Arquivos para processar",
        options=selectable,
        default=[
            row[
                "name"
            ]
            for row in rows
            if row.get(
                "status"
            )
            == "NEW"
            and row.get(
                "extension"
            )
            == ".zip"
        ],
        key=(
            "stage185_data_files"
        ),
    )

    validation = (
        validate_inbox_selection(
            selected
        )
    )

    if selected:
        if validation.get(
            "valid"
        ):
            status_badge(
                "Validação",
                "VALID",
            )
        else:
            status_badge(
                "Validação",
                "ERROR",
            )

            for error in validation.get(
                "errors",
                [],
            ):
                st.error(
                    str(
                        error
                    )
                )

    process_disabled = (
        not selected
        or not validation.get(
            "valid"
        )
    )

    if st.button(
        "PROCESSAR DATASET",
        type="primary",
        use_container_width=True,
        disabled=(
            process_disabled
        ),
        key=(
            "stage185_process_dataset"
        ),
    ):
        progress_bar = st.progress(
            0
        )

        status_box = st.empty()

        callback = (
            _progress_callback(
                progress_bar,
                status_box,
            )
        )

        try:
            process_datasets(
                selected,
                progress_callback=(
                    callback
                ),
            )

        except Exception as exc:
            progress_bar.empty()

            status_box.error(
                "Processamento não concluído."
            )

            st.error(
                (
                    "Não foi possível preparar "
                    "o dataset selecionado."
                )
            )

            st.caption(
                type(
                    exc
                ).__name__
            )

            return

        progress_bar.progress(
            100
        )

        status_box.success(
            "Dataset preparado."
        )

        st.cache_data.clear()

        st.success(
            (
                "O dataset está disponível "
                "para novas pesquisas."
            )
        )

        st.rerun()


def render() -> None:
    page_header(
        "Data Manager",
        (
            "Gerenciamento dos datasets "
            "utilizados pelo Operar Range."
        ),
    )

    _render_dataset_catalog()

    _render_inbox()


if __name__ == "__main__":
    render()
