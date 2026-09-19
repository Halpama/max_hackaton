"""Spread the declared trip budget over the selected places.

OpenTripMap has no pricing data, so we start from typical per-person costs per
category and rescale them so the itinerary total lands inside the user's budget.
"""
from app.services.places import PlaceCandidate

#: Typical cost per person, in roubles.
BASE_COST: dict[str, int] = {
    "museum": 600,
    "food": 900,
    "walk": 0,
    "location": 0,
}

#: Share of the budget that goes to tickets and food; the rest covers transport,
#: accommodation and a safety buffer.
ACTIVITY_BUDGET_SHARE = 0.55

MIN_SCALE = 0.4
#: A generous budget must not inflate a doughnut stand into a 4 500 ₽ stop, so
#: the scale is capped well below the point where prices stop looking real.
MAX_SCALE = 1.6


def format_money(value: float) -> str:
    return f"{int(round(value)):,}".replace(",", " ")


def travelers_suffix(travelers: int) -> str:
    n = max(travelers, 1)
    if n == 1:
        return "за 1 чел"
    return f"на {n} чел"


def price_label(value: float, *, approximate: bool, travelers: int = 1) -> str:
    """Human price string. Paid figures are totals for the whole party."""
    if value <= 0:
        return "Бесплатно"
    prefix = "~" if approximate else ""
    return f"{prefix}{format_money(value)} ₽ · {travelers_suffix(travelers)}"


def base_cost(candidate: PlaceCandidate) -> float:
    """Typical per-person cost, nudged by how major the place is.

    Without this every museum in a trip prints the same number, which reads as
    a placeholder. OpenTripMap popularity (1..7) is the only signal we have.
    """
    base = BASE_COST.get(candidate.category_kind, 0)
    if base <= 0:
        return 0.0
    popularity = max(1, min(7, candidate.rate))
    return base * (0.6 + popularity / 7 * 0.7)


def compute_scale(candidates: list[PlaceCandidate], budget: int, travelers: int) -> float:
    base_total = sum(base_cost(c) for c in candidates) * max(travelers, 1)
    if base_total <= 0 or budget <= 0:
        return 1.0

    available = budget * ACTIVITY_BUDGET_SHARE
    return max(MIN_SCALE, min(MAX_SCALE, available / base_total))


def price_for(
    candidate: PlaceCandidate, *, scale: float, travelers: int
) -> tuple[float | None, str, bool]:
    """Return (priceValue, priceLabel, isEstimate) for one place.

    `priceValue` is the estimated total for all travellers (per-person base × N).
    No free source publishes ticket prices, so any figure here is our own
    guess and says so. "Бесплатно" for a park or a square is not a guess.
    """
    base = base_cost(candidate)
    if base <= 0:
        return None, "Бесплатно", False

    party = max(travelers, 1)
    raw = base * scale * party
    # Round to a believable price step.
    value = max(50.0, round(raw / 50) * 50.0)
    return (
        value,
        price_label(
            value,
            approximate=candidate.category_kind == "food",
            travelers=party,
        ),
        True,
    )


def budget_label(budget: int) -> str:
    if budget <= 0:
        return "Бюджет не задан"
    return f"~{format_money(budget)} ₽"
