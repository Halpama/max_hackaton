"""GigaChat prompts. Every call has a deterministic fallback so a flaky or
unconfigured LLM degrades the itinerary instead of breaking it."""
import re
from dataclasses import replace

import orjson

from app.clients.gigachat import gigachat
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.trip import TripDraft
from app.services.places import PlaceCandidate

logger = get_logger(__name__)

INTEREST_LABELS = {
    "sights": "достопримечательности",
    "museums": "музеи",
    "gastro": "гастрономия",
    "walks": "прогулки",
    "nature": "природа",
    "unusual": "необычные места",
}

PACE_LABELS = {"calm": "спокойный", "medium": "средний", "active": "активный"}

#: Hard bounds for a single stop — the model sometimes invents half-day fountains.
MIN_STAY_MINUTES = 15
MAX_STAY_MINUTES = 240


def titlecase_city(value: str) -> str:
    """The model sometimes answers "нижний новгород"; that becomes a UI heading.

    Only all-lowercase replies are touched, so "Санкт-Петербург" and "Нижний
    Новгород-на-Волге" survive untouched.
    """
    if not value or value != value.lower():
        return value
    return re.sub(r"[^\s\-]+", lambda match: match.group(0).capitalize(), value)


def extract_json(raw: str) -> dict:
    """Pull a JSON object out of a model reply that may be fenced or chatty."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text.strip("`")
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"No JSON object in model reply: {raw[:200]}")

    return orjson.loads(text[start : end + 1])


def clamp_stay_minutes(value: object) -> int | None:
    """Snap a model duration onto a readable quarter-hour inside safe bounds."""
    try:
        minutes = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if minutes <= 0:
        return None
    snapped = int(round(minutes / 15) * 15)
    return max(MIN_STAY_MINUTES, min(MAX_STAY_MINUTES, snapped))


def _parse_stops(data: dict) -> list[tuple[str, int | None]]:
    """Accept both {"stops":[{id,minutes}]} and legacy {"selected":[id,...]}."""
    stops = data.get("stops")
    if isinstance(stops, list) and stops:
        parsed: list[tuple[str, int | None]] = []
        for item in stops:
            if isinstance(item, dict):
                xid = str(item.get("id") or "").strip()
                if xid:
                    parsed.append((xid, clamp_stay_minutes(item.get("minutes"))))
            elif item:
                parsed.append((str(item), None))
        return parsed

    selected = data.get("selected") or []
    return [(str(xid), None) for xid in selected if xid]


async def analyze_destination(draft: TripDraft) -> dict:
    """Normalise the destination and choose a search radius.

    Returns {"city": <display name>, "geoQuery": <geocoder name>, "radiusMeters": int}.
    """
    fallback = {
        "city": draft.destination.strip(),
        "geoQuery": draft.destination.strip(),
        "radiusMeters": 7000,
    }

    if not settings.gigachat_configured:
        return fallback

    interests = ", ".join(INTEREST_LABELS.get(i, i) for i in draft.interests) or "любые"
    prompt = (
        "Ты помощник по планированию путешествий. "
        "Пользователь ввёл направление, возможно с опечаткой или в разговорной форме.\n"
        f"Направление: «{draft.destination}»\n"
        f"Интересы: {interests}\n"
        f"Темп: {PACE_LABELS.get(draft.pace, draft.pace)}\n\n"
        "Верни СТРОГО один JSON-объект без пояснений и markdown:\n"
        '{"city": "каноничное название города по-русски", '
        '"geoQuery": "то же название по-русски для геокодера (НЕ латиница, НЕ другой город)", '
        '"radiusMeters": число от 3000 до 15000 — радиус поиска мест от центра}'
    )

    try:
        reply = await gigachat.complete(
            [{"role": "user", "content": prompt}], temperature=0.1, max_tokens=256
        )
        data = extract_json(reply)
    except Exception as exc:  # noqa: BLE001
        logger.warning("analyze_destination fell back to raw input: %s", exc)
        return fallback

    city = titlecase_city(str(data.get("city") or "").strip()) or fallback["city"]
    geo_query = str(data.get("geoQuery") or "").strip() or city

    try:
        radius = int(data.get("radiusMeters") or 7000)
    except (TypeError, ValueError):
        radius = 7000

    return {
        "city": city,
        "geoQuery": geo_query,
        "radiusMeters": max(3000, min(15000, radius)),
    }


async def curate_places(
    draft: TripDraft,
    candidates: list[PlaceCandidate],
    needed: int,
    *,
    memory_block: str | None = None,
) -> list[PlaceCandidate]:
    """Pick places and typical visit lengths; fall back to ranking on failure."""
    by_rating = sorted(candidates, key=lambda c: (c.rate, bool(c.image_url)), reverse=True)
    fallback = by_rating[:needed]

    if not settings.gigachat_configured:
        return fallback

    # Cap the prompt so a large candidate pool cannot blow the token budget.
    shortlist = by_rating[: min(len(by_rating), max(needed * 3, needed))]
    listing = "\n".join(
        f"{i + 1}. id={c.xid} | {c.title} | {c.category} | популярность {c.rate}/7"
        for i, c in enumerate(shortlist)
    )
    interests = ", ".join(INTEREST_LABELS.get(i, i) for i in draft.interests) or "любые"
    memory = f"\nПамять сервиса (учитывай при выборе):\n{memory_block}\n" if memory_block else ""

    prompt = (
        f"Собери маршрут по городу для группы: {draft.adults} взрослых и "
        f"{draft.children} детей (всего {draft.travelers} чел.).\n"
        f"Интересы: {interests}\n"
        f"Темп: {PACE_LABELS.get(draft.pace, draft.pace)}\n"
        f"Бюджет на всю поездку: {draft.budget} ₽"
        + (" (только бесплатные места)" if draft.budget <= 0 else "")
        + "\n\n"
        f"Кандидаты:\n{listing}\n"
        f"{memory}\n"
        f"Выбери ровно {needed} лучших мест в логичном порядке осмотра. "
        "Избегай дубликатов и однотипных мест подряд. "
        "Если выбраны гастро-интересы, добавь 1-2 места с едой.\n"
        "Не предлагай отели и жильё — только точки маршрута.\n"
        "Для каждого места укажи реалистичное время визита туриста в минутах:\n"
        "• фонтан, памятник, мост, смотровая, фототочка — 15–30\n"
        "• кафе / ресторан — 45–75\n"
        "• музей / галерея / храм — 60–150\n"
        "• парк / набережная — 60–120\n"
        "• загородная локация / остров на полдня — 150–210\n"
        "Не растягивай короткие точки на полдня.\n\n"
        "Верни СТРОГО один JSON-объект без пояснений:\n"
        '{"stops": [{"id": "id1", "minutes": 30}, {"id": "id2", "minutes": 90}]}'
    )

    try:
        reply = await gigachat.complete(
            [{"role": "user", "content": prompt}], temperature=0.3, max_tokens=1200
        )
        data = extract_json(reply)
        stops = _parse_stops(data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("curate_places fell back to rating order: %s", exc)
        return fallback

    index = {c.xid: c for c in candidates}
    picked: list[PlaceCandidate] = []
    for xid, minutes in stops:
        candidate = index.get(xid)
        if candidate is None or any(c.xid == xid for c in picked):
            continue
        picked.append(
            replace(candidate, stay_minutes=minutes)
            if minutes is not None
            else candidate
        )

    if len(picked) < max(2, needed // 2):
        logger.warning("Model returned %d usable ids, keeping ranking order", len(picked))
        return fallback

    # Top up from our ranking if the model returned fewer than requested.
    for candidate in fallback:
        if len(picked) >= needed:
            break
        if all(c.xid != candidate.xid for c in picked):
            picked.append(candidate)

    return picked[:needed]
