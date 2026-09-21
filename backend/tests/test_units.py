import hashlib
import hmac
import json
from datetime import date, datetime
from urllib.parse import urlencode

import pytest

from app.core import security
from app.core.config import settings
from app.services import budget, formatting
from app.services.llm import extract_json
from app.services.places import (
    normalize_title,
    parse_rate,
    pick_category,
    pick_category_kind,
    prettify_title,
)
from app.services.scheduler import build_day_slots
from app.services.transit import has_metro, pick_mode


@pytest.mark.parametrize(
    ("count", "expected"),
    [(1, "1 путешественник"), (2, "2 путешественника"), (5, "5 путешественников"), (11, "11 путешественников")],
)
def test_travelers_label(count: int, expected: str):
    assert formatting.travelers_label(count) == expected


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [(45, "45 мин"), (60, "1 час"), (120, "2 часа"), (90, "1.5 часа"), (300, "5 часов")],
)
def test_duration_label(minutes: int, expected: str):
    assert formatting.duration_label(minutes) == expected


def test_date_range_label():
    assert formatting.date_range_label(date(2026, 9, 15), date(2026, 9, 17)) == "15–17 сентября"
    assert formatting.date_range_label(date(2026, 9, 28), date(2026, 10, 2)) == "28 сент – 2 окт"


def test_budget_label_and_prices():
    assert budget.budget_label(45000) == "~45 000 ₽"
    assert budget.price_label(0, approximate=False) == "Бесплатно"
    assert budget.price_label(800, approximate=False) == "800 ₽ · за 1 чел"
    assert budget.price_label(1500, approximate=True, travelers=2) == "~1 500 ₽ · на 2 чел"


@pytest.mark.parametrize(
    ("meters", "expected"),
    [(300, "walk"), (1200, "walk"), (3000, "metro"), (20000, "taxi")],
)
def test_transit_mode_thresholds(meters: int, expected: str):
    assert pick_mode(meters) == expected


def test_category_mapping():
    assert pick_category_kind(["museums", "cultural"]) == "museum"
    assert pick_category_kind(["foods"]) == "food"
    assert pick_category_kind(["gardens_and_parks"]) == "walk"
    assert pick_category_kind(["architecture"]) == "location"
    assert pick_category(["museums"]) == "Музей"
    assert pick_category(["unknown_kind"]) == "Достопримечательность"


def test_public_space_is_not_a_museum():
    # OpenTripMap tags squares and parks as "cultural"; they used to be priced
    # like a ticketed venue.
    assert pick_category_kind(["urban_environment", "cultural", "squares"]) == "walk"
    assert pick_category_kind(["gardens_and_parks", "cultural"]) == "walk"


def test_outdoor_monument_is_not_a_museum():
    kinds = ["historic", "monuments_and_memorials", "museums", "history_museums"]
    assert pick_category_kind(kinds, "Памятник К. Д. Ушинскому") == "location"
    assert pick_category(kinds, "Памятник К. Д. Ушинскому") == "Памятник"
    # A genuine museum keeps its ticket even with a memorial tag.
    assert pick_category_kind(kinds, "Музей политической истории") == "museum"


def test_sculpture_is_location_not_walk():
    # OpenTripMap often pairs sculptures with urban_environment — that must not
    # turn a statue into footprints.
    kinds = ["sculptures", "urban_environment", "interesting_places"]
    assert pick_category_kind(kinds, "Девушка с веслом") == "location"
    assert pick_category(kinds, "Девушка с веслом") == "Скульптура"
    assert pick_category_kind(["sculptures"], "Скульптура «Рабочий»") == "location"


def test_open_air_toponyms_never_sell_a_ticket():
    kinds = ["museums", "cultural", "interesting_places"]
    assert pick_category_kind(kinds, "Конюшенная площадь") == "walk"
    assert pick_category(kinds, "Конюшенная площадь") != "Музей"
    assert pick_category_kind(kinds, 'Парк "Дендрарий"') == "walk"
    # The type word has to be the name's first or last, not buried in it.
    assert pick_category_kind(kinds, "Музей истории площади Искусств") == "museum"


@pytest.mark.parametrize(
    ("value", "expected"),
    [("3", 3), ("3h", 4), (7, 7), ("7h", 7), (None, 0), ("", 0), ("rubbish", 0)],
)
def test_parse_rate_handles_heritage_suffix(value, expected: int):
    # OpenTripMap marks heritage objects as "3h"; int() used to raise on it.
    assert parse_rate(value) == expected


def test_normalize_title_ignores_qualifiers():
    assert normalize_title('Парк "Дендрарий" (верхний)') == normalize_title(
        'Парк "Дендрарий" (нижний)'
    )
    assert normalize_title("Зимний дворец") != normalize_title("Летний дворец")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('центр семьи "Казан"', 'Центр семьи "Казан"'),
        ("Эрмитаж", "Эрмитаж"),
        ("  музей изо  ", "Музей изо"),
        ("«казанский кремль»", "«Казанский кремль»"),
    ],
)
def test_prettify_title(raw: str, expected: str):
    assert prettify_title(raw) == expected


def test_metro_is_only_suggested_where_it_exists():
    assert has_metro("Санкт-Петербург")
    assert has_metro("Нижний Новгород")
    assert not has_metro("Сочи")
    assert not has_metro("Суздаль")
    assert pick_mode(3000, metro=False) == "taxi"
    assert pick_mode(3000, metro=True) == "metro"


def test_day_slots_respect_arrival_and_departure():
    slots = build_day_slots(datetime(2026, 9, 15, 10, 0), datetime(2026, 9, 17, 18, 0))

    assert len(slots) == 3
    assert slots[0].start.hour == 10
    assert slots[1].start.hour == 9 and slots[1].start.minute == 30
    assert slots[-1].end.hour == 18


def test_day_slots_drop_unusable_tail():
    # Departure at 09:45 leaves only 15 minutes on the last day.
    slots = build_day_slots(datetime(2026, 9, 15, 10, 0), datetime(2026, 9, 16, 9, 45))
    assert len(slots) == 1


def test_extract_json_handles_fenced_replies():
    assert extract_json('```json\n{"city": "Казань"}\n```') == {"city": "Казань"}
    assert extract_json('Вот ответ: {"city": "Сочи"} — готово') == {"city": "Сочи"}

    with pytest.raises(ValueError):
        extract_json("нет json")


def test_dev_mode_accepts_missing_init_data():
    settings.auth_mode = "dev"
    user = security.resolve_user(None)
    assert user.max_user_id == settings.dev_user_id


def test_max_mode_verifies_signature():
    settings.auth_mode = "max"
    settings.max_bot_token = "secret-token"

    fields = {"auth_date": "1700000000", "user": json.dumps({"id": 42, "username": "ann"})}
    check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", b"secret-token", hashlib.sha256).digest()
    signature = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()

    valid = urlencode({**fields, "hash": signature})
    user = security.resolve_user(f"tma {valid}")
    assert user.max_user_id == 42
    assert user.username == "ann"

    tampered = urlencode({**fields, "hash": "0" * 64})
    with pytest.raises(security.UnauthorizedError):
        security.resolve_user(f"tma {tampered}")

    settings.auth_mode = "dev"


def test_city_suggest_skips_village_namesakes():
    from app.clients.geocoding import is_trip_city

    real_kazan = {
        "name": "Казань",
        "feature_code": "PPLA",
        "population": 1_243_500,
        "admin1": "Татарстан",
        "country_code": "RU",
    }
    village = {
        "name": "Казань-Омга",
        "feature_code": "PPL",
        "population": None,
        "admin1": "Кировская Область",
        "country_code": "RU",
    }
    namesake = {
        "name": "Казань",
        "feature_code": "PPL",
        "population": None,
        "admin1": "Кировская Область",
        "country_code": "RU",
    }

    assert is_trip_city(real_kazan)
    assert not is_trip_city(village)
    assert not is_trip_city(namesake)
