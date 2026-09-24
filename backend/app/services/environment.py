"""Classify places as indoor, outdoor or mixed with a safe rules fallback."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Literal

from app.core.config import settings

EnvironmentKind = Literal["indoor", "outdoor", "mixed", "unknown"]
logger = logging.getLogger(__name__)

INDOOR_KINDS = {
    "museums", "art_galleries", "theatres_and_entertainments", "opera_houses",
    "concert_halls", "planetariums", "restaurants", "cafes", "foods", "bakeries",
    "pubs", "theatre", "concert-hall", "observatory", "art-space", "art-centers",
}
OUTDOOR_KINDS = {
    "gardens_and_parks", "natural", "beaches", "bridges", "view_points",
    "sculptures", "squares", "urban_environment", "fountains", "park", "bridge",
    "fountain", "photo-places",
}
MIXED_KINDS = {
    "fortifications", "religion", "historic_architecture", "palaces", "palace",
    "homesteads", "suburb", "temple", "church", "monastery",
}
INDOOR_WORDS = {"музей", "галерея", "театр", "ресторан", "кафе", "бар", "выставка"}
OUTDOOR_WORDS = {"парк", "площадь", "мост", "набережная", "фонтан", "пляж", "сквер", "сад", "памятник", "скульптура"}
MIXED_WORDS = {"кремль", "крепость", "усадьба", "дворец", "монастырь", "собор", "заповедник"}


def classify_by_rules(title: str, kinds: list[str], category_kind: str) -> EnvironmentKind:
    kind_set = set(kinds)
    words = set(re.findall(r"[\w-]+", title.lower(), flags=re.UNICODE))
    if kind_set & MIXED_KINDS or words & MIXED_WORDS:
        return "mixed"
    if kind_set & INDOOR_KINDS or words & INDOOR_WORDS:
        return "indoor"
    if kind_set & OUTDOOR_KINDS or words & OUTDOOR_WORDS:
        return "outdoor"
    if category_kind == "food":
        return "indoor"
    return "unknown"


def _model_prediction(
    *, title: str, description: str, opening_hours: str | None, kinds: list[str], category_kind: str
) -> tuple[EnvironmentKind, float] | None:
    if not settings.environment_model_file.exists():
        return None
    try:
        import joblib
        from scipy.sparse import hstack

        artifact = joblib.load(settings.environment_model_file)
        text = " ".join((title, description, opening_hours or ""))
        text_features = artifact["text_vectorizer"].transform([text])
        kind_features = artifact["kind_encoder"].transform([kinds])
        category_features = artifact["category_encoder"].transform([[category_kind]])
        features = hstack((text_features, kind_features, category_features)).tocsr()
        model = artifact["model"]
        probabilities = model.predict_proba(features)[0]
        index = int(probabilities.argmax())
        return str(model.classes_[index]), float(probabilities[index])  # type: ignore[return-value]
    except Exception as exc:  # noqa: BLE001 - ML is optional enrichment
        logger.warning("environment model unavailable: %s", exc)
        return None


def classify_environment(
    *, title: str, description: str, opening_hours: str | None, kinds: list[str], category_kind: str
) -> EnvironmentKind:
    rules_label = classify_by_rules(title, kinds, category_kind)
    prediction = _model_prediction(
        title=title,
        description=description,
        opening_hours=opening_hours,
        kinds=kinds,
        category_kind=category_kind,
    )
    if prediction is None:
        return rules_label

    model_label, confidence = prediction
    if settings.environment_model_mode == "shadow":
        if model_label != rules_label:
            logger.info("environment disagreement title=%r rules=%s model=%s score=%.2f", title, rules_label, model_label, confidence)
        return rules_label
    if settings.environment_model_mode == "active" and confidence >= settings.environment_model_threshold:
        return model_label
    return rules_label