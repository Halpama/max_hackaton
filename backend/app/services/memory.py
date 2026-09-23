"""First-party city/place memory in Postgres (survives Redis flush)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.russian_cities import normalize_city_key
from app.db.models import CityMemory, PlaceStats
from app.schemas.trip import Place as PlaceSchema
from app.services.places import PlaceCandidate


async def load_city_memory(session: AsyncSession, city: str) -> CityMemory | None:
    key = normalize_city_key(city)
    return await session.scalar(select(CityMemory).where(CityMemory.city_key == key))


async def load_place_stats_for_city(
    session: AsyncSession, city: str
) -> dict[str, PlaceStats]:
    key = normalize_city_key(city)
    rows = await session.scalars(
        select(PlaceStats).where(PlaceStats.city == key)
    )
    # Also match display-case city strings stored earlier.
    rows2 = await session.scalars(
        select(PlaceStats).where(PlaceStats.city.ilike(city.strip()))
    )
    out: dict[str, PlaceStats] = {}
    for row in list(rows) + list(rows2):
        out[row.external_id] = row
    return out


def boost_candidates(
    candidates: list[PlaceCandidate],
    stats: dict[str, PlaceStats],
    *,
    hints: list[str] | None = None,
) -> list[PlaceCandidate]:
    """Reorder candidates using pick_count and thin search name hints."""
    if not candidates:
        return candidates

    hint_tokens = [h.casefold() for h in (hints or []) if h]

    def score(c: PlaceCandidate) -> tuple[int, int, int]:
        row = stats.get(c.xid)
        picks = row.pick_count if row else 0
        tip_hit = 0
        title = c.title.casefold()
        for hint in hint_tokens:
            if hint and (hint in title or title in hint):
                tip_hit = 1
                break
        return (picks, tip_hit, c.rate)

    return sorted(candidates, key=score, reverse=True)


def curation_memory_block(
    candidates: list[PlaceCandidate],
    stats: dict[str, PlaceStats],
    city_memory: CityMemory | None,
) -> str:
    """Compact first-party context for the GigaChat curation prompt."""
    lines: list[str] = []
    if city_memory and city_memory.digest:
        lines.append(f"Контекст по городу: {city_memory.digest[:400]}")
    if city_memory and city_memory.discovery_hints:
        hints = ", ".join(str(h) for h in city_memory.discovery_hints[:8])
        lines.append(f"Часто упоминают: {hints}")

    noted = 0
    for c in candidates[:20]:
        row = stats.get(c.xid)
        if row is None or row.pick_count <= 0:
            continue
        avg_stay = (
            int(row.stay_minutes_sum / row.stay_samples)
            if row.stay_samples
            else None
        )
        tip = f"; заметка: {row.tip}" if row.tip else ""
        stay = f", обычно ~{avg_stay} мин" if avg_stay else ""
        lines.append(
            f"- {c.title}: выбирали {row.pick_count}×{stay}{tip}"
        )
        noted += 1
        if noted >= 8:
            break
    return "\n".join(lines)


async def record_successful_route(
    session: AsyncSession,
    *,
    city: str,
    lat: float,
    lon: float,
    radius_meters: int,
    interests: list[str],
    places: list[PlaceSchema],
    discovery_hints: list[str] | None = None,
    digest: str | None = None,
) -> None:
    """Upsert city playbook + per-place pick stats after a ready route."""
    city_key = normalize_city_key(city)
    memory = await session.scalar(
        select(CityMemory).where(CityMemory.city_key == city_key)
    )
    if memory is None:
        memory = CityMemory(
            city_key=city_key,
            display_name=city,
            lat=lat,
            lon=lon,
            radius_meters=radius_meters,
            trip_count=0,
            discovery_hints=[],
            digest=None,
        )
        session.add(memory)

    memory.display_name = city
    memory.lat = lat
    memory.lon = lon
    memory.radius_meters = radius_meters
    memory.trip_count = int(memory.trip_count or 0) + 1
    if discovery_hints:
        merged = list(memory.discovery_hints or [])
        for hint in discovery_hints:
            if hint and hint not in merged:
                merged.append(hint)
        memory.discovery_hints = merged[:24]
    if digest:
        memory.digest = digest[:800]

    for place in places:
        row = await session.scalar(
            select(PlaceStats).where(PlaceStats.external_id == place.id)
        )
        coords = place.coordinates or [None, None]
        lon_v = float(coords[0]) if coords and coords[0] is not None else None
        lat_v = float(coords[1]) if coords and len(coords) > 1 and coords[1] is not None else None
        if row is None:
            row = PlaceStats(
                external_id=place.id,
                city=city_key,
                title=place.title,
                category=place.category,
                category_kind=place.category_kind,
                lat=lat_v,
                lon=lon_v,
                pick_count=0,
                stay_minutes_sum=0,
                stay_samples=0,
                source_name=place.source_name,
                source_url=place.source_url,
                interests={},
            )
            session.add(row)

        row.title = place.title
        row.city = city_key
        row.category = place.category
        row.category_kind = place.category_kind
        row.lat = lat_v
        row.lon = lon_v
        row.source_name = place.source_name or row.source_name
        row.source_url = place.source_url or row.source_url
        row.pick_count = int(row.pick_count or 0) + 1

        # Parse duration like "1 ч 30 мин" lightly via duration_label stored on place.
        minutes = _parse_duration_minutes(place.duration_label)
        if minutes:
            row.stay_minutes_sum = int(row.stay_minutes_sum or 0) + minutes
            row.stay_samples = int(row.stay_samples or 0) + 1

        hist = dict(row.interests or {})
        for interest in interests:
            hist[interest] = int(hist.get(interest, 0)) + 1
        row.interests = hist


def _parse_duration_minutes(label: str | None) -> int | None:
    if not label:
        return None
    text = label.lower().replace("ё", "е")
    hours = 0
    mins = 0
    if "ч" in text:
        try:
            hours = int("".join(ch for ch in text.split("ч", 1)[0] if ch.isdigit()) or 0)
        except ValueError:
            hours = 0
    if "мин" in text:
        part = text.split("мин", 1)[0]
        digits = "".join(ch for ch in part[-4:] if ch.isdigit())
        try:
            mins = int(digits or 0)
        except ValueError:
            mins = 0
    total = hours * 60 + mins
    return total if total > 0 else None
