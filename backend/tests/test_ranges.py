from datetime import UTC, date, datetime

import pytest

from app.contracts.ws.common import RangeRequest
from app.pipeline.ranges import BadTimezone, resolve, suggestion


def utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


@pytest.mark.parametrize(
    ("granularity", "anchor", "tz", "start", "end", "label"),
    [
        ("week", "2026-10-14", "Europe/London", utc(2026, 10, 11, 23), utc(2026, 10, 18, 23),
         "Mon 12 Oct – Sun 18 Oct 2026, London time"),
        ("day", "2026-10-17", "Australia/Melbourne", utc(2026, 10, 16, 13), utc(2026, 10, 17, 13),
         "Sat 17 Oct 2026, Melbourne time"),
        # The clocks go back on Sun 25 Oct 2026 in London: that week is an hour longer.
        ("week", "2026-10-25", "Europe/London", utc(2026, 10, 18, 23), utc(2026, 10, 26, 0),
         "Mon 19 Oct – Sun 25 Oct 2026, London time"),
        ("month", "2026-10-20", "Europe/London", utc(2026, 9, 30, 23), utc(2026, 11, 1, 0),
         "October 2026, London time"),
        ("week", "2026-12-30", "UTC", utc(2026, 12, 28), utc(2027, 1, 4), "Mon 28 Dec – Sun 3 Jan 2027, UTC"),
    ],
)  # fmt: skip
def test_resolve(granularity: str, anchor: str, tz: str, start: datetime, end: datetime, label: str) -> None:
    w = resolve(RangeRequest(granularity=granularity, anchor=date.fromisoformat(anchor)), tz)
    assert (w.start, w.end, w.label) == (start, end, label)


def test_bad_timezone() -> None:
    with pytest.raises(BadTimezone):
        resolve(RangeRequest(granularity="day", anchor=date(2026, 10, 17)), "Mars/Olympus_Mons")


@pytest.mark.parametrize(
    ("granularity", "anchor", "label", "next_anchor"),
    [
        ("day", "2026-10-14", "Try the whole week: Mon 12 – Sun 18 Oct", "2026-10-12"),
        ("week", "2026-10-14", "Try the previous week: Mon 5 – Sun 11 Oct", "2026-10-05"),
        ("week", "2026-10-07", "Try the previous week: Mon 28 Sep – Sun 4 Oct", "2026-09-28"),
        ("month", "2026-10-14", "Try September 2026", "2026-09-01"),
    ],
)
def test_suggestion(granularity: str, anchor: str, label: str, next_anchor: str) -> None:
    s = suggestion(RangeRequest(granularity=granularity, anchor=date.fromisoformat(anchor)))
    assert (s.label, s.range.anchor.isoformat()) == (label, next_anchor)
