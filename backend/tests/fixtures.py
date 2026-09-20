"""Canned OpenTripMap / OSRM responses for the pipeline tests."""
import re

import respx
from httpx import Response

OTM_BASE = "https://api.opentripmap.com/0.1/ru/places"

GEONAME = {
    "name": "Saint Petersburg",
    "country": "RU",
    "lat": 59.93863,
    "lon": 30.31413,
    "population": 5351935,
    "timezone": "Europe/Moscow",
}

RAW_PLACES = [
    ("hermitage", "Государственный Эрмитаж", "museums,cultural", 7, 30.31456, 59.93984),
    ("palace_square", "Дворцовая площадь", "urban_environment,interesting_places", 6, 30.31413, 59.93863),
    ("pyshechnaya", "Пышечная", "foods", 4, 30.32295, 59.93555),
    ("russian_museum", "Русский музей", "museums", 7, 30.33250, 59.93866),
    ("summer_garden", "Летний сад", "gardens_and_parks,natural", 6, 30.33470, 59.94520),
    ("kazan_cathedral", "Казанский собор", "architecture,religion", 7, 30.32450, 59.93430),
    ("spilled_blood", "Спас на Крови", "architecture,monuments_and_memorials", 7, 30.32890, 59.94010),
    ("bridge", "Аничков мост", "bridges,urban_environment", 5, 30.34320, 59.93330),
    ("cafe_singer", "Кафе Зингеръ", "foods", 5, 30.32570, 59.93560),
    ("peterhof", "Петергоф", "gardens_and_parks", 7, 29.90890, 59.88460),
]


def _radius_item(entry: tuple) -> dict:
    xid, name, kinds, rate, lon, lat = entry
    return {
        "xid": xid,
        "name": name,
        "kinds": kinds,
        "rate": rate,
        "dist": 500.0,
        "point": {"lon": lon, "lat": lat},
    }


def _details(entry: tuple) -> dict:
    xid, name, kinds, rate, lon, lat = entry
    return {
        "xid": xid,
        "name": name,
        "kinds": kinds,
        "rate": rate,
        "point": {"lon": lon, "lat": lat},
        "address": {"road": "Тестовая улица", "house_number": "1", "city": "Санкт-Петербург"},
        "wikipedia_extracts": {
            "text": f"{name} — известное место Санкт-Петербурга, которое стоит посетить во время поездки."
        },
        "preview": {"source": f"https://images.example/{xid}.jpg"},
    }


def mock_external_apis(router: respx.MockRouter) -> None:
    """Register OpenTripMap and OSRM stubs on the given respx router."""
    router.get(f"{OTM_BASE}/geoname").mock(return_value=Response(200, json=GEONAME))

    def radius_response(request):
        kinds = request.url.params.get("kinds", "")
        wanted = {k for k in kinds.split(",") if k}
        matched = [
            entry
            for entry in RAW_PLACES
            if wanted & set(entry[2].split(","))
        ] or list(RAW_PLACES)
        return Response(200, json=[_radius_item(entry) for entry in matched])

    router.get(f"{OTM_BASE}/radius").mock(side_effect=radius_response)

    by_xid = {entry[0]: entry for entry in RAW_PLACES}

    def details_response(request):
        xid = request.url.path.rsplit("/", 1)[-1]
        entry = by_xid.get(xid)
        if entry is None:
            return Response(404, json={"error": "not found"})
        return Response(200, json=_details(entry))

    router.get(re.compile(rf"{re.escape(OTM_BASE)}/xid/.+")).mock(side_effect=details_response)

    router.get(re.compile(r"https://routing\.openstreetmap\.de/.+")).mock(
        return_value=Response(200, json={"routes": [{"distance": 900.0, "duration": 720.0}]})
    )
    router.get(re.compile(r"https://router\.project-osrm\.org/.+")).mock(
        return_value=Response(200, json={"routes": [{"distance": 900.0, "duration": 720.0}]})
    )


KUDAGO_PLACES = [
    ("Государственный Эрмитаж", ["museums"], 2195, "ср–вс 11:00–18:00", 30.31456, 59.93984),
    ("Дворцовая площадь", ["attractions"], 1411, "", 30.31413, 59.93863),
    ("Летний сад", ["park"], 1331, "ежедневно 10:00–22:00", 30.33470, 59.94520),
    ("Пышечная", ["restaurants"], 860, "ежедневно 09:00–20:00", 30.32295, 59.93555),
    ("Мозаичный дворик", ["photo-places"], 640, "", 30.35180, 59.94620),
    ("Музей Фаберже", ["museums"], 520, "пн–вс 10:00–20:45", 30.34390, 59.93390),
]


def _kudago_item(index: int, entry: tuple) -> dict:
    title, categories, favorites, timetable, lon, lat = entry
    return {
        "id": 1000 + index,
        "title": title,
        "slug": f"place-{index}",
        "address": "Тестовая улица, д. 1",
        "timetable": timetable,
        "description": f"{title} — одно из самых известных мест Санкт-Петербурга, куда стоит зайти.",
        "body_text": "",
        "coords": {"lat": lat, "lon": lon},
        "subway": "Адмиралтейская",
        "favorites_count": favorites,
        "comments_count": 12,
        "is_closed": False,
        "is_stub": False,
        "categories": categories,
        "site_url": f"https://kudago.com/spb/place/place-{index}/",
        "images": [
            {
                "image": f"https://media.kudago.com/{index}.jpg",
                "thumbnails": {"640x384": f"https://media.kudago.com/thumb/{index}.jpg"},
            }
        ],
    }


def mock_kudago(router: respx.MockRouter, *, places: list[tuple] | None = None) -> None:
    """Stub the KudaGo catalogue; the first page carries everything."""
    entries = KUDAGO_PLACES if places is None else places

    def response(request):
        page = int(request.url.params.get("page", 1))
        if page > 1:
            return Response(200, json={"count": len(entries), "results": []})
        results = [_kudago_item(i, entry) for i, entry in enumerate(entries)]
        return Response(200, json={"count": len(entries), "results": results})

    router.get("https://kudago.com/public-api/v1.4/places/").mock(side_effect=response)


def mock_weather(router: respx.MockRouter, *, days: list[str]) -> None:
    router.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=Response(
            200,
            json={
                "daily": {
                    "time": days,
                    "weather_code": [61] * len(days),
                    "temperature_2m_max": [14.4] * len(days),
                    "temperature_2m_min": [7.2] * len(days),
                    "precipitation_probability_max": [70] * len(days),
                }
            },
        )
    )


def mock_ors(router: respx.MockRouter, *, status: int = 200) -> None:
    payload = {
        "features": [{"properties": {"summary": {"distance": 1240.0, "duration": 960.0}}}]
    }
    router.get(re.compile(r"https://api\.openrouteservice\.org/v2/directions/.+")).mock(
        return_value=Response(status, json=payload if status == 200 else {})
    )


SAMPLE_DRAFT = {
    "destination": "Санкт-Петербург",
    "startDate": "2026-09-15",
    "startTime": "10:00",
    "endDate": "2026-09-17",
    "endTime": "18:00",
    "budget": 45000,
    "travelers": 2,
    "interests": ["sights", "museums", "gastro"],
    "pace": "medium",
    "findHousing": False,
}
