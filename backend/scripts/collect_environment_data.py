#!/usr/bin/env python
"""Collect place records for the outdoor/indoor environment dataset.

Examples (run from backend/):
    python scripts/collect_environment_data.py --cities "Москва,Казань,Сочи"
    python scripts/collect_environment_data.py --cities-file cities.txt --limit 80
    python scripts/collect_environment_data.py --cities-file cities_new.txt \
        --limit 60 --append-to ml_data/environment_places.jsonl

The script writes JSONL. ``auto_environment`` is only a weak label; review it
and fill ``manual_environment`` before training a model.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

OTM_URL = "https://api.opentripmap.com/0.1/ru/places"
KUDAGO_URL = "https://kudago.com/public-api/v1.4/places/"
KUDAGO_CITIES = {
    "москва": "msk",
    "санкт-петербург": "spb",
    "петербург": "spb",
    "казань": "kzn",
    "сочи": "sochi",
    "нижний новгород": "nnv",
    "екатеринбург": "ekb",
    "новосибирск": "nsk",
    "самара": "smr",
    "краснодар": "krd",
    "уфа": "ufa",
    "красноярск": "krasnoyarsk",
    "выборг": "vbg",
}
OTM_KINDS = (
    "interesting_places,architecture,monuments_and_memorials,museums,"
    "theatres_and_entertainments,foods,restaurants,cafes,"
    "urban_environment,gardens_and_parks,natural,bridges,view_points,"
    "sculptures,beaches,fortifications,religion"
)
KUDAGO_CATEGORIES = (
    "attractions,sights,palace,homesteads,bridge,fountain,museums,theatre,"
    "concert-hall,art-space,art-centers,restaurants,bar,anticafe,park,"
    "prirodnyj-zapovednik,suburb,photo-places,questroom,observatory"
)
INDOOR_KINDS = {
    "museums",
    "art_galleries",
    "theatres_and_entertainments",
    "opera_houses",
    "concert_halls",
    "planetariums",
    "restaurants",
    "cafes",
    "foods",
    "bakeries",
    "pubs",
}
OUTDOOR_KINDS = {
    "gardens_and_parks",
    "natural",
    "beaches",
    "bridges",
    "view_points",
    "sculptures",
    "squares",
    "urban_environment",
    "fountains",
}
MIXED_KINDS = {
    "fortifications",
    "religion",
    "historic_architecture",
    "palaces",
    "homesteads",
    "suburb",
}
INDOOR_WORDS = {
    "музей", "галерея", "театр", "ресторан", "кафе", "бар", "выставка",
    "museum", "gallery", "theatre", "restaurant", "cafe", "bar",
}
OUTDOOR_WORDS = {
    "парк", "площадь", "мост", "набережная", "фонтан", "пляж", "сквер",
    "сад", "смотровая", "памятник", "скульптура", "park", "bridge", "square",
}
MIXED_WORDS = {
    "кремль", "крепость", "усадьба", "дворец", "монастырь", "собор",
    "заповедник", "крепост", "palace", "castle", "monastery", "cathedral",
}


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_title(value: str) -> str:
    return re.sub(r"[^\w]+", " ", value.lower(), flags=re.UNICODE).strip()


def dataset_key(record: dict[str, Any]) -> tuple[str, str, str]:
    """Stable key used to avoid duplicates across separate collection runs."""
    return (
        str(record.get("source") or ""),
        str(record.get("id") or ""),
        f"{record.get('city', '')}:{normalize_title(str(record.get('title') or ''))}",
    )


def load_existing(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid JSON in {path} line {line_number}: {exc}") from exc
            if isinstance(record, dict):
                records.append(record)
    return records


def classify_weak(kinds: list[str], title: str, category_kind: str) -> tuple[str, float, str]:
    """Return a conservative weak label and a reason for manual review."""
    kind_set = set(kinds)
    words = set(re.findall(r"[\w-]+", title.lower(), flags=re.UNICODE))
    indoor = kind_set & INDOOR_KINDS or words & INDOOR_WORDS
    outdoor = kind_set & OUTDOOR_KINDS or words & OUTDOOR_WORDS
    mixed = kind_set & MIXED_KINDS or words & MIXED_WORDS

    if mixed or (indoor and outdoor):
        return "mixed", 0.72, "mixed kind/title signals"
    if indoor:
        confidence = 0.92 if kind_set & INDOOR_KINDS else 0.78
        return "indoor", confidence, "indoor kind/title signal"
    if outdoor:
        confidence = 0.92 if kind_set & OUTDOOR_KINDS else 0.78
        return "outdoor", confidence, "outdoor kind/title signal"
    if category_kind == "food":
        return "indoor", 0.65, "food category fallback"
    return "unknown", 0.0, "no reliable signal"


def description_from_otm(details: dict[str, Any]) -> str:
    extracts = details.get("wikipedia_extracts") or {}
    info = details.get("info") or {}
    return clean_text(
        extracts.get("text") if isinstance(extracts, dict) else ""
    ) or clean_text(info.get("descr") if isinstance(info, dict) else "")


def otm_record(city: str, details: dict[str, Any]) -> dict[str, Any] | None:
    point = details.get("point") or {}
    title = clean_text(details.get("name"))
    if not details.get("xid") or not title or "lon" not in point or "lat" not in point:
        return None

    kinds = [item for item in clean_text(details.get("kinds")).split(",") if item]
    category_kind = (
        "food" if set(kinds) & {"foods", "restaurants", "cafes", "bakeries", "pubs"}
        else "museum" if "museums" in kinds
        else "walk" if set(kinds) & OUTDOOR_KINDS
        else "location"
    )
    description = description_from_otm(details)
    label, confidence, reason = classify_weak(kinds, title, category_kind)
    return {
        "id": f"otm:{details['xid']}",
        "source": "opentripmap",
        "city": city,
        "title": title,
        "kinds": kinds,
        "description": description,
        "category_kind": category_kind,
        "rate": details.get("rate"),
        "coordinates": [point["lon"], point["lat"]],
        "opening_hours": None,
        "has_photo": bool((details.get("preview") or {}).get("source")),
        "auto_environment": label,
        "auto_confidence": confidence,
        "auto_reason": reason,
        "manual_environment": None,
        "raw_categories": [],
    }


def kudago_record(city: str, item: dict[str, Any]) -> dict[str, Any] | None:
    title = clean_text(item.get("title"))
    coords = item.get("coords") or {}
    if not title or item.get("id") is None or coords.get("lat") is None or coords.get("lon") is None:
        return None

    categories = [clean_text(value) for value in item.get("categories") or []]
    category_kind = (
        "food" if set(categories) & {"restaurants", "bar", "anticafe"}
        else "museum" if set(categories) & {"museums", "theatre", "concert-hall", "art-space", "art-centers"}
        else "walk" if set(categories) & {"park", "prirodnyj-zapovednik", "suburb"}
        else "location"
    )
    description = clean_text(item.get("description")) or clean_text(item.get("body_text"))
    label, confidence, reason = classify_weak(categories, title, category_kind)
    images = item.get("images") or []
    return {
        "id": f"kudago:{item['id']}",
        "source": "kudago",
        "city": city,
        "title": title,
        "kinds": categories,
        "description": description,
        "category_kind": category_kind,
        "rate": None,
        "coordinates": [coords["lon"], coords["lat"]],
        "opening_hours": clean_text(item.get("timetable")) or None,
        "has_photo": bool(images),
        "auto_environment": label,
        "auto_confidence": confidence,
        "auto_reason": reason,
        "manual_environment": None,
        "raw_categories": categories,
    }


async def get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> Any:
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()


async def collect_city(
    client: httpx.AsyncClient,
    city: str,
    *,
    api_key: str,
    radius_meters: int,
    limit: int,
    include_kudago: bool,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    if include_kudago and city.lower() in KUDAGO_CITIES:
        try:
            page_size = min(limit, 100)
            for page in range(1, 5):
                params = {
                    "location": KUDAGO_CITIES[city.lower()],
                    "categories": KUDAGO_CATEGORIES,
                    "fields": "id,title,address,timetable,description,body_text,coords,favorites_count,categories,images,site_url",
                    "expand": "images",
                    "text_format": "text",
                    "page_size": page_size,
                    "page": page,
                    "order_by": "-favorites_count",
                }
                payload = await get_json(client, KUDAGO_URL, params)
                results = payload.get("results") or []
                for item in results:
                    record = kudago_record(city, item)
                    if record and record["id"] not in seen:
                        records.append(record)
                        seen.add(record["id"])
                        if len(records) >= limit:
                            break
                if len(records) >= limit or len(results) < page_size:
                    break
        except httpx.HTTPError as exc:
            print(f"warning: KudaGo failed for {city}: {exc}", file=sys.stderr)

    if not api_key:
        print(f"warning: OPENTRIPMAP_API_KEY is empty; skipped OTM for {city}", file=sys.stderr)
        return records

    try:
        geoname = await get_json(
            client,
            f"{OTM_URL}/geoname",
            {"name": city, "apikey": api_key},
        )
        found = await get_json(
            client,
            f"{OTM_URL}/radius",
            {
                "lat": geoname["lat"],
                "lon": geoname["lon"],
                "radius": radius_meters,
                "kinds": OTM_KINDS,
                "rate": 1,
                "format": "json",
                "limit": limit,
                "apikey": api_key,
            },
        )
        xids = [str(item["xid"]) for item in found if item.get("xid")]
        for xid in xids:
            try:
                details = await get_json(client, f"{OTM_URL}/xid/{xid}", {"apikey": api_key})
            except httpx.HTTPError as exc:
                print(f"warning: OTM details failed for {city}/{xid}: {exc}", file=sys.stderr)
                continue
            record = otm_record(city, details)
            if record and record["id"] not in seen:
                records.append(record)
                seen.add(record["id"])
    except (httpx.HTTPError, KeyError, TypeError) as exc:
        print(f"warning: OpenTripMap failed for {city}: {exc}", file=sys.stderr)

    return records


def parse_cities(args: argparse.Namespace) -> list[str]:
    cities: list[str] = []
    if args.cities:
        cities.extend(item.strip() for item in args.cities.split(",") if item.strip())
    if args.cities_file:
        cities.extend(
            line.strip()
            for line in Path(args.cities_file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    result: list[str] = []
    seen: set[str] = set()
    for city in cities:
        key = city.casefold()
        if key not in seen:
            result.append(city)
            seen.add(key)
    if not result:
        raise SystemExit("provide --cities or --cities-file")
    return result


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cities", help="comma-separated city names")
    parser.add_argument("--cities-file", help="UTF-8 file with one city per line")
    parser.add_argument("--output", default="ml_data/environment_places.jsonl")
    parser.add_argument(
        "--append-to",
        help="append only new records to this existing JSONL instead of overwriting --output",
    )
    parser.add_argument(
        "--max-new",
        type=int,
        help="stop after this many records not already present in --append-to",
    )
    parser.add_argument("--radius", type=int, default=15000)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--no-kudago", action="store_true")
    args = parser.parse_args()
    if args.radius < 100 or args.limit < 1:
        parser.error("--radius must be >= 100 and --limit must be >= 1")
    if args.max_new is not None and args.max_new < 1:
        parser.error("--max-new must be >= 1")

    cities = parse_cities(args)
    api_key = settings.opentripmap_api_key
    output = Path(args.append_to or args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    records = load_existing(output) if args.append_to else []
    existing_keys = {dataset_key(record) for record in records}
    collected_new = 0

    async with httpx.AsyncClient(timeout=httpx.Timeout(args.timeout, connect=10.0)) as client:
        for city in cities:
            print(f"collecting {city}...", flush=True)
            city_records = await collect_city(
                client,
                city,
                api_key=api_key,
                radius_meters=args.radius,
                limit=args.limit,
                include_kudago=not args.no_kudago,
            )
            added = 0
            for record in city_records:
                key = dataset_key(record)
                if key in existing_keys:
                    continue
                records.append(record)
                existing_keys.add(key)
                added += 1
                collected_new += 1
                if args.max_new is not None and collected_new >= args.max_new:
                    break
            print(f"  fetched={len(city_records)} new={added}", flush=True)
            if args.max_new is not None and collected_new >= args.max_new:
                break

    with output.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    counts: dict[str, int] = {}
    for record in records:
        label = record["auto_environment"]
        counts[label] = counts.get(label, 0) + 1
    print(f"wrote {len(records)} records to {output}; new={collected_new}")
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))