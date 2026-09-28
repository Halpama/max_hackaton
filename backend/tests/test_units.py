import asyncio
import hashlib
import hmac
import json
import time
from datetime import date, datetime
from urllib.parse import urlencode

import pytest

from app.core import security
from app.core.config import settings
from app.schemas.trip import DayWeather, TripDraft
from app.services import budget, formatting
from app.services import llm as llm_module
from app.services.llm import extract_json
from app.services.places import PlaceCandidate
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
    assert budget.budget_label(0) == "0 ₽"
    assert budget.price_label(0, approximate=False) == "Бесплатно"
    assert budget.price_label(800, approximate=False) == "800 ₽ · за 1 чел"
    assert budget.price_label(1500, approximate=True, travelers=2) == "~1 500 ₽ · на 2 чел"


def test_zero_budget_is_free_only():
    from app.services.places import PlaceCandidate

    paid = PlaceCandidate(
        xid="m1",
        title="Музей",
        coordinates=(30.0, 59.0),
        kinds=["museums"],
        rate=5,
        category="Музей",
        category_kind="museum",
        address="",
        description="",
        image_url="",
        city="Санкт-Петербург",
    )
    free = PlaceCandidate(
        xid="p1",
        title="Парк",
        coordinates=(30.1, 59.1),
        kinds=["gardens_and_parks"],
        rate=5,
        category="Парк",
        category_kind="walk",
        address="",
        description="",
        image_url="",
        city="Санкт-Петербург",
    )
    assert budget.is_free_candidate(free)
    assert not budget.is_free_candidate(paid)
    assert budget.compute_scale([paid, free], 0, 1) == 0.0
    value, label, _ = budget.price_for(paid, scale=0.0, travelers=1)
    assert value is None and label == "Бесплатно"


def test_russia_bbox_rejects_africa():
    from app.clients.geocoding import in_russia

    assert in_russia(42.98, 47.50)  # Makhachkala
    assert in_russia(55.75, 37.62)  # Moscow
    assert not in_russia(-18.9, 47.5)  # Madagascar-ish
    assert not in_russia(36.8, 10.2)  # Tunis



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


def test_bot_planner_keyboard_native_open_only():
    from app.bot.client import MaxBotClient

    client = MaxBotClient()
    client._me = {"user_id": 42, "username": "trip_planner_bot", "name": "Trip"}
    rows = client.planner_keyboard()
    open_app = rows[0][0]
    assert open_app["type"] == "open_app"
    assert open_app["web_app"] == "trip_planner_bot"
    assert open_app["contact_id"] == 42
    assert open_app["payload"] == "planner"
    # Must not put the Vercel SPA URL into open_app.web_app
    assert not str(open_app.get("web_app", "")).startswith("http")
    assert client.max_deeplink() == "https://max.ru/trip_planner_bot?startapp"

    # Web app opens only natively — no browser / deeplink link duplicates.
    button_types = [btn["type"] for row in rows for btn in row]
    assert "link" not in button_types
    assert set(button_types) == {"open_app", "callback"}
    utility = {btn["payload"] for row in rows for btn in row if btn["type"] == "callback"}
    assert utility == {"/help", "/about"}


def test_bot_command_normalization():
    from app.bot.handlers import _normalize_command

    assert _normalize_command("/start@trip_bot") == "/start"
    assert _normalize_command("@trip_bot /help") == "/help"
    assert _normalize_command("  Помощь ") == "помощь"


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

    fields = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": 42, "username": "ann"}),
    }
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

    expired = {
        "auth_date": str(int(time.time()) - security.MAX_AUTH_AGE_SECONDS - 10),
        "user": json.dumps({"id": 42}),
    }
    expired_check = "\n".join(f"{k}={expired[k]}" for k in sorted(expired))
    expired_sig = hmac.new(
        secret, expired_check.encode(), hashlib.sha256
    ).hexdigest()
    with pytest.raises(security.UnauthorizedError, match="expired"):
        security.resolve_user(f"tma {urlencode({**expired, 'hash': expired_sig})}")

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


def test_environment_rules_cover_common_kinds() -> None:
    from app.services.environment import classify_by_rules

    assert classify_by_rules("Третьяковская галерея", ["museums"], "museum") == "indoor"
    assert classify_by_rules("Летний сад", ["gardens_and_parks"], "walk") == "outdoor"
    assert classify_by_rules("Казанский кремль", ["fortifications"], "location") == "mixed"
    assert classify_by_rules("Кофейня на углу", [], "food") == "indoor"
    assert classify_by_rules("Что-то невиданное", ["weird-kind"], "location") == "unknown"


def test_environment_kinds_signature_is_stable() -> None:
    from app.services.environment import kinds_signature

    # order-independent, noise slugs dropped — train/inference must agree
    assert kinds_signature(["park", "museums", "sights"]) == "museums|park"
    assert kinds_signature(["museums", "park", "attractions"]) == "museums|park"
    assert kinds_signature([]) == ""


def test_environment_classifier_respects_mode(monkeypatch) -> None:
    from app.core.config import settings
    from app.services import environment

    monkeypatch.setattr(settings, "environment_model_mode", "off")
    label, score = environment.classify_environment_with_score(
        title="Эрмитаж", description="", opening_hours=None,
        kinds=["museums"], category_kind="museum",
    )
    assert (label, score) == ("indoor", 1.0)


def test_environment_model_override_in_active_mode(tmp_path, monkeypatch) -> None:
    """A tiny fake pipeline artifact must be able to override weak rules."""
    from app.core.config import settings
    from app.services import environment

    class FakePipeline:
        classes_ = ("indoor", "mixed", "outdoor")

        def predict_proba(self, X):
            # always say "outdoor" with high confidence (numpy, like sklearn)
            import numpy as np

            return np.tile([0.05, 0.05, 0.9], (len(X), 1))

    monkeypatch.setattr(settings, "environment_model_mode", "active")
    monkeypatch.setattr(settings, "environment_model_path", str(tmp_path / "model.joblib"))
    monkeypatch.setattr(environment._load_artifact, "cache_clear", lambda: None)
    monkeypatch.setattr(
        environment, "_get_predictor",
        lambda: environment._Predictor({"pipeline": FakePipeline()}, tmp_path / "model.joblib"),
    )
    label, score = environment.classify_environment_with_score(
        title="Странное место", description="", opening_hours=None,
        kinds=["other"], category_kind="unknown",
    )
    assert label == "outdoor"
    assert score >= settings.environment_model_threshold

def test_limit_outdoor_when_stormy_keeps_one_open_air_stop() -> None:
    from app.services.places import PlaceCandidate
    from app.services.scheduler import limit_outdoor_when_stormy

    def place(xid: str, kind: str) -> PlaceCandidate:
        return PlaceCandidate(
            xid=xid,
            title=xid,
            coordinates=(30.0, 60.0),
            kinds=[],
            rate=3,
            category="x",
            category_kind="location",
            address="a",
            description="d",
            image_url="",
            city="СПб",
            interests=set(),
            environment_kind=kind,
        )

    day = [
        place("park", "outdoor"),
        place("museum", "indoor"),
        place("fortress", "outdoor"),
        place("gallery", "indoor"),
        place("lookout", "outdoor"),
    ]

    # Dry day and ordinary rain (80%) leave the day untouched — no reordering,
    # no drops: a daily forecast cannot say when it will rain anyway.
    dry = limit_outdoor_when_stormy(day, precipitation_chance=10)
    assert [c.xid for c in dry] == ["park", "museum", "fortress", "gallery", "lookout"]
    rain = limit_outdoor_when_stormy(day, precipitation_chance=80)
    assert [c.xid for c in rain] == ["park", "museum", "fortress", "gallery", "lookout"]

    # ≥90%: exactly one outdoor stop survives — the last by route order, put
    # at the end of the day; all indoor/mixed stops keep their relative order.
    storm = limit_outdoor_when_stormy(day, precipitation_chance=95)
    assert [c.xid for c in storm] == ["museum", "gallery", "lookout"]
    assert sum(1 for c in storm if c.environment_kind == "outdoor") == 1

    # One or zero outdoor stops already satisfy the cap — nothing changes.
    single = [place("park", "outdoor"), place("museum", "indoor")]
    assert [c.xid for c in limit_outdoor_when_stormy(single, precipitation_chance=99)] == [
        "park",
        "museum",
    ]
    unknown = [place("odd", "unknown"), place("even", "unknown")]
    assert len(limit_outdoor_when_stormy(unknown, precipitation_chance=99)) == 2


def test_to_candidate_sets_environment_kind(monkeypatch) -> None:
    from app.services import places

    monkeypatch.setattr(
        places,
        "classify_environment",
        lambda **kwargs: "outdoor",
    )
    details = {
        "xid": "otm1",
        "name": "Летний сад",
        "point": {"lon": 30.33, "lat": 59.94},
        "kinds": "gardens_and_parks",
        "rate": "3",
        "preview": {},
    }
    candidate = places.to_candidate(details, "Санкт-Петербург", {"walks"})
    assert candidate is not None
    assert candidate.environment_kind == "outdoor"


# --------------------------------------------------------------------------
# Weather-aware curation prompt (no new model: forecast + environment_kind
# are fed into the existing GigaChat call). The tests below mirror the manual
# stand cases — a rainy city and a clear one; run the same drafts against the
# VDS with GIGACHAT configured to eyeball the real model replies.
# --------------------------------------------------------------------------


def _cand(xid: str, env: str, *, rate: int = 5, kind: str = "location") -> PlaceCandidate:
    return PlaceCandidate(
        xid=xid,
        title=f"Место {xid}",
        coordinates=(30.33, 59.94),
        kinds=[],
        rate=rate,
        category="Категория",
        category_kind=kind,  # type: ignore[arg-type]
        address="",
        description="",
        image_url="",
        city="Санкт-Петербург",
        environment_kind=env,
    )


def _draft() -> TripDraft:
    return TripDraft(
        destination="Санкт-Петербург",
        startDate="2026-07-01",
        startTime="10:00",
        endDate="2026-07-02",
        endTime="18:00",
        budget=10000,
        adults=2,
        children=0,
        interests=["sights"],
        pace="medium",
    )


def _weather(icon: str, chance: int | None, *, label: str = "Дождь") -> DayWeather:
    return DayWeather(
        label=label if icon != "clear" else "Ясно",
        icon=icon,
        tempHigh=22,
        tempLow=14,
        precipitationChance=chance,
    )


def test_weather_forecast_block_marks_rainy_days():
    from datetime import date as d

    forecast = {
        d(2026, 7, 1): _weather("rain", 80),
        d(2026, 7, 2): _weather("clear", 10, label="Ясно"),
    }
    block = llm_module.weather_forecast_block(forecast)
    assert "Погода на даты поездки" in block
    assert "вероятность осадков 80%" in block
    assert "дождливый день" in block
    assert "Дождливых дней: 1 из 2" in block


def test_weather_forecast_block_all_wet_and_none():
    from datetime import date as d

    assert llm_module.weather_forecast_block({}) == ""
    assert llm_module.weather_forecast_block(None) == ""

    all_wet = llm_module.weather_forecast_block(
        {d(2026, 7, 1): _weather("storm", 90), d(2026, 7, 2): _weather("snow", 70)}
    )
    assert "Все дни под угрозой осадков" in all_wet

    dry = llm_module.weather_forecast_block({d(2026, 7, 1): _weather("clear", 5)})
    assert "Дождливых дней нет" in dry


def test_weather_forecast_block_without_chance_uses_icon():
    from datetime import date as d

    # Icon says rain but Open-Meteo returned no probability — still a wet day.
    block = llm_module.weather_forecast_block({d(2026, 7, 1): _weather("rain", None)})
    assert "оценка по типу погоды" in block
    assert "дождливый день" in block


def test_weather_forecast_block_stormy_summary():
    from datetime import date as d

    storm = llm_module.weather_forecast_block(
        {
            d(2026, 7, 1): _weather("storm", 95),
            d(2026, 7, 2): _weather("clear", 10, label="Ясно"),
        }
    )
    assert "Дней с осадками ≥90%: 1" in storm
    assert "максимум одно открытое место" in storm

    # 80% is rainy but not stormy — the ≥90% line must not appear.
    plain = llm_module.weather_forecast_block({d(2026, 7, 1): _weather("rain", 80)})
    assert "≥90%" not in plain


def test_outdoor_cap_for_day_only_stormy_days():
    from datetime import date as d

    caps = llm_module.outdoor_cap_for_day(
        {
            d(2026, 7, 1): _weather("storm", 95),
            d(2026, 7, 2): _weather("rain", 80),
            d(2026, 7, 3): _weather("clear", 5),
        }
    )
    assert caps[d(2026, 7, 1)] == 1
    assert caps[d(2026, 7, 2)] is None
    assert caps[d(2026, 7, 3)] is None
    assert llm_module.outdoor_cap_for_day(None) == {}


def test_enforce_outdoor_caps_drops_extras_and_backfills():
    # Модель (или рейтинг-fallback) набивает ливневый трип открытыми местами —
    # страховка оставляет максимум по одному на штормовой день и добирает крытые.
    candidates = [
        _cand("p1", "outdoor", rate=7),
        _cand("p2", "outdoor", rate=6),
        _cand("p3", "outdoor", rate=5),
        _cand("m1", "indoor", rate=4),
        _cand("m2", "mixed", rate=3),
        _cand("m3", "indoor", rate=2),
    ]
    picked = candidates[:3]
    caps = {date(2026, 7, 1): 1}
    result = llm_module.enforce_outdoor_caps(picked, candidates, 4, caps, days=1)
    assert sum(1 for c in result if c.environment_kind == "outdoor") == 1
    assert len(result) == 4
    assert {c.xid for c in result} == {"p1", "m1", "m2", "m3"}

    # Без штормовых дней список не трогается.
    untouched = llm_module.enforce_outdoor_caps(picked, candidates, 4, {}, days=1)
    assert untouched == picked


def _captured_prompt(monkeypatch, *, forecast, candidates):
    prompts: list[str] = []

    async def fake_complete(messages, **kwargs):
        prompts.append(messages[0]["content"])
        return '{"stops": [' + ", ".join(
            f'{{"id": "{c.xid}", "minutes": 60}}' for c in candidates
        ) + "]}"

    monkeypatch.setattr(settings, "gigachat_auth_key", "test-key")
    monkeypatch.setattr(llm_module.gigachat, "complete", fake_complete)
    picked = asyncio.run(
        llm_module.curate_places(_draft(), candidates, len(candidates), forecast=forecast)
    )
    assert prompts, "curate_places must build exactly one prompt"
    return prompts[0], picked


def test_curate_prompt_includes_forecast_env_and_rule(monkeypatch):
    from datetime import date as d

    candidates = [_cand("museum", "indoor"), _cand("park", "outdoor")]
    forecast = {d(2026, 7, 1): _weather("rain", 80)}
    prompt, picked = _captured_prompt(monkeypatch, forecast=forecast, candidates=candidates)

    assert "Погода на даты поездки" in prompt
    assert "вероятность осадков 80%" in prompt
    assert "окружение: крытое" in prompt
    assert "окружение: открытое" in prompt
    assert "не набирай такой день" in prompt
    assert [c.xid for c in picked] == ["museum", "park"]


def test_curate_prompt_omits_weather_when_no_forecast(monkeypatch):
    # Trip beyond the forecast horizon: no invented rain, no weather rules.
    candidates = [_cand("museum", "indoor"), _cand("park", "outdoor")]
    prompt, _ = _captured_prompt(monkeypatch, forecast={}, candidates=candidates)

    assert "Погода на даты поездки" not in prompt
    assert "не набирай такой день" not in prompt
    # Environment labels stay — they are cheap and always known.
    assert "окружение:" in prompt


def test_curate_prompt_clear_city_lists_dry_summary(monkeypatch):
    from datetime import date as d

    candidates = [_cand("street", "outdoor"), _cand("gallery", "indoor")]
    forecast = {d(2026, 7, 1): _weather("clear", 10, label="Ясно")}
    prompt, _ = _captured_prompt(monkeypatch, forecast=forecast, candidates=candidates)

    assert "Дождливых дней нет" in prompt
    assert "окружение: открытое" in prompt


def test_curate_prompt_stormy_city_has_90_rule(monkeypatch):
    from datetime import date as d

    candidates = [
        _cand("volcano", "outdoor"),
        _cand("museum", "indoor"),
        _cand("fortress", "outdoor"),
    ]
    forecast = {d(2026, 7, 1): _weather("storm", 95)}
    prompt, _ = _captured_prompt(monkeypatch, forecast=forecast, candidates=candidates)

    assert "максимум ОДНО открытое место" in prompt
    assert "Дней с осадками ≥90%: 1" in prompt
    # Прогноз суточный — в промпте есть прямое объяснение, почему правило на день.
    assert "не знает, когда именно пойдёт дождь" in prompt
