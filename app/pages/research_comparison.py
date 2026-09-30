from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.common import (
    dataframe_view,
    page_header,
    section_title,
)
from operar_range.research_comparison_engine import (
    compare_experiments,
    compare_researches,
)
from operar_range.research_workspace import (
    list_researches,
)


def _research_ids() -> list[str]:
    values: list[str] = []

    for row in list_researches():
        research_id = row.get(
            "research_id"
        )

        if research_id:
            values.append(
                str(
                    research_id
                )
            )

    return sorted(
        set(
            values
        )
    )


def _experiment_ids(
    comparison: dict,
    side: str,
) -> list[str]:
    key = (
        "experiments_a"
        if side == "A"
        else "experiments_b"
    )

    values = []

    for row in comparison.get(
        key,
        [],
    ):
        experiment_id = row.get(
            "experiment_id"
        )

        if experiment_id:
            values.append(
                str(
                    experiment_id
                )
            )

    return sorted(
        set(
            values
        )
    )


def _metadata_frame(
    result: dict,
) -> pd.DataFrame:
    a = result.get(
        "research_a",
        {},
    )

    b = result.get(
        "research_b",
        {},
    )

    rows = [
        {
            "Field": "Research ID",
            "Research A": (
                a.get(
                    "research_id"
                )
            ),
            "Research B": (
                b.get(
                    "research_id"
                )
            ),
        },
        {
            "Field": "Dataset ID",
            "Research A": (
                a.get(
                    "dataset_id"
                )
            ),
            "Research B": (
                b.get(
                    "dataset_id"
                )
            ),
        },
        {
            "Field": "Period start",
            "Research A": (
                a.get(
                    "period_start"
                )
            ),
            "Research B": (
                b.get(
                    "period_start"
                )
            ),
        },
        {
            "Field": "Period end",
            "Research A": (
                a.get(
                    "period_end"
                )
            ),
            "Research B": (
                b.get(
                    "period_end"
                )
            ),
        },
        {
            "Field": "Family",
            "Research A": (
                a.get(
                    "family"
                )
            ),
            "Research B": (
                b.get(
                    "family"
                )
            ),
        },
        {
            "Field": "Generation",
            "Research A": (
                a.get(
                    "generation"
                )
            ),
            "Research B": (
                b.get(
                    "generation"
                )
            ),
        },
        {
            "Field": "Same dataset",
            "Research A": (
                result.get(
                    "same_dataset"
                )
            ),
            "Research B": (
                result.get(
                    "same_dataset"
                )
            ),
        },
        {
            "Field": "Same period",
            "Research A": (
                result.get(
                    "same_period"
                )
            ),
            "Research B": (
                result.get(
                    "same_period"
                )
            ),
        },
    ]

    return pd.DataFrame(
        rows
    )


def _matched_frame(
    result: dict,
) -> pd.DataFrame:
    rows = []

    for item in result.get(
        "matched_experiments",
        [],
    ):
        rows.append(
            {
                "Status": (
                    item.get(
                        "status"
                    )
                ),
                "Config SHA-256": (
                    item.get(
                        "config_sha256"
                    )
                ),
                "Experiment A": (
                    item.get(
                        "experiment_a_id"
                    )
                ),
                "Experiment B": (
                    item.get(
                        "experiment_b_id"
                    )
                ),
                "Identity version A": (
                    item.get(
                        "config_identity_version_a"
                    )
                ),
                "Identity version B": (
                    item.get(
                        "config_identity_version_b"
                    )
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def _simple_frame(
    result: dict,
    key: str,
) -> pd.DataFrame:
    rows = result.get(
        key,
        [],
    )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(
        rows
    )


def _comparison_section(
    comparison: dict,
) -> None:
    left = comparison[
        "experiment_a"
    ]

    right = comparison[
        "experiment_b"
    ]

    section_title(
        "Identidade"
    )

    identity = pd.DataFrame(
        [
            {
                "Field": field,
                "Experiment A": (
                    left[
                        "identity"
                    ].get(
                        field
                    )
                ),
                "Experiment B": (
                    right[
                        "identity"
                    ].get(
                        field
                    )
                ),
            }
            for field in (
                "experiment_id",
                "config_sha256",
                "config_identity_version",
                "motor_version",
                "rules_version",
                "analytics_version",
            )
        ]
    )

    dataframe_view(
        identity,
        height=300,
    )

    section_title(
        "Configuração"
    )

    config_fields = sorted(
        set(
            left[
                "configuration"
            ]
        )
        | set(
            right[
                "configuration"
            ]
        )
    )

    config_rows = []

    for field in config_fields:
        config_rows.append(
            {
                "Parameter": field,
                "A": (
                    left[
                        "configuration"
                    ].get(
                        field
                    )
                ),
                "B": (
                    right[
                        "configuration"
                    ].get(
                        field
                    )
                ),
                "A - B": (
                    comparison[
                        "configuration_delta"
                    ].get(
                        field
                    )
                ),
            }
        )

    dataframe_view(
        pd.DataFrame(
            config_rows
        ),
        height=520,
    )

    sections = (
        (
            "Trade 1 Metrics",
            "metrics",
            "metrics_delta",
        ),
        (
            "Trade 2 Metrics",
            "trade2_metrics",
            "trade2_metrics_delta",
        ),
        (
            "Lifecycle Metrics",
            "lifecycle_metrics",
            "lifecycle_metrics_delta",
        ),
        (
            "Trade 1 × Lifecycle",
            "lifecycle_comparison",
            "lifecycle_comparison_delta",
        ),
    )

    for (
        title,
        source_key,
        delta_key,
    ) in sections:
        section_title(
            title
        )

        fields = sorted(
            set(
                left[
                    source_key
                ]
            )
            | set(
                right[
                    source_key
                ]
            )
        )

        rows = []

        for field in fields:
            rows.append(
                {
                    "Metric": field,
                    "A": (
                        left[
                            source_key
                        ].get(
                            field
                        )
                    ),
                    "B": (
                        right[
                            source_key
                        ].get(
                            field
                        )
                    ),
                    "A - B": (
                        comparison[
                            delta_key
                        ].get(
                            field
                        )
                    ),
                }
            )

        dataframe_view(
            pd.DataFrame(
                rows
            ),
            height=440,
        )


def render() -> None:
    page_header(
        "Research Comparison",
        (
            "Comparação read-only entre "
            "pesquisas e experimentos "
            "persistidos."
        ),
    )

    research_ids = (
        _research_ids()
    )

    if not research_ids:
        st.info(
            "Nenhuma Research disponível."
        )
        return

    mode = st.radio(
        "Modo",
        options=[
            "Comparar Pesquisas",
            "Comparar Experimentos",
        ],
        horizontal=True,
        key="research_comparison_mode",
    )

    left_column, right_column = (
        st.columns(
            2
        )
    )

    with left_column:
        research_a = st.selectbox(
            "Research A",
            options=research_ids,
            index=0,
            key="research_comparison_a",
        )

    with right_column:
        research_b = st.selectbox(
            "Research B",
            options=research_ids,
            index=(
                1
                if len(
                    research_ids
                ) > 1
                else 0
            ),
            key="research_comparison_b",
        )

    research_result = (
        compare_researches(
            research_a_id=(
                research_a
            ),
            research_b_id=(
                research_b
            ),
        )
    )

    st.divider()

    section_title(
        "Research Metadata"
    )

    dataframe_view(
        _metadata_frame(
            research_result
        ),
        height=380,
    )

    if mode == "Comparar Pesquisas":
        counts = (
            research_result[
                "counts"
            ]
        )

        columns = st.columns(
            6
        )

        labels = (
            (
                "Experiments A",
                "experiments_a",
            ),
            (
                "Experiments B",
                "experiments_b",
            ),
            (
                "Matched",
                "matched_experiments",
            ),
            (
                "Only A",
                "only_in_a",
            ),
            (
                "Only B",
                "only_in_b",
            ),
            (
                "Conflicts",
                "identity_conflicts",
            ),
        )

        for column, (
            label,
            key,
        ) in zip(
            columns,
            labels,
        ):
            column.metric(
                label,
                counts.get(
                    key,
                    0,
                ),
            )

        st.caption(
            (
                "Status: "
                f"{research_result['status']}"
            )
        )

        section_title(
            "Matched Experiments"
        )

        dataframe_view(
            _matched_frame(
                research_result
            ),
            height=360,
        )

        section_title(
            "Only in Research A"
        )

        dataframe_view(
            _simple_frame(
                research_result,
                "only_in_a",
            ),
            height=300,
        )

        section_title(
            "Only in Research B"
        )

        dataframe_view(
            _simple_frame(
                research_result,
                "only_in_b",
            ),
            height=300,
        )

        section_title(
            "Identity Conflicts"
        )

        dataframe_view(
            _simple_frame(
                research_result,
                "identity_conflicts",
            ),
            height=300,
        )

        for index, matched in enumerate(
            research_result.get(
                "matched_experiments",
                []
            ),
            start=1,
        ):
            with st.expander(
                (
                    f"Matched {index}: "
                    f"{matched.get('experiment_a_id')} "
                    "× "
                    f"{matched.get('experiment_b_id')}"
                ),
                expanded=False,
            ):
                _comparison_section(
                    matched[
                        "comparison"
                    ]
                )

        return

    options_a = _experiment_ids(
        research_result,
        "A",
    )

    options_b = _experiment_ids(
        research_result,
        "B",
    )

    if (
        not options_a
        or not options_b
    ):
        st.info(
            (
                "Uma das Researches não possui "
                "experimentos disponíveis."
            )
        )
        return

    selector_a, selector_b = (
        st.columns(
            2
        )
    )

    with selector_a:
        experiment_a = st.selectbox(
            "Experiment A",
            options=options_a,
            key=(
                "research_comparison_exp_a"
            ),
        )

    with selector_b:
        experiment_b = st.selectbox(
            "Experiment B",
            options=options_b,
            key=(
                "research_comparison_exp_b"
            ),
        )

    explicit = (
        compare_experiments(
            research_a_id=(
                research_a
            ),
            experiment_a_id=(
                experiment_a
            ),
            research_b_id=(
                research_b
            ),
            experiment_b_id=(
                experiment_b
            ),
        )
    )

    st.caption(
        (
            "Same config: "
            f"{explicit['same_config']}"
        )
    )

    _comparison_section(
        explicit[
            "comparison"
        ]
    )


if __name__ == "__main__":
    render()
