"""Parse free-text Russian opening hours into open/close windows."""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

#: Monday=0 … Sunday=6, matching datetime.weekday().
_DAY_INDEX: dict[str, int] = {
    "пн": 0,
    "понедельник": 0,
    "вт": 1,
    "вторник": 1,
    "ср": 2,
    "среда": 2,
    "чт": 3,
    "четверг": 3,
    "пт": 4,
    "пятница": 4,
    "сб": 5,
    "суббота": 5,
    "вс": 6,
    "воскресенье": 6,
}

_DAY_TOKEN = (
    r"(?:ежедневно|ежедн\.?|пн|вт|ср|чт|пт|сб|вс|"
    r"понедельник|вторник|среда|четверг|пятница|суббота|воскресенье)"
)
_DAYS_PART = rf"{_DAY_TOKEN}(?:\s*[–\—\-—,и]\s*{_DAY_TOKEN})*"
_TIME = r"\d{1,2}[:.]\d{2}"
_HOURS_PART = rf"(?:весь\s+день|круглосуточно|{_TIME}\s*[–\—\-—]\s*{_TIME})"
_SEGMENT_RE = re.compile(rf"({_DAYS_PART})\s+({_HOURS_PART})", re.IGNORECASE | re.UNICODE)
_RANGE_RE = re.compile(
    rf"({_DAY_TOKEN})\s*[–\—\-—]\s*({_DAY_TOKEN})", re.IGNORECASE | re.UNICODE
)
_SINGLE_RE = re.compile(_DAY_TOKEN, re.IGNORECASE | re.UNICODE)


def _parse_clock(value: str) -> time:
    hours, minutes = re.split(r"[:.]", value, maxsplit=1)
    return time(int(hours) % 24, int(minutes))


def _day_key(token: str) -> int | None:
    key = token.lower().rstrip(".")
    if key.startswith("ежедн"):
        return None  # handled by caller as all days
    return _DAY_INDEX.get(key)


def _expand_days(raw: str) -> set[int]:
    lower = raw.lower().strip()
    if lower.startswith("ежедн"):
        return set(range(7))

    days: set[int] = set()
    consumed = [False] * len(lower)

    for match in _RANGE_RE.finditer(lower):
        start = _day_key(match.group(1))
        end = _day_key(match.group(2))
        if start is None or end is None:
            continue
        if end < start:
            chunk = list(range(start, 7)) + list(range(0, end + 1))
        else:
            chunk = list(range(start, end + 1))
        days.update(chunk)
        for i in range(match.start(), match.end()):
            consumed[i] = True

    remainder = "".join(ch if not consumed[i] else " " for i, ch in enumerate(lower))
    for match in _SINGLE_RE.finditer(remainder):
        token = match.group(0)
        if token.lower().startswith("ежедн"):
            return set(range(7))
        index = _day_key(token)
        if index is not None:
            days.add(index)

    return days or set(range(7))


def _parse_hours_span(raw: str) -> tuple[time, time] | None:
    lower = raw.lower().strip()
    if "весь" in lower or "круглосуточно" in lower:
        return time(0, 0), time(23, 59)

    match = re.search(rf"({_TIME})\s*[–\—\-—]\s*({_TIME})", raw)
    if not match:
        return None
    return _parse_clock(match.group(1)), _parse_clock(match.group(2))


def hours_for_day(raw: str | None, day: date) -> tuple[time, time] | None:
    """Return (open, close) for `day`, or None when hours are unknown."""
    if not raw:
        return None

    cleaned = re.sub(r"\([^)]*\)", " ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None

    weekday = day.weekday()
    for match in _SEGMENT_RE.finditer(cleaned):
        days = _expand_days(match.group(1))
        span = _parse_hours_span(match.group(2))
        if span and weekday in days:
            return span

    # Bare "10:00–20:00" with no day prefix — treat as every day.
    if not _SEGMENT_RE.search(cleaned):
        return _parse_hours_span(cleaned)

    return None


def _close_datetime(day: date, opens: time, closes: time) -> datetime:
    close_dt = datetime.combine(day, closes)
    if closes <= opens:
        close_dt += timedelta(days=1)
    return close_dt


def fit_visit(
    start: datetime,
    stay_minutes: int,
    *,
    opening_hours: str | None,
    day_end: datetime,
) -> tuple[datetime, datetime, int]:
    """Clip a visit so it does not run past closing time or the day boundary.

    Museums that close at 20:00 must not be scheduled until 21:00.
    """
    finish = start + timedelta(minutes=stay_minutes)
    if finish > day_end:
        finish = day_end

    window = hours_for_day(opening_hours, start.date())
    if window:
        opens, closes = window
        open_dt = datetime.combine(start.date(), opens)
        close_dt = _close_datetime(start.date(), opens, closes)

        if start < open_dt:
            start = open_dt
            finish = start + timedelta(minutes=stay_minutes)

        if finish > close_dt:
            finish = close_dt

        if start >= close_dt:
            start = max(open_dt, close_dt - timedelta(minutes=min(stay_minutes, 60)))
            finish = close_dt
        elif finish <= start:
            finish = min(close_dt, start + timedelta(minutes=15))

    stay = max(15, int((finish - start).total_seconds() // 60))
    return start, finish, stay
