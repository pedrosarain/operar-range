from __future__ import annotations

import pytest

from operar_range.quantitative_models import (
    US_OPEN_BREAKOUT_V1_ID,
    default_quantitative_model,
    get_quantitative_model,
    list_quantitative_models,
)


def test_only_one_model_exists_in_stage185():
    models = list_quantitative_models()

    assert len(models) == 1
    assert (
        models[0]["model_id"]
        == US_OPEN_BREAKOUT_V1_ID
    )


def test_official_model_name():
    model = default_quantitative_model()

    assert (
        model["name"]
        == "US OPEN BREAKOUT V1"
    )


def test_official_model_hypothesis():
    model = default_quantitative_model()

    assert (
        model["hypothesis"]
        == (
            "Rompimento do candle "
            "imediatamente anterior à "
            "abertura de Nova York."
        )
    )


def test_official_model_uses_trade1():
    model = default_quantitative_model()

    assert (
        model["strategy"]
        == "TRADE_1"
    )


def test_model_contains_required_components():
    model = default_quantitative_model()

    components = {
        row["name"]: row["status"]
        for row in model["components"]
    }

    assert (
        components["Trade 1"]
        == "ACTIVE"
    )

    assert (
        components["Gestão"]
        == "ACTIVE"
    )

    assert (
        components["Runner"]
        == "ACTIVE"
    )

    assert (
        components["Analytics"]
        == "ACTIVE"
    )

    assert (
        components["Ranking"]
        == "ACTIVE"
    )

    assert (
        components["Trade 2"]
        == "ACTIVE"
    )


def test_internal_fields_are_fixed():
    model = default_quantitative_model()

    internal = model["internal"]

    assert (
        internal["family"]
        == "US_OPEN_BREAKOUT_V1"
    )

    assert (
        internal["generation"]
        == 1
    )

    assert (
        internal["rules_version"]
        == "ADR-004+STAGE10"
    )

    assert (
        internal["batch_size"]
        == 1000
    )


def test_unknown_model_is_rejected():
    with pytest.raises(KeyError):
        get_quantitative_model(
            "UNKNOWN_MODEL"
        )


def test_model_copy_cannot_mutate_source():
    first = default_quantitative_model()

    first["name"] = "CHANGED"

    second = default_quantitative_model()

    assert (
        second["name"]
        == "US OPEN BREAKOUT V1"
    )
