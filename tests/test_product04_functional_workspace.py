from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative: str) -> str:
    return (
        ROOT / relative
    ).read_text(
        encoding="utf-8"
    )


def test_product04_research_identity():
    source = _source(
        "app/pages/new_research.py"
    )

    for text in (
        "Nome da pesquisa",
        "Dataset",
        "Modelo",
        "Data inicial",
        "Data final",
        "Descrição opcional",
    ):
        assert text in source


def test_product04_only_official_initial_model():
    model = _source(
        "src/operar_range/"
        "quantitative_models.py"
    )

    assert (
        "US OPEN BREAKOUT V1"
        in model
    )


def test_product04_trade1_parameters():
    source = _source(
        "app/pages/new_research.py"
    )

    for text in (
        "Stops a testar",
        "Pontos da Parcial 1",
        "% da Parcial 1",
        "Ativar Break-even",
        "Ativar Target final",
        "Ativar Runner",
    ):
        assert text in source


def test_product04_trade2_parameters():
    source = _source(
        "app/pages/new_research.py"
    )

    for text in (
        "Trade 2",
        "Ligado",
        "Desligado",
        "Herdar gestão do Trade 1",
        "Personalizar Trade 2",
        "oficial de elegibilidade ",
        "após STOP.",
    ):
        assert text in source


def test_product04_stage28_grid():
    source = _source(
        "app/pages/new_research.py"
    )

    for text in (
        "Targets",
        "Stops",
        "Trade 2 Targets",
        "Trade 2 Stops",
        "Lista",
        "Range",
        "target_step",
        "stop_step",
    ):
        assert text in source


def test_product04_estimate():
    source = _source(
        "app/pages/new_research.py"
    )

    for text in (
        "Pregões",
        "Experimentos estimados",
        "Execution Units",
        "Targets",
        "Stops",
        "Configurações estimadas",
        "Path rows estimadas",
        "Tempo estimado",
        "sem baseline ",
        "Nenhuma duração é inventada.",
    ):
        assert text in source


def test_product04_create_and_execute():
    source = _source(
        "app/pages/new_research.py"
    )

    assert (
        "CRIAR E EXECUTAR PESQUISA"
        in source
    )
    assert (
        "create_research_stage22("
        in source
    )
    assert (
        "execute_research("
        in source
    )
    assert (
        "ABRIR PESQUISA"
        in source
    )


def test_product04_progress_states():
    ui = _source(
        "app/pages/new_research.py"
    )
    backend = _source(
        "src/operar_range/"
        "research_workspace.py"
    )

    for text in (
        "Preparando pesquisa",
        "Gerando experimentos",
        "Validando configurações",
        "Executando pesquisa",
        "Calculando Analytics",
        "Analisando trajetórias",
        "Preparando respostas",
        "Gerando Rankings",
        "Concluída",
    ):
        assert text in ui

    assert (
        '"PATH_ANALYSIS"'
        in backend
    )
    assert (
        '"PATH_AGGREGATION"'
        in backend
    )


def test_product04_completed_requires_questions_artifacts():
    source = _source(
        "src/operar_range/"
        "research_workspace.py"
    )

    for text in (
        "QUESTION_ARTIFACT_FILENAMES",
        "path_analysis.parquet",
        "path_target_analytics.parquet",
        "path_stop_analytics.parquet",
        "path_target_stop_matrix.parquet",
        "path_trade2_analytics.parquet",
        "research_question_artifact_status",
        "require_research_question_artifacts",
        "question_artifacts_ready",
        "analytical_ready",
    ):
        assert text in source

    execute_start = source.index(
        "def execute_research("
    )

    result_start = source.index(
        "def research_result_paths(",
        execute_start,
    )

    block = source[
        execute_start:result_start
    ]

    assert (
        block.index(
            "require_research_question_artifacts"
        )
        < block.index(
            'status="COMPLETED"'
        )
    )


def test_product04_no_new_quant_engine():
    forbidden = (
        "product04_engine.py",
        "optimization_engine.py",
        "monte_carlo_engine.py",
        "ai_engine.py",
    )

    engine_root = (
        ROOT
        / "src"
        / "operar_range"
    )

    for name in forbidden:
        assert not (
            engine_root / name
        ).exists()
