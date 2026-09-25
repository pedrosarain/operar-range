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
            OPEN + timedelta(seconds=index)
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


def test_long(reference, tmp_path):
    path = make_parquet(
        tmp_path,
        [
            950,
            980,
            1000,
            1050,
            1100,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["entry_found"] is True
    assert result["direction"] == "LONG"
    assert result["entry_trigger_level"] == 1000
    assert result["trade_number"] == 3
    assert (
        result["first_traded_price_after_trigger"]
        == 1000
    )


def test_short(reference, tmp_path):
    path = make_parquet(
        tmp_path,
        [
            950,
            930,
            900,
            850,
            800,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["entry_found"] is True
    assert result["direction"] == "SHORT"
    assert result["entry_trigger_level"] == 900
    assert result["trade_number"] == 3


def test_tick_order_timestamp(
    reference,
    tmp_path,
):
    timestamps = [
        OPEN,
        OPEN + timedelta(seconds=2),
        OPEN + timedelta(seconds=1),
    ]

    path = make_parquet(
        tmp_path,
        [950, 960, 970],
        timestamps=timestamps,
    )

    with pytest.raises(
        ValueError,
        match="not ordered by timestamp",
    ):
        trade1.reconstruct_trade1(
            path,
            SESSION_DATE,
        )


def test_tick_order_trade_number(
    reference,
    tmp_path,
):
    timestamps = [
        OPEN,
        OPEN,
        OPEN,
    ]

    path = make_parquet(
        tmp_path,
        [950, 960, 970],
        trade_numbers=[10, 12, 11],
        timestamps=timestamps,
    )

    with pytest.raises(
        ValueError,
        match="trade_number",
    ):
        trade1.reconstruct_trade1(
            path,
            SESSION_DATE,
        )


def test_mfe_long(reference, tmp_path):
    path = make_parquet(
        tmp_path,
        [
            1000,
            1125,
            1080,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["mfe_points"] == 125
    assert result["mfe_price"] == 1125
    assert (
        result["mfe_timestamp"]
        == (
            OPEN
            + timedelta(seconds=1)
        ).isoformat()
    )


def test_mae_long(reference, tmp_path):
    path = make_parquet(
        tmp_path,
        [
            1000,
            950,
            830,
            900,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["mae_points"] == 170
    assert result["mae_price"] == 830

    assert (
        result["mae_timestamp"]
        == (
            OPEN
            + timedelta(seconds=2)
        ).isoformat()
    )


def test_mfe_short(reference, tmp_path):
    path = make_parquet(
        tmp_path,
        [
            900,
            800,
            775,
            850,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["mfe_points"] == 125
    assert result["mfe_price"] == 775


def test_mae_short(reference, tmp_path):
    path = make_parquet(
        tmp_path,
        [
            900,
            950,
            1070,
            1000,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["mae_points"] == 170
    assert result["mae_price"] == 1070


def test_jumped_entry_level_long(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            950,
            1010,
            1020,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["direction"] == "LONG"
    assert result["entry_trigger_level"] == 1000

    assert (
        result["first_traded_price_after_trigger"]
        == 1010
    )

    assert result["jumped_entry_level"] is True


def test_jumped_entry_level_short(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            950,
            890,
            880,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["direction"] == "SHORT"
    assert result["entry_trigger_level"] == 900

    assert (
        result["first_traded_price_after_trigger"]
        == 890
    )

    assert result["jumped_entry_level"] is True


def test_return_to_entry(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            1100,
            1125,
            1050,
            1000,
            900,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert (
        result["returned_to_zero_exact"]
        is True
    )

    assert (
        result["zero_return_timestamp"]
        == (
            OPEN
            + timedelta(seconds=4)
        ).isoformat()
    )

    assert (
        result[
            "max_favorable_before_first_zero"
        ]
        == 125
    )

    assert (
        result["never_returned_to_entry"]
        is False
    )


def test_never_returned_to_entry(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            1100,
            1200,
            1150,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert (
        result["returned_to_zero_exact"]
        is False
    )

    assert (
        result["zero_return_timestamp"]
        is None
    )

    assert (
        result["never_returned_to_entry"]
        is True
    )


def test_target_before_stop(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            1125,
            900,
            830,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    target = result["targets"]["125"]
    stop = result["stops"]["170"]

    assert target["reached"] is True
    assert stop["hit"] is True

    assert (
        datetime.fromisoformat(
            target["timestamp"]
        )
        <
        datetime.fromisoformat(
            stop["timestamp"]
        )
    )


def test_stop_before_target(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            830,
            1000,
            1125,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    target = result["targets"]["125"]
    stop = result["stops"]["170"]

    assert target["reached"] is True
    assert stop["hit"] is True

    assert (
        datetime.fromisoformat(
            stop["timestamp"]
        )
        <
        datetime.fromisoformat(
            target["timestamp"]
        )
    )


@pytest.mark.parametrize(
    "level",
    [100, 125, 150, 170, 175, 200],
)
def test_all_stops(
    reference,
    tmp_path,
    level,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            1000 - level,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    stop = result["stops"][str(level)]

    assert stop["hit"] is True

    assert (
        stop["timestamp"]
        == (
            OPEN
            + timedelta(seconds=1)
        ).isoformat()
    )

    assert stop["price"] == 1000 - level


@pytest.mark.parametrize(
    "level",
    [100, 125, 150, 175, 200, 400, 1000],
)
def test_all_targets(
    reference,
    tmp_path,
    level,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            1000 + level,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    target = result["targets"][str(level)]

    assert target["reached"] is True

    assert (
        target["timestamp"]
        == (
            OPEN
            + timedelta(seconds=1)
        ).isoformat()
    )


def test_last_tick_and_last_price(
    reference,
    tmp_path,
):
    path = make_parquet(
        tmp_path,
        [
            1000,
            1100,
            1200,
            1175,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["last_price_of_session"] == 1175

    assert (
        result["last_tick"]["price"]
        == 1175
    )

    assert (
        result["last_tick"]["trade_number"]
        == 4
    )

    assert (
        result["last_tick"]["timestamp"]
        == (
            OPEN
            + timedelta(seconds=3)
        ).isoformat()
    )
