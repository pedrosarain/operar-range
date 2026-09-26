from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from operar_range.runner import (
    M5Candle,
    runner_trigger,
)


@dataclass(frozen=True)
class ManagementConfig:
    stop_points: float

    partial_1_points: float | None = None
    partial_1_pct: float | None = None

    partial_2_points: float | None = None
    partial_2_pct: float | None = None

    partial_3_points: float | None = None
    partial_3_pct: float | None = None

    break_even_enabled: bool = False
    break_even_after_partial: int | None = None

    final_target_points: float | None = None

    runner_enabled: bool = False
    runner_pct: float | None = None
    runner_exit_rule: str | None = None

    position_size: float = 100.0


def validate_config(
    config: ManagementConfig,
) -> None:
    if config.stop_points <= 0:
        raise ValueError(
            "stop_points must be greater than zero."
        )

    if config.position_size <= 0:
        raise ValueError(
            "position_size must be greater than zero."
        )

    partials = [
        (
            config.partial_1_points,
            config.partial_1_pct,
        ),
        (
            config.partial_2_points,
            config.partial_2_pct,
        ),
        (
            config.partial_3_points,
            config.partial_3_pct,
        ),
    ]

    total_partial_pct = 0.0

    for index, (
        points,
        pct,
    ) in enumerate(
        partials,
        start=1,
    ):
        if points is None and pct is None:
            continue

        if points is None or pct is None:
            raise ValueError(
                f"Partial {index} must define "
                "both points and percentage."
            )

        if points <= 0:
            raise ValueError(
                f"Partial {index} points "
                "must be greater than zero."
            )

        if pct <= 0:
            raise ValueError(
                f"Partial {index} percentage "
                "must be greater than zero."
            )

        if pct > 100:
            raise ValueError(
                f"Partial {index} percentage "
                "cannot exceed 100."
            )

        total_partial_pct += pct

    if total_partial_pct > 100 + 1e-12:
        raise ValueError(
            "Sum of partial percentages "
            "cannot exceed 100%."
        )

    if (
        config.final_target_points is not None
        and config.final_target_points <= 0
    ):
        raise ValueError(
            "final_target_points must be "
            "greater than zero."
        )

    if config.break_even_enabled:
        if config.break_even_after_partial not in (
            1,
            2,
            3,
        ):
            raise ValueError(
                "break_even_after_partial must "
                "be 1, 2 or 3."
            )

        selected = partials[
            config.break_even_after_partial - 1
        ]

        if (
            selected[0] is None
            or selected[1] is None
        ):
            raise ValueError(
                "Break-even references a "
                "partial that is not configured."
            )

    if config.runner_enabled:
        if config.runner_pct is None:
            raise ValueError(
                "runner_pct is required "
                "when runner is enabled."
            )

        if config.runner_pct <= 0:
            raise ValueError(
                "runner_pct must be greater "
                "than zero."
            )

        if config.runner_pct > 100:
            raise ValueError(
                "runner_pct cannot exceed 100."
            )

        if (
            config.runner_exit_rule
            != "CANDLE_BREAK_M5"
        ):
            raise ValueError(
                "Unsupported runner_exit_rule."
            )

        if (
            total_partial_pct
            + config.runner_pct
            > 100 + 1e-12
        ):
            raise ValueError(
                "Partials plus runner cannot "
                "exceed 100%."
            )

    else:
        if config.runner_pct is not None:
            raise ValueError(
                "runner_pct requires "
                "runner_enabled=True."
            )

        if config.runner_exit_rule is not None:
            raise ValueError(
                "runner_exit_rule requires "
                "runner_enabled=True."
            )


def _trigger_price(
    direction: str,
    entry_price: float,
    signed_points: float,
) -> float:
    if direction == "LONG":
        return entry_price + signed_points

    if direction == "SHORT":
        return entry_price - signed_points

    raise ValueError(
        f"Unsupported direction: {direction}"
    )


def _actual_points(
    direction: str,
    entry_price: float,
    price: float,
) -> float:
    if direction == "LONG":
        return price - entry_price

    if direction == "SHORT":
        return entry_price - price

    raise ValueError(
        f"Unsupported direction: {direction}"
    )


def _event(
    *,
    sequence: int,
    event_type: str,
    timestamp: str,
    trade_number: int,
    actual_price: float,
    trigger_level: float,
    realized_points: float,
    pct_closed: float,
    initial_position: float,
    remaining_position: float,
) -> dict[str, Any]:
    quantity_closed = (
        initial_position
        * pct_closed
        / 100.0
    )

    return {
        "sequence": sequence,
        "event_type": event_type,
        "timestamp": timestamp,
        "trade_number": trade_number,
        "trigger_level": trigger_level,
        "first_traded_price_after_trigger": (
            actual_price
        ),
        "jumped_trigger_level": (
            actual_price != trigger_level
        ),
        "realized_points": realized_points,
        "pct_closed": pct_closed,
        "quantity_closed": quantity_closed,
        "remaining_position": (
            remaining_position
        ),
        "remaining_pct": (
            100.0
            * remaining_position
            / initial_position
        ),
        "weighted_points": (
            realized_points
            * pct_closed
            / 100.0
        ),
    }


def _configured_partial_numbers(
    config: ManagementConfig,
) -> list[int]:
    numbers = []

    if (
        config.partial_1_points is not None
        and config.partial_1_pct is not None
    ):
        numbers.append(1)

    if (
        config.partial_2_points is not None
        and config.partial_2_pct is not None
    ):
        numbers.append(2)

    if (
        config.partial_3_points is not None
        and config.partial_3_pct is not None
    ):
        numbers.append(3)

    return numbers


def _all_configured_partials_executed(
    configured_partials: list[int],
    executed_partials: set[int],
) -> bool:
    return all(
        number in executed_partials
        for number in configured_partials
    )


def simulate_management(
    *,
    trajectory: list[dict[str, Any]],
    date: str,
    direction: str,
    entry_price: float,
    config: ManagementConfig,
    runner_candles: list[M5Candle] | None = None,
) -> dict[str, Any]:
    validate_config(config)

    if not trajectory:
        raise ValueError(
            "Trajectory cannot be empty."
        )

    if direction not in (
        "LONG",
        "SHORT",
    ):
        raise ValueError(
            f"Unsupported direction: {direction}"
        )

    if (
        config.runner_enabled
        and runner_candles is None
    ):
        raise ValueError(
            "runner_candles is required "
            "when runner is enabled."
        )

    initial_position = float(
        config.position_size
    )

    remaining_position = (
        initial_position
    )

    partial_definitions = [
        (
            1,
            config.partial_1_points,
            config.partial_1_pct,
        ),
        (
            2,
            config.partial_2_points,
            config.partial_2_pct,
        ),
        (
            3,
            config.partial_3_points,
            config.partial_3_pct,
        ),
    ]

    configured_partials = (
        _configured_partial_numbers(
            config
        )
    )

    executed_partials: set[int] = set()

    partial_results: dict[
        int,
        dict[str, Any],
    ] = {
        1: {
            "executed": False,
            "realized_points": None,
            "weighted_points": 0.0,
        },
        2: {
            "executed": False,
            "realized_points": None,
            "weighted_points": 0.0,
        },
        3: {
            "executed": False,
            "realized_points": None,
            "weighted_points": 0.0,
        },
    }

    executions: list[
        dict[str, Any]
    ] = []

    be_active = False
    be_activate_after_row = False

    runner_active = False
    runner_activate_after_row = False

    runner_activation_timestamp: str | None = None
    runner_activation_trade_number: int | None = None

    runner_position = 0.0

    runner_result: dict[str, Any] = {
        "enabled": config.runner_enabled,
        "executed": False,
        "activation_timestamp": None,
        "activation_trade_number": None,
        "pct": config.runner_pct,
        "exit_rule": (
            config.runner_exit_rule
        ),
        "protected_candle": None,
        "trigger_level": None,
        "timestamp": None,
        "trade_number": None,
        "first_traded_price_after_trigger": None,
        "jumped_trigger_level": None,
        "realized_points": None,
        "weighted_points": 0.0,
    }

    final_component = {
        "executed": False,
        "event_type": None,
        "realized_points": None,
        "weighted_points": 0.0,
    }

    sequence = 0

    def append_exit(
        *,
        event_type: str,
        row: dict[str, Any],
        trigger_level: float,
        close_pct: float,
    ) -> dict[str, Any]:
        nonlocal sequence
        nonlocal remaining_position

        sequence += 1

        actual_price = float(
            row["price"]
        )

        realized_points = (
            _actual_points(
                direction,
                entry_price,
                actual_price,
            )
        )

        quantity_to_close = (
            initial_position
            * close_pct
            / 100.0
        )

        quantity_to_close = min(
            quantity_to_close,
            remaining_position,
        )

        actual_pct_closed = (
            100.0
            * quantity_to_close
            / initial_position
        )

        remaining_position -= (
            quantity_to_close
        )

        if abs(
            remaining_position
        ) < 1e-12:
            remaining_position = 0.0

        event = _event(
            sequence=sequence,
            event_type=event_type,
            timestamp=row["timestamp"],
            trade_number=int(
                row["trade_number"]
            ),
            actual_price=actual_price,
            trigger_level=trigger_level,
            realized_points=realized_points,
            pct_closed=actual_pct_closed,
            initial_position=initial_position,
            remaining_position=remaining_position,
        )

        executions.append(event)

        return event

    # Posição integral em runner:
    # sem parciais configuradas, o runner existe
    # desde a entrada.
    if (
        config.runner_enabled
        and not configured_partials
    ):
        runner_active = True

        runner_activation_timestamp = (
            trajectory[0]["timestamp"]
        )

        runner_activation_trade_number = int(
            trajectory[0][
                "trade_number"
            ]
        )

        runner_position = min(
            remaining_position,
            initial_position
            * float(
                config.runner_pct
            )
            / 100.0,
        )

        runner_result[
            "activation_timestamp"
        ] = runner_activation_timestamp

        runner_result[
            "activation_trade_number"
        ] = runner_activation_trade_number

    for row in trajectory:
        if remaining_position <= 0:
            break

        current_price = float(
            row["price"]
        )

        current_points = (
            _actual_points(
                direction,
                entry_price,
                current_price,
            )
        )

        runner_signal = None

        if (
            runner_active
            and runner_position > 0
        ):
            runner_signal = (
                runner_trigger(
                    direction=direction,
                    row=row,
                    candles=runner_candles,
                    activation_timestamp=(
                        runner_activation_timestamp
                    ),
                )
            )

        # -------------------------------------------------
        # PROTEÇÃO: BE / RUNNER / STOP
        # -------------------------------------------------

        if be_active:
            be_triggered = (
                current_points <= 0
            )

            runner_triggered = (
                runner_signal is not None
            )

            if (
                be_triggered
                and runner_triggered
            ):
                runner_level = float(
                    runner_signal[
                        "trigger_level"
                    ]
                )

                # Quando o mesmo salto de preço
                # atravessa runner e BE, escolhemos
                # o nível encontrado primeiro no
                # deslocamento do preço.
                if direction == "LONG":
                    runner_first = (
                        runner_level
                        > entry_price
                    )
                else:
                    runner_first = (
                        runner_level
                        < entry_price
                    )

                if runner_first:
                    runner_pct_to_close = (
                        100.0
                        * runner_position
                        / initial_position
                    )

                    event = append_exit(
                        event_type=(
                            "EXIT_RUNNER_CANDLE"
                        ),
                        row=row,
                        trigger_level=(
                            runner_level
                        ),
                        close_pct=(
                            runner_pct_to_close
                        ),
                    )

                    event[
                        "protected_candle"
                    ] = runner_signal[
                        "protected_candle"
                    ]

                    event[
                        "runner_exit_rule"
                    ] = (
                        "CANDLE_BREAK_M5"
                    )

                    runner_position = 0.0

                    runner_result.update(
                        {
                            "executed": True,
                            "protected_candle": (
                                runner_signal[
                                    "protected_candle"
                                ]
                            ),
                            "trigger_level": (
                                runner_level
                            ),
                            "timestamp": (
                                event[
                                    "timestamp"
                                ]
                            ),
                            "trade_number": (
                                event[
                                    "trade_number"
                                ]
                            ),
                            "first_traded_price_after_trigger": (
                                event[
                                    "first_traded_price_after_trigger"
                                ]
                            ),
                            "jumped_trigger_level": (
                                event[
                                    "jumped_trigger_level"
                                ]
                            ),
                            "realized_points": (
                                event[
                                    "realized_points"
                                ]
                            ),
                            "weighted_points": (
                                event[
                                    "weighted_points"
                                ]
                            ),
                        }
                    )

                    if remaining_position <= 0:
                        final_component = {
                            "executed": True,
                            "event_type": (
                                "EXIT_RUNNER_CANDLE"
                            ),
                            "realized_points": (
                                event[
                                    "realized_points"
                                ]
                            ),
                            "weighted_points": (
                                event[
                                    "weighted_points"
                                ]
                            ),
                        }

                        break

                else:
                    remaining_pct = (
                        100.0
                        * remaining_position
                        / initial_position
                    )

                    event = append_exit(
                        event_type=(
                            "EXIT_BREAK_EVEN"
                        ),
                        row=row,
                        trigger_level=(
                            entry_price
                        ),
                        close_pct=(
                            remaining_pct
                        ),
                    )

                    runner_position = 0.0

                    final_component = {
                        "executed": True,
                        "event_type": (
                            "EXIT_BREAK_EVEN"
                        ),
                        "realized_points": (
                            event[
                                "realized_points"
                            ]
                        ),
                        "weighted_points": (
                            event[
                                "weighted_points"
                            ]
                        ),
                    }

                    break

            elif be_triggered:
                remaining_pct = (
                    100.0
                    * remaining_position
                    / initial_position
                )

                event = append_exit(
                    event_type=(
                        "EXIT_BREAK_EVEN"
                    ),
                    row=row,
                    trigger_level=entry_price,
                    close_pct=remaining_pct,
                )

                runner_position = 0.0

                final_component = {
                    "executed": True,
                    "event_type": (
                        "EXIT_BREAK_EVEN"
                    ),
                    "realized_points": (
                        event[
                            "realized_points"
                        ]
                    ),
                    "weighted_points": (
                        event[
                            "weighted_points"
                        ]
                    ),
                }

                break

            elif runner_triggered:
                runner_pct_to_close = (
                    100.0
                    * runner_position
                    / initial_position
                )

                event = append_exit(
                    event_type=(
                        "EXIT_RUNNER_CANDLE"
                    ),
                    row=row,
                    trigger_level=float(
                        runner_signal[
                            "trigger_level"
                        ]
                    ),
                    close_pct=(
                        runner_pct_to_close
                    ),
                )

                event[
                    "protected_candle"
                ] = runner_signal[
                    "protected_candle"
                ]

                event[
                    "runner_exit_rule"
                ] = (
                    "CANDLE_BREAK_M5"
                )

                runner_position = 0.0

                runner_result.update(
                    {
                        "executed": True,
                        "protected_candle": (
                            runner_signal[
                                "protected_candle"
                            ]
                        ),
                        "trigger_level": (
                            runner_signal[
                                "trigger_level"
                            ]
                        ),
                        "timestamp": (
                            event[
                                "timestamp"
                            ]
                        ),
                        "trade_number": (
                            event[
                                "trade_number"
                            ]
                        ),
                        "first_traded_price_after_trigger": (
                            event[
                                "first_traded_price_after_trigger"
                            ]
                        ),
                        "jumped_trigger_level": (
                            event[
                                "jumped_trigger_level"
                            ]
                        ),
                        "realized_points": (
                            event[
                                "realized_points"
                            ]
                        ),
                        "weighted_points": (
                            event[
                                "weighted_points"
                            ]
                        ),
                    }
                )

                if remaining_position <= 0:
                    final_component = {
                        "executed": True,
                        "event_type": (
                            "EXIT_RUNNER_CANDLE"
                        ),
                        "realized_points": (
                            event[
                                "realized_points"
                            ]
                        ),
                        "weighted_points": (
                            event[
                                "weighted_points"
                            ]
                        ),
                    }

                    break

        else:
            if (
                current_points
                <= -config.stop_points
            ):
                remaining_pct = (
                    100.0
                    * remaining_position
                    / initial_position
                )

                stop_level = (
                    _trigger_price(
                        direction,
                        entry_price,
                        -config.stop_points,
                    )
                )

                event = append_exit(
                    event_type="STOP",
                    row=row,
                    trigger_level=stop_level,
                    close_pct=remaining_pct,
                )

                runner_position = 0.0

                final_component = {
                    "executed": True,
                    "event_type": "STOP",
                    "realized_points": (
                        event[
                            "realized_points"
                        ]
                    ),
                    "weighted_points": (
                        event[
                            "weighted_points"
                        ]
                    ),
                }

                break

            if runner_signal is not None:
                runner_pct_to_close = (
                    100.0
                    * runner_position
                    / initial_position
                )

                event = append_exit(
                    event_type=(
                        "EXIT_RUNNER_CANDLE"
                    ),
                    row=row,
                    trigger_level=float(
                        runner_signal[
                            "trigger_level"
                        ]
                    ),
                    close_pct=(
                        runner_pct_to_close
                    ),
                )

                event[
                    "protected_candle"
                ] = runner_signal[
                    "protected_candle"
                ]

                event[
                    "runner_exit_rule"
                ] = (
                    "CANDLE_BREAK_M5"
                )

                runner_position = 0.0

                runner_result.update(
                    {
                        "executed": True,
                        "protected_candle": (
                            runner_signal[
                                "protected_candle"
                            ]
                        ),
                        "trigger_level": (
                            runner_signal[
                                "trigger_level"
                            ]
                        ),
                        "timestamp": (
                            event[
                                "timestamp"
                            ]
                        ),
                        "trade_number": (
                            event[
                                "trade_number"
                            ]
                        ),
                        "first_traded_price_after_trigger": (
                            event[
                                "first_traded_price_after_trigger"
                            ]
                        ),
                        "jumped_trigger_level": (
                            event[
                                "jumped_trigger_level"
                            ]
                        ),
                        "realized_points": (
                            event[
                                "realized_points"
                            ]
                        ),
                        "weighted_points": (
                            event[
                                "weighted_points"
                            ]
                        ),
                    }
                )

                if remaining_position <= 0:
                    final_component = {
                        "executed": True,
                        "event_type": (
                            "EXIT_RUNNER_CANDLE"
                        ),
                        "realized_points": (
                            event[
                                "realized_points"
                            ]
                        ),
                        "weighted_points": (
                            event[
                                "weighted_points"
                            ]
                        ),
                    }

                    break

        # -------------------------------------------------
        # PARCIAIS
        # -------------------------------------------------

        for (
            partial_number,
            partial_points,
            partial_pct,
        ) in partial_definitions:
            if remaining_position <= 0:
                break

            if (
                partial_points is None
                or partial_pct is None
            ):
                continue

            if (
                partial_number
                in executed_partials
            ):
                continue

            if (
                current_points
                < partial_points
            ):
                continue

            partial_level = (
                _trigger_price(
                    direction,
                    entry_price,
                    partial_points,
                )
            )

            event = append_exit(
                event_type=(
                    f"PARTIAL_{partial_number}"
                ),
                row=row,
                trigger_level=partial_level,
                close_pct=partial_pct,
            )

            executed_partials.add(
                partial_number
            )

            partial_results[
                partial_number
            ] = {
                "executed": True,
                "timestamp": event[
                    "timestamp"
                ],
                "trade_number": event[
                    "trade_number"
                ],
                "trigger_level": event[
                    "trigger_level"
                ],
                "first_traded_price_after_trigger": (
                    event[
                        "first_traded_price_after_trigger"
                    ]
                ),
                "jumped_trigger_level": (
                    event[
                        "jumped_trigger_level"
                    ]
                ),
                "pct_closed": event[
                    "pct_closed"
                ],
                "quantity_closed": event[
                    "quantity_closed"
                ],
                "remaining_position": event[
                    "remaining_position"
                ],
                "realized_points": event[
                    "realized_points"
                ],
                "weighted_points": event[
                    "weighted_points"
                ],
            }

            if (
                config.break_even_enabled
                and config.break_even_after_partial
                == partial_number
            ):
                # O próprio registro da parcial
                # não pode disparar BE
                # retroativamente.
                be_activate_after_row = True

        # Runner passa a existir somente depois
        # que todas as parciais configuradas
        # tiverem sido executadas.
        if (
            config.runner_enabled
            and not runner_active
            and configured_partials
            and _all_configured_partials_executed(
                configured_partials,
                executed_partials,
            )
        ):
            runner_activate_after_row = True

        if remaining_position <= 0:
            final_component = {
                "executed": True,
                "event_type": (
                    "FULLY_CLOSED_BY_PARTIALS"
                ),
                "realized_points": None,
                "weighted_points": 0.0,
            }
            break

        # -------------------------------------------------
        # ALVO FINAL
        # -------------------------------------------------

        if (
            config.final_target_points
            is not None
            and current_points
            >= config.final_target_points
        ):
            remaining_pct = (
                100.0
                * remaining_position
                / initial_position
            )

            target_level = (
                _trigger_price(
                    direction,
                    entry_price,
                    config.final_target_points,
                )
            )

            event = append_exit(
                event_type="FINAL_TARGET",
                row=row,
                trigger_level=target_level,
                close_pct=remaining_pct,
            )

            runner_position = 0.0

            final_component = {
                "executed": True,
                "event_type": (
                    "FINAL_TARGET"
                ),
                "realized_points": (
                    event[
                        "realized_points"
                    ]
                ),
                "weighted_points": (
                    event[
                        "weighted_points"
                    ]
                ),
            }

            break

        # Ativações acontecem somente depois
        # do processamento completo do registro
        # em que a parcial ocorreu.
        if be_activate_after_row:
            be_active = True
            be_activate_after_row = False

        if runner_activate_after_row:
            runner_active = True
            runner_activate_after_row = False

            runner_activation_timestamp = (
                row["timestamp"]
            )

            runner_activation_trade_number = int(
                row["trade_number"]
            )

            runner_position = min(
                remaining_position,
                initial_position
                * float(
                    config.runner_pct
                )
                / 100.0,
            )

            runner_result[
                "activation_timestamp"
            ] = runner_activation_timestamp

            runner_result[
                "activation_trade_number"
            ] = runner_activation_trade_number

    # -------------------------------------------------
    # FIM DA TRAJECTORY
    # -------------------------------------------------

    if remaining_position > 0:
        last_row = trajectory[-1]

        remaining_pct = (
            100.0
            * remaining_position
            / initial_position
        )

        event = append_exit(
            event_type=(
                "END_OF_TRAJECTORY"
            ),
            row=last_row,
            trigger_level=float(
                last_row["price"]
            ),
            close_pct=remaining_pct,
        )

        if (
            runner_active
            and runner_position > 0
        ):
            runner_result.update(
                {
                    "executed": True,
                    "trigger_level": float(
                        last_row["price"]
                    ),
                    "timestamp": (
                        event["timestamp"]
                    ),
                    "trade_number": (
                        event[
                            "trade_number"
                        ]
                    ),
                    "first_traded_price_after_trigger": (
                        event[
                            "first_traded_price_after_trigger"
                        ]
                    ),
                    "jumped_trigger_level": False,
                    "realized_points": (
                        event[
                            "realized_points"
                        ]
                    ),
                    "weighted_points": (
                        event[
                            "weighted_points"
                        ]
                    ),
                }
            )

            runner_position = 0.0

        final_component = {
            "executed": True,
            "event_type": (
                "END_OF_TRAJECTORY"
            ),
            "realized_points": (
                event[
                    "realized_points"
                ]
            ),
            "weighted_points": (
                event[
                    "weighted_points"
                ]
            ),
        }

    total_weighted_points = sum(
        float(
            event["weighted_points"]
        )
        for event in executions
    )

    total_position_points = sum(
        float(
            event["realized_points"]
        )
        * float(
            event["quantity_closed"]
        )
        for event in executions
    )

    final_event = (
        executions[-1]
        if executions
        else None
    )

    return {
        "status": "OK",
        "date": date,
        "direction": direction,
        "entry_price": float(
            entry_price
        ),
        "position_size": (
            initial_position
        ),
        "config": asdict(config),
        "executions": executions,
        "remaining_position": (
            remaining_position
        ),
        "remaining_pct": (
            100.0
            * remaining_position
            / initial_position
        ),
        "partial_1_result": (
            partial_results[1]
        ),
        "partial_2_result": (
            partial_results[2]
        ),
        "partial_3_result": (
            partial_results[3]
        ),
        "runner_result": (
            runner_result
        ),
        "remaining_position_result": (
            final_component
        ),
        "total_weighted_points": (
            total_weighted_points
        ),
        "total_position_points": (
            total_position_points
        ),
        "final_reason": (
            final_event[
                "event_type"
            ]
            if final_event
            else None
        ),
        "final_timestamp": (
            final_event["timestamp"]
            if final_event
            else None
        ),
        "final_price": (
            final_event[
                "first_traded_price_after_trigger"
            ]
            if final_event
            else None
        ),
    }