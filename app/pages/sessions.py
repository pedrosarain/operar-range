from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.common import (
    dataframe_view,
    key_value_panel,
    page_header,
    section_title,
)
from app.data_access import (
    load_session_trajectory,
    normalize_date_column,
    session_row,
    trade1_database,
    trajectory_chart_frame,
    trajectory_manifest_row,
)
from app.formatting import (
    NA_TEXT,
    as_text,
    format_boolean,
    format_date,
    format_datetime,
    format_float,
    format_integer,
    format_points,
)


SESSION_TABLE_FIELDS = [
    "date",
    "trade1_status",
    "direction",
    "buy_level",
    "sell_level",
    "entry_price",
    "entry_timestamp",
    "mfe_points",
    "mae_points",
]


SESSION_DETAIL_FIELDS = [
    (
        "Data",
        [
            "date",
        ],
        format_date,
    ),
    (
        "Abertura NY",
        [
            "ny_open_time",
            "ny_open_timestamp",
            "us_open_time",
        ],
        as_text,
    ),
    (
        "Candle referência",
        [
            "reference_candle",
            "reference_candle_timestamp",
            "reference_timestamp",
        ],
        as_text,
    ),
    (
        "Máxima",
        [
            "reference_high",
            "candle_high",
            "high",
        ],
        format_float,
    ),
    (
        "Mínima",
        [
            "reference_low",
            "candle_low",
            "low",
        ],
        format_float,
    ),
    (
        "Máxima intraday",
        [
            "intraday_high",
            "day_high",
        ],
        format_float,
    ),
    (
        "Mínima intraday",
        [
            "intraday_low",
            "day_low",
        ],
        format_float,
    ),
    (
        "Offset buy",
        [
            "buy_offset",
            "buy_offset_points",
        ],
        format_points,
    ),
    (
        "Offset sell",
        [
            "sell_offset",
            "sell_offset_points",
        ],
        format_points,
    ),
    (
        "Buy level",
        [
            "buy_level",
        ],
        format_float,
    ),
    (
        "Sell level",
        [
            "sell_level",
        ],
        format_float,
    ),
    (
        "Trade 1 existe?",
        [
            "trade1_status",
        ],
        as_text,
    ),
    (
        "Direção",
        [
            "direction",
        ],
        as_text,
    ),
    (
        "Entrada",
        [
            "entry_price",
        ],
        format_float,
    ),
    (
        "Timestamp",
        [
            "entry_timestamp",
        ],
        format_datetime,
    ),
    (
        "MFE",
        [
            "mfe_points",
            "mfe",
        ],
        format_points,
    ),
    (
        "MAE",
        [
            "mae_points",
            "mae",
        ],
        format_points,
    ),
]


def _first_value(
    row: dict | None,
    fields: list[str],
):
    if not row:
        return None

    for field in fields:
        if field not in row:
            continue

        value = row.get(
            field
        )

        if value is None:
            continue

        try:
            if pd.isna(
                value
            ):
                continue
        except (
            TypeError,
            ValueError,
        ):
            pass

        return value

    return None


def _format_detail_value(
    row: dict | None,
    fields: list[str],
    formatter,
) -> str:
    value = _first_value(
        row,
        fields,
    )

    if value is None:
        return NA_TEXT

    try:
        return formatter(
            value
        )
    except Exception:
        return as_text(
            value
        )


def _status_filter(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    if (
        dataframe.empty
        or "trade1_status"
        not in dataframe.columns
    ):
        return dataframe

    options = [
        "ALL",
        "TRADE_1",
        "NO_TRADE_1",
    ]

    selected = st.selectbox(
        "Trade status",
        options=options,
        key="sessions_status",
    )

    if selected == "ALL":
        return dataframe

    return dataframe[
        dataframe[
            "trade1_status"
        ].astype(str)
        == selected
    ].copy()


def _direction_filter(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    if (
        dataframe.empty
        or "direction"
        not in dataframe.columns
    ):
        return dataframe

    values = (
        dataframe[
            "direction"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    values = sorted(
        values
    )

    selected = st.multiselect(
        "Direção",
        options=values,
        default=[],
        key="sessions_direction",
    )

    if not selected:
        return dataframe

    return dataframe[
        dataframe[
            "direction"
        ]
        .astype(str)
        .isin(
            selected
        )
    ].copy()


def _date_filter(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    if (
        dataframe.empty
        or "date"
        not in dataframe.columns
    ):
        return dataframe

    normalized = (
        normalize_date_column(
            dataframe
        )
    )

    if (
        "_date_dt"
        not in normalized.columns
        or normalized[
            "_date_dt"
        ]
        .dropna()
        .empty
    ):
        return dataframe

    valid_dates = (
        normalized[
            "_date_dt"
        ]
        .dropna()
    )

    minimum = (
        valid_dates.min()
        .date()
    )

    maximum = (
        valid_dates.max()
        .date()
    )

    selected = st.date_input(
        "Período",
        value=(
            minimum,
            maximum,
        ),
        min_value=minimum,
        max_value=maximum,
        key="sessions_date_range",
    )

    if not isinstance(
        selected,
        tuple,
    ):
        selected = (
            selected,
            selected,
        )

    if len(
        selected
    ) == 1:
        start = selected[0]
        end = selected[0]
    else:
        start = selected[0]
        end = selected[1]

    mask = (
        normalized[
            "_date_dt"
        ].dt.date
        >= start
    ) & (
        normalized[
            "_date_dt"
        ].dt.date
        <= end
    )

    result = normalized[
        mask.fillna(
            False
        )
    ].copy()

    if (
        "_date_dt"
        in result.columns
    ):
        result = result.drop(
            columns=[
                "_date_dt"
            ]
        )

    return result


def _sessions_table(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe

    visible = [
        column
        for column in (
            SESSION_TABLE_FIELDS
        )
        if column
        in dataframe.columns
    ]

    display = dataframe[
        visible
    ].copy()

    if "date" in display.columns:
        display[
            "date"
        ] = display[
            "date"
        ].map(
            format_date
        )

    if (
        "entry_timestamp"
        in display.columns
    ):
        display[
            "entry_timestamp"
        ] = display[
            "entry_timestamp"
        ].map(
            format_datetime
        )

    for field in (
        "mfe_points",
        "mae_points",
    ):
        if field in display.columns:
            display[
                field
            ] = display[
                field
            ].map(
                format_points
            )

    return display


def _no_trade_reason(
    row: dict | None,
) -> str:
    if not row:
        return NA_TEXT

    candidates = [
        "no_trade_reason",
        "reason",
        "trade1_reason",
        "status_reason",
        "skip_reason",
    ]

    value = _first_value(
        row,
        candidates,
    )

    return (
        as_text(
            value
        )
        if value is not None
        else NA_TEXT
    )


def _trajectory_summary(
    trajectory: pd.DataFrame,
    manifest_row: dict | None,
    session: dict | None,
) -> list[
    tuple[str, str]
]:
    if trajectory.empty:
        return [
            (
                "Trajectory",
                "UNAVAILABLE",
            )
        ]

    timestamp_column = None

    for candidate in (
        "timestamp",
        "time",
        "datetime",
    ):
        if candidate in trajectory.columns:
            timestamp_column = (
                candidate
            )
            break

    first_timestamp = None
    last_timestamp = None

    if timestamp_column:
        timestamps = pd.to_datetime(
            trajectory[
                timestamp_column
            ],
            errors="coerce",
        ).dropna()

        if not timestamps.empty:
            first_timestamp = (
                timestamps.min()
            )

            last_timestamp = (
                timestamps.max()
            )

    trajectory_hash = None

    if manifest_row:
        trajectory_hash = (
            manifest_row.get(
                "sha256"
            )
            or manifest_row.get(
                "trajectory_sha256"
            )
        )

    return [
        (
            "Registros",
            format_integer(
                len(
                    trajectory
                )
            ),
        ),
        (
            "Primeiro timestamp",
            format_datetime(
                first_timestamp
            ),
        ),
        (
            "Último timestamp",
            format_datetime(
                last_timestamp
            ),
        ),
        (
            "MFE",
            format_points(
                _first_value(
                    session,
                    [
                        "mfe_points",
                        "mfe",
                    ],
                )
            ),
        ),
        (
            "MAE",
            format_points(
                _first_value(
                    session,
                    [
                        "mae_points",
                        "mae",
                    ],
                )
            ),
        ),
        (
            "Trajectory SHA-256",
            as_text(
                trajectory_hash
            ),
        ),
    ]


def _render_trajectory(
    date_value: str,
    session: dict | None,
) -> None:
    section_title(
        "Trajectory",
        (
            "Carregamento lazy da trajectory "
            "persistida. RAW não é acessado."
        ),
    )

    manifest_row = (
        trajectory_manifest_row(
            date_value
        )
    )

    if not manifest_row:
        st.info(
            "Trajectory indisponível "
            "para este pregão."
        )
        return

    exists_value = (
        manifest_row.get(
            "trajectory_exists"
        )
    )

    if (
        exists_value is False
        or str(
            exists_value
        ).lower()
        == "false"
    ):
        st.info(
            "Trajectory indisponível "
            "para este pregão."
        )
        return

    trajectory = (
        load_session_trajectory(
            date_value
        )
    )

    if trajectory.empty:
        st.info(
            "Trajectory indisponível "
            "ou vazia."
        )
        return

    key_value_panel(
        _trajectory_summary(
            trajectory,
            manifest_row,
            session,
        ),
        title="Trajectory metadata",
    )

    chart_frame = (
        trajectory_chart_frame(
            trajectory,
            max_points=5000,
        )
    )

    if chart_frame.empty:
        st.info(
            "Trajectory encontrada, mas "
            "não há colunas timestamp/price "
            "compatíveis para visualização."
        )
        return

    st.caption(
        (
            f"Visualização: {len(chart_frame)} "
            f"ponto(s) de {len(trajectory)} "
            "registro(s). O downsampling "
            "afeta somente o gráfico."
        )
    )

    chart = (
        chart_frame.set_index(
            "timestamp"
        )
    )

    st.line_chart(
        chart[
            [
                "price"
            ]
        ],
        use_container_width=True,
    )

    entry_price = (
        _first_value(
            session,
            [
                "entry_price",
            ],
        )
    )

    if entry_price is not None:
        st.caption(
            (
                "Entry price: "
                f"{format_float(entry_price)}"
            )
        )


def _render_session_detail(
    date_value: str,
) -> None:
    session = session_row(
        date_value
    )

    if not session:
        st.info(
            "Detalhe do pregão "
            "indisponível."
        )
        return

    st.divider()

    section_title(
        f"Pregão — {format_date(date_value)}"
    )

    status = str(
        session.get(
            "trade1_status"
        )
        or NA_TEXT
    )

    if status == "NO_TRADE_1":
        st.warning(
            "SEM TRADE 1"
        )

        reason = _no_trade_reason(
            session
        )

        st.caption(
            (
                "Motivo: "
                f"{reason}"
            )
        )

    detail_items = []

    for (
        label,
        fields,
        formatter,
    ) in SESSION_DETAIL_FIELDS:
        detail_items.append(
            (
                label,
                _format_detail_value(
                    session,
                    fields,
                    formatter,
                ),
            )
        )

    key_value_panel(
        detail_items,
        title="Session detail",
    )

    if status == "NO_TRADE_1":
        return

    _render_trajectory(
        date_value,
        session,
    )


def render() -> None:
    page_header(
        "Sessions",
        (
            "Consulta dos pregões analisados "
            "e detalhe read-only do Trade 1."
        ),
    )

    dataframe = (
        trade1_database()
    )

    if dataframe.empty:
        st.info(
            "trade1_database.parquet "
            "indisponível."
        )
        return

    section_title(
        "Filtros"
    )

    columns = st.columns(
        3
    )

    with columns[0]:
        filtered = (
            _date_filter(
                dataframe
            )
        )

    with columns[1]:
        filtered = (
            _direction_filter(
                filtered
            )
        )

    with columns[2]:
        filtered = (
            _status_filter(
                filtered
            )
        )

    if (
        "date"
        in filtered.columns
    ):
        filtered = (
            filtered.sort_values(
                "date"
            )
        )

    st.caption(
        (
            f"{len(filtered)} pregão(ões) "
            "visível(is)."
        )
    )

    dataframe_view(
        _sessions_table(
            filtered
        ),
        height=450,
    )

    if (
        filtered.empty
        or "date"
        not in filtered.columns
    ):
        return

    date_options = (
        filtered[
            "date"
        ]
        .astype(str)
        .drop_duplicates()
        .tolist()
    )

    selected_date = (
        st.selectbox(
            "Selecionar pregão para detalhe",
            options=date_options,
            format_func=(
                format_date
            ),
            key=(
                "sessions_selected_date"
            ),
        )
    )

    if selected_date:
        _render_session_detail(
            selected_date
        )


if __name__ == "__main__":
    render()