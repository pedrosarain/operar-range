from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable


PATH_PARAMETER_VERSION = (
    "parametric-path-research-v1"
)


DEFAULT_TARGET_VALUES = (
    100,
    125,
    150,
    175,
    200,
    250,
    300,
    350,
    400,
    500,
    600,
    800,
    1000,
)

DEFAULT_STOP_VALUES = (
    100,
    125,
    150,
    175,
    200,
)


GRID_SOURCE_DEFAULT = "DEFAULT"
GRID_SOURCE_EXPLICIT = "EXPLICIT"
GRID_SOURCE_RANGE = "RANGE"

TRADE2_GRID_SOURCE_INHERITED = (
    "INHERITED"
)

TRADE2_GRID_SOURCE_EXPLICIT = (
    "EXPLICIT"
)


@dataclass(
    frozen=True
)
class GridInput:
    values: tuple[int, ...] | None = None
    start: int | None = None
    end: int | None = None
    step: int | None = None


@dataclass(
    frozen=True
)
class CanonicalPathGrid:
    target_values: tuple[int, ...]
    stop_values: tuple[int, ...]

    trade2_target_values_effective: (
        tuple[int, ...]
    )
    trade2_stop_values_effective: (
        tuple[int, ...]
    )

    target_grid_source: str
    stop_grid_source: str

    trade2_target_grid_source: str
    trade2_stop_grid_source: str

    target_count: int
    stop_count: int

    trade1_matrix_size: int

    trade2_target_count: int
    trade2_stop_count: int
    trade2_matrix_size: int

    valid_trade1_count: int
    valid_trade2_count: int

    estimated_trade1_path_rows: int
    estimated_trade2_path_rows: int
    estimated_path_rows: int

    parameter_definition_json: str
    parameter_definition_sha256: str

    parameter_version: str = (
        PATH_PARAMETER_VERSION
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "parameter_version": (
                self.parameter_version
            ),

            "target_values": list(
                self.target_values
            ),
            "stop_values": list(
                self.stop_values
            ),

            (
                "trade2_target_values_"
                "effective"
            ): list(
                self
                .trade2_target_values_effective
            ),
            (
                "trade2_stop_values_"
                "effective"
            ): list(
                self
                .trade2_stop_values_effective
            ),

            "target_grid_source": (
                self.target_grid_source
            ),
            "stop_grid_source": (
                self.stop_grid_source
            ),

            (
                "trade2_target_grid_source"
            ): (
                self
                .trade2_target_grid_source
            ),
            (
                "trade2_stop_grid_source"
            ): (
                self
                .trade2_stop_grid_source
            ),

            "target_count": (
                self.target_count
            ),
            "stop_count": (
                self.stop_count
            ),

            "trade1_matrix_size": (
                self.trade1_matrix_size
            ),

            "trade2_target_count": (
                self.trade2_target_count
            ),
            "trade2_stop_count": (
                self.trade2_stop_count
            ),
            "trade2_matrix_size": (
                self.trade2_matrix_size
            ),

            "valid_trade1_count": (
                self.valid_trade1_count
            ),
            "valid_trade2_count": (
                self.valid_trade2_count
            ),

            (
                "estimated_trade1_"
                "path_rows"
            ): (
                self
                .estimated_trade1_path_rows
            ),
            (
                "estimated_trade2_"
                "path_rows"
            ): (
                self
                .estimated_trade2_path_rows
            ),
            "estimated_path_rows": (
                self.estimated_path_rows
            ),

            (
                "parameter_definition_json"
            ): (
                self
                .parameter_definition_json
            ),
            (
                "parameter_definition_sha256"
            ): (
                self
                .parameter_definition_sha256
            ),
        }


def _normalize_integer(
    value: Any,
    *,
    name: str,
) -> int:
    if isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"{name} must be a "
            "positive integer."
        )

    try:
        numeric = int(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"{name} must be a "
            "positive integer."
        ) from exc

    try:
        original = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"{name} must be a "
            "positive integer."
        ) from exc

    if float(
        numeric
    ) != original:
        raise ValueError(
            f"{name} must be an "
            "integer."
        )

    if numeric <= 0:
        raise ValueError(
            f"{name} must be > 0."
        )

    return numeric


def _canonical_values(
    values: Iterable[Any],
    *,
    name: str,
) -> tuple[int, ...]:
    normalized = {
        _normalize_integer(
            value,
            name=name,
        )
        for value in values
    }

    if not normalized:
        raise ValueError(
            f"{name} cannot be empty."
        )

    return tuple(
        sorted(
            normalized
        )
    )


def _range_values(
    *,
    start: Any,
    end: Any,
    step: Any,
    name: str,
) -> tuple[int, ...]:
    normalized_start = (
        _normalize_integer(
            start,
            name=f"{name}_start",
        )
    )

    normalized_end = (
        _normalize_integer(
            end,
            name=f"{name}_end",
        )
    )

    normalized_step = (
        _normalize_integer(
            step,
            name=f"{name}_step",
        )
    )

    if (
        normalized_start
        > normalized_end
    ):
        raise ValueError(
            f"{name}_start must be "
            f"<= {name}_end."
        )

    generated = tuple(
        range(
            normalized_start,
            normalized_end + 1,
            normalized_step,
        )
    )

    if not generated:
        raise ValueError(
            f"{name} range produced "
            "no values."
        )

    return generated


def normalize_grid_input(
    *,
    values: Iterable[Any] | None = None,
    start: Any | None = None,
    end: Any | None = None,
    step: Any | None = None,
    default_values: (
        Iterable[Any] | None
    ) = None,
    name: str,
) -> tuple[
    tuple[int, ...],
    str,
]:
    explicit_present = (
        values is not None
    )

    range_fields = (
        start,
        end,
        step,
    )

    range_any = any(
        value is not None
        for value in range_fields
    )

    range_all = all(
        value is not None
        for value in range_fields
    )

    if (
        explicit_present
        and range_any
    ):
        raise ValueError(
            f"{name}: explicit values "
            "and range definition cannot "
            "be supplied together."
        )

    if (
        range_any
        and not range_all
    ):
        raise ValueError(
            f"{name}: range requires "
            "start, end and step."
        )

    if explicit_present:
        return (
            _canonical_values(
                values,
                name=name,
            ),
            GRID_SOURCE_EXPLICIT,
        )

    if range_all:
        return (
            _range_values(
                start=start,
                end=end,
                step=step,
                name=name,
            ),
            GRID_SOURCE_RANGE,
        )

    if default_values is None:
        raise ValueError(
            f"{name}: no values or "
            "default supplied."
        )

    return (
        _canonical_values(
            default_values,
            name=name,
        ),
        GRID_SOURCE_DEFAULT,
    )


def _canonical_json(
    value: dict[str, Any],
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
    )


def parameter_definition_sha256(
    definition: dict[str, Any],
) -> str:
    payload = (
        _canonical_json(
            definition
        )
        .encode(
            "utf-8"
        )
    )

    return hashlib.sha256(
        payload
    ).hexdigest()


def canonical_parameter_definition(
    *,
    target_values: Iterable[Any],
    stop_values: Iterable[Any],
    trade2_target_values_effective: (
        Iterable[Any]
    ),
    trade2_stop_values_effective: (
        Iterable[Any]
    ),
    target_grid_source: str,
    stop_grid_source: str,
    trade2_target_grid_source: str,
    trade2_stop_grid_source: str,
) -> dict[str, Any]:
    return {
        "parameter_version": (
            PATH_PARAMETER_VERSION
        ),

        "target_values": list(
            target_values
        ),
        "stop_values": list(
            stop_values
        ),

        (
            "trade2_target_values_"
            "effective"
        ): list(
            trade2_target_values_effective
        ),

        (
            "trade2_stop_values_"
            "effective"
        ): list(
            trade2_stop_values_effective
        ),

        "target_grid_source": (
            target_grid_source
        ),
        "stop_grid_source": (
            stop_grid_source
        ),

        (
            "trade2_target_grid_source"
        ): (
            trade2_target_grid_source
        ),

        (
            "trade2_stop_grid_source"
        ): (
            trade2_stop_grid_source
        ),
    }


def resolve_path_grid(
    *,
    target_values: (
        Iterable[Any] | None
    ) = None,
    target_start: Any | None = None,
    target_end: Any | None = None,
    target_step: Any | None = None,

    stop_values: (
        Iterable[Any] | None
    ) = None,
    stop_start: Any | None = None,
    stop_end: Any | None = None,
    stop_step: Any | None = None,

    trade2_target_values: (
        Iterable[Any] | None
    ) = None,
    trade2_target_start: Any | None = None,
    trade2_target_end: Any | None = None,
    trade2_target_step: Any | None = None,

    trade2_stop_values: (
        Iterable[Any] | None
    ) = None,
    trade2_stop_start: Any | None = None,
    trade2_stop_end: Any | None = None,
    trade2_stop_step: Any | None = None,

    valid_trade1_count: int = 0,
    valid_trade2_count: int = 0,
) -> CanonicalPathGrid:
    (
        canonical_targets,
        target_grid_source,
    ) = normalize_grid_input(
        values=target_values,
        start=target_start,
        end=target_end,
        step=target_step,
        default_values=(
            DEFAULT_TARGET_VALUES
        ),
        name="target",
    )

    (
        canonical_stops,
        stop_grid_source,
    ) = normalize_grid_input(
        values=stop_values,
        start=stop_start,
        end=stop_end,
        step=stop_step,
        default_values=(
            DEFAULT_STOP_VALUES
        ),
        name="stop",
    )

    trade2_target_custom = (
        trade2_target_values
        is not None
        or trade2_target_start
        is not None
        or trade2_target_end
        is not None
        or trade2_target_step
        is not None
    )

    if trade2_target_custom:
        (
            canonical_trade2_targets,
            _,
        ) = normalize_grid_input(
            values=(
                trade2_target_values
            ),
            start=(
                trade2_target_start
            ),
            end=(
                trade2_target_end
            ),
            step=(
                trade2_target_step
            ),
            default_values=None,
            name="trade2_target",
        )

        trade2_target_grid_source = (
            TRADE2_GRID_SOURCE_EXPLICIT
        )

    else:
        canonical_trade2_targets = (
            canonical_targets
        )

        trade2_target_grid_source = (
            TRADE2_GRID_SOURCE_INHERITED
        )

    trade2_stop_custom = (
        trade2_stop_values
        is not None
        or trade2_stop_start
        is not None
        or trade2_stop_end
        is not None
        or trade2_stop_step
        is not None
    )

    if trade2_stop_custom:
        (
            canonical_trade2_stops,
            _,
        ) = normalize_grid_input(
            values=(
                trade2_stop_values
            ),
            start=(
                trade2_stop_start
            ),
            end=(
                trade2_stop_end
            ),
            step=(
                trade2_stop_step
            ),
            default_values=None,
            name="trade2_stop",
        )

        trade2_stop_grid_source = (
            TRADE2_GRID_SOURCE_EXPLICIT
        )

    else:
        canonical_trade2_stops = (
            canonical_stops
        )

        trade2_stop_grid_source = (
            TRADE2_GRID_SOURCE_INHERITED
        )

    normalized_trade1_count = int(
        valid_trade1_count
    )

    normalized_trade2_count = int(
        valid_trade2_count
    )

    if normalized_trade1_count < 0:
        raise ValueError(
            "valid_trade1_count "
            "cannot be negative."
        )

    if normalized_trade2_count < 0:
        raise ValueError(
            "valid_trade2_count "
            "cannot be negative."
        )

    target_count = len(
        canonical_targets
    )

    stop_count = len(
        canonical_stops
    )

    trade1_matrix_size = (
        target_count
        * stop_count
    )

    trade2_target_count = len(
        canonical_trade2_targets
    )

    trade2_stop_count = len(
        canonical_trade2_stops
    )

    trade2_matrix_size = (
        trade2_target_count
        * trade2_stop_count
    )

    estimated_trade1_path_rows = (
        trade1_matrix_size
        * normalized_trade1_count
    )

    estimated_trade2_path_rows = (
        trade2_matrix_size
        * normalized_trade2_count
    )

    estimated_path_rows = (
        estimated_trade1_path_rows
        + estimated_trade2_path_rows
    )

    definition = (
        canonical_parameter_definition(
            target_values=(
                canonical_targets
            ),
            stop_values=(
                canonical_stops
            ),
            trade2_target_values_effective=(
                canonical_trade2_targets
            ),
            trade2_stop_values_effective=(
                canonical_trade2_stops
            ),
            target_grid_source=(
                target_grid_source
            ),
            stop_grid_source=(
                stop_grid_source
            ),
            trade2_target_grid_source=(
                trade2_target_grid_source
            ),
            trade2_stop_grid_source=(
                trade2_stop_grid_source
            ),
        )
    )

    definition_json = (
        _canonical_json(
            definition
        )
    )

    definition_sha256 = (
        hashlib.sha256(
            definition_json.encode(
                "utf-8"
            )
        ).hexdigest()
    )

    return CanonicalPathGrid(
        target_values=(
            canonical_targets
        ),
        stop_values=(
            canonical_stops
        ),

        trade2_target_values_effective=(
            canonical_trade2_targets
        ),

        trade2_stop_values_effective=(
            canonical_trade2_stops
        ),

        target_grid_source=(
            target_grid_source
        ),
        stop_grid_source=(
            stop_grid_source
        ),

        trade2_target_grid_source=(
            trade2_target_grid_source
        ),
        trade2_stop_grid_source=(
            trade2_stop_grid_source
        ),

        target_count=(
            target_count
        ),
        stop_count=(
            stop_count
        ),

        trade1_matrix_size=(
            trade1_matrix_size
        ),

        trade2_target_count=(
            trade2_target_count
        ),
        trade2_stop_count=(
            trade2_stop_count
        ),
        trade2_matrix_size=(
            trade2_matrix_size
        ),

        valid_trade1_count=(
            normalized_trade1_count
        ),
        valid_trade2_count=(
            normalized_trade2_count
        ),

        estimated_trade1_path_rows=(
            estimated_trade1_path_rows
        ),
        estimated_trade2_path_rows=(
            estimated_trade2_path_rows
        ),
        estimated_path_rows=(
            estimated_path_rows
        ),

        parameter_definition_json=(
            definition_json
        ),
        parameter_definition_sha256=(
            definition_sha256
        ),
    )


def historical_default_grid(
    *,
    valid_trade1_count: int = 0,
    valid_trade2_count: int = 0,
) -> CanonicalPathGrid:
    return resolve_path_grid(
        valid_trade1_count=(
            valid_trade1_count
        ),
        valid_trade2_count=(
            valid_trade2_count
        ),
    )
