from __future__ import annotations

from pathlib import Path

from operar_range.quantitative_models import (
    default_quantitative_model,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


def test_trade2_is_active_in_official_model():
    model = default_quantitative_model()

    components = {
        row["name"]: row["status"]
        for row in model[
            "components"
        ]
    }

    assert (
        components["Trade 1"]
        == "ACTIVE"
    )

    assert (
        components["Trade 2"]
        == "ACTIVE"
    )


def test_trade2_is_not_an_independent_model():
    model = default_quantitative_model()

    assert (
        model["name"]
        == "US OPEN BREAKOUT V1"
    )

    assert (
        model["strategy"]
        == "TRADE_1"
    )

    assert (
        "Trade 2"
        in {
            row["name"]
            for row in model[
                "components"
            ]
        }
    )


def test_workspace_exposes_trade_lifecycle_results():
    source = (
        PROJECT_ROOT
        / "app/pages/experiments.py"
    ).read_text(
        encoding="utf-8"
    )

    required = [
        "Trade Lifecycle",
        "Trade 1",
        "Trade 2 elegível",
        "Trade 2 ocorreu",
        "Trade 2",
        "Resultado consolidado",
        "trade1_result_points",
        "trade2_result_points",
        "consolidated_result_points",
    ]

    for value in required:
        assert value in source


def test_experiment_detail_exposes_session_results():
    source = (
        PROJECT_ROOT
        / "app/data_access.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        '"results": []'
        in source
    )

    assert (
        "results = experiment_results()"
        in source
    )

    assert (
        'orient="records"'
        in source
    )


def test_workspace_preserves_legacy_trade1_fallback():
    source = (
        PROJECT_ROOT
        / "app/pages/experiments.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        '"trade1_result_points"'
        in source
    )

    assert (
        '"total_weighted_points"'
        in source
    )

    assert (
        "trade1_result = row.get"
        in source
    )


def test_workspace_does_not_replace_legacy_metric():
    source = (
        PROJECT_ROOT
        / "app/pages/experiments.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        '"Total weighted points"'
        in source
    )

    assert (
        '"total_weighted_points"'
        in source
    )


def test_research_result_contract_contains_lifecycle_fields():
    source = (
        PROJECT_ROOT
        / "src/operar_range/batch_execution.py"
    ).read_text(
        encoding="utf-8"
    )

    required = [
        '"trade1_result_points"',
        '"trade2_eligible"',
        '"trade2_occurred"',
        '"trade2_executed"',
        '"trade2_result_points"',
        '"consolidated_result_points"',
        '"lifecycle_version"',
    ]

    for value in required:
        assert value in source


def test_total_weighted_points_is_explicitly_preserved():
    source = (
        PROJECT_ROOT
        / "src/operar_range/batch_execution.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        'base[\n                "total_weighted_points"\n            ] = trade1_result_points'
        in source
    )

    assert (
        'base[\n                "trade1_result_points"\n            ] = trade1_result_points'
        in source
    )


def test_no_trade2_specific_ranking_was_added():
    ranking_source = (
        PROJECT_ROOT
        / "src/operar_range/ranking_engine.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "trade2_result_points"
        not in ranking_source
    )

    assert (
        "consolidated_result_points"
        not in ranking_source
    )


def test_no_full_lifecycle_analytics_engine_was_added():
    forbidden = [
        "trade2_analytics.py",
        "lifecycle_analytics.py",
        "full_lifecycle_analytics.py",
    ]

    for filename in forbidden:
        assert not (
            PROJECT_ROOT
            / "src/operar_range"
            / filename
        ).exists()
