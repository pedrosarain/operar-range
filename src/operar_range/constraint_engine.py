from __future__ import annotations

import hashlib
import inspect
import json
import math
import textwrap
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pyarrow as pa
import pyarrow.parquet as pq


ENGINE_VERSION = "constraint-engine-v1"
RULE_VERSION = "1"
SUPPORTED_RUNNER_RULES = {
    "CANDLE_BREAK_M5",
}


@dataclass(frozen=True)
class Finding:
    rule_code: str
    message: str
    severity: str


@dataclass(frozen=True)
class Rule:
    rule_code: str
    rule_name: str
    version: str
    severity: str
    description: str
    active: bool
    evaluator: Callable[
        [dict[str, Any]],
        list[Finding],
    ]


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


def _is_number(
    value: Any,
) -> bool:
    if isinstance(
        value,
        bool,
    ):
        return False

    if not isinstance(
        value,
        (int, float),
    ):
        return False

    return math.isfinite(
        float(value)
    )


def _configured_partial(
    config: dict[str, Any],
    number: int,
) -> bool:
    points = config.get(
        f"partial_{number}_points"
    )

    pct = config.get(
        f"partial_{number}_pct"
    )

    return (
        points is not None
        and pct is not None
    )


def _explicit_allocations(
    config: dict[str, Any],
) -> list[float]:
    values: list[float] = []

    for number in (
        1,
        2,
        3,
    ):
        points = config.get(
            f"partial_{number}_points"
        )

        pct = config.get(
            f"partial_{number}_pct"
        )

        if (
            points is not None
            and pct is not None
            and _is_number(pct)
        ):
            values.append(
                float(pct)
            )

    if (
        config.get(
            "runner_enabled"
        )
        is True
    ):
        runner_pct = config.get(
            "runner_pct"
        )

        if _is_number(
            runner_pct
        ):
            values.append(
                float(runner_pct)
            )

    return values


def _finding(
    rule: Rule,
    message: str,
) -> Finding:
    return Finding(
        rule_code=rule.rule_code,
        message=message,
        severity=rule.severity,
    )


def _eval_c001(
    config: dict[str, Any],
) -> list[Finding]:
    value = config.get(
        "stop_points"
    )

    if (
        not _is_number(value)
        or float(value) <= 0
    ):
        return [
            Finding(
                "C001",
                (
                    "stop_points must be a "
                    "positive numeric value."
                ),
                "ERROR",
            )
        ]

    return []


def _eval_c002(
    config: dict[str, Any],
) -> list[Finding]:
    findings = []

    fields = (
        "partial_1_pct",
        "partial_2_pct",
        "partial_3_pct",
        "runner_pct",
    )

    for field in fields:
        value = config.get(field)

        if value is None:
            continue

        if (
            not _is_number(value)
            or not (
                0
                < float(value)
                <= 100
            )
        ):
            findings.append(
                Finding(
                    "C002",
                    (
                        f"{field} must satisfy "
                        "0 < pct <= 100."
                    ),
                    "ERROR",
                )
            )

    return findings


def _eval_c003(
    config: dict[str, Any],
) -> list[Finding]:
    total = sum(
        _explicit_allocations(
            config
        )
    )

    if total > 100 + 1e-12:
        return [
            Finding(
                "C003",
                (
                    "Explicit allocation "
                    f"totals {total}%, above "
                    "100%."
                ),
                "ERROR",
            )
        ]

    return []


def _eval_c004(
    config: dict[str, Any],
) -> list[Finding]:
    findings = []

    for number in (
        1,
        2,
        3,
    ):
        points = config.get(
            f"partial_{number}_points"
        )

        pct = config.get(
            f"partial_{number}_pct"
        )

        if (
            points is None
        ) != (
            pct is None
        ):
            findings.append(
                Finding(
                    "C004",
                    (
                        f"Partial {number} "
                        "must define both "
                        "points and percentage."
                    ),
                    "ERROR",
                )
            )

    return findings


def _eval_c005(
    config: dict[str, Any],
) -> list[Finding]:
    configured = []

    for number in (
        1,
        2,
        3,
    ):
        if not _configured_partial(
            config,
            number,
        ):
            continue

        value = config.get(
            f"partial_{number}_points"
        )

        if not _is_number(
            value
        ):
            continue

        configured.append(
            (
                number,
                float(value),
            )
        )

    for (
        previous,
        current,
    ) in zip(
        configured,
        configured[1:],
    ):
        if (
            previous[1]
            >= current[1]
        ):
            return [
                Finding(
                    "C005",
                    (
                        "Configured partial "
                        "targets must be "
                        "strictly increasing."
                    ),
                    "ERROR",
                )
            ]

    return []


def _eval_c006(
    config: dict[str, Any],
) -> list[Finding]:
    if (
        config.get(
            "break_even_enabled"
        )
        is not True
    ):
        return []

    target = config.get(
        "break_even_after_partial"
    )

    if target not in (
        1,
        2,
        3,
    ):
        return [
            Finding(
                "C006",
                (
                    "Break-even enabled "
                    "without a valid partial "
                    "reference."
                ),
                "ERROR",
            )
        ]

    if not _configured_partial(
        config,
        int(target),
    ):
        return [
            Finding(
                "C006",
                (
                    "Break-even references "
                    "a partial that is not "
                    "configured."
                ),
                "ERROR",
            )
        ]

    return []


def _eval_c007(
    config: dict[str, Any],
) -> list[Finding]:
    if (
        config.get(
            "break_even_enabled"
        )
        is True
    ):
        return []

    if (
        config.get(
            "break_even_after_partial"
        )
        is not None
    ):
        return [
            Finding(
                "C007",
                (
                    "break_even_after_partial "
                    "is active while "
                    "break_even_enabled is "
                    "false."
                ),
                "ERROR",
            )
        ]

    return []


def _eval_c008(
    config: dict[str, Any],
) -> list[Finding]:
    if (
        config.get(
            "runner_enabled"
        )
        is not True
    ):
        return []

    findings = []

    pct = config.get(
        "runner_pct"
    )

    rule = config.get(
        "runner_rule"
    )

    if (
        not _is_number(pct)
        or float(pct) <= 0
    ):
        findings.append(
            Finding(
                "C008",
                (
                    "Runner enabled without "
                    "valid runner_pct."
                ),
                "ERROR",
            )
        )

    if (
        rule
        not in SUPPORTED_RUNNER_RULES
    ):
        findings.append(
            Finding(
                "C008",
                (
                    "Runner enabled without "
                    "a supported runner_rule."
                ),
                "ERROR",
            )
        )

    return findings


def _eval_c009(
    config: dict[str, Any],
) -> list[Finding]:
    if (
        config.get(
            "runner_enabled"
        )
        is True
    ):
        return []

    runner_pct = config.get(
        "runner_pct"
    )

    runner_rule = config.get(
        "runner_rule"
    )

    pct_active = (
        runner_pct is not None
        and (
            not _is_number(
                runner_pct
            )
            or float(
                runner_pct
            ) > 0
        )
    )

    rule_active = (
        runner_rule
        not in (
            None,
            "",
        )
    )

    if (
        pct_active
        or rule_active
    ):
        return [
            Finding(
                "C009",
                (
                    "Runner is disabled but "
                    "runner fields remain "
                    "active."
                ),
                "ERROR",
            )
        ]

    return []


def _eval_c010(
    config: dict[str, Any],
) -> list[Finding]:
    total = sum(
        _explicit_allocations(
            config
        )
    )

    if total > 100 + 1e-12:
        return [
            Finding(
                "C010",
                (
                    "Total explicitly closed "
                    f"position is {total}%, "
                    "above 100%."
                ),
                "ERROR",
            )
        ]

    return []


def _eval_c011(
    config: dict[str, Any],
) -> list[Finding]:
    final_target = config.get(
        "final_target_points"
    )

    if final_target is None:
        return []

    total = sum(
        _explicit_allocations(
            config
        )
    )

    if total >= 100 - 1e-12:
        return [
            Finding(
                "C011",
                (
                    "final_target_points is "
                    "configured but no "
                    "undeclared residual "
                    "position remains."
                ),
                "ERROR",
            )
        ]

    return []


def _eval_c012(
    config: dict[str, Any],
) -> list[Finding]:
    value = config.get(
        "final_target_points"
    )

    if value is None:
        return []

    if (
        not _is_number(value)
        or float(value) <= 0
    ):
        return [
            Finding(
                "C012",
                (
                    "final_target_points must "
                    "be positive when "
                    "configured."
                ),
                "ERROR",
            )
        ]

    return []


def _eval_c013(
    config: dict[str, Any],
) -> list[Finding]:
    if (
        config.get(
            "runner_enabled"
        )
        is True
        and config.get(
            "final_target_points"
        )
        is not None
    ):
        return [
            Finding(
                "C013",
                (
                    "Runner and final target "
                    "are conflicting destinations "
                    "for the same remaining "
                    "position."
                ),
                "ERROR",
            )
        ]

    return []


RULES = (
    Rule(
        "C001",
        "INVALID_STOP",
        RULE_VERSION,
        "ERROR",
        (
            "stop_points must be a "
            "positive number."
        ),
        True,
        _eval_c001,
    ),
    Rule(
        "C002",
        "INVALID_PERCENTAGE",
        RULE_VERSION,
        "ERROR",
        (
            "Configured percentages must "
            "satisfy 0 < pct <= 100."
        ),
        True,
        _eval_c002,
    ),
    Rule(
        "C003",
        "PERCENTAGE_SUM",
        RULE_VERSION,
        "ERROR",
        (
            "Explicit allocation cannot "
            "exceed 100%."
        ),
        True,
        _eval_c003,
    ),
    Rule(
        "C004",
        "INCOMPLETE_PARTIAL",
        RULE_VERSION,
        "ERROR",
        (
            "Partial points and percentage "
            "must be configured together."
        ),
        True,
        _eval_c004,
    ),
    Rule(
        "C005",
        "PARTIAL_ORDER",
        RULE_VERSION,
        "ERROR",
        (
            "Configured partial targets "
            "must be strictly increasing."
        ),
        True,
        _eval_c005,
    ),
    Rule(
        "C006",
        "BREAK_EVEN_WITHOUT_PARTIAL",
        RULE_VERSION,
        "ERROR",
        (
            "Break-even must reference an "
            "existing partial."
        ),
        True,
        _eval_c006,
    ),
    Rule(
        "C007",
        "INACTIVE_BREAK_EVEN_REFERENCE",
        RULE_VERSION,
        "ERROR",
        (
            "Disabled break-even cannot "
            "retain an active partial "
            "reference."
        ),
        True,
        _eval_c007,
    ),
    Rule(
        "C008",
        "INCONSISTENT_RUNNER",
        RULE_VERSION,
        "ERROR",
        (
            "Enabled runner requires "
            "percentage and supported rule."
        ),
        True,
        _eval_c008,
    ),
    Rule(
        "C009",
        "DISABLED_RUNNER_WITH_FIELDS",
        RULE_VERSION,
        "ERROR",
        (
            "Disabled runner cannot retain "
            "active runner fields."
        ),
        True,
        _eval_c009,
    ),
    Rule(
        "C010",
        "TOTAL_POSITION_EXCEEDED",
        RULE_VERSION,
        "ERROR",
        (
            "Explicit closing allocation "
            "cannot exceed 100%."
        ),
        True,
        _eval_c010,
    ),
    Rule(
        "C011",
        "FINAL_TARGET_WITHOUT_POSITION",
        RULE_VERSION,
        "ERROR",
        (
            "A final target requires "
            "possible residual position."
        ),
        True,
        _eval_c011,
    ),
    Rule(
        "C012",
        "INVALID_FINAL_TARGET",
        RULE_VERSION,
        "ERROR",
        (
            "Final target must be positive."
        ),
        True,
        _eval_c012,
    ),
    Rule(
        "C013",
        "RUNNER_FINAL_TARGET_CONFLICT",
        RULE_VERSION,
        "ERROR",
        (
            "Runner and final target are "
            "mutually exclusive while they "
            "refer to the same remaining "
            "position."
        ),
        True,
        _eval_c013,
    ),
)


RULE_MANIFEST_SCHEMA = pa.schema(
    [
        ("rule_code", pa.string()),
        ("rule_name", pa.string()),
        ("version", pa.string()),
        ("severity", pa.string()),
        ("description", pa.string()),
        ("active", pa.bool_()),
        ("created_at", pa.string()),
        ("evaluator_sha256", pa.string()),
    ]
)


EXTRA_SCHEMA = (
    ("constraint_status", pa.string()),
    ("rejection_count", pa.int64()),
    (
        "rejection_codes",
        pa.list_(pa.string()),
    ),
    ("rejection_details", pa.string()),
    ("warning_count", pa.int64()),
    (
        "warning_codes",
        pa.list_(pa.string()),
    ),
    ("warning_details", pa.string()),
    ("rule_set_sha256", pa.string()),
)


def evaluator_sha256(
    rule: Rule,
) -> str:
    source = textwrap.dedent(
        inspect.getsource(
            rule.evaluator
        )
    ).strip()

    return _sha256_text(source)


def rule_set_sha256(
    rules: tuple[Rule, ...] = RULES,
) -> str:
    payload = []

    for rule in sorted(
        (
            item
            for item in rules
            if item.active
        ),
        key=lambda item: (
            item.rule_code
        ),
    ):
        payload.append(
            {
                "rule_code": (
                    rule.rule_code
                ),
                "rule_name": (
                    rule.rule_name
                ),
                "version": (
                    rule.version
                ),
                "severity": (
                    rule.severity
                ),
                "active": (
                    rule.active
                ),
                "description": (
                    rule.description
                ),
                "evaluator_sha256": (
                    evaluator_sha256(
                        rule
                    )
                ),
            }
        )

    return _sha256_text(
        _canonical_json(
            payload
        )
    )


def rule_manifest_rows(
    *,
    created_at: str,
    rules: tuple[Rule, ...] = RULES,
) -> list[dict[str, Any]]:
    return [
        {
            "rule_code": (
                rule.rule_code
            ),
            "rule_name": (
                rule.rule_name
            ),
            "version": (
                rule.version
            ),
            "severity": (
                rule.severity
            ),
            "description": (
                rule.description
            ),
            "active": (
                rule.active
            ),
            "created_at": (
                created_at
            ),
            "evaluator_sha256": (
                evaluator_sha256(
                    rule
                )
            ),
        }
        for rule in sorted(
            rules,
            key=lambda item: (
                item.rule_code
            ),
        )
    ]


def evaluate_config(
    config: dict[str, Any],
    *,
    rules: tuple[Rule, ...] = RULES,
) -> tuple[
    list[Finding],
    list[Finding],
]:
    errors = []
    warnings = []

    for rule in rules:
        if not rule.active:
            continue

        findings = rule.evaluator(
            config
        )

        for finding in findings:
            if (
                finding.severity
                == "ERROR"
            ):
                errors.append(
                    finding
                )

            elif (
                finding.severity
                == "WARNING"
            ):
                warnings.append(
                    finding
                )

            else:
                raise ValueError(
                    "Unsupported severity: "
                    f"{finding.severity}"
                )

    return (
        errors,
        warnings,
    )


def _validate_registry_identity(
    generated_rows: list[
        dict[str, Any]
    ],
    registry_rows: list[
        dict[str, Any]
    ],
) -> None:
    registry = {
        row["experiment_id"]: row
        for row in registry_rows
    }

    for row in generated_rows:
        experiment_id = row[
            "experiment_id"
        ]

        if experiment_id not in registry:
            raise RuntimeError(
                "Experiment missing from "
                "official Registry: "
                f"{experiment_id}"
            )

        registered = registry[
            experiment_id
        ]

        if (
            registered.get(
                "config_sha256"
            )
            != row.get(
                "config_sha256"
            )
        ):
            raise RuntimeError(
                "Registry identity mismatch "
                f"for {experiment_id}."
            )


def _output_schema(
    source_schema: pa.Schema,
) -> pa.Schema:
    fields = list(
        source_schema
    )

    names = {
        field.name
        for field in fields
    }

    for (
        name,
        data_type,
    ) in EXTRA_SCHEMA:
        if name not in names:
            fields.append(
                pa.field(
                    name,
                    data_type,
                )
            )

    return pa.schema(
        fields
    )


def _write_rows(
    rows: list[dict[str, Any]],
    path: Path,
    schema: pa.Schema,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        rows,
        schema=schema,
    )

    pq.write_table(
        table,
        path,
        compression="zstd",
    )


def _write_rule_manifest(
    *,
    path: Path,
    created_at: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        rule_manifest_rows(
            created_at=created_at
        ),
        schema=RULE_MANIFEST_SCHEMA,
    )

    pq.write_table(
        table,
        path,
        compression="zstd",
    )


def run_constraint_engine(
    *,
    generated_path: str | Path = (
        "data/research/"
        "generated_experiments.parquet"
    ),
    registry_path: str | Path = (
        "data/research/"
        "experiment_registry.parquet"
    ),
    valid_path: str | Path = (
        "data/research/"
        "valid_experiments.parquet"
    ),
    rejected_path: str | Path = (
        "data/research/"
        "rejected_experiments.parquet"
    ),
    rules_path: str | Path = (
        "data/research/"
        "constraint_rules.parquet"
    ),
    summary_path: str | Path = (
        "data/reports/"
        "constraint_engine_summary.json"
    ),
    executed_at: str | None = None,
) -> dict[str, Any]:
    generated_path = Path(
        generated_path
    )
    registry_path = Path(
        registry_path
    )
    valid_path = Path(
        valid_path
    )
    rejected_path = Path(
        rejected_path
    )
    rules_path = Path(
        rules_path
    )
    summary_path = Path(
        summary_path
    )

    if executed_at is None:
        executed_at = (
            datetime.now(
                timezone.utc
            )
            .replace(
                microsecond=0
            )
            .isoformat()
        )

    if not generated_path.exists():
        raise FileNotFoundError(
            generated_path
        )

    if not registry_path.exists():
        raise FileNotFoundError(
            registry_path
        )

    registry_hash_before = (
        sha256_file(
            registry_path
        )
    )

    generated_table = pq.read_table(
        generated_path
    )

    generated_rows = (
        generated_table.to_pylist()
    )

    registry_rows = pq.read_table(
        registry_path
    ).to_pylist()

    _validate_registry_identity(
        generated_rows,
        registry_rows,
    )

    active_rule_hash = (
        rule_set_sha256()
    )

    valid_rows = []
    rejected_rows = []

    seen_config_hashes: set[
        str
    ] = set()

    rejection_counter = Counter()
    warning_counter = Counter()

    for source_row in (
        generated_rows
    ):
        row = dict(
            source_row
        )

        errors, warnings = (
            evaluate_config(
                row
            )
        )

        config_hash = row.get(
            "config_sha256"
        )

        if config_hash in (
            seen_config_hashes
        ):
            errors.append(
                Finding(
                    "C014",
                    (
                        "Duplicate "
                        "config_sha256 in "
                        "generated definitions."
                    ),
                    "ERROR",
                )
            )
        else:
            seen_config_hashes.add(
                config_hash
            )

        errors = sorted(
            errors,
            key=lambda item: (
                item.rule_code,
                item.message,
            ),
        )

        warnings = sorted(
            warnings,
            key=lambda item: (
                item.rule_code,
                item.message,
            ),
        )

        for finding in errors:
            rejection_counter[
                finding.rule_code
            ] += 1

        for finding in warnings:
            warning_counter[
                finding.rule_code
            ] += 1

        row[
            "constraint_status"
        ] = (
            "INVALID"
            if errors
            else "VALID"
        )

        row[
            "rejection_count"
        ] = len(errors)

        row[
            "rejection_codes"
        ] = [
            finding.rule_code
            for finding in errors
        ]

        row[
            "rejection_details"
        ] = _canonical_json(
            [
                {
                    "rule_code": (
                        finding.rule_code
                    ),
                    "message": (
                        finding.message
                    ),
                    "severity": (
                        finding.severity
                    ),
                }
                for finding in errors
            ]
        )

        row[
            "warning_count"
        ] = len(warnings)

        row[
            "warning_codes"
        ] = [
            finding.rule_code
            for finding in warnings
        ]

        row[
            "warning_details"
        ] = _canonical_json(
            [
                {
                    "rule_code": (
                        finding.rule_code
                    ),
                    "message": (
                        finding.message
                    ),
                    "severity": (
                        finding.severity
                    ),
                }
                for finding in warnings
            ]
        )

        row[
            "rule_set_sha256"
        ] = active_rule_hash

        if errors:
            rejected_rows.append(
                row
            )
        else:
            valid_rows.append(
                row
            )

    schema = _output_schema(
        generated_table.schema
    )

    _write_rows(
        valid_rows,
        valid_path,
        schema,
    )

    _write_rows(
        rejected_rows,
        rejected_path,
        schema,
    )

    _write_rule_manifest(
        path=rules_path,
        created_at=executed_at,
    )

    registry_hash_after = (
        sha256_file(
            registry_path
        )
    )

    if (
        registry_hash_before
        != registry_hash_after
    ):
        raise RuntimeError(
            "Constraint Engine modified "
            "experiment_registry.parquet."
        )

    definition_hashes = sorted(
        {
            row.get(
                "definition_sha256"
            )
            for row in generated_rows
            if row.get(
                "definition_sha256"
            )
        }
    )

    if len(
        definition_hashes
    ) == 1:
        definition_hash = (
            definition_hashes[0]
        )
    else:
        definition_hash = (
            _sha256_text(
                _canonical_json(
                    definition_hashes
                )
            )
        )

    summary = {
        "generated_total": len(
            generated_rows
        ),
        "valid_total": len(
            valid_rows
        ),
        "invalid_total": len(
            rejected_rows
        ),
        "warning_total": sum(
            warning_counter.values()
        ),
        "rejection_count_by_rule": (
            dict(
                sorted(
                    rejection_counter.items()
                )
            )
        ),
        "warning_count_by_rule": (
            dict(
                sorted(
                    warning_counter.items()
                )
            )
        ),
        "definition_sha256": (
            definition_hash
        ),
        "rule_set_sha256": (
            active_rule_hash
        ),
        (
            "generated_experiments_sha256"
        ): sha256_file(
            generated_path
        ),
        (
            "valid_experiments_sha256"
        ): sha256_file(
            valid_path
        ),
        (
            "rejected_experiments_sha256"
        ): sha256_file(
            rejected_path
        ),
        "constraint_rules_sha256": (
            sha256_file(
                rules_path
            )
        ),
        "registry_sha256": (
            registry_hash_after
        ),
        "executed_at": executed_at,
        "engine_version": (
            ENGINE_VERSION
        ),
    }

    summary_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_path.write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        "summary": summary,
        "valid_rows": valid_rows,
        "rejected_rows": (
            rejected_rows
        ),
        "registry_unchanged": (
            registry_hash_before
            == registry_hash_after
        ),
        "valid_path": str(
            valid_path
        ),
        "rejected_path": str(
            rejected_path
        ),
        "rules_path": str(
            rules_path
        ),
        "summary_path": str(
            summary_path
        ),
    }