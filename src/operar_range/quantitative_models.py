from __future__ import annotations

from copy import deepcopy
from typing import Any


US_OPEN_BREAKOUT_V1_ID = (
    "US_OPEN_BREAKOUT_V1"
)


US_OPEN_BREAKOUT_V1 = {
    "model_id": (
        US_OPEN_BREAKOUT_V1_ID
    ),
    "name": (
        "US OPEN BREAKOUT V1"
    ),
    "version": 1,
    "status": "ACTIVE",
    "hypothesis": (
        "Rompimento do candle "
        "imediatamente anterior à "
        "abertura de Nova York."
    ),
    "strategy": "TRADE_1",
    "components": [
        {
            "name": "Trade 1",
            "status": "ACTIVE",
        },
        {
            "name": "Gestão",
            "status": "ACTIVE",
        },
        {
            "name": "Runner",
            "status": "ACTIVE",
        },
        {
            "name": "Analytics",
            "status": "ACTIVE",
        },
        {
            "name": "Ranking",
            "status": "ACTIVE",
        },
        {
            "name": "Trade 2",
            "status": "ACTIVE",
        },
    ],
    #
    # Estes campos continuam sendo
    # utilizados internamente pelos
    # motores existentes. Eles não são
    # parâmetros editáveis do pesquisador.
    #
    "internal": {
        "family": (
            "US_OPEN_BREAKOUT_V1"
        ),
        "generation": 1,
        "rules_version": (
            "ADR-004+STAGE10"
        ),
        "batch_size": 1000,
    },
}


def list_quantitative_models() -> list[
    dict[str, Any]
]:
    return [
        deepcopy(
            US_OPEN_BREAKOUT_V1
        )
    ]


def get_quantitative_model(
    model_id: str,
) -> dict[str, Any]:
    if (
        model_id
        != US_OPEN_BREAKOUT_V1_ID
    ):
        raise KeyError(
            (
                "Unknown quantitative "
                f"model: {model_id}"
            )
        )

    return deepcopy(
        US_OPEN_BREAKOUT_V1
    )


def default_quantitative_model() -> dict[
    str,
    Any,
]:
    return get_quantitative_model(
        US_OPEN_BREAKOUT_V1_ID
    )
