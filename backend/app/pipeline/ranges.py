"""resolve_range: a day, week or month in the user's timezone, as a UTC window."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.contracts.ws.common import RangeRequest
from app.contracts.ws.server_message import RangeSuggestion

# Sources give kickoff times only; a match is in the window if it ends there.
MATCH_LENGTH = timedelta(hours=2)


class BadTimezone(ValueError):
    pass


@dataclass(frozen=True)
class Window:
    start: datetime  # UTC, inclusive
    end: datetime  # UTC, exclusive
    label: str  # "Mon 12 Oct – Sun 18 Oct 2026, London time"
    when: str  # "between Mon 12 Oct and Sun 18 Oct 2026", for messages

    @property
    def kickoff_from(self) -> datetime:
        return self.start - MATCH_LENGTH

    @property
    def kickoff_to(self) -> datetime:
        return self.end - MATCH_LENGTH


def zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise BadTimezone(f"unknown timezone {name!r}") from e


def zone_label(name: str) -> str:
    """Europe/London -> London time; UTC -> UTC."""
    city = name.rsplit("/", 1)[-1].replace("_", " ")
    return "UTC" if city in ("UTC", "Etc") else f"{city} time"


def day_label(d: date) -> str:
    return f"{d:%a} {d.day} {d:%b}"


def bounds(r: RangeRequest) -> tuple[date, date]:
    """First day, and the day after the last."""
    a = r.anchor
    if r.granularity == "day":
        return a, a + timedelta(days=1)
    if r.granularity == "week":
        monday = a - timedelta(days=a.weekday())
        return monday, monday + timedelta(days=7)
    first = a.replace(day=1)
    return first, (first + timedelta(days=32)).replace(day=1)


def resolve(r: RangeRequest, timezone: str) -> Window:
    tz = zone(timezone)
    first, after = bounds(r)
    last = after - timedelta(days=1)
    if r.granularity == "day":
        text = f"{day_label(first)} {first.year}"
        when = f"on {text}"
    elif r.granularity == "week":
        text = f"{day_label(first)} – {day_label(last)} {last.year}"
        when = f"between {day_label(first)} and {day_label(last)} {last.year}"
    else:
        text = f"{first:%B %Y}"
        when = f"in {text}"
    return Window(
        start=datetime.combine(first, time(), tz).astimezone(UTC),
        end=datetime.combine(after, time(), tz).astimezone(UTC),
        label=f"{text}, {zone_label(timezone)}",
        when=when,
    )


def span(first: date, last: date) -> str:
    """Mon 12 – Sun 18 Oct, or Mon 28 Sep – Sun 4 Oct across months."""
    if (first.year, first.month) == (last.year, last.month):
        return f"{first:%a} {first.day} – {day_label(last)}"
    return f"{day_label(first)} – {day_label(last)}"


def suggestion(r: RangeRequest) -> RangeSuggestion:
    """Where to look when a range has no matches: a day's week, else the period before."""
    first, _ = bounds(r)
    if r.granularity in ("day", "week"):
        monday, after = bounds(
            RangeRequest(granularity="week", anchor=r.anchor if r.granularity == "day" else first - timedelta(days=7))
        )
        week = RangeRequest(granularity="week", anchor=monday)
        what = "the whole week" if r.granularity == "day" else "the previous week"
        return RangeSuggestion(label=f"Try {what}: {span(monday, after - timedelta(days=1))}", range=week)
    prev = (first - timedelta(days=1)).replace(day=1)
    return RangeSuggestion(label=f"Try {prev:%B %Y}", range=RangeRequest(granularity="month", anchor=prev))
