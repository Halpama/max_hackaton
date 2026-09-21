"""Guard the wire contract against drift in the frontend TypeScript types."""
import re
from pathlib import Path

import pytest

from app.schemas.trip import (
    Activity,
    DayPlan,
    Place,
    RoutePlan,
    TransitLeg,
    TripDraft,
    TripSummary,
)

TYPES_FILE = (
    Path(__file__).resolve().parents[2]
    / "web/src/features/trip-planner/model/types.ts"
)

MODELS = {
    "TripDraft": TripDraft,
    "Place": Place,
    "Activity": Activity,
    "TransitLeg": TransitLeg,
    "DayPlan": DayPlan,
    "RoutePlan": RoutePlan,
    "TripSummary": TripSummary,
}


def ts_interface_fields(source: str, name: str) -> set[str]:
    match = re.search(rf"export interface {name} \{{(.*?)\n\}}", source, re.DOTALL)
    if match is None:
        raise AssertionError(f"Interface {name} not found in types.ts")

    fields: set[str] = set()
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "/*", "*")):
            continue
        field = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\??\s*:", stripped)
        if field:
            fields.add(field.group(1))
    return fields


@pytest.mark.skipif(not TYPES_FILE.exists(), reason="frontend sources not checked out")
@pytest.mark.parametrize("name", list(MODELS))
def test_schema_matches_typescript_interface(name: str):
    source = TYPES_FILE.read_text(encoding="utf-8")
    expected = ts_interface_fields(source, name)
    actual = {
        field.alias or key
        for key, field in MODELS[name].model_fields.items()
    }

    assert actual == expected, (
        f"{name} mismatch\n"
        f"  missing in backend: {sorted(expected - actual)}\n"
        f"  extra in backend:   {sorted(actual - expected)}"
    )


def test_place_serialises_to_camel_case():
    place = Place(
        id="x",
        title="T",
        category="Музей",
        category_kind="museum",
        city="СПб",
        price_label="800 ₽",
        price_value=800,
        duration_label="2 часа",
        time_range="09:00 – 11:00",
        rating=4.9,
        reviews_label="популярность 7/7",
        address="Дворцовая пл., 2",
        description="…",
        image_url="https://example/x.jpg",
        coordinates=(30.3, 59.9),
    )

    payload = place.model_dump(by_alias=True)
    assert payload["categoryKind"] == "museum"
    assert payload["priceLabel"] == "800 ₽"
    assert payload["imageUrl"].startswith("https://")
    assert payload["coordinates"] == (30.3, 59.9)
    assert "category_kind" not in payload
