"""First-party memory helpers and expanded city fallbacks."""

from app.clients.geocoding import POPULAR_CITIES, _KNOWN_COORDS
from app.data.russian_cities import KNOWN_COORDS, normalize_city_key
from app.db.models import PlaceStats
from app.services.memory import boost_candidates, curation_memory_block
from app.services.places import PlaceCandidate


def _candidate(xid: str, title: str, rate: int = 3) -> PlaceCandidate:
    return PlaceCandidate(
        xid=xid,
        title=title,
        coordinates=(49.1, 55.7),
        kinds=["museums"],
        rate=rate,
        category="музей",
        category_kind="museum",
        address="",
        description="",
        image_url="",
        city="Казань",
    )


def test_known_coords_cover_far_more_than_megacities():
    assert len(KNOWN_COORDS) >= 80
    assert "махачкала" in KNOWN_COORDS
    assert "ялта" in KNOWN_COORDS
    assert "суздаль" in KNOWN_COORDS
    assert _KNOWN_COORDS is KNOWN_COORDS
    assert len(POPULAR_CITIES) >= 16


def test_boost_candidates_prefers_pick_count_and_hints():
    a = _candidate("a", "Кремль", rate=7)
    b = _candidate("b", "Скрытый дворик", rate=2)
    stats = {
        "b": PlaceStats(
            external_id="b",
            city="казань",
            title="Скрытый дворик",
            pick_count=5,
            stay_minutes_sum=0,
            stay_samples=0,
            interests={},
        )
    }
    ordered = boost_candidates([a, b], stats, hints=["Скрытый дворик Казань"])
    assert ordered[0].xid == "b"


def test_curation_memory_block_mentions_picks():
    c = _candidate("x", "Мечеть Кул-Шариф")
    stats = {
        "x": PlaceStats(
            external_id="x",
            city="казань",
            title="Мечеть Кул-Шариф",
            pick_count=3,
            stay_minutes_sum=180,
            stay_samples=2,
            tip="лучше утром",
            interests={"sights": 3},
        )
    }
    block = curation_memory_block([c], stats, None)
    assert "выбирали 3" in block
    assert "лучше утром" in block


def test_normalize_city_key_folds_yo():
    assert normalize_city_key("Орёл") == "орел"
