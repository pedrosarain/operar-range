from __future__ import annotations

from pathlib import Path

import pytest

from operar_range.distributed_executor import (
    _relative_path,
    _resolve_project_path,
)


def test_stage22_dataset_path_roundtrip():
    project_root = Path.cwd()

    absolute = (
        project_root
        / "data"
        / "datasets"
        / "DS-TEST"
        / "trajectories"
        / "trade1.parquet"
    )

    relative = _relative_path(
        path=absolute,
        project_root=project_root,
    )

    assert (
        relative
        == (
            "data/datasets/DS-TEST/"
            "trajectories/trade1.parquet"
        )
    )

    assert (
        Path(relative).is_absolute()
        is False
    )

    resolved = _resolve_project_path(
        path=relative,
        project_root=project_root,
    )

    assert (
        resolved
        == absolute.resolve()
    )


def test_stage22_absolute_path_remains_forbidden():
    project_root = Path.cwd()

    absolute = (
        project_root
        / "data"
        / "datasets"
        / "DS-TEST"
        / "normalized"
    ).resolve()

    with pytest.raises(
        RuntimeError,
        match=(
            "Absolute paths are not allowed"
        ),
    ):
        _resolve_project_path(
            path=absolute,
            project_root=project_root,
        )
