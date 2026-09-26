from datetime import date, datetime, timedelta

import pyarrow as pa
import pyarrow.parquet as pq

import operar_range.trade1 as trade1


SESSION_DATE = date(2026, 8, 18)
NY_OPEN = datetime(2026, 8, 18, 10, 30)


def make_parquet(
    tmp_path,
    timestamps,
    prices,
):
    path = tmp_path / "ticks.parquet"

    table = pa.table(
        {
            "timestamp": pa.array(
                timestamps,
                type=pa.timestamp("us"),
            ),
            "trade_number": pa.array(
                list(
                    range(
                        1,
                        len(prices) + 1,
                    )
                ),
                type=pa.int64(),
            ),
            "price": pa.array(
                prices,
                type=pa.float64(),
            ),
        }
    )

    pq.write_table(
        table,
        path,
    )

    return path


def fake_reference(
    parquet_path,
    session_date,
):
    return {
        "ny_open_brt": NY_OPEN.isoformat(),
        "buy_level": 1000.0,
        "sell_level": 900.0,
    }


def test_trade1_exists_when_breakout_occurs_in_next_candle(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        trade1,
        "reconstruct_reference_session",
        fake_reference,
    )

    path = make_parquet(
        tmp_path,
        [
            NY_OPEN,
            NY_OPEN + timedelta(minutes=2),
            NY_OPEN + timedelta(minutes=4, seconds=59),
            NY_OPEN + timedelta(minutes=5),
        ],
        [
            950,
            970,
            1000,
            1010,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["entry_found"] is True
    assert result["direction"] == "LONG"
    assert result["entry_timestamp"] == (
        NY_OPEN
        + timedelta(
            minutes=4,
            seconds=59,
        )
    ).isoformat()


def test_trade1_does_not_exist_when_breakout_occurs_after_next_candle(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        trade1,
        "reconstruct_reference_session",
        fake_reference,
    )

    path = make_parquet(
        tmp_path,
        [
            NY_OPEN,
            NY_OPEN + timedelta(minutes=4, seconds=59),
            NY_OPEN + timedelta(minutes=5),
            NY_OPEN + timedelta(minutes=9),
        ],
        [
            950,
            990,
            1000,
            1100,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["entry_found"] is False
    assert result["direction"] is None
    assert result["trade1_status"] == "NO_TRADE_1"

    assert result["trade1_window_start"] == (
        NY_OPEN.isoformat()
    )

    assert result["trade1_window_end"] == (
        NY_OPEN
        + timedelta(minutes=5)
    ).isoformat()


def test_tick_at_exact_window_end_is_not_valid_entry(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        trade1,
        "reconstruct_reference_session",
        fake_reference,
    )

    path = make_parquet(
        tmp_path,
        [
            NY_OPEN,
            NY_OPEN + timedelta(minutes=4, seconds=59),
            NY_OPEN + timedelta(minutes=5),
        ],
        [
            950,
            990,
            1000,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["entry_found"] is False
    assert result["trade1_status"] == "NO_TRADE_1"


def test_short_breakout_inside_window_remains_valid(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        trade1,
        "reconstruct_reference_session",
        fake_reference,
    )

    path = make_parquet(
        tmp_path,
        [
            NY_OPEN,
            NY_OPEN + timedelta(minutes=1),
            NY_OPEN + timedelta(minutes=6),
        ],
        [
            950,
            900,
            850,
        ],
    )

    result = trade1.reconstruct_trade1(
        path,
        SESSION_DATE,
    )

    assert result["entry_found"] is True
    assert result["direction"] == "SHORT"
    assert result["entry_timestamp"] == (
        NY_OPEN
        + timedelta(minutes=1)
    ).isoformat()