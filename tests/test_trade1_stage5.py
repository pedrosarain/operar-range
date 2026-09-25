from datetime import date, datetime, timedelta

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import operar_range.trade1 as trade1


SESSION_DATE = date(2026, 8, 18)
OPEN = datetime(2026, 8, 18, 10, 30)


def make_parquet(
    tmp_path,
    prices,
    trade_numbers=None,
    timestamps=None,
):
    if trade_numbers is None:
        trade_numbers = list(
            range(1, len(prices) + 1)
        )

    if timestamps is None:
        timestamps = [
            OPEN + timedelta(milliseconds=index)
            for index in range(len(prices))
        ]

    table = pa.table(
        {
            "timestamp": pa.array(
                timestamps,
                type=pa.timestamp("us"),
            ),
            "trade_number": pa.array(
                trade_numbers,
                type=pa.int64(),
            ),
            "price": pa.array(
                prices,
                type=pa.float64(),
            ),
        }
    )

    path = tmp_path / "ticks.parquet"

    pq.write_table(
        table,
        path,
    )

    return path


@pytest.fixture
def reference(monkeypatch):
    def fake_reference(
        parquet_path,
        session_date,
    ):
        return {
            "ny_open_brt": OPEN.isoformat(),
            "buy_level": 1000.0,
            "sell_level": 900.0,
        }

    monkeypatch.setattr(
        trade1,
        "reconstruct_reference_session",
        fake_reference,
    )


def test_trajectory_starts_at_entry(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            950,
            1000,
            1005,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    trajectory = result["trajectory"]

    assert trajectory[0] == {
        "timestamp": (
            OPEN + timedelta(milliseconds=1)
        ).isoformat(),
        "trade_number": 2,
        "price": 1000.0,
        "points_from_entry": 0.0,
        "favorable_excursion": 0.0,
        "adverse_excursion": 0.0,
    }


def test_trajectory_records_only_price_changes(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            1000,
            1000,
            995,
            995,
            1000,
            1000,
            1005,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    prices = [
        event["price"]
        for event in result["trajectory"]
    ]

    assert prices == [
        1000,
        995,
        1000,
        1005,
    ]


def test_long_points_from_entry(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            995,
            1010,
            990,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    points = [
        event["points_from_entry"]
        for event in result["trajectory"]
    ]

    assert points == [
        0,
        -5,
        10,
        -10,
    ]


def test_short_points_from_entry(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            900,
            905,
            890,
            910,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    points = [
        event["points_from_entry"]
        for event in result["trajectory"]
    ]

    assert points == [
        0,
        -5,
        10,
        -10,
    ]


def test_accumulated_favorable_excursion(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            1010,
            1005,
            1025,
            1015,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    excursions = [
        event["favorable_excursion"]
        for event in result["trajectory"]
    ]

    assert excursions == [
        0,
        10,
        10,
        25,
        25,
    ]


def test_accumulated_adverse_excursion(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            990,
            995,
            975,
            985,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    excursions = [
        event["adverse_excursion"]
        for event in result["trajectory"]
    ]

    assert excursions == [
        0,
        10,
        10,
        25,
        25,
    ]


def test_trajectory_preserves_timestamp_and_trade_number(
    reference,
    tmp_path,
):
    timestamps = [
        OPEN,
        OPEN,
        OPEN,
        OPEN + timedelta(milliseconds=1),
    ]

    path = make_parquet(
        tmp_path,
        [
            1000,
            1000,
            995,
            1000,
        ],
        trade_numbers=[
            100,
            110,
            120,
            130,
        ],
        timestamps=timestamps,
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    trajectory = result["trajectory"]

    assert trajectory[0]["trade_number"] == 100
    assert trajectory[1]["trade_number"] == 120
    assert trajectory[2]["trade_number"] == 130


def test_trajectory_reconstructs_zero_return_sequence(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            1000,
            995,
            990,
            995,
            1000,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert [
        event["price"]
        for event in result["trajectory"]
    ] == [
        1000,
        995,
        990,
        995,
        1000,
    ]


def test_existing_trade1_fields_remain_available(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            1100,
            830,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["direction"] == "LONG"
    assert result["entry_trigger_level"] == 1000
    assert "mfe_points" in result
    assert "mae_points" in result
    assert "stops" in result
    assert "targets" in result
    assert "last_tick" in result
    assert "trajectory" in result