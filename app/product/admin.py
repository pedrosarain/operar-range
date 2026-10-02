from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl
import streamlit as st

from app.product.shared import (
    page_title,
)
from operar_range.research_workspace import (
    list_available_datasets,
    list_inbox_files,
    list_researches,
    load_research_manifest,
    process_dataset_import_stage22,
    research_paths,
    save_dataset_upload,
    validate_inbox_selection,
)


DATA_ROOT = Path(
    "data"
)


ADMIN_TABS = (
    "Datasets",
    "Hashes",
    "Runtime",
    "Manifest",
    "Registry",
    "Logs",
    "Versionamento",
    "Auditoria",
)


def _text(
    value: Any,
) -> str:
    if value is None:
        return "—"

    if isinstance(
        value,
        list,
    ):
        if not value:
            return "—"

        return ", ".join(
            str(
                item
            )
            for item in value
        )

    return str(
        value
    )


def _read_parquet(
    path: Path,
) -> pl.DataFrame:
    try:
        if not path.exists():
            return pl.DataFrame()

        return pl.read_parquet(
            path
        )

    except Exception:
        return pl.DataFrame()


def _read_json(
    path: Path,
) -> dict[str, Any]:
    try:
        if not path.exists():
            return {}

        data = json.loads(
            path.read_text()
        )

        if isinstance(
            data,
            dict,
        ):
            return data

        return {}

    except Exception:
        return {}


def _dataset_key(
    row: dict[str, Any],
) -> str:
    return str(
        row.get(
            "dataset_id"
        )
        or row.get(
            "dataset_key"
        )
        or ""
    )


def _research_id(
    row: dict[str, Any],
) -> str:
    return str(
        row.get(
            "research_id"
        )
        or ""
    )


def _datasets() -> list[
    dict[str, Any]
]:
    return list(
        list_available_datasets()
    )


def _researches() -> list[
    dict[str, Any]
]:
    return [
        row
        for row
        in list_researches()
        if _research_id(
            row
        )
    ]


def _dataset_selector(
    *,
    key: str,
) -> dict[str, Any] | None:
    rows = _datasets()

    if not rows:
        st.info(
            "Nenhum Dataset disponível."
        )
        return None

    values = [
        _dataset_key(
            row
        )
        for row in rows
        if _dataset_key(
            row
        )
    ]

    if not values:
        st.info(
            "Nenhum Dataset identificável disponível."
        )
        return None

    selected = st.selectbox(
        "Dataset",
        options=values,
        key=key,
    )

    for row in rows:
        if (
            _dataset_key(
                row
            )
            == selected
        ):
            return row

    return None


def _research_selector(
    *,
    key: str,
) -> dict[str, Any] | None:
    rows = _researches()

    if not rows:
        st.info(
            "Nenhuma Research disponível."
        )
        return None

    values = [
        _research_id(
            row
        )
        for row in rows
    ]

    selected = st.selectbox(
        "Research",
        options=values,
        key=key,
    )

    for row in rows:
        if (
            _research_id(
                row
            )
            == selected
        ):
            return row

    return None


def _render_dataset_catalog() -> None:
    st.subheader(
        "Datasets"
    )

    rows = _datasets()

    if not rows:
        st.info(
            "Nenhum Dataset disponível."
        )

    else:
        ready = sum(
            1
            for row in rows
            if bool(
                row.get(
                    "prepared_for_research"
                )
            )
        )

        sessions = sum(
            int(
                row.get(
                    "sessions_total"
                )
                or 0
            )
            for row in rows
        )

        records = sum(
            int(
                row.get(
                    "records_total"
                )
                or 0
            )
            for row in rows
        )

        c1, c2, c3, c4 = (
            st.columns(
                4
            )
        )

        with c1:
            st.metric(
                "Datasets",
                len(
                    rows
                ),
            )

        with c2:
            st.metric(
                "Prontos para pesquisa",
                ready,
            )

        with c3:
            st.metric(
                "Pregões",
                sessions,
            )

        with c4:
            st.metric(
                "Registros",
                records,
            )

        visible = []

        for row in rows:
            visible.append(
                {
                    "Dataset ID": (
                        row.get(
                            "dataset_id"
                        )
                        or row.get(
                            "dataset_key"
                        )
                    ),
                    "Mercado": row.get(
                        "market"
                    ),
                    "Ativo": (
                        row.get(
                            "asset"
                        )
                        or row.get(
                            "ticker"
                        )
                    ),
                    "Período inicial": (
                        row.get(
                            "period_start"
                        )
                    ),
                    "Período final": (
                        row.get(
                            "period_end"
                        )
                    ),
                    "Pregões": (
                        row.get(
                            "sessions_total"
                        )
                    ),
                    "Registros": (
                        row.get(
                            "records_total"
                        )
                    ),
                    "Qualidade": (
                        row.get(
                            "quality_status"
                        )
                    ),
                    "Research ready": bool(
                        row.get(
                            "prepared_for_research"
                        )
                        or row.get(
                            "research_ready"
                        )
                    ),
                }
            )

        st.dataframe(
            visible,
            use_container_width=True,
            hide_index=True,
        )




def _render_dataset_import() -> None:
    st.markdown(
        "### Importar novo Dataset"
    )

    st.caption(
        (
            "Todos os arquivos enviados nesta "
            "importação formarão um único Dataset ID."
        )
    )

    left, right = st.columns(
        2
    )

    with left:
        market = st.text_input(
            "Mercado *",
            placeholder=(
                "Ex.: B3"
            ),
            key=(
                "product01_admin_dataset_market"
            ),
        )

    with right:
        asset = st.text_input(
            "Ativo *",
            placeholder=(
                "Ex.: WIN"
            ),
            key=(
                "product01_admin_dataset_asset"
            ),
        )

    provider = st.text_input(
        "Fornecedor",
        placeholder=(
            "Ex.: TickData, LSEG, Profit"
        ),
        key=(
            "product01_admin_dataset_provider"
        ),
    )

    uploads = st.file_uploader(
        "Arquivos ZIP do Dataset",
        type=[
            "zip",
        ],
        accept_multiple_files=True,
        key=(
            "product01_admin_dataset_uploads"
        ),
    )

    selected_names: list[str] = []

    upload_error: Exception | None = None

    if uploads:
        for upload in uploads:
            try:
                result = (
                    save_dataset_upload(
                        filename=(
                            upload.name
                        ),
                        content=(
                            upload.getvalue()
                        ),
                    )
                )

                selected_names.append(
                    str(
                        result[
                            "name"
                        ]
                    )
                )

            except Exception as exc:
                upload_error = exc

                st.error(
                    (
                        "Não foi possível armazenar "
                        f"{upload.name}."
                    )
                )

                st.caption(
                    str(
                        exc
                    )
                )

                break

    selected_names = sorted(
        set(
            selected_names
        )
    )

    if selected_names:
        st.caption(
            (
                f"{len(selected_names)} arquivo(s) "
                "compõem esta importação."
            )
        )

        inbox = [
            row
            for row in list_inbox_files()
            if str(
                row.get(
                    "name"
                )
                or ""
            )
            in set(
                selected_names
            )
        ]

        if inbox:
            visible = [
                {
                    "Arquivo": row.get(
                        "name"
                    ),
                    "Status": row.get(
                        "status"
                    ),
                    "Bytes": row.get(
                        "size_bytes"
                    ),
                    "SHA-256": row.get(
                        "sha256"
                    ),
                    "Erro": row.get(
                        "error"
                    ),
                }
                for row in inbox
            ]

            st.dataframe(
                visible,
                use_container_width=True,
                hide_index=True,
            )

    validation = (
        validate_inbox_selection(
            selected_names
        )
        if selected_names
        else {
            "valid": False,
            "errors": [],
        }
    )

    metadata_valid = bool(
        str(
            market
        ).strip()
        and str(
            asset
        ).strip()
    )

    disabled = bool(
        not selected_names
        or not metadata_valid
        or not validation.get(
            "valid"
        )
        or upload_error is not None
    )

    if selected_names:
        if disabled:
            st.warning(
                (
                    "A importação ainda não está "
                    "pronta para execução."
                )
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

        else:
            st.success(
                "Importação pronta."
            )

    if st.button(
        "IMPORTAR E PREPARAR DATASET",
        type="primary",
        use_container_width=True,
        disabled=disabled,
        key=(
            "product01_admin_process_dataset"
        ),
    ):
        progress = st.progress(
            0
        )

        status = st.empty()

        def callback(
            stage: str,
            fraction: float,
            details: dict,
        ) -> None:
            progress.progress(
                int(
                    max(
                        0.0,
                        min(
                            1.0,
                            float(
                                fraction
                            ),
                        ),
                    )
                    * 100
                )
            )

            status.info(
                (
                    "Etapa atual: "
                    + str(
                        stage
                    )
                )
            )

        try:
            result = (
                process_dataset_import_stage22(
                    market=market,
                    asset=asset,
                    provider=(
                        provider
                        or None
                    ),
                    filenames=(
                        selected_names
                    ),
                    progress_callback=(
                        callback
                    ),
                )
            )

        except Exception as exc:
            status.error(
                "Importação não concluída."
            )

            st.error(
                "Dataset não pôde ser preparado."
            )

            st.caption(
                str(
                    exc
                )
            )

            return

        progress.progress(
            100
        )

        status.success(
            "Dataset pronto para pesquisa."
        )

        st.success(
            (
                "Dataset registrado: "
                + str(
                    result.get(
                        "dataset_id"
                    )
                )
            )
        )

        st.rerun()


def _render_hashes() -> None:
    st.subheader(
        "Hashes"
    )

    st.caption(
        (
            "Identidades criptográficas já "
            "persistidas pelos contratos existentes."
        )
    )

    dataset = _dataset_selector(
        key=(
            "product01_admin_hash_dataset"
        )
    )

    if dataset is not None:
        st.markdown(
            "#### Dataset"
        )

        st.json(
            {
                "dataset_id": (
                    dataset.get(
                        "dataset_id"
                    )
                ),
                "source_sha256": (
                    dataset.get(
                        "source_sha256"
                    )
                ),
            },
            expanded=False,
        )

    research = _research_selector(
        key=(
            "product01_admin_hash_research"
        )
    )

    if research is None:
        return

    fields = {
        key: value
        for key, value
        in research.items()
        if (
            "sha256"
            in str(
                key
            ).lower()
            or "hash"
            in str(
                key
            ).lower()
        )
        and value is not None
    }

    st.markdown(
        "#### Research"
    )

    if fields:
        st.json(
            fields,
            expanded=False,
        )

    else:
        st.info(
            (
                "Nenhum hash exposto no registro "
                "atual desta Research."
            )
        )


def _render_runtime() -> None:
    st.subheader(
        "Runtime"
    )

    rows = _researches()

    if not rows:
        st.info(
            "Nenhuma execução registrada."
        )
        return

    visible = []

    for row in rows:
        visible.append(
            {
                "Research ID": (
                    row.get(
                        "research_id"
                    )
                ),
                "Status": (
                    row.get(
                        "status"
                    )
                ),
                "Etapa": (
                    row.get(
                        "current_stage"
                    )
                ),
                "Criada": (
                    row.get(
                        "created_at"
                    )
                ),
                "Iniciada": (
                    row.get(
                        "started_at"
                    )
                ),
                "Finalizada": (
                    row.get(
                        "completed_at"
                    )
                    or row.get(
                        "failed_at"
                    )
                ),
                "Duração (s)": (
                    row.get(
                        "duration_seconds"
                    )
                ),
                "Unidades": (
                    row.get(
                        "execution_units_total"
                    )
                ),
                "Batches": (
                    row.get(
                        "batches_total"
                    )
                ),
            }
        )

    st.dataframe(
        visible,
        use_container_width=True,
        hide_index=True,
    )


def _render_manifest() -> None:
    st.subheader(
        "Manifest"
    )

    dataset = _dataset_selector(
        key=(
            "product01_admin_manifest_dataset"
        )
    )

    if dataset is not None:
        dataset_id = str(
            dataset.get(
                "dataset_id"
            )
            or ""
        )

        if dataset_id:
            path = (
                DATA_ROOT
                / "datasets"
                / dataset_id
                / "dataset_manifest.json"
            )

            manifest = _read_json(
                path
            )

            st.markdown(
                "#### Dataset Manifest"
            )

            if manifest:
                st.json(
                    manifest,
                    expanded=False,
                )

            else:
                st.info(
                    (
                        "Manifest canônico não "
                        "disponível para este Dataset."
                    )
                )

    research = _research_selector(
        key=(
            "product01_admin_manifest_research"
        )
    )

    if research is None:
        return

    research_id = _research_id(
        research
    )

    st.markdown(
        "#### Research Manifest"
    )

    try:
        manifest = (
            load_research_manifest(
                research_id
            )
        )

    except Exception as exc:
        st.info(
            "Manifest da Research indisponível."
        )

        st.caption(
            str(
                exc
            )
        )

        return

    st.json(
        manifest,
        expanded=False,
    )


def _render_registry() -> None:
    st.subheader(
        "Registry"
    )

    registry_paths = [
        (
            DATA_ROOT
            / "research"
            / "experiment_registry.parquet"
        ),
        (
            DATA_ROOT
            / "research"
            / "constraint_stage14_controlled_registry.parquet"
        ),
    ]

    names = [
        path.name
        for path in registry_paths
        if path.exists()
    ]

    if not names:
        st.info(
            "Nenhum Registry disponível."
        )
        return

    selected = st.selectbox(
        "Registry",
        options=names,
        key=(
            "product01_admin_registry"
        ),
    )

    path = next(
        path
        for path in registry_paths
        if path.name == selected
    )

    frame = _read_parquet(
        path
    )

    if frame.is_empty():
        st.info(
            "Registry sem registros disponíveis."
        )
        return

    st.metric(
        "Registros",
        frame.height,
    )

    st.dataframe(
        frame.to_pandas(),
        use_container_width=True,
        hide_index=True,
    )


def _render_logs() -> None:
    st.subheader(
        "Logs"
    )

    st.caption(
        (
            "Eventos de erro e execução já "
            "persistidos no workspace."
        )
    )

    rows = _researches()

    events = []

    for row in rows:
        if (
            row.get(
                "error_type"
            )
            or row.get(
                "error_message"
            )
            or str(
                row.get(
                    "status"
                )
                or ""
            ).upper()
            == "FAILED"
        ):
            events.append(
                {
                    "Research ID": (
                        row.get(
                            "research_id"
                        )
                    ),
                    "Status": (
                        row.get(
                            "status"
                        )
                    ),
                    "Falhou em": (
                        row.get(
                            "failed_at"
                        )
                    ),
                    "Tipo": (
                        row.get(
                            "error_type"
                        )
                    ),
                    "Mensagem": (
                        row.get(
                            "error_message"
                        )
                    ),
                }
            )

    if not events:
        st.info(
            "Nenhum erro registrado."
        )
        return

    st.dataframe(
        events,
        use_container_width=True,
        hide_index=True,
    )


def _render_versioning() -> None:
    st.subheader(
        "Versionamento"
    )

    versions: dict[str, Any] = {}

    try:
        from operar_range.ingest import (
            DATASET_VERSION,
            INGEST_VERSION,
            NORMALIZATION_VERSION,
        )

        versions[
            "Dataset"
        ] = DATASET_VERSION

        versions[
            "Ingest"
        ] = INGEST_VERSION

        versions[
            "Normalization"
        ] = NORMALIZATION_VERSION

    except Exception:
        pass

    try:
        from operar_range.scanner import (
            MOTOR_VERSION,
        )

        versions[
            "Motor"
        ] = MOTOR_VERSION

    except Exception:
        pass

    try:
        from operar_range.research_engine import (
            RULES_VERSION,
        )

        versions[
            "Rules"
        ] = RULES_VERSION

    except Exception:
        pass

    try:
        from operar_range.experiment_registry import (
            REGISTRY_VERSION,
        )

        versions[
            "Registry"
        ] = REGISTRY_VERSION

    except Exception:
        pass

    try:
        from operar_range.constraint_engine import (
            ENGINE_VERSION as CONSTRAINT_ENGINE_VERSION,
        )

        versions[
            "Constraint Engine"
        ] = CONSTRAINT_ENGINE_VERSION

    except Exception:
        pass

    try:
        from operar_range.experiment_generator import (
            GENERATOR_VERSION,
        )

        versions[
            "Experiment Generator"
        ] = GENERATOR_VERSION

    except Exception:
        pass

    try:
        from operar_range.ranking_engine import (
            RANKING_ENGINE_VERSION,
        )

        versions[
            "Ranking Engine"
        ] = RANKING_ENGINE_VERSION

    except Exception:
        pass

    if versions:
        st.dataframe(
            [
                {
                    "Componente": key,
                    "Versão": value,
                }
                for key, value
                in versions.items()
            ],
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            (
                "Nenhuma versão técnica pôde "
                "ser resolvida."
            )
        )

    st.divider()

    rows = _researches()

    workspace_versions = sorted(
        {
            str(
                row.get(
                    "workspace_version"
                )
            )
            for row in rows
            if row.get(
                "workspace_version"
            )
        }
    )

    if workspace_versions:
        st.caption(
            (
                "Workspace versions registradas: "
                + ", ".join(
                    workspace_versions
                )
            )
        )


def _render_audit() -> None:
    st.subheader(
        "Auditoria"
    )

    rows = _researches()

    completed = [
        row
        for row in rows
        if str(
            row.get(
                "status"
            )
            or ""
        ).upper()
        == "COMPLETED"
    ]

    failed = [
        row
        for row in rows
        if str(
            row.get(
                "status"
            )
            or ""
        ).upper()
        == "FAILED"
    ]

    lineage_ok = [
        row
        for row in rows
        if row.get(
            "lineage_match"
        )
        is True
    ]

    repeated = [
        row
        for row in rows
        if row.get(
            "quantitative_execution_repeated"
        )
        is True
    ]

    c1, c2, c3, c4 = (
        st.columns(
            4
        )
    )

    with c1:
        st.metric(
            "Researches",
            len(
                rows
            ),
        )

    with c2:
        st.metric(
            "Concluídas",
            len(
                completed
            ),
        )

    with c3:
        st.metric(
            "Falhas",
            len(
                failed
            ),
        )

    with c4:
        st.metric(
            "Lineage match",
            len(
                lineage_ok
            ),
        )

    st.caption(
        (
            "Execuções quantitativas marcadas "
            "como repetidas: "
            + str(
                len(
                    repeated
                )
            )
        )
    )

    if not rows:
        return

    audit_rows = []

    for row in rows:
        audit_rows.append(
            {
                "Research ID": (
                    row.get(
                        "research_id"
                    )
                ),
                "Status": (
                    row.get(
                        "status"
                    )
                ),
                "Lineage match": (
                    row.get(
                        "lineage_match"
                    )
                ),
                "Execução repetida": (
                    row.get(
                        "quantitative_execution_repeated"
                    )
                ),
                "Experimentos gerados": (
                    row.get(
                        "experiments_generated"
                    )
                ),
                "Experimentos válidos": (
                    row.get(
                        "experiments_valid"
                    )
                ),
                "Experimentos inválidos": (
                    row.get(
                        "experiments_invalid"
                    )
                ),
                "Erro": (
                    row.get(
                        "error_type"
                    )
                ),
            }
        )

    st.dataframe(
        audit_rows,
        use_container_width=True,
        hide_index=True,
    )


ADMIN_SECTIONS = (
    "Dados",
    "Sistema",
    "Avançado",
)

ADMIN_DATA_TABS = (
    "Importar Dataset",
    "Datasets",
)

ADMIN_ADVANCED_TABS = (
    "Hashes",
    "Runtime",
    "Registry",
    "Manifest",
    "Logs",
    "Versionamento",
)


def render() -> None:
    page_title(
        "Administração",
        (
            "Gerenciamento de dados e "
            "estado administrativo da plataforma."
        ),
    )

    st.caption(
        (
            "Área administrativa do Operar Range. "
            "Recursos técnicos permanecem "
            "separados em Avançado."
        )
    )

    sections = st.tabs(
        list(
            ADMIN_SECTIONS
        )
    )

    with sections[0]:
        st.subheader(
            "Dados"
        )

        data_tabs = st.tabs(
            list(
                ADMIN_DATA_TABS
            )
        )

        with data_tabs[0]:
            _render_dataset_import()

        with data_tabs[1]:
            _render_dataset_catalog()

    with sections[1]:
        st.subheader(
            "Sistema"
        )

        st.caption(
            (
                "Estado e auditoria da "
                "operação da plataforma."
            )
        )

        _render_audit()

    with sections[2]:
        st.subheader(
            "Avançado"
        )

        st.warning(
            (
                "Informações técnicas para "
                "auditoria e diagnóstico."
            )
        )

        advanced_tabs = st.tabs(
            list(
                ADMIN_ADVANCED_TABS
            )
        )

        with advanced_tabs[0]:
            _render_hashes()

        with advanced_tabs[1]:
            _render_runtime()

        with advanced_tabs[2]:
            _render_registry()

        with advanced_tabs[3]:
            _render_manifest()

        with advanced_tabs[4]:
            _render_logs()

        with advanced_tabs[5]:
            _render_versioning()
