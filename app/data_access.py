from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import pyarrow.parquet as pq
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_ROOT = PROJECT_ROOT / "data"
RESEARCH_ROOT = DATA_ROOT / "research"
REPORTS_ROOT = DATA_ROOT / "reports"
TRAJECTORIES_ROOT = DATA_ROOT / "trajectories"


DATASETS = {
    "trade1_database": (
        RESEARCH_ROOT
        / "trade1_database.parquet"
    ),
    "trajectory_manifest": (
        RESEARCH_ROOT
        / "trade1_trajectory_manifest.parquet"
    ),
    "experiment_registry": (
        RESEARCH_ROOT
        / "experiment_registry.parquet"
    ),
    "valid_experiments": (
        RESEARCH_ROOT
        / "valid_experiments.parquet"
    ),
    "experiment_results": (
        RESEARCH_ROOT
        / "experiment_results.parquet"
    ),
    "experiment_metrics": (
        RESEARCH_ROOT
        / "experiment_metrics.parquet"
    ),
    "experiment_metrics_yearly": (
        RESEARCH_ROOT
        / "experiment_metrics_yearly.parquet"
    ),
    "experiment_metrics_monthly": (
        RESEARCH_ROOT
        / "experiment_metrics_monthly.parquet"
    ),
    "experiment_rankings": (
        RESEARCH_ROOT
        / "experiment_rankings.parquet"
    ),
    "ranking_manifest": (
        RESEARCH_ROOT
        / "ranking_manifest.parquet"
    ),
    "batch_execution_plan": (
        RESEARCH_ROOT
        / "batch_execution_plan.parquet"
    ),
    "batch_failures": (
        RESEARCH_ROOT
        / "batch_failures.parquet"
    ),
}


REPORTS = {
    "ranking_summary": (
        REPORTS_ROOT
        / "ranking_summary.json"
    ),
    "constraint_engine_summary": (
        REPORTS_ROOT
        / "constraint_engine_summary.json"
    ),
    "batch_run_manifest": (
        RESEARCH_ROOT
        / "batch_run_manifest.json"
    ),
}


CONFIG_FIELDS = [
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
]


EXPERIMENT_ID_FIELDS = [
    "experiment_id",
    "experiment_name",
    "family",
    "generation",
    "status",
    "config_sha256",
]


OVERALL_SCOPE = "OVERALL"
YEARLY_SCOPE = "YEARLY"
MONTHLY_SCOPE = "MONTHLY"


def project_path(
    path: str | Path,
) -> Path:
    path = Path(path)

    if path.is_absolute():
        return path

    return (
        PROJECT_ROOT
        / path
    ).resolve()


def sha256_file(
    path: str | Path,
) -> str | None:
    path = project_path(
        path
    )

    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def file_metadata(
    path: str | Path,
) -> dict[str, Any]:
    path = project_path(
        path
    )

    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "size_bytes": None,
            "modified_at": None,
            "sha256": None,
        }

    stat = path.stat()

    return {
        "path": str(path),
        "exists": True,
        "size_bytes": int(
            stat.st_size
        ),
        "modified_at": (
            pd.Timestamp(
                stat.st_mtime,
                unit="s",
                tz="UTC",
            ).isoformat()
        ),
        "sha256": (
            sha256_file(
                path
            )
        ),
    }


@st.cache_data(
    show_spinner=False
)
def read_parquet(
    path: str | Path,
) -> pd.DataFrame:
    path = project_path(
        path
    )

    if not path.exists():
        return pd.DataFrame()

    try:
        table = pq.read_table(
            path
        )

        return table.to_pandas()

    except Exception:
        return pd.DataFrame()


@st.cache_data(
    show_spinner=False
)
def read_json(
    path: str | Path,
) -> dict[str, Any]:
    path = project_path(
        path
    )

    if not path.exists():
        return {}

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return {}


def dataset(
    name: str,
) -> pd.DataFrame:
    path = DATASETS.get(
        name
    )

    if path is None:
        raise KeyError(
            f"Unknown dataset: {name}"
        )

    return read_parquet(
        path
    )


def report(
    name: str,
) -> dict[str, Any]:
    path = REPORTS.get(
        name
    )

    if path is None:
        raise KeyError(
            f"Unknown report: {name}"
        )

    return read_json(
        path
    )


def available_columns(
    dataframe: pd.DataFrame,
    requested: Iterable[str],
) -> list[str]:
    return [
        column
        for column in requested
        if column
        in dataframe.columns
    ]


def first_existing_column(
    dataframe: pd.DataFrame,
    candidates: Iterable[str],
) -> str | None:
    for column in candidates:
        if column in dataframe.columns:
            return column

    return None


def safe_value(
    row: pd.Series
    | dict[str, Any]
    | None,
    field: str,
    default: Any = None,
) -> Any:
    if row is None:
        return default

    if isinstance(
        row,
        pd.Series,
    ):
        if field not in row.index:
            return default

        value = row[
            field
        ]

    else:
        if field not in row:
            return default

        value = row.get(
            field
        )

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    return value


def safe_int(
    value: Any,
) -> int | None:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    try:
        return int(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def safe_float(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    try:
        return float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def safe_bool(
    value: Any,
) -> bool | None:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(
        value,
        bool,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        normalized = (
            value.strip()
            .lower()
        )

        if normalized in {
            "true",
            "1",
            "yes",
            "sim",
        }:
            return True

        if normalized in {
            "false",
            "0",
            "no",
            "nao",
            "não",
        }:
            return False

    return bool(
        value
    )


def normalize_date_column(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe.copy()

    result = dataframe.copy()

    if "date" not in result.columns:
        return result

    result[
        "_date_dt"
    ] = pd.to_datetime(
        result[
            "date"
        ],
        errors="coerce",
    )

    return result


def experiment_registry() -> pd.DataFrame:
    return dataset(
        "experiment_registry"
    )


def valid_experiments() -> pd.DataFrame:
    return dataset(
        "valid_experiments"
    )


def experiment_metrics() -> pd.DataFrame:
    return dataset(
        "experiment_metrics"
    )


def experiment_metrics_yearly() -> pd.DataFrame:
    return dataset(
        "experiment_metrics_yearly"
    )


def experiment_metrics_monthly() -> pd.DataFrame:
    return dataset(
        "experiment_metrics_monthly"
    )


def experiment_results() -> pd.DataFrame:
    return dataset(
        "experiment_results"
    )


def trade1_database() -> pd.DataFrame:
    return dataset(
        "trade1_database"
    )


def trajectory_manifest() -> pd.DataFrame:
    return dataset(
        "trajectory_manifest"
    )


def rankings_overall() -> pd.DataFrame:
    return dataset(
        "experiment_rankings"
    )


def ranking_manifest_overall() -> pd.DataFrame:
    return dataset(
        "ranking_manifest"
    )


def _stage16_scope_dir(
    scope: str,
    year: int | None = None,
    month: int | None = None,
) -> Path | None:
    if scope == OVERALL_SCOPE:
        return None

    if scope == YEARLY_SCOPE:
        if year is None:
            return None

        return (
            RESEARCH_ROOT
            / "stage16_validation"
            / f"yearly_{year}"
        )

    if scope == MONTHLY_SCOPE:
        if (
            year is None
            or month is None
        ):
            return None

        return (
            RESEARCH_ROOT
            / "stage16_validation"
            / (
                f"monthly_"
                f"{year}_"
                f"{month:02d}"
            )
        )

    return None


def rankings_for_scope(
    *,
    scope: str,
    year: int | None = None,
    month: int | None = None,
) -> pd.DataFrame:
    if scope == OVERALL_SCOPE:
        return rankings_overall()

    scope_dir = (
        _stage16_scope_dir(
            scope,
            year,
            month,
        )
    )

    if scope_dir is None:
        return pd.DataFrame()

    return read_parquet(
        scope_dir
        / "experiment_rankings.parquet"
    )


def ranking_manifest_for_scope(
    *,
    scope: str,
    year: int | None = None,
    month: int | None = None,
) -> pd.DataFrame:
    if scope == OVERALL_SCOPE:
        return ranking_manifest_overall()

    scope_dir = (
        _stage16_scope_dir(
            scope,
            year,
            month,
        )
    )

    if scope_dir is None:
        return pd.DataFrame()

    return read_parquet(
        scope_dir
        / "ranking_manifest.parquet"
    )


def available_years() -> list[int]:
    dataframe = (
        experiment_metrics_yearly()
    )

    if (
        dataframe.empty
        or "year"
        not in dataframe.columns
    ):
        return []

    values = (
        pd.to_numeric(
            dataframe[
                "year"
            ],
            errors="coerce",
        )
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    return sorted(
        values
    )


def available_months(
    year: int,
) -> list[int]:
    dataframe = (
        experiment_metrics_monthly()
    )

    if (
        dataframe.empty
        or "year"
        not in dataframe.columns
        or "month"
        not in dataframe.columns
    ):
        return []

    subset = dataframe[
        pd.to_numeric(
            dataframe[
                "year"
            ],
            errors="coerce",
        )
        == int(
            year
        )
    ]

    values = (
        pd.to_numeric(
            subset[
                "month"
            ],
            errors="coerce",
        )
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    return sorted(
        values
    )


def experiments_table() -> pd.DataFrame:
    registry = experiment_registry()
    valid = valid_experiments()

    if registry.empty:
        return pd.DataFrame()

    result = registry.copy()

    if valid.empty:
        return result

    valid_columns = [
        "experiment_id",
        *CONFIG_FIELDS,
    ]

    valid_columns = (
        available_columns(
            valid,
            valid_columns,
        )
    )

    if "experiment_id" not in valid_columns:
        return result

    config_frame = (
        valid[
            valid_columns
        ]
        .drop_duplicates(
            subset=[
                "experiment_id"
            ]
        )
        .copy()
    )

    duplicate_fields = [
        field
        for field
        in config_frame.columns
        if (
            field
            != "experiment_id"
            and field
            in result.columns
        )
    ]

    if duplicate_fields:
        config_frame = (
            config_frame.drop(
                columns=(
                    duplicate_fields
                )
            )
        )

    return result.merge(
        config_frame,
        on="experiment_id",
        how="left",
        validate="one_to_one",
    )


def experiment_detail(
    experiment_id: str,
) -> dict[str, Any]:
    experiments = (
        experiments_table()
    )

    metrics = (
        experiment_metrics()
    )

    result: dict[
        str,
        Any
    ] = {
        "experiment": None,
        "metrics": None,
    }

    if not experiments.empty:
        subset = experiments[
            experiments[
                "experiment_id"
            ]
            == experiment_id
        ]

        if not subset.empty:
            result[
                "experiment"
            ] = (
                subset.iloc[0]
                .to_dict()
            )

    if (
        not metrics.empty
        and "experiment_id"
        in metrics.columns
    ):
        subset = metrics[
            metrics[
                "experiment_id"
            ]
            == experiment_id
        ]

        if not subset.empty:
            result[
                "metrics"
            ] = (
                subset.iloc[0]
                .to_dict()
            )

    return result


def compare_experiments(
    experiment_a: str,
    experiment_b: str,
) -> dict[str, Any]:
    return {
        "a": (
            experiment_detail(
                experiment_a
            )
        ),
        "b": (
            experiment_detail(
                experiment_b
            )
        ),
    }


def session_row(
    date_value: str,
) -> dict[str, Any] | None:
    dataframe = (
        trade1_database()
    )

    if (
        dataframe.empty
        or "date"
        not in dataframe.columns
    ):
        return None

    subset = dataframe[
        dataframe[
            "date"
        ].astype(str)
        == str(
            date_value
        )
    ]

    if subset.empty:
        return None

    return (
        subset.iloc[0]
        .to_dict()
    )


def trajectory_manifest_row(
    date_value: str,
) -> dict[str, Any] | None:
    dataframe = (
        trajectory_manifest()
    )

    if (
        dataframe.empty
        or "date"
        not in dataframe.columns
    ):
        return None

    subset = dataframe[
        dataframe[
            "date"
        ].astype(str)
        == str(
            date_value
        )
    ]

    if subset.empty:
        return None

    return (
        subset.iloc[0]
        .to_dict()
    )


def resolve_trajectory_path(
    manifest_row: dict[
        str,
        Any
    ] | None,
) -> Path | None:
    if not manifest_row:
        return None

    path_value = None

    for field in (
        "trajectory_path",
        "path",
    ):
        value = manifest_row.get(
            field
        )

        if value:
            path_value = value
            break

    if not path_value:
        return None

    path = Path(
        str(
            path_value
        )
    )

    if not path.is_absolute():
        path = (
            PROJECT_ROOT
            / path
        )

    path = path.resolve()

    try:
        path.relative_to(
            PROJECT_ROOT
        )

    except ValueError:
        return None

    return path


@st.cache_data(
    show_spinner=False
)
def read_trajectory(
    path: str | Path,
) -> pd.DataFrame:
    path = project_path(
        path
    )

    if not path.exists():
        return pd.DataFrame()

    try:
        table = pq.read_table(
            path
        )

        return table.to_pandas()

    except Exception:
        return pd.DataFrame()


def load_session_trajectory(
    date_value: str,
) -> pd.DataFrame:
    manifest_row = (
        trajectory_manifest_row(
            date_value
        )
    )

    path = resolve_trajectory_path(
        manifest_row
    )

    if path is None:
        return pd.DataFrame()

    return read_trajectory(
        path
    )


def downsample_dataframe(
    dataframe: pd.DataFrame,
    max_points: int = 5000,
) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe.copy()

    if max_points <= 0:
        raise ValueError(
            "max_points must be positive."
        )

    total_rows = len(
        dataframe
    )

    if total_rows <= max_points:
        return (
            dataframe
            .copy()
            .reset_index(
                drop=True
            )
        )

    if max_points == 1:
        return (
            dataframe
            .iloc[
                [[0]]
            ]
            .copy()
            .reset_index(
                drop=True
            )
        )

    positions = [
        (
            index
            * (
                total_rows
                - 1
            )
            // (
                max_points
                - 1
            )
        )
        for index in range(
            max_points
        )
    ]

    sampled = (
        dataframe
        .iloc[
            positions
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    return sampled


def trajectory_chart_frame(
    dataframe: pd.DataFrame,
    max_points: int = 5000,
) -> pd.DataFrame:
    if dataframe.empty:
        return pd.DataFrame()

    timestamp_column = (
        first_existing_column(
            dataframe,
            [
                "timestamp",
                "time",
                "datetime",
            ],
        )
    )

    price_column = (
        first_existing_column(
            dataframe,
            [
                "price",
                "last_price",
            ],
        )
    )

    if (
        timestamp_column is None
        or price_column is None
    ):
        return pd.DataFrame()

    frame = dataframe[
        [
            timestamp_column,
            price_column,
        ]
    ].copy()

    frame.columns = [
        "timestamp",
        "price",
    ]

    frame[
        "timestamp"
    ] = pd.to_datetime(
        frame[
            "timestamp"
        ],
        errors="coerce",
    )

    frame[
        "price"
    ] = pd.to_numeric(
        frame[
            "price"
        ],
        errors="coerce",
    )

    frame = (
        frame.dropna(
            subset=[
                "timestamp",
                "price",
            ]
        )
        .sort_values(
            "timestamp"
        )
        .reset_index(
            drop=True
        )
    )

    return downsample_dataframe(
        frame,
        max_points=(
            max_points
        ),
    )


def latest_dataset() -> dict[str, Any] | None:
    candidates = []

    for name, path in (
        DATASETS.items()
    ):
        metadata = (
            file_metadata(
                path
            )
        )

        if not metadata[
            "exists"
        ]:
            continue

        candidates.append(
            {
                "name": name,
                **metadata,
            }
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: (
            item[
                "modified_at"
            ]
            or ""
        ),
    )


def dataset_inventory() -> pd.DataFrame:
    rows = []

    for name, path in (
        DATASETS.items()
    ):
        metadata = (
            file_metadata(
                path
            )
        )

        row_count = None
        columns = None

        if metadata[
            "exists"
        ]:
            try:
                parquet = (
                    pq.ParquetFile(
                        path
                    )
                )

                row_count = (
                    parquet.metadata
                    .num_rows
                )

                columns = len(
                    parquet.schema.names
                )

            except Exception:
                row_count = None
                columns = None

        rows.append(
            {
                "dataset": name,
                "path": str(
                    path.relative_to(
                        PROJECT_ROOT
                    )
                ),
                "exists": (
                    metadata[
                        "exists"
                    ]
                ),
                "rows": (
                    row_count
                ),
                "columns": (
                    columns
                ),
                "size_bytes": (
                    metadata[
                        "size_bytes"
                    ]
                ),
                "sha256": (
                    metadata[
                        "sha256"
                    ]
                ),
                "modified_at": (
                    metadata[
                        "modified_at"
                    ]
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def report_inventory() -> pd.DataFrame:
    rows = []

    for name, path in (
        REPORTS.items()
    ):
        metadata = (
            file_metadata(
                path
            )
        )

        rows.append(
            {
                "report": name,
                "path": str(
                    path.relative_to(
                        PROJECT_ROOT
                    )
                ),
                "exists": (
                    metadata[
                        "exists"
                    ]
                ),
                "size_bytes": (
                    metadata[
                        "size_bytes"
                    ]
                ),
                "sha256": (
                    metadata[
                        "sha256"
                    ]
                ),
                "modified_at": (
                    metadata[
                        "modified_at"
                    ]
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def overview_counts() -> dict[str, Any]:
    sessions = trade1_database()
    manifest = trajectory_manifest()
    registry = experiment_registry()
    valid = valid_experiments()
    results = experiment_results()
    ranking_manifest = (
        ranking_manifest_overall()
    )

    trade_status_column = (
        first_existing_column(
            sessions,
            [
                "trade1_status",
                "trade_status",
            ],
        )
    )

    if sessions.empty:
        session_count = None
        trade1_count = None
        no_trade_count = None

    else:
        session_count = len(
            sessions
        )

        if trade_status_column:
            statuses = (
                sessions[
                    trade_status_column
                ]
                .astype(str)
            )

            trade1_count = int(
                (
                    statuses
                    == "TRADE_1"
                ).sum()
            )

            no_trade_count = int(
                (
                    statuses
                    == "NO_TRADE_1"
                ).sum()
            )

        else:
            trade1_count = None
            no_trade_count = None

    if registry.empty:
        registry_count = None
        active_count = None
        frozen_count = None

    else:
        registry_count = len(
            registry
        )

        if "status" in registry.columns:
            active_count = int(
                (
                    registry[
                        "status"
                    ]
                    == "ACTIVE"
                ).sum()
            )

            frozen_count = int(
                (
                    registry[
                        "status"
                    ]
                    == "FROZEN"
                ).sum()
            )

        else:
            active_count = None
            frozen_count = None

    period_start = None
    period_end = None

    period_source = (
        sessions
        if not sessions.empty
        else manifest
    )

    if (
        not period_source.empty
        and "date"
        in period_source.columns
    ):
        dates = pd.to_datetime(
            period_source[
                "date"
            ],
            errors="coerce",
        ).dropna()

        if not dates.empty:
            period_start = (
                dates.min()
                .date()
                .isoformat()
            )

            period_end = (
                dates.max()
                .date()
                .isoformat()
            )

    return {
        "sessions_total": (
            session_count
        ),
        "trade1_count": (
            trade1_count
        ),
        "no_trade1_count": (
            no_trade_count
        ),
        "registry_total": (
            registry_count
        ),
        "registry_active": (
            active_count
        ),
        "registry_frozen": (
            frozen_count
        ),
        "valid_experiments": (
            len(valid)
            if not valid.empty
            else None
        ),
        "execution_rows": (
            len(results)
            if not results.empty
            else None
        ),
        "ranking_types": (
            (
                ranking_manifest[
                    "ranking_type"
                ]
                .nunique()
            )
            if (
                not ranking_manifest.empty
                and "ranking_type"
                in ranking_manifest.columns
            )
            else None
        ),
        "period_start": (
            period_start
        ),
        "period_end": (
            period_end
        ),
    }


def detected_versions() -> dict[str, Any]:
    metrics = (
        experiment_metrics()
    )

    results = (
        experiment_results()
    )

    registry = (
        experiment_registry()
    )

    motor_version = None
    rules_version = None

    for dataframe in (
        metrics,
        results,
        registry,
    ):
        if dataframe.empty:
            continue

        if (
            motor_version
            is None
            and "motor_version"
            in dataframe.columns
        ):
            values = (
                dataframe[
                    "motor_version"
                ]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            if values:
                motor_version = (
                    values[0]
                )

        if (
            rules_version
            is None
            and "rules_version"
            in dataframe.columns
        ):
            values = (
                dataframe[
                    "rules_version"
                ]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            if values:
                rules_version = (
                    values[0]
                )

    return {
        "motor_version": (
            motor_version
        ),
        "rules_version": (
            rules_version
        ),
    }


def regression_status() -> dict[str, Any]:
    """
    A Etapa 17 não inventa nem hardcodeia
    a Full Regression Suite.

    Se futuramente existir um recurso
    persistido homologado, ele poderá ser
    lido aqui.

    Atualmente retorna N/A.
    """
    return {
        "available": False,
        "total_tests": None,
        "passed": None,
        "failed": None,
        "errors": None,
        "execution_time": None,
        "status": "N/A",
    }