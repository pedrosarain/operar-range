from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from app.components.common import (
    key_value_panel,
    metric_cards,
    section_title,
)
from app.formatting import (
    NA_TEXT,
    format_integer,
)
from operar_range.research_workspace import (
    load_research_definition,
    load_research_manifest,
    research_paths,
)


def _read_parquet(
    path: Path | None,
) -> pd.DataFrame:
    if (
        path is None
        or not path.exists()
    ):
        return pd.DataFrame()

    try:
        return pd.read_parquet(
            path
        )

    except Exception:
        return pd.DataFrame()


def _first_value(
    row: dict[str, Any],
    candidates: tuple[str, ...],
) -> Any:
    for candidate in candidates:
        if candidate not in row:
            continue

        value = row.get(
            candidate
        )

        if value is None:
            continue

        try:
            if pd.isna(
                value
            ):
                continue
        except Exception:
            pass

        return value

    return None


def _metric_text(
    value: Any,
    *,
    suffix: str = "",
    decimals: int = 2,
) -> str:
    if value is None:
        return NA_TEXT

    try:
        numeric = float(
            value
        )

        return (
            f"{numeric:.{decimals}f}"
            f"{suffix}"
        )

    except Exception:
        return str(
            value
        )


def _bool_text(
    value: Any,
) -> str:
    if value is True:
        return "Sim"

    if value is False:
        return "Não"

    return NA_TEXT


def _research_paths(
    research_id: str,
) -> dict[str, Path]:
    raw = research_paths(
        research_id
    )

    return {
        key: Path(
            value
        )
        for key, value
        in raw.items()
        if value is not None
    }


def _best_experiment_from_existing_ranking(
    paths: dict[str, Path],
) -> dict[str, Any] | None:
    ranking_path = paths.get(
        "rankings"
    )

    rankings = _read_parquet(
        ranking_path
    )

    if rankings.empty:
        return None

    if (
        "experiment_id"
        not in rankings.columns
    ):
        return None

    #
    # IMPORTANT:
    # No ranking is calculated here.
    #
    # We consume the persisted order from
    # the existing ranking artifact only.
    #
    first = (
        rankings.iloc[
            0
        ]
        .to_dict()
    )

    return first


def _experiment_metrics_row(
    paths: dict[str, Path],
    experiment_id: str | None,
) -> dict[str, Any]:
    if not experiment_id:
        return {}

    metrics = _read_parquet(
        paths.get(
            "metrics"
        )
    )

    if (
        metrics.empty
        or "experiment_id"
        not in metrics.columns
    ):
        return {}

    subset = metrics[
        metrics[
            "experiment_id"
        ]
        .astype(
            str
        )
        == str(
            experiment_id
        )
    ]

    if subset.empty:
        return {}

    return (
        subset.iloc[
            0
        ]
        .to_dict()
    )


def _experiment_config_row(
    paths: dict[str, Path],
    experiment_id: str | None,
) -> dict[str, Any]:
    if not experiment_id:
        return {}

    candidates = [
        paths.get(
            "valid"
        ),
        paths.get(
            "generated"
        ),
        paths.get(
            "experiment_manifest"
        ),
    ]

    for candidate in candidates:
        dataframe = _read_parquet(
            candidate
        )

        if (
            dataframe.empty
            or "experiment_id"
            not in dataframe.columns
        ):
            continue

        subset = dataframe[
            dataframe[
                "experiment_id"
            ]
            .astype(
                str
            )
            == str(
                experiment_id
            )
        ]

        if subset.empty:
            continue

        return (
            subset.iloc[
                0
            ]
            .to_dict()
        )

    return {}


def _research_result_status(
    definition: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    candidates = (
        "hypothesis_result",
        "hypothesis_status",
        "validation_result",
        "research_result",
        "conclusion_status",
    )

    value = _first_value(
        {
            **definition,
            **manifest,
        },
        candidates,
    )

    if value is None:
        return (
            "Ainda não registrado "
            "nos artifacts atuais"
        )

    return str(
        value
    )


def _discoveries(
    definition: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    candidates = (
        "discoveries",
        "findings",
        "conclusions",
        "research_findings",
    )

    combined = {
        **definition,
        **manifest,
    }

    for key in candidates:
        value = combined.get(
            key
        )

        if not value:
            continue

        if isinstance(
            value,
            list,
        ):
            return [
                str(item)
                for item in value
            ]

        return [
            str(
                value
            )
        ]

    return []


def _next_hypotheses(
    definition: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    candidates = (
        "next_hypotheses",
        "suggested_hypotheses",
        "future_hypotheses",
    )

    combined = {
        **definition,
        **manifest,
    }

    for key in candidates:
        value = combined.get(
            key
        )

        if not value:
            continue

        if isinstance(
            value,
            list,
        ):
            return [
                str(item)
                for item in value
            ]

        return [
            str(
                value
            )
        ]

    return []


def _critical_period_status(
    paths: dict[str, Path],
) -> tuple[str, str]:
    monthly = _read_parquet(
        paths.get(
            "metrics_monthly"
        )
    )

    if monthly.empty:
        month_status = (
            "Não disponível "
            "nos artifacts atuais"
        )

    else:
        #
        # UX-01 must not create a new
        # quantitative definition of
        # "critical month".
        #
        month_status = (
            "Dados mensais disponíveis "
            "em Analytics; classificação "
            "de mês crítico não existe "
            "como fato persistido."
        )

    #
    # There is currently no homologated
    # daily critical-period artifact
    # identified by the presentation audit.
    #
    day_status = (
        "Classificação de dia crítico "
        "não existe como fato persistido."
    )

    return (
        month_status,
        day_status,
    )


def render_research_result(
    research_id: str,
) -> None:
    paths = _research_paths(
        research_id
    )

    try:
        definition = (
            load_research_definition(
                research_id
            )
        )

    except Exception:
        definition = {}

    try:
        manifest = (
            load_research_manifest(
                research_id
            )
        )

    except Exception:
        manifest = {}

    ranking = (
        _best_experiment_from_existing_ranking(
            paths
        )
    )

    best_experiment_id = (
        str(
            ranking.get(
                "experiment_id"
            )
        )
        if (
            ranking
            and ranking.get(
                "experiment_id"
            )
            is not None
        )
        else None
    )

    metrics = (
        _experiment_metrics_row(
            paths,
            best_experiment_id,
        )
    )

    config = (
        _experiment_config_row(
            paths,
            best_experiment_id,
        )
    )

    hypothesis = _first_value(
        definition,
        (
            "hypothesis",
            "research_hypothesis",
            "description",
        ),
    )

    result_status = (
        _research_result_status(
            definition,
            manifest,
        )
    )

    win_rate = _first_value(
        metrics,
        (
            "win_rate",
            "win_rate_pct",
            "winner_pct",
            "winning_rate",
        ),
    )

    expectancy = _first_value(
        metrics,
        (
            "expectancy",
            "expectancy_points",
            "expected_value",
            "expectancy_per_trade",
        ),
    )

    profit_factor = _first_value(
        metrics,
        (
            "profit_factor",
            "pf",
        ),
    )

    max_drawdown = _first_value(
        metrics,
        (
            "max_drawdown",
            "max_drawdown_points",
            "maximum_drawdown",
        ),
    )

    stop = _first_value(
        config,
        (
            "stop_points",
            "trade1_stop_points",
        ),
    )

    partial = _first_value(
        config,
        (
            "partial_1_points",
            "partial1_points",
        ),
    )

    runner = _first_value(
        config,
        (
            "runner_enabled",
            "runner",
        ),
    )

    month_status, day_status = (
        _critical_period_status(
            paths
        )
    )

    discoveries = _discoveries(
        definition,
        manifest,
    )

    next_hypotheses = (
        _next_hypotheses(
            definition,
            manifest,
        )
    )

    section_title(
        "Resultado da pesquisa",
        (
            "A resposta central da pesquisa. "
            "Esta tela apenas apresenta fatos "
            "já persistidos pelos motores."
        ),
    )

    st.markdown(
        "### Hipótese"
    )

    st.write(
        (
            str(
                hypothesis
            )
            if hypothesis
            else (
                "Hipótese não registrada "
                "na definição atual."
            )
        )
    )

    st.markdown(
        "### Resultado"
    )

    st.info(
        result_status
    )

    if (
        "confirm"
        not in result_status.lower()
        and "reject"
        not in result_status.lower()
        and "rejeit"
        not in result_status.lower()
    ):
        st.caption(
            (
                "UX-01 não infere confirmação "
                "ou rejeição. Esse estado só "
                "é exibido quando já existe "
                "como dado persistido."
            )
        )

    metric_cards(
        [
            (
                "Win Rate",
                _metric_text(
                    win_rate,
                    suffix=(
                        "%"
                        if win_rate
                        is not None
                        else ""
                    ),
                ),
            ),
            (
                "Expectancy",
                _metric_text(
                    expectancy
                ),
            ),
            (
                "Profit Factor",
                _metric_text(
                    profit_factor
                ),
            ),
            (
                "Maior Drawdown",
                _metric_text(
                    max_drawdown
                ),
            ),
        ],
        columns=4,
    )

    st.divider()

    section_title(
        "Configuração em destaque",
        (
            "Configuração associada ao "
            "primeiro experimento do ranking "
            "já persistido pela plataforma."
        ),
    )

    metric_cards(
        [
            (
                "Experimento",
                (
                    best_experiment_id
                    or NA_TEXT
                ),
            ),
            (
                "Stop",
                _metric_text(
                    stop
                ),
            ),
            (
                "Parcial 1",
                _metric_text(
                    partial
                ),
            ),
            (
                "Runner",
                _bool_text(
                    runner
                ),
            ),
        ],
        columns=4,
    )

    if ranking is None:
        st.caption(
            (
                "Nenhum ranking persistido "
                "foi encontrado para esta "
                "pesquisa."
            )
        )

    st.divider()

    left, right = st.columns(
        2
    )

    with left:
        section_title(
            "Meses críticos"
        )

        st.info(
            month_status
        )

    with right:
        section_title(
            "Dias críticos"
        )

        st.info(
            day_status
        )

    st.divider()

    section_title(
        "Conclusões e descobertas"
    )

    if discoveries:
        for discovery in discoveries:
            st.markdown(
                f"- {discovery}"
            )

    else:
        st.info(
            (
                "Nenhuma conclusão textual "
                "foi persistida para esta "
                "pesquisa."
            )
        )

    st.divider()

    section_title(
        "Próximas hipóteses"
    )

    if next_hypotheses:
        for hypothesis_item in (
            next_hypotheses
        ):
            st.markdown(
                f"- {hypothesis_item}"
            )

    else:
        st.info(
            (
                "Nenhuma próxima hipótese "
                "foi persistida. A interface "
                "não cria hipóteses novas "
                "automaticamente."
            )
        )


if __name__ == "__main__":
    active = (
        st.session_state.get(
            "active_research_id"
        )
    )

    if active:
        render_research_result(
            str(
                active
            )
        )

    else:
        st.info(
            "Nenhuma pesquisa ativa."
        )
