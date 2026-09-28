from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from itertools import product
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from operar_range.experiment_registry import (
    migrate_registry,
)
from operar_range.management import (
    ManagementConfig,
)
from operar_range.trade2_configuration import (
    TRADE2_MANAGEMENT_INHERIT,
    TRADE2_OVERRIDE_FIELDS,
    management_config_sha256,
    normalize_trade2_overrides,
    resolve_trade2_management_config,
    trade2_control_from_row,
    trade2_has_explicit_overrides,
    trade2_override_sha256,
)


GENERATOR_VERSION = "experiment-generator-v1"


CONFIG_FIELDS = (
    "stop_points",
    "partial_1_points",
    "partial_1_pct",
    "partial_2_points",
    "partial_2_pct",
    "partial_3_points",
    "partial_3_pct",
    "break_even_enabled",
    "break_even_after_partial",
    "runner_enabled",
    "runner_pct",
    "runner_rule",
    "final_target_points",
)


GENERATED_EXPERIMENT_SCHEMA = pa.schema(
    [
        ("experiment_id", pa.string()),
        ("family", pa.string()),
        ("generation", pa.int64()),
        ("experiment_name", pa.string()),
        ("config_sha256", pa.string()),
        ("created_at", pa.string()),
        ("engine_version", pa.string()),
        ("rules_version", pa.string()),
        ("definition_sha256", pa.string()),

        ("trade1_config_sha256", pa.string()),
        ("trade2_override_sha256", pa.string()),
        (
            "trade2_effective_config_sha256",
            pa.string(),
        ),
        (
            "trade2_has_explicit_overrides",
            pa.bool_(),
        ),
        ("trade2_enabled", pa.bool_()),
        ("trade2_management_mode", pa.string()),

        ("trade2_stop_mode", pa.string()),
        ("trade2_stop_points", pa.float64()),

        ("trade2_partial_1_mode", pa.string()),
        ("trade2_partial_1_points", pa.float64()),
        ("trade2_partial_1_pct", pa.float64()),

        ("trade2_partial_2_mode", pa.string()),
        ("trade2_partial_2_points", pa.float64()),
        ("trade2_partial_2_pct", pa.float64()),

        ("trade2_partial_3_mode", pa.string()),
        ("trade2_partial_3_points", pa.float64()),
        ("trade2_partial_3_pct", pa.float64()),

        ("trade2_break_even_mode", pa.string()),
        (
            "trade2_break_even_after_partial",
            pa.int64(),
        ),

        ("trade2_runner_mode", pa.string()),
        ("trade2_runner_pct", pa.float64()),
        ("trade2_runner_rule", pa.string()),

        ("trade2_final_target_mode", pa.string()),
        (
            "trade2_final_target_points",
            pa.float64(),
        ),

        ("stop_points", pa.float64()),
        ("partial_1_points", pa.float64()),
        ("partial_1_pct", pa.float64()),
        ("partial_2_points", pa.float64()),
        ("partial_2_pct", pa.float64()),
        ("partial_3_points", pa.float64()),
        ("partial_3_pct", pa.float64()),
        ("break_even_enabled", pa.bool_()),
        ("break_even_after_partial", pa.int64()),
        ("runner_enabled", pa.bool_()),
        ("runner_pct", pa.float64()),
        ("runner_rule", pa.string()),
        ("final_target_points", pa.float64()),
    ]
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


def _sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_file(
    path: str | Path,
) -> str:
    path = Path(path)

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _management_config_from_config(
    config: dict[str, Any],
) -> ManagementConfig:
    return ManagementConfig(
        stop_points=float(
            config[
                "stop_points"
            ]
        ),
        partial_1_points=(
            config.get(
                "partial_1_points"
            )
        ),
        partial_1_pct=(
            config.get(
                "partial_1_pct"
            )
        ),
        partial_2_points=(
            config.get(
                "partial_2_points"
            )
        ),
        partial_2_pct=(
            config.get(
                "partial_2_pct"
            )
        ),
        partial_3_points=(
            config.get(
                "partial_3_points"
            )
        ),
        partial_3_pct=(
            config.get(
                "partial_3_pct"
            )
        ),
        break_even_enabled=bool(
            config.get(
                "break_even_enabled"
            )
        ),
        break_even_after_partial=(
            config.get(
                "break_even_after_partial"
            )
        ),
        final_target_points=(
            config.get(
                "final_target_points"
            )
        ),
        runner_enabled=bool(
            config.get(
                "runner_enabled"
            )
        ),
        runner_pct=(
            config.get(
                "runner_pct"
            )
        ),
        runner_exit_rule=(
            config.get(
                "runner_rule"
            )
        ),
        position_size=100.0,
    )


def _global_config_sha256(
    *,
    trade1_config: dict[str, Any],
    trade2_overrides: dict[str, Any],
    trade2_enabled: bool | None = None,
    trade2_management_mode: str | None = None,
) -> str:
    trade2_overrides = (
        normalize_trade2_overrides(
            trade2_overrides
        )
    )

    trade1_hash = config_sha256(
        trade1_config
    )

    control_row: dict[str, Any] = {}

    if trade2_enabled is not None:
        control_row[
            "trade2_enabled"
        ] = bool(
            trade2_enabled
        )

    if trade2_management_mode is not None:
        control_row[
            "trade2_management_mode"
        ] = str(
            trade2_management_mode
        )

    control = trade2_control_from_row(
        control_row
    )

    #
    # BACKWARD COMPATIBILITY:
    # chamada/artifact legado sem controle
    # explícito e sem override preserva
    # EXATAMENTE o hash histórico.
    #
    if (
        control[
            "legacy_semantics"
        ]
        and not trade2_has_explicit_overrides(
            trade2_overrides
        )
    ):
        return trade1_hash

    trade1_management = (
        _management_config_from_config(
            trade1_config
        )
    )

    effective_trade2 = (
        resolve_trade2_management_config(
            trade1_config=(
                trade1_management
            ),
            overrides=(
                trade2_overrides
            ),
            validate_effective=False,
        )
    )

    payload = {
        "trade1_config_sha256": (
            trade1_hash
        ),
        "trade2_enabled": (
            control[
                "trade2_enabled"
            ]
        ),
        "trade2_management_mode": (
            control[
                "trade2_management_mode"
            ]
        ),
        "trade2_override_sha256": (
            trade2_override_sha256(
                trade2_overrides
            )
        ),
        (
            "trade2_effective_config_sha256"
        ): (
            management_config_sha256(
                effective_trade2
            )
        ),
    }

    return _sha256_text(
        _canonical_json(
            payload
        )
    )


def config_sha256(
    config: dict[str, Any],
) -> str:
    canonical = {
        field: config.get(field)
        for field in CONFIG_FIELDS
    }

    return _sha256_text(
        _canonical_json(
            canonical
        )
    )


def definition_sha256(
    *,
    family: str,
    generation: int,
    created_at: str,
    engine_version: str,
    rules_version: str,
    base_config: dict[str, Any],
    parameter_definition: dict[
        str,
        dict[str, Any],
    ],
) -> str:
    payload = {
        "family": family,
        "generation": generation,
        "created_at": created_at,
        "engine_version": engine_version,
        "rules_version": rules_version,
        "base_config": base_config,
        "parameter_definition": (
            parameter_definition
        ),
    }

    return _sha256_text(
        _canonical_json(payload)
    )


def _normalize_number(
    value: Decimal,
) -> int | float:
    if value == value.to_integral():
        return int(value)

    return float(value)


def expand_range(
    *,
    start: int | float,
    end: int | float,
    step: int | float,
) -> list[int | float]:
    start_decimal = Decimal(
        str(start)
    )

    end_decimal = Decimal(
        str(end)
    )

    step_decimal = Decimal(
        str(step)
    )

    if step_decimal == 0:
        raise ValueError(
            "Range step cannot be zero."
        )

    if (
        start_decimal < end_decimal
        and step_decimal < 0
    ):
        raise ValueError(
            "Ascending range requires "
            "a positive step."
        )

    if (
        start_decimal > end_decimal
        and step_decimal > 0
    ):
        raise ValueError(
            "Descending range requires "
            "a negative step."
        )

    values: list[
        int | float
    ] = []

    current = start_decimal

    if step_decimal > 0:
        while current <= end_decimal:
            values.append(
                _normalize_number(
                    current
                )
            )

            current += step_decimal

    else:
        while current >= end_decimal:
            values.append(
                _normalize_number(
                    current
                )
            )

            current += step_decimal

    return values


def expand_parameter(
    definition: dict[str, Any],
) -> list[Any]:
    if "values" in definition:
        values = list(
            definition["values"]
        )

        if not values:
            raise ValueError(
                "Parameter values "
                "cannot be empty."
            )

        return values

    required = {
        "start",
        "end",
        "step",
    }

    if required.issubset(
        definition
    ):
        return expand_range(
            start=definition[
                "start"
            ],
            end=definition[
                "end"
            ],
            step=definition[
                "step"
            ],
        )

    raise ValueError(
        "Parameter definition must "
        "contain either values or "
        "start/end/step."
    )


def generate_configurations(
    *,
    base_config: dict[str, Any],
    parameter_definition: dict[
        str,
        dict[str, Any],
    ],
    trade2_base_overrides: (
        dict[str, Any]
        | None
    ) = None,
    trade2_parameter_definition: (
        dict[
            str,
            dict[str, Any],
        ]
        | None
    ) = None,
    trade2_enabled: (
        bool
        | None
    ) = None,
    trade2_management_mode: (
        str
        | None
    ) = None,
) -> list[dict[str, Any]]:
    parameter_names = list(
        parameter_definition.keys()
    )

    parameter_values = [
        expand_parameter(
            parameter_definition[
                name
            ]
        )
        for name in parameter_names
    ]

    trade2_definition = (
        trade2_parameter_definition
        or {}
    )

    trade2_parameter_names = list(
        trade2_definition.keys()
    )

    for name in trade2_parameter_names:
        if (
            name
            not in TRADE2_OVERRIDE_FIELDS
        ):
            raise ValueError(
                (
                    "Unsupported Trade 2 "
                    "parameter: "
                    f"{name}"
                )
            )

    trade2_parameter_values = [
        expand_parameter(
            trade2_definition[
                name
            ]
        )
        for name in (
            trade2_parameter_names
        )
    ]

    trade2_combinations = (
        list(
            product(
                *trade2_parameter_values
            )
        )
        if trade2_parameter_names
        else [
            ()
        ]
    )

    configurations = []

    for combination in product(
        *parameter_values
    ):
        config = dict(
            base_config
        )

        for (
            parameter_name,
            parameter_value,
        ) in zip(
            parameter_names,
            combination,
        ):
            config[
                parameter_name
            ] = parameter_value

        complete = {
            field: config.get(field)
            for field in CONFIG_FIELDS
        }

        for trade2_combination in (
            trade2_combinations
        ):
            overrides = {
                field: value
                for field, value
                in (
                    trade2_base_overrides
                    or {}
                ).items()
                if field
                in TRADE2_OVERRIDE_FIELDS
            }

            for (
                parameter_name,
                parameter_value,
            ) in zip(
                trade2_parameter_names,
                trade2_combination,
            ):
                overrides[
                    parameter_name
                ] = parameter_value

            from operar_range.trade2_configuration import (
                normalize_trade2_overrides,
            )

            normalized = (
                normalize_trade2_overrides(
                    overrides
                )
            )

            combined = dict(
                complete
            )

            combined.update(
                normalized
            )

            if trade2_enabled is not None:
                combined[
                    "trade2_enabled"
                ] = bool(
                    trade2_enabled
                )

            if (
                trade2_management_mode
                is not None
            ):
                combined[
                    "trade2_management_mode"
                ] = str(
                    trade2_management_mode
                )

            configurations.append(
                combined
            )

    return configurations


def _experiment_number(
    experiment_id: str,
) -> int | None:
    match = re.fullmatch(
        r"EXP-(\d{6})",
        str(experiment_id),
    )

    if match is None:
        return None

    return int(
        match.group(1)
    )


def _read_existing_rows(
    path: str | Path | None,
) -> list[dict[str, Any]]:
    if path is None:
        return []

    path = Path(path)

    if not path.exists():
        return []

    return pq.read_table(
        path
    ).to_pylist()


def _normalized_paths(
    paths: list[
        str | Path | None
    ],
) -> list[Path]:
    normalized: list[
        Path
    ] = []

    seen: set[str] = set()

    for raw_path in paths:
        if raw_path is None:
            continue

        path = Path(
            raw_path
        )

        key = str(
            path
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        normalized.append(
            path
        )

    return normalized


def _reserved_ids(
    paths: list[
        str | Path | None
    ],
) -> set[str]:
    reserved: set[str] = set()

    for path in _normalized_paths(
        paths
    ):
        for row in (
            _read_existing_rows(
                path
            )
        ):
            experiment_id = (
                row.get(
                    "experiment_id"
                )
            )

            if experiment_id:
                reserved.add(
                    str(
                        experiment_id
                    )
                )

    return reserved


def _existing_hash_id_map(
    paths: list[
        str | Path | None
    ],
) -> dict[str, str]:
    mapping: dict[
        str,
        str
    ] = {}

    for path in _normalized_paths(
        paths
    ):
        for row in (
            _read_existing_rows(
                path
            )
        ):
            config_hash = row.get(
                "config_sha256"
            )

            experiment_id = row.get(
                "experiment_id"
            )

            if (
                not config_hash
                or not experiment_id
            ):
                continue

            config_hash = str(
                config_hash
            )

            experiment_id = str(
                experiment_id
            )

            existing_id = mapping.get(
                config_hash
            )

            if (
                existing_id is not None
                and existing_id
                != experiment_id
            ):
                raise RuntimeError(
                    "Same config_sha256 "
                    "is associated with "
                    "different experiment IDs: "
                    f"{config_hash}: "
                    f"{existing_id}, "
                    f"{experiment_id}"
                )

            mapping[
                config_hash
            ] = experiment_id

    return mapping


def _next_available_id(
    *,
    reserved: set[str],
    start_after: int,
) -> tuple[str, int]:
    number = (
        start_after + 1
    )

    while True:
        experiment_id = (
            f"EXP-{number:06d}"
        )

        if (
            experiment_id
            not in reserved
        ):
            return (
                experiment_id,
                number,
            )

        number += 1


def assign_experiment_ids(
    *,
    configurations: list[
        dict[str, Any]
    ],
    existing_generated_path: (
        str | Path | None
    ) = None,
    registry_path: (
        str | Path | None
    ) = None,
    reserved_paths: list[
        str | Path | None
    ] | None = None,
) -> list[
    tuple[
        str,
        dict[str, Any],
        str,
    ]
]:
    reserved_paths = (
        reserved_paths or []
    )

    identity_paths = [
        registry_path,
        *reserved_paths,
        existing_generated_path,
    ]

    reserved = _reserved_ids(
        identity_paths
    )

    existing_hash_map = (
        _existing_hash_id_map(
            identity_paths
        )
    )

    numbers = [
        number
        for experiment_id in reserved
        if (
            number
            := _experiment_number(
                experiment_id
            )
        )
        is not None
    ]

    current_max = (
        max(numbers)
        if numbers
        else 0
    )

    assigned = []

    assigned_hashes: dict[
        str,
        str
    ] = {}

    for config in configurations:
        trade1_config = {
            field: config.get(
                field
            )
            for field in CONFIG_FIELDS
        }

        trade2_overrides = {
            field: config[
                field
            ]
            for field
            in TRADE2_OVERRIDE_FIELDS
            if field in config
        }

        config_hash = (
            _global_config_sha256(
                trade1_config=(
                    trade1_config
                ),
                trade2_overrides=(
                    trade2_overrides
                ),
                trade2_enabled=(
                    config.get(
                        "trade2_enabled"
                    )
                ),
                trade2_management_mode=(
                    config.get(
                        "trade2_management_mode"
                    )
                ),
            )
        )

        existing_id = (
            existing_hash_map.get(
                config_hash
            )
        )

        if existing_id is None:
            existing_id = (
                assigned_hashes.get(
                    config_hash
                )
            )

        if existing_id:
            experiment_id = (
                existing_id
            )

        else:
            (
                experiment_id,
                current_max,
            ) = _next_available_id(
                reserved=reserved,
                start_after=(
                    current_max
                ),
            )

            reserved.add(
                experiment_id
            )

            assigned_hashes[
                config_hash
            ] = experiment_id

        assigned.append(
            (
                experiment_id,
                config,
                config_hash,
            )
        )

    return assigned


def build_experiment_rows(
    *,
    family: str,
    generation: int,
    created_at: str,
    rules_version: str,
    base_config: dict[str, Any],
    parameter_definition: dict[
        str,
        dict[str, Any],
    ],
    trade2_base_overrides: (
        dict[str, Any]
        | None
    ) = None,
    trade2_parameter_definition: (
        dict[
            str,
            dict[str, Any],
        ]
        | None
    ) = None,
    trade2_enabled: (
        bool
        | None
    ) = None,
    trade2_management_mode: (
        str
        | None
    ) = None,
    engine_version: str = (
        GENERATOR_VERSION
    ),
    existing_generated_path: (
        str | Path | None
    ) = None,
    registry_path: (
        str | Path | None
    ) = None,
    reserved_paths: list[
        str | Path | None
    ] | None = None,
) -> list[dict[str, Any]]:
    configurations = (
        generate_configurations(
            base_config=base_config,
            parameter_definition=(
                parameter_definition
            ),
            trade2_base_overrides=(
                trade2_base_overrides
            ),
            trade2_parameter_definition=(
                trade2_parameter_definition
            ),
            trade2_enabled=(
                trade2_enabled
            ),
            trade2_management_mode=(
                trade2_management_mode
            ),
        )
    )

    assigned = assign_experiment_ids(
        configurations=configurations,
        existing_generated_path=(
            existing_generated_path
        ),
        registry_path=registry_path,
        reserved_paths=reserved_paths,
    )

    definition_hash = (
        definition_sha256(
            family=family,
            generation=generation,
            created_at=created_at,
            engine_version=(
                engine_version
            ),
            rules_version=(
                rules_version
            ),
            base_config=base_config,
            parameter_definition=(
                parameter_definition
            ),
        )
    )

    rows: list[
        dict[str, Any]
    ] = []

    for (
        experiment_id,
        config,
        config_hash,
    ) in assigned:
        experiment_name = (
            f"{family}_"
            f"G{generation}_"
            f"{experiment_id}"
        )

        row = {
            "experiment_id": (
                experiment_id
            ),
            "family": family,
            "generation": int(
                generation
            ),
            "experiment_name": (
                experiment_name
            ),
            "config_sha256": (
                config_hash
            ),
            "created_at": (
                created_at
            ),
            "engine_version": (
                engine_version
            ),
            "rules_version": (
                rules_version
            ),
            "definition_sha256": (
                definition_hash
            ),
        }

        trade1_config = {
            field: config.get(
                field
            )
            for field in CONFIG_FIELDS
        }

        trade1_management = (
            _management_config_from_config(
                trade1_config
            )
        )

        trade2_overrides = {
            field: config[
                field
            ]
            for field
            in TRADE2_OVERRIDE_FIELDS
            if field in config
        }

        normalized_trade2 = (
            normalize_trade2_overrides(
                trade2_overrides
            )
        )

        effective_trade2 = (
            resolve_trade2_management_config(
                trade1_config=(
                    trade1_management
                ),
                overrides=(
                    normalized_trade2
                ),
                validate_effective=False,
            )
        )

        row[
            "trade1_config_sha256"
        ] = config_sha256(
            trade1_config
        )

        row[
            "trade2_override_sha256"
        ] = trade2_override_sha256(
            normalized_trade2
        )

        row[
            "trade2_effective_config_sha256"
        ] = management_config_sha256(
            effective_trade2
        )

        row[
            "trade2_has_explicit_overrides"
        ] = trade2_has_explicit_overrides(
            normalized_trade2
        )

        row[
            "trade2_enabled"
        ] = config.get(
            "trade2_enabled"
        )

        row[
            "trade2_management_mode"
        ] = config.get(
            "trade2_management_mode"
        )

        for field in CONFIG_FIELDS:
            row[field] = (
                config.get(
                    field
                )
            )

        for field in (
            TRADE2_OVERRIDE_FIELDS
        ):
            row[field] = (
                normalized_trade2.get(
                    field
                )
            )

        rows.append(
            row
        )

    return rows


def write_generated_experiments(
    rows: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        rows,
        schema=(
            GENERATED_EXPERIMENT_SCHEMA
        ),
    )

    pq.write_table(
        table,
        output_path,
        compression="zstd",
    )

    return output_path


def generate_experiment_database(
    *,
    output_path: str | Path,
    family: str,
    generation: int,
    created_at: str,
    rules_version: str,
    base_config: dict[str, Any],
    parameter_definition: dict[
        str,
        dict[str, Any],
    ],
    trade2_base_overrides: (
        dict[str, Any]
        | None
    ) = None,
    trade2_parameter_definition: (
        dict[
            str,
            dict[str, Any],
        ]
        | None
    ) = None,
    trade2_enabled: (
        bool
        | None
    ) = None,
    trade2_management_mode: (
        str
        | None
    ) = None,
    engine_version: str = (
        GENERATOR_VERSION
    ),
    existing_generated_path: (
        str | Path | None
    ) = None,
    registry_path: (
        str | Path | None
    ) = None,
    reserved_paths: list[
        str | Path | None
    ] | None = None,
    register_generated: bool = True,
) -> dict[str, Any]:
    rows = build_experiment_rows(
        family=family,
        generation=generation,
        created_at=created_at,
        rules_version=rules_version,
        base_config=base_config,
        parameter_definition=(
            parameter_definition
        ),
        trade2_base_overrides=(
            trade2_base_overrides
        ),
        trade2_parameter_definition=(
            trade2_parameter_definition
        ),
        trade2_enabled=(
            trade2_enabled
        ),
        trade2_management_mode=(
            trade2_management_mode
        ),
        engine_version=(
            engine_version
        ),
        existing_generated_path=(
            existing_generated_path
        ),
        registry_path=(
            registry_path
        ),
        reserved_paths=(
            reserved_paths
        ),
    )

    generated_path = (
        write_generated_experiments(
            rows=rows,
            output_path=output_path,
        )
    )

    registry_result = None

    if (
        register_generated
        and registry_path is not None
    ):
        registry_result = (
            migrate_registry(
                registry_path=(
                    registry_path
                ),
                source_paths=[
                    generated_path,
                ],
            )
        )

    definition_hashes = sorted(
        {
            row[
                "definition_sha256"
            ]
            for row in rows
            if row.get(
                "definition_sha256"
            )
        }
    )

    if len(
        definition_hashes
    ) == 1:
        generated_definition_hash = (
            definition_hashes[0]
        )

    else:
        generated_definition_hash = (
            _sha256_text(
                _canonical_json(
                    definition_hashes
                )
            )
        )

    result = {
        "rows": rows,
        "experiment_count": len(
            rows
        ),
        "output_path": str(
            generated_path
        ),
        "sha256": sha256_file(
            generated_path
        ),
        "definition_sha256": (
            generated_definition_hash
        ),
        "registry_updated": (
            registry_result is not None
        ),
    }

    if registry_result is not None:
        result[
            "registry_new_experiments"
        ] = registry_result[
            "new_experiments"
        ]

        result[
            "registry_next_available_id"
        ] = registry_result[
            "next_available_id"
        ]

        result[
            "registry_sha256"
        ] = registry_result[
            "registry_sha256"
        ]

        result[
            "registry_path"
        ] = registry_result[
            "registry_path"
        ]

    return result