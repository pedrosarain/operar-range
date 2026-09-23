from datetime import date
from operar_range.calendar import ny_regular_open_brt, reference_candle_window


def hm(dt):
    return dt.strftime("%H:%M")


def test_us_winter_open_is_1130_brt():
    assert hm(ny_regular_open_brt(date(2026, 1, 5))) == "11:30"


def test_after_us_dst_start_open_is_1030_brt():
    assert hm(ny_regular_open_brt(date(2026, 3, 9))) == "10:30"


def test_before_us_dst_end_open_is_1030_brt():
    assert hm(ny_regular_open_brt(date(2026, 10, 30))) == "10:30"


def test_after_us_dst_end_open_is_1130_brt():
    assert hm(ny_regular_open_brt(date(2026, 11, 2))) == "11:30"


def test_reference_is_last_five_minute_candle_before_open():
    start, end = reference_candle_window(date(2026, 9, 22))
    assert hm(start) == "10:25"
    assert hm(end) == "10:30"
