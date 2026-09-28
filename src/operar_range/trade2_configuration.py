from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from operar_range.management import (
    ManagementConfig,
    validate_config,
)


TRADE2_CONFIG_VERSION = (
    "trade2-parametric-config-v1"
)

INHERIT = "INHERIT"
CONFIGURE = "CONFIGURE"
DISABLE = "DISABLE"

VALID_MODES = {
    INHERIT,
    CONFIGURE,
    DISABLE,
}


TRADE2_OVERRIDE_FIELDS = (
    "trade2_stop_mode",
    "trade2_stop_points",

    "trade2_partial_1_mode",
    "trade2_partial_1_points",
    "trade2_partial_1_pct",

    "trade2_partial_2_mode",
    "trade2_partial_2_points",
    "trade2_partial_2_pct",

    "trade2_partial_3_mode",
    "trade2_partial_3_points",
    "trade2_partial_3_pct",

    "trade2_break_even_mode",
    "trade2_break_even_after_partial",

    "trade2_runner_mode",
    "trade2_runner_pct",
    "trade2_runner_rule",

    "trade2_final_target_mode",
    "trade2_final_target_points",
)


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def inherit_all_overrides() -> dict[str, Any]:
    return {
        "trade2_stop_mode": INHERIT,
        "trade2_stop_points": None,

        "trade2_partial_1_mode": INHERIT,
        "trade2_partial_1_points": None,
        "trade2_partial_1_pct": None,

        "trade2_partial_2_mode": INHERIT,
        "trade2_partial_2_points": None,
        "trade2_partial_2_pct": None,

        "trade2_partial_3_mode": INHERIT,
        "trade2_partial_3_points": None,
        "trade2_partial_3_pct": None,

        "trade2_break_even_mode": INHERIT,
        "trade2_break_even_after_partial": None,

        "trade2_runner_mode": INHERIT,
        "trade2_runner_pct": None,
        "trade2_runner_rule": None,

        "trade2_final_target_mode": INHERIT,
        "trade2_final_target_points": None,
    }


def normalize_trade2_overrides(
    raw: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = (
        inherit_all_overrides()
    )

    if raw is None:
        return normalized

    for field in (
        TRADE2_OVERRIDE_FIELDS
    ):
        if field in raw:
            normalized[field] = (
                raw[field]
            )

    return normalized


def trade2_has_explicit_overrides(
    raw: dict[str, Any] | None,
) -> bool:
    overrides = (
        normalize_trade2_overrides(
            raw
        )
    )

    mode_fields = (
        "trade2_stop_mode",
        "trade2_partial_1_mode",
        "trade2_partial_2_mode",
        "trade2_partial_3_mode",
        "trade2_break_even_mode",
        "trade2_runner_mode",
        "trade2_final_target_mode",
    )

    return any(
        overrides[field]
        != INHERIT
        for field in mode_fields
    )


def _validate_mode(
    *,
    component: str,
    mode: Any,
    allow_disable: bool,
) -> str:
    mode = str(
        mode
    )

    allowed = (
        VALID_MODES
        if allow_disable
        else {
            INHERIT,
            CONFIGURE,
        }
    )

    if mode not in allowed:
        raise ValueError(
            (
                f"Unsupported {component} "
                f"mode: {mode}"
            )
        )

    return mode


def resolve_trade2_management_config(
    *,
    trade1_config: ManagementConfig,
    overrides: dict[str, Any] | None,
    validate_effective: bool = True,
) -> ManagementConfig:
    raw = (
        normalize_trade2_overrides(
            overrides
        )
    )

    effective = asdict(
        trade1_config
    )

    stop_mode = _validate_mode(
        component="Trade 2 stop",
        mode=raw[
            "trade2_stop_mode"
        ],
        allow_disable=False,
    )

    if stop_mode == CONFIGURE:
        value = raw.get(
            "trade2_stop_points"
        )

        if value is None:
            raise ValueError(
                (
                    "trade2_stop_points is "
                    "required when stop mode "
                    "is CONFIGURE."
                )
            )

        effective[
            "stop_points"
        ] = float(
            value
        )

    for index in (
        1,
        2,
        3,
    ):
        prefix = (
            f"trade2_partial_{index}"
        )

        mode = _validate_mode(
            component=(
                f"Trade 2 partial {index}"
            ),
            mode=raw[
                f"{prefix}_mode"
            ],
            allow_disable=True,
        )

        points_field = (
            f"partial_{index}_points"
        )

        pct_field = (
            f"partial_{index}_pct"
        )

        if mode == CONFIGURE:
            points = raw.get(
                f"{prefix}_points"
            )

            pct = raw.get(
                f"{prefix}_pct"
            )

            if (
                points is None
                or pct is None
            ):
                raise ValueError(
                    (
                        f"{prefix} CONFIGURE "
                        "requires points and pct."
                    )
                )

            effective[
                points_field
            ] = float(
                points
            )

            effective[
                pct_field
            ] = float(
                pct
            )

        elif mode == DISABLE:
            effective[
                points_field
            ] = None

            effective[
                pct_field
            ] = None

    break_even_mode = (
        _validate_mode(
            component=(
                "Trade 2 break-even"
            ),
            mode=raw[
                "trade2_break_even_mode"
            ],
            allow_disable=True,
        )
    )

    if break_even_mode == CONFIGURE:
        after = raw.get(
            "trade2_break_even_after_partial"
        )

        if after is None:
            raise ValueError(
                (
                    "trade2_break_even_after_partial "
                    "is required when break-even "
                    "mode is CONFIGURE."
                )
            )

        effective[
            "break_even_enabled"
        ] = True

        effective[
            "break_even_after_partial"
        ] = int(
            after
        )

    elif break_even_mode == DISABLE:
        effective[
            "break_even_enabled"
        ] = False

        effective[
            "break_even_after_partial"
        ] = None

    runner_mode = _validate_mode(
        component="Trade 2 runner",
        mode=raw[
            "trade2_runner_mode"
        ],
        allow_disable=True,
    )

    if runner_mode == CONFIGURE:
        pct = raw.get(
            "trade2_runner_pct"
        )

        rule = raw.get(
            "trade2_runner_rule"
        )

        if (
            pct is None
            or rule is None
        ):
            raise ValueError(
                (
                    "Trade 2 runner CONFIGURE "
                    "requires pct and rule."
                )
            )

        effective[
            "runner_enabled"
        ] = True

        effective[
            "runner_pct"
        ] = float(
            pct
        )

        effective[
            "runner_exit_rule"
        ] = str(
            rule
        )

    elif runner_mode == DISABLE:
        effective[
            "runner_enabled"
        ] = False

        effective[
            "runner_pct"
        ] = None

        effective[
            "runner_exit_rule"
        ] = None

    final_target_mode = (
        _validate_mode(
            component=(
                "Trade 2 final target"
            ),
            mode=raw[
                "trade2_final_target_mode"
            ],
            allow_disable=True,
        )
    )

    if final_target_mode == CONFIGURE:
        target = raw.get(
            "trade2_final_target_points"
        )

        if target is None:
            raise ValueError(
                (
                    "trade2_final_target_points "
                    "is required when final target "
                    "mode is CONFIGURE."
                )
            )

        effective[
            "final_target_points"
        ] = float(
            target
        )

    elif final_target_mode == DISABLE:
        effective[
            "final_target_points"
        ] = None

    config = ManagementConfig(
        **effective
    )

    if validate_effective:
        validate_config(
            config
        )

    return config


def management_config_sha256(
    config: ManagementConfig,
) -> str:
    return _sha256(
        asdict(
            config
        )
    )


def trade2_override_sha256(
    overrides: dict[str, Any] | None,
) -> str:
    return _sha256(
        normalize_trade2_overrides(
            overrides
        )
    )


def trade2_lineage(
    *,
    trade1_config: ManagementConfig,
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = (
        normalize_trade2_overrides(
            overrides
        )
    )

    effective = (
        resolve_trade2_management_config(
            trade1_config=(
                trade1_config
            ),
            overrides=(
                normalized
            ),
        )
    )

    return {
        "trade2_config_version": (
            TRADE2_CONFIG_VERSION
        ),
        "trade2_inherits_all": (
            not trade2_has_explicit_overrides(
                normalized
            )
        ),
        "trade1_configuration": (
            asdict(
                trade1_config
            )
        ),
        "trade2_overrides": (
            normalized
        ),
        "trade2_effective_configuration": (
            asdict(
                effective
            )
        ),
        "trade1_config_sha256": (
            management_config_sha256(
                trade1_config
            )
        ),
        "trade2_override_sha256": (
            trade2_override_sha256(
                normalized
            )
        ),
        "trade2_effective_config_sha256": (
            management_config_sha256(
                effective
            )
        ),
    }


TRADE2_MANAGEMENT_INHERIT = "INHERIT"
TRADE2_MANAGEMENT_CUSTOM = "CUSTOM"

TRADE2_MANAGEMENT_MODES = {
    TRADE2_MANAGEMENT_INHERIT,
    TRADE2_MANAGEMENT_CUSTOM,
}


def trade2_control_from_row(
    row: dict[str, Any],
) -> dict[str, Any]:
    """
    Resolve o controle do Trade 2 preservando
    compatibilidade histórica.

    Ausência de trade2_enabled representa
    artifact legado produzido antes da Stage 21.
    O comportamento histórico era Trade 2 ON.
    """

    explicit_enabled = (
        "trade2_enabled"
        in row
        and row.get(
            "trade2_enabled"
        )
        is not None
    )

    if explicit_enabled:
        enabled = bool(
            row[
                "trade2_enabled"
            ]
        )
    else:
        enabled = True

    explicit_management_mode = (
        "trade2_management_mode"
        in row
        and row.get(
            "trade2_management_mode"
        )
        is not None
    )

    if explicit_management_mode:
        management_mode = str(
            row[
                "trade2_management_mode"
            ]
        )
    else:
        management_mode = (
            TRADE2_MANAGEMENT_INHERIT
        )

    if (
        management_mode
        not in TRADE2_MANAGEMENT_MODES
    ):
        raise ValueError(
            (
                "Unsupported "
                "trade2_management_mode: "
                f"{management_mode}"
            )
        )

    return {
        "trade2_enabled": enabled,
        "trade2_enabled_explicit": (
            explicit_enabled
        ),
        "trade2_management_mode": (
            management_mode
        ),
        (
            "trade2_management_mode_explicit"
        ): (
            explicit_management_mode
        ),
        "legacy_semantics": (
            not explicit_enabled
        ),
    }


def validate_trade2_control(
    row: dict[str, Any],
) -> None:
    control = trade2_control_from_row(
        row
    )

    raw_overrides = {
        field: row[
            field
        ]
        for field in TRADE2_OVERRIDE_FIELDS
        if field in row
    }

    has_overrides = (
        trade2_has_explicit_overrides(
            raw_overrides
        )
    )

    if (
        control[
            "trade2_enabled"
        ]
        is False
        and has_overrides
    ):
        raise ValueError(
            (
                "Trade 2 is disabled but "
                "explicit Trade 2 management "
                "overrides are active."
            )
        )

    if (
        control[
            "trade2_enabled"
        ]
        is True
        and control[
            "trade2_management_mode"
        ]
        == TRADE2_MANAGEMENT_INHERIT
        and has_overrides
    ):
        raise ValueError(
            (
                "Trade 2 management mode is "
                "INHERIT but explicit overrides "
                "are active."
            )
        )

    if (
        control[
            "trade2_enabled"
        ]
        is True
        and control[
            "trade2_management_mode"
        ]
        == TRADE2_MANAGEMENT_CUSTOM
        and not has_overrides
    ):
        raise ValueError(
            (
                "Trade 2 management mode is "
                "CUSTOM but no explicit "
                "override is configured."
            )
        )
