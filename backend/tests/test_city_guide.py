"""City guide enrichment from Wikipedia."""

from datetime import date

import respx
from httpx import Response

from app.services.city_guide import build_city_guide


@respx.mock
async def test_build_city_guide_uses_wikipedia_for_unknown_city(monkeypatch):
    monkeypatch.setattr(
        "app.services.city_guide.settings.searxng_enabled",
        False,
    )
    respx.get(
        url__regex=r"https://ru\.wikipedia\.org/api/rest_v1/page/summary/.+"
    ).mock(
        return_value=Response(
            200,
            json={
                "extract": "Ульяновск — город в России, административный центр Ульяновской области. Стоит на Волге.",
                "description": "город в России",
                "thumbnail": {
                    "source": "https://upload.wikimedia.org/wikipedia/commons/thumb/u.jpg/330px-u.jpg"
                },
                "content_urls": {
                    "desktop": {"page": "https://ru.wikipedia.org/wiki/Ульяновск"}
                },
            },
        )
    )

    guide = await build_city_guide("Ульяновск", date(2026, 6, 1))
    assert "Волге" in guide["history"]
    assert guide["source_name"] == "Википедия"
    assert guide["image_url"]
    assert guide["trip_month"] == 6
    assert len(guide["seasonality"]) == 12
