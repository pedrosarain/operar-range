from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

if str(
    PROJECT_ROOT
) not in sys.path:
    sys.path.insert(
        0,
        str(
            PROJECT_ROOT
        ),
    )


from app import main
from app.pages import research_comparison


def test_research_comparison_page_registered():
    assert (
        "Research Comparison"
        in main.PAGES
    )


def test_research_comparison_page_uses_expected_renderer():
    assert (
        main.PAGES[
            "Research Comparison"
        ]
        is research_comparison.render
    )


def test_research_comparison_has_two_modes():
    source = (
        Path(
            research_comparison.__file__
        )
        .read_text(
            encoding="utf-8"
        )
    )

    assert (
        "Comparar Pesquisas"
        in source
    )

    assert (
        "Comparar Experimentos"
        in source
    )


def test_workspace_page_uses_comparison_engine():
    source = (
        Path(
            research_comparison.__file__
        )
        .read_text(
            encoding="utf-8"
        )
    )

    assert (
        "compare_researches"
        in source
    )

    assert (
        "compare_experiments"
        in source
    )


def test_workspace_does_not_call_backtest_engine():
    source = (
        Path(
            research_comparison.__file__
        )
        .read_text(
            encoding="utf-8"
        )
        .lower()
    )

    forbidden = (
        "execute_batch(",
        "run_analytics(",
        "run_trade_lifecycle_analytics(",
        "generate_experiment_database(",
    )

    for token in forbidden:
        assert token not in source
