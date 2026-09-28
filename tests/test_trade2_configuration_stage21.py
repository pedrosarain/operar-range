from __future__ import annotations

from dataclasses import asdict

import pytest

from operar_range.management import (
    ManagementConfig,
)
from operar_range.trade2_configuration import (
    CONFIGURE,
    DISABLE,
    INHERIT,
    inherit_all_overrides,
    resolve_trade2_management_config,
    trade2_has_explicit_overrides,
    trade2_lineage,
    trade2_override_sha256,
)


def _trade1() -> ManagementConfig:
    return ManagementConfig(
        stop_points=170.0,
        partial_1_points=125.0,
        partial_1_pct=70.0,
        partial_2_points=None,
        partial_2_pct=None,
        partial_3_points=None,
        partial_3_pct=None,
        break_even_enabled=True,
        break_even_after_partial=1,
        final_target_points=400.0,
        position_size=100.0,
        runner_enabled=True,
        runner_pct=30.0,
        runner_exit_rule="CANDLE_BREAK_M5",
    )


def test_inherit_all_equals_trade1():
    trade1 = _trade1()

    effective = (
        resolve_trade2_management_config(
            trade1_config=trade1,
            overrides=None,
        )
    )

    assert effective == trade1
    assert (
        trade2_has_explicit_overrides(
            None
        )
        is False
    )


def test_override_only_stop():
    trade1 = _trade1()

    effective = (
        resolve_trade2_management_config(
            trade1_config=trade1,
            overrides={
                "trade2_stop_mode": (
                    CONFIGURE
                ),
                "trade2_stop_points": 120.0,
            },
        )
    )

    assert effective.stop_points == 120.0
    assert effective.partial_1_points == 125.0
    assert effective.partial_1_pct == 70.0
    assert effective.break_even_enabled is True
    assert effective.runner_enabled is True
    assert effective.final_target_points == 400.0


def test_override_only_partial():
    effective = (
        resolve_trade2_management_config(
            trade1_config=_trade1(),
            overrides={
                "trade2_partial_1_mode": (
                    CONFIGURE
                ),
                "trade2_partial_1_points": 100.0,
                "trade2_partial_1_pct": 40.0,
            },
        )
    )

    assert effective.stop_points == 170.0
    assert effective.partial_1_points == 100.0
    assert effective.partial_1_pct == 40.0
    assert effective.runner_enabled is True


def test_override_only_break_even():
    effective = (
        resolve_trade2_management_config(
            trade1_config=_trade1(),
            overrides={
                "trade2_break_even_mode": (
                    CONFIGURE
                ),
                "trade2_break_even_after_partial": 1,
            },
        )
    )

    assert effective.break_even_enabled is True
    assert effective.break_even_after_partial == 1
    assert effective.stop_points == 170.0


def test_disable_inherited_break_even():
    effective = (
        resolve_trade2_management_config(
            trade1_config=_trade1(),
            overrides={
                "trade2_break_even_mode": (
                    DISABLE
                ),
            },
        )
    )

    assert effective.break_even_enabled is False
    assert effective.break_even_after_partial is None


def test_override_only_runner():
    effective = (
        resolve_trade2_management_config(
            trade1_config=_trade1(),
            overrides={
                "trade2_runner_mode": (
                    CONFIGURE
                ),
                "trade2_runner_pct": 20.0,
                "trade2_runner_rule": (
                    "CANDLE_BREAK_M5"
                ),
            },
        )
    )

    assert effective.runner_enabled is True
    assert effective.runner_pct == 20.0
    assert (
        effective.runner_exit_rule
        == "CANDLE_BREAK_M5"
    )


def test_explicit_disable_inherited_runner():
    effective = (
        resolve_trade2_management_config(
            trade1_config=_trade1(),
            overrides={
                "trade2_runner_mode": (
                    DISABLE
                ),
            },
        )
    )

    assert effective.runner_enabled is False
    assert effective.runner_pct is None
    assert effective.runner_exit_rule is None


def test_explicit_remove_inherited_partial():
    trade1 = _trade1()

    # BE também precisa ser removido porque,
    # na configuração efetiva, ele referencia
    # a partial 1 que está sendo removida.
    effective = (
        resolve_trade2_management_config(
            trade1_config=trade1,
            overrides={
                "trade2_partial_1_mode": (
                    DISABLE
                ),
                "trade2_break_even_mode": (
                    DISABLE
                ),
            },
        )
    )

    assert effective.partial_1_points is None
    assert effective.partial_1_pct is None
    assert effective.break_even_enabled is False


def test_invalid_effective_config_is_rejected():
    # Remover a partial herdada sem remover
    # o BE herdado gera configuração efetiva
    # estruturalmente inválida.
    with pytest.raises(
        ValueError
    ):
        resolve_trade2_management_config(
            trade1_config=_trade1(),
            overrides={
                "trade2_partial_1_mode": (
                    DISABLE
                ),
            },
        )


def test_multiple_overrides():
    effective = (
        resolve_trade2_management_config(
            trade1_config=_trade1(),
            overrides={
                "trade2_stop_mode": CONFIGURE,
                "trade2_stop_points": 120.0,

                "trade2_partial_1_mode": (
                    CONFIGURE
                ),
                "trade2_partial_1_points": 100.0,
                "trade2_partial_1_pct": 50.0,

                "trade2_break_even_mode": (
                    DISABLE
                ),

                "trade2_runner_mode": DISABLE,

                "trade2_final_target_mode": (
                    CONFIGURE
                ),
                "trade2_final_target_points": 200.0,
            },
        )
    )

    assert effective.stop_points == 120.0
    assert effective.partial_1_points == 100.0
    assert effective.partial_1_pct == 50.0
    assert effective.break_even_enabled is False
    assert effective.runner_enabled is False
    assert effective.final_target_points == 200.0


def test_inherit_is_distinct_from_disable():
    inherited = inherit_all_overrides()

    assert (
        inherited[
            "trade2_runner_mode"
        ]
        == INHERIT
    )

    disabled = dict(
        inherited
    )

    disabled[
        "trade2_runner_mode"
    ] = DISABLE

    assert (
        trade2_override_sha256(
            inherited
        )
        != trade2_override_sha256(
            disabled
        )
    )


def test_different_stop_overrides_have_different_hashes():
    first = {
        "trade2_stop_mode": CONFIGURE,
        "trade2_stop_points": 120.0,
    }

    second = {
        "trade2_stop_mode": CONFIGURE,
        "trade2_stop_points": 125.0,
    }

    assert (
        trade2_override_sha256(
            first
        )
        != trade2_override_sha256(
            second
        )
    )


def test_lineage_reconstructs_raw_and_effective_configuration():
    trade1 = _trade1()

    overrides = {
        "trade2_stop_mode": CONFIGURE,
        "trade2_stop_points": 120.0,
        "trade2_runner_mode": DISABLE,
    }

    lineage = trade2_lineage(
        trade1_config=trade1,
        overrides=overrides,
    )

    assert (
        lineage[
            "trade1_configuration"
        ]
        == asdict(
            trade1
        )
    )

    assert (
        lineage[
            "trade2_overrides"
        ][
            "trade2_stop_mode"
        ]
        == CONFIGURE
    )

    assert (
        lineage[
            "trade2_effective_configuration"
        ][
            "stop_points"
        ]
        == 120.0
    )

    assert (
        lineage[
            "trade2_effective_configuration"
        ][
            "runner_enabled"
        ]
        is False
    )

    assert lineage[
        "trade1_config_sha256"
    ]

    assert lineage[
        "trade2_override_sha256"
    ]

    assert lineage[
        "trade2_effective_config_sha256"
    ]


def test_inherit_lineage_marks_inherits_all():
    lineage = trade2_lineage(
        trade1_config=_trade1(),
        overrides=None,
    )

    assert (
        lineage[
            "trade2_inherits_all"
        ]
        is True
    )

    assert (
        lineage[
            "trade1_configuration"
        ]
        == lineage[
            "trade2_effective_configuration"
        ]
    )


def test_resolution_is_deterministic():
    overrides = {
        "trade2_stop_mode": CONFIGURE,
        "trade2_stop_points": 120.0,
        "trade2_runner_mode": DISABLE,
    }

    first = trade2_lineage(
        trade1_config=_trade1(),
        overrides=overrides,
    )

    second = trade2_lineage(
        trade1_config=_trade1(),
        overrides=overrides,
    )

    assert first == second


from operar_range.trade2_configuration import (
    TRADE2_MANAGEMENT_CUSTOM,
    TRADE2_MANAGEMENT_INHERIT,
    trade2_control_from_row,
    validate_trade2_control,
)


def test_trade2_control_legacy_defaults_to_on_inherit():
    control = trade2_control_from_row(
        {}
    )

    assert (
        control[
            "trade2_enabled"
        ]
        is True
    )

    assert (
        control[
            "trade2_management_mode"
        ]
        == TRADE2_MANAGEMENT_INHERIT
    )

    assert (
        control[
            "legacy_semantics"
        ]
        is True
    )


def test_trade2_explicit_off_is_valid_without_overrides():
    row = {
        "trade2_enabled": False,
        "trade2_management_mode": (
            TRADE2_MANAGEMENT_INHERIT
        ),
    }

    validate_trade2_control(
        row
    )

    control = trade2_control_from_row(
        row
    )

    assert (
        control[
            "trade2_enabled"
        ]
        is False
    )

    assert (
        control[
            "legacy_semantics"
        ]
        is False
    )


def test_trade2_on_inherit_is_valid():
    row = {
        "trade2_enabled": True,
        "trade2_management_mode": (
            TRADE2_MANAGEMENT_INHERIT
        ),
    }

    validate_trade2_control(
        row
    )

    control = trade2_control_from_row(
        row
    )

    assert (
        control[
            "trade2_enabled"
        ]
        is True
    )

    assert (
        control[
            "trade2_management_mode"
        ]
        == TRADE2_MANAGEMENT_INHERIT
    )


def test_trade2_on_custom_with_override_is_valid():
    row = {
        "trade2_enabled": True,
        "trade2_management_mode": (
            TRADE2_MANAGEMENT_CUSTOM
        ),
        "trade2_stop_mode": CONFIGURE,
        "trade2_stop_points": 120.0,
    }

    validate_trade2_control(
        row
    )


def test_trade2_off_with_active_override_is_invalid():
    row = {
        "trade2_enabled": False,
        "trade2_management_mode": (
            TRADE2_MANAGEMENT_INHERIT
        ),
        "trade2_stop_mode": CONFIGURE,
        "trade2_stop_points": 120.0,
    }

    with pytest.raises(
        ValueError,
        match=(
            "Trade 2 is disabled"
        ),
    ):
        validate_trade2_control(
            row
        )


def test_trade2_inherit_with_active_override_is_invalid():
    row = {
        "trade2_enabled": True,
        "trade2_management_mode": (
            TRADE2_MANAGEMENT_INHERIT
        ),
        "trade2_runner_mode": DISABLE,
    }

    with pytest.raises(
        ValueError,
        match=(
            "management mode is INHERIT"
        ),
    ):
        validate_trade2_control(
            row
        )


def test_trade2_custom_without_override_is_invalid():
    row = {
        "trade2_enabled": True,
        "trade2_management_mode": (
            TRADE2_MANAGEMENT_CUSTOM
        ),
    }

    with pytest.raises(
        ValueError,
        match=(
            "management mode is CUSTOM"
        ),
    ):
        validate_trade2_control(
            row
        )


def test_trade2_control_is_deterministic():
    row = {
        "trade2_enabled": True,
        "trade2_management_mode": (
            TRADE2_MANAGEMENT_CUSTOM
        ),
        "trade2_stop_mode": CONFIGURE,
        "trade2_stop_points": 120.0,
    }

    first = trade2_control_from_row(
        row
    )

    second = trade2_control_from_row(
        row
    )

    assert first == second
