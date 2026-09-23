"""Russian labels rendered server-side so the frontend can print them as-is."""
from datetime import date, datetime, time

MONTHS_GENITIVE = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)

MONTHS_SHORT = (
    "янв", "фев", "мар", "апр", "мая", "июн",
    "июл", "авг", "сент", "окт", "ноя", "дек",
)


WEEKDAYS = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")


def weekday_label(value: date) -> str:
    """«14 марта, пятница» — the weekday matters when museums close on Mondays."""
    return f"{value.day} {MONTHS_GENITIVE[value.month - 1]}, {WEEKDAYS[value.weekday()]}"


def plural(count: int, one: str, few: str, many: str) -> str:
    """Russian pluralisation: 1 стол, 2 стола, 5 столов."""
    mod100 = abs(count) % 100
    if 11 <= mod100 <= 14:
        return many
    mod10 = abs(count) % 10
    if mod10 == 1:
        return one
    if 2 <= mod10 <= 4:
        return few
    return many


def travelers_label(adults: int, children: int = 0) -> str:
    if not children:
        word = plural(adults, "путешественник", "путешественника", "путешественников")
        return f"{adults} {word}"

    parts = [f"{adults} {plural(adults, 'взрослый', 'взрослых', 'взрослых')}" ]
    if children:
        parts.append(f"{children} {plural(children, 'ребёнок', 'ребёнка', 'детей')}")
    return ", ".join(parts)


def travelers_short_label(adults: int, children: int = 0) -> str:
    if not children:
        return f"{adults} чел"
    return travelers_label(adults, children)


def date_range_label(start: date, end: date) -> str:
    if start == end:
        return f"{start.day} {MONTHS_GENITIVE[start.month - 1]}"
    if start.month == end.month and start.year == end.year:
        return f"{start.day}–{end.day} {MONTHS_GENITIVE[start.month - 1]}"
    return (
        f"{start.day} {MONTHS_SHORT[start.month - 1]} – "
        f"{end.day} {MONTHS_SHORT[end.month - 1]}"
    )


def short_date_range_label(start: date, end: date) -> str:
    """Compact variant used on the trips list."""
    if start == end:
        return f"{start.day} {MONTHS_SHORT[start.month - 1]}"
    if start.month == end.month and start.year == end.year:
        return f"{start.day}–{end.day} {MONTHS_SHORT[start.month - 1]}"
    return (
        f"{start.day} {MONTHS_SHORT[start.month - 1]} – "
        f"{end.day} {MONTHS_SHORT[end.month - 1]}"
    )


def duration_label(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} мин"

    hours = minutes / 60
    if minutes % 60 == 0:
        whole = minutes // 60
        return f"{whole} {plural(whole, 'час', 'часа', 'часов')}"

    if minutes % 30 == 0:
        # 1.5 часа / 2.5 часа — matches the mock formatting.
        return f"{hours:.1f} часа".replace(".0", "")

    return f"{hours:.1f} часа"


def time_label(value: time | datetime) -> str:
    return f"{value.hour:02d}:{value.minute:02d}"


def time_range_label(start: datetime, end: datetime) -> str:
    return f"{time_label(start)} – {time_label(end)}"
