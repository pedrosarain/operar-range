from __future__ import annotations

import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

SRC_ROOT = (
    PROJECT_ROOT
    / "src"
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(SRC_ROOT),
    )


from app import main
from app.pages import query


def test_query_page_registered():
    assert (
        "Query"
        in main.PAGES
    )

    assert (
        main.PAGES[
            "Query"
        ]
        is query.render
    )


def test_query_builder_minimal():
    built = query._build_query(
        research_id="RES-TEST",
        experiment_id="",
        exact_date_enabled=False,
        exact_date=date(
            2026,
            8,
            18,
        ),
        year="",
        month="QUALQUER",
        trade1_outcome=None,
        trade2_enabled=None,
        trade2_eligible=None,
        trade2_executed=None,
        trade2_winner=None,
        trade2_loser=None,
        trade2_breakeven=None,
        direction=None,
        result_sign=None,
        runner_occurred=None,
    )

    assert (
        built.research_id
        == "RES-TEST"
    )

    assert (
        built.experiment_id
        is None
    )

    assert (
        built.date
        is None
    )

    assert (
        built.year
        is None
    )

    assert (
        built.month
        is None
    )


def test_query_builder_complete():
    built = query._build_query(
        research_id="RES-TEST",
        experiment_id=(
            "EXP-000047"
        ),
        exact_date_enabled=True,
        exact_date=date(
            2026,
            8,
            18,
        ),
        year="2026",
        month="8",
        trade1_outcome="LOSS",
        trade2_enabled=True,
        trade2_eligible=True,
        trade2_executed=True,
        trade2_winner=False,
        trade2_loser=True,
        trade2_breakeven=False,
        direction="LONG",
        result_sign="NEGATIVE",
        runner_occurred=False,
    )

    assert (
        built.research_id
        == "RES-TEST"
    )

    assert (
        built.experiment_id
        == "EXP-000047"
    )

    assert (
        built.date
        == "2026-08-18"
    )

    assert (
        built.year
        == 2026
    )

    assert (
        built.month
        == 8
    )

    assert (
        built.trade1_outcome
        == "LOSS"
    )

    assert (
        built.trade2_enabled
        is True
    )

    assert (
        built.trade2_eligible
        is True
    )

    assert (
        built.trade2_executed
        is True
    )

    assert (
        built.trade2_winner
        is False
    )

    assert (
        built.trade2_loser
        is True
    )

    assert (
        built.trade2_breakeven
        is False
    )

    assert (
        built.direction
        == "LONG"
    )

    assert (
        built.result_sign
        == "NEGATIVE"
    )

    assert (
        built.runner_occurred
        is False
    )


def test_optional_text():
    assert (
        query._optional_text(
            ""
        )
        is None
    )

    assert (
        query._optional_text(
            "   "
        )
        is None
    )

    assert (
        query._optional_text(
            " EXP-000047 "
        )
        == "EXP-000047"
    )


def test_optional_int():
    assert (
        query._optional_int(
            ""
        )
        is None
    )

    assert (
        query._optional_int(
            "  "
        )
        is None
    )

    assert (
        query._optional_int(
            "2026"
        )
        == 2026
    )
