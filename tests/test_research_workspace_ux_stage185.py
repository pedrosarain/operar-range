from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


APP_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


def _app_test(
    relative_path: str,
) -> AppTest:
    return AppTest.from_file(
        str(
            APP_ROOT
            / relative_path
        )
    )


def _texts(
    app: AppTest,
) -> str:
    values = []

    for element_type in (
        "markdown",
        "caption",
        "info",
        "success",
        "warning",
        "error",
        "subheader",
        "title",
    ):
        try:
            elements = getattr(
                app,
                element_type,
            )
        except Exception:
            continue

        for element in elements:
            try:
                values.append(
                    str(
                        element.value
                    )
                )
            except Exception:
                pass

    return "\n".join(
        values
    )


def test_new_research_page_loads():
    app = _app_test(
        "app/pages/new_research.py"
    )

    app.run(
        timeout=15
    )

    assert not app.exception


def test_new_research_uses_wizard_language():
    app = _app_test(
        "app/pages/new_research.py"
    )

    app.run(
        timeout=15
    )

    text = _texts(
        app
    )

    assert (
        "Nova Pesquisa"
        in text
    )

    assert (
        "US OPEN BREAKOUT V1"
        in text
        or any(
            (
                getattr(
                    widget,
                    "value",
                    None
                )
                == "US OPEN BREAKOUT V1"
            )
            for widget
            in app.text_input
        )
    )


def test_new_research_hides_internal_fields():
    source = (
        APP_ROOT
        / "app/pages/new_research.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        '"Family"'
        not in source
    )

    assert (
        '"Generation"'
        not in source
    )

    assert (
        '"Batch size"'
        not in source
    )


def test_new_research_model_explains_hypothesis():
    source = (
        APP_ROOT
        / "src/operar_range/quantitative_models.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "Rompimento do candle"
        in source
    )

    assert (
        "abertura de Nova York"
        in source
    )


def test_trade2_is_not_active():
    source = (
        APP_ROOT
        / "src/operar_range/quantitative_models.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        '"name": "Trade 2"'
        in source
    )

    assert (
        '"EM_DESENVOLVIMENTO"'
        in source
    )


def test_data_manager_page_loads():
    app = _app_test(
        "app/pages/data.py"
    )

    app.run(
        timeout=15
    )

    assert not app.exception


def test_data_manager_contains_dataset_language():
    source = (
        APP_ROOT
        / "app/pages/data.py"
    ).read_text(
        encoding="utf-8"
    )

    required = [
        "Datasets disponíveis",
        "Preparado para pesquisa?",
        "Normalization Version",
        "Ingest Version",
        "SHA-256",
        "Pregões",
        "Registros",
    ]

    for value in required:
        assert value in source


def test_researches_page_loads():
    app = _app_test(
        "app/pages/researches.py"
    )

    app.run(
        timeout=15
    )

    assert not app.exception


def test_research_history_uses_research_language():
    source = (
        APP_ROOT
        / "app/pages/researches.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "Histórico de pesquisas"
        in source
    )

    assert (
        "Pesquisa ativa"
        in source
    )

    assert (
        "Research History"
        not in source
    )


def test_nan_is_treated_in_research_history():
    source = (
        APP_ROOT
        / "app/pages/researches.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "math.isnan"
        in source
    )

    assert (
        "fillna"
        in source
    )


def test_research_errors_do_not_show_raw_exception_text():
    source = (
        APP_ROOT
        / "app/pages/researches.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "str(exc)"
        not in source
    )


def test_new_research_errors_do_not_show_traceback():
    source = (
        APP_ROOT
        / "app/pages/new_research.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "traceback"
        not in source.lower()
    )

    assert (
        "st.exception"
        not in source
    )


def test_empty_dataset_state_is_handled():
    source = (
        APP_ROOT
        / "app/pages/new_research.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "Nenhum dataset preparado"
        in source
    )


def test_research_summary_contains_required_fields():
    source = (
        APP_ROOT
        / "app/pages/new_research.py"
    ).read_text(
        encoding="utf-8"
    )

    required = [
        "Modelo",
        "Pregões",
        "Experimentos estimados",
        "Execution Units",
        "Batches",
        "Tempo estimado",
        "EXECUTAR PESQUISA",
    ]

    for value in required:
        assert value in source


def test_active_research_navigation_is_preserved():
    source = (
        APP_ROOT
        / "app/pages/researches.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        'st.session_state[\n            "active_research_id"\n        ] = research_id'
        in source
    )

    assert (
        'st.switch_page(\n            "main.py"\n        )'
        in source
    )


def test_completed_research_requires_results():
    source = (
        APP_ROOT
        / "app/pages/researches.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        '!= "COMPLETED"'
        in source
    )

    assert (
        '"metrics"'
        in source
    )

    assert (
        '"rankings"'
        in source
    )


def test_no_new_quantitative_engine_was_added():
    forbidden = [
        "trade2.py",
        "pattern_engine.py",
        "new_metric_engine.py",
    ]

    for filename in forbidden:
        assert not (
            APP_ROOT
            / "src/operar_range"
            / filename
        ).exists()
