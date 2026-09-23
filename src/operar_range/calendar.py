from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def ny_regular_open_brt(session_date: date) -> datetime:
    """Return 09:30 New York converted to São Paulo local time.

    This intentionally derives the clock time from IANA timezone rules instead
    of hard-coding 10:30/11:30 date ranges.

    It does NOT yet decide whether the U.S. cash market is open on that date.
    Exchange holiday/session validation is a separate layer.
    """
    ny_open = datetime.combine(session_date, time(9, 30), tzinfo=NY)
    return ny_open.astimezone(SAO_PAULO)


def reference_candle_window(session_date: date, timeframe_minutes: int = 5) -> tuple[datetime, datetime]:
    """Window of the last complete candle immediately before NY regular open."""
    open_brt = ny_regular_open_brt(session_date)
    start = open_brt - timedelta(minutes=timeframe_minutes)
    return start, open_brt
