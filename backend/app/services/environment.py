"""Classify places as indoor, outdoor or mixed.

Two layers:

1. A deterministic rule layer over OpenTripMap/KudaGo kind slugs and title
   keywords.  It always answers ``indoor``/``outdoor``/``mixed`` (``unknown``
   only when there is no signal at all), so the pipeline keeps working with no
   model artifact on disk.
2. An optional ML layer (scikit-learn pipeline saved by
   ``scripts/train_environment_model.py``) that runs on top of the rules and
   can override them when it is confident enough.

The mode is controlled by ``ENVIRONMENT_MODEL_MODE``:

* ``off``    — rules only.
* ``shadow`` — the model predicts but never overrides; disagreements are
  logged so precision can be measured before going live.
* ``active`` — the model overrides the rules only when its probability for a
  class different from the rule label reaches ``ENVIRONMENT_MODEL_THRESHOLD``,
  or when the rules produced no signal at all (then a slightly lower bar,
  ``ENVIRONMENT_MODEL_FALLBACK_THRESHOLD``, applies).

Artifact formats supported (auto-detected):

* ``{"pipeline": Pipeline}`` — a single scikit-learn ``Pipeline`` trained via
  ``scripts/train_environment_model.py`` (preferred).
* ``{"model", "text_vectorizer", "kind_encoder", "category_encoder"}`` — the
  legacy hand-stacked feature format kept for backward compatibility.
"""
from __future__ import annotations

import functools
import logging
import re
from pathlib import Path
from typing import Any, Literal

from app.core.config import settings

EnvironmentKind = Literal["indoor", "outdoor", "mixed", "unknown"]
logger = logging.getLogger(__name__)

INDOOR_KINDS = {
    "museums", "art_galleries", "theatres_and_entertainments", "opera_houses",
    "concert_halls", "planetariums", "restaurants", "cafes", "foods", "bakeries",
    "pubs", "theatre", "concert-hall", "observatory", "art-space", "art-centers",
    "cinema", "shops", "shopping", "coworking", "workshops", "education-centers",
    "nightlife", "clubs", "interiors", "exhibitions", "anticafes", "anticafe",
    "theaters", "opera_houses"  # correct spellings of theatres/opera
}
#: Unambiguous *indoor* signals: matched as substrings of the title and via
#: exact kind slugs (2GIS spelling variants live here, e.g. "theaters").
INDOOR_KINDS_EXTRA = {
    "aquariums", "dolphinariums", "circuses", "bowling", "billiards", "quest",
    "museums_and_expositions", "exhibition_halls", "planetarium", "water_parks",
}
INDOOR_EXTRA_WORDS = {
    "ледокол", "теплоход", "бассейн", "термальный", "термы", "баня", "сауна",
    "боулинг", "квест", "дельфинарий", "цирк",
}
OUTDOOR_KINDS = {
    "gardens_and_parks", "natural", "beaches", "bridges", "view_points",
    "sculptures", "squares", "urban_environment", "fountains", "park", "bridge",
    "fountain", "photo-places", "observation-decks", "streets", "landmarks",
    "archaeological", "beach", "zoos", "beaches_and_bays", "trampolines",
    "ski_complexes", "yacht_clubs", "tourism_centers",
}
#: Strong but not absolute outdoor signals (used only when nothing stronger
#: matched, so they never override an indoor/mixed signal above them).
OUTDOOR_WEAK_WORDS = {"отель", "гостиница", "кемпинг", "турбаза", "база отдыха"}
MIXED_KINDS = {
    "fortifications", "religion", "historic_architecture", "palaces", "palace",
    "homesteads", "suburb", "temple", "church", "monastery", "parks_and_gardens",
    "amusement", "attractions", "religious_organizations", "monasteries",
    "cathedrals", "moslems", "synagogues", "shrines",
}
#: Kinds that are pure noise for this task ("sights", "interesting_places"...).
IGNORED_KINDS = {
    "attractions", "sights", "interesting_places", "kids", "recreation",
    "tours", "walkaround_areas", "urban_objects", "public_catering",
}

#: Kind signatures that appear in the labelled dataset with exactly one label.
#: These are near-deterministic signals (e.g. ``museums`` → indoor), and they
#: rescue cases where title keywords miss (foreign names like "Эрмитаж") or
#: where the linear text model is under-confident on rare phrasing.  Derived
#: from ml_data/environment_labeled.jsonl; regenerate with:
#:   python -c "...kinds_signature over the dataset, keep unique-label sigs..."
SIGNATURE_LABELS: dict[str, EnvironmentKind] = {
    "amusement|museums|restaurants": "indoor",
    "amusement|museums": "indoor",
    "art-centers|museums": "indoor",
    "art-centers|restaurants": "indoor",
    "bar": "indoor",
    "concert-hall": "indoor",
    "museums|photo-places": "indoor",
    "museums": "indoor",
    "restaurants": "indoor",
    "theatre": "indoor",
    "amusement|park|suburb": "outdoor",
    "amusement|photo-places": "outdoor",
    "bridge": "outdoor",
    "fountain": "outdoor",
    "park": "outdoor",
    "photo-places": "outdoor",
    "animal-shelters|park|suburb": "outdoor",
    "art-space|park": "outdoor",
    "church": "mixed",
    "homesteads|museums": "mixed",
    "museums|temple": "mixed",
}

INDOOR_WORDS = {
    "музей", "музеи", "галерея", "театр", "ресторан", "кафе", "бар", "выставка",
    "экспозиция", "кинотеатр", "торговый", "тц", "коворкинг", "концертный",
    "филармония", "планетарий", "аквариум", "океанариум", "зал", "павильон",
}
OUTDOOR_WORDS = {
    "парк", "площадь", "мост", "набережная", "фонтан", "пляж", "сквер", "сад",
    "памятник", "скульптура", "смотровая", "бульвар", "аллея", "остров",
    "каньон", "водопад", "горнолыжный", "тропа", "эко тропа", "высота",
    "прогулочная", "улица", "переулок", "наб",
}
MIXED_WORDS = {
    "кремль", "крепость", "усадьба", "дворец", "монастырь", "заповедник",
    "храм", "собор", "церковь", "мечеть", "синагога", "пагода",
    "пасаж", "пассаж", "гостиный двор",
    "фортификация", "бастион", "стадион", "башня", "тарханы",
}


def classify_by_rules(title: str, kinds: list[str], category_kind: str) -> EnvironmentKind:
    """Deterministic fallback used alone in ``off``/``shadow`` modes."""
    # Noise slugs ("tours", "sights", ...) carry no indoor/outdoor signal and
    # would otherwise pollute the kind signature match below.
    kinds = [k for k in kinds if k not in IGNORED_KINDS]
    kind_set = set(kinds)
    lowered = title.lower()
    words = set(re.findall(r"[\w-]+", lowered, flags=re.UNICODE))
    signature = kinds_signature(list(kinds))
    if signature in SIGNATURE_LABELS:
        return SIGNATURE_LABELS[signature]
    if kind_set & MIXED_KINDS or words & MIXED_WORDS:
        return "mixed"
    if (
        kind_set & INDOOR_KINDS
        or kind_set & INDOOR_KINDS_EXTRA
        or words & INDOOR_WORDS
        or any(w in lowered for w in INDOOR_EXTRA_WORDS)
    ):
        return "indoor"
    if kind_set & OUTDOOR_KINDS or words & OUTDOOR_WORDS:
        return "outdoor"
    if category_kind == "food":
        return "indoor"
    if words & OUTDOOR_WEAK_WORDS:
        return "outdoor"
    return "unknown"


# ---------------------------------------------------------------------------
# Feature engineering shared by training and inference
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[\w\-]+", flags=re.UNICODE)


class ItemSelector:
    """Pick one string field out of a list of record dicts.

    Lives here (not in the training script) on purpose: the fitted pipeline is
    pickled into the joblib artifact, so at inference time ``joblib.load``
    must be able to import this class from an application module that is
    always installed — ``__main__`` of a script would not be.

    ``as_list`` returns a plain list (for text vectorizers); otherwise a
    column-shaped 2D numpy array is returned (for OneHotEncoder).
    """

    def __init__(self, key: str, as_list: bool = False) -> None:
        self.key = key
        self.as_list = as_list

    def fit(self, X, y=None):  # noqa: N803 - sklearn signature
        return self

    def transform(self, X):  # noqa: N803
        values = [row[self.key] for row in X]
        if self.as_list:
            return values
        import numpy as np

        return np.array(values).reshape(-1, 1)


def text_of(title: str, description: str, opening_hours: str | None) -> str:
    """Single canonical text representation used by the vectorizer."""
    return " ".join(filter(None, (title, description, opening_hours or "")))


def kinds_signature(kinds: list[str]) -> str:
    """Stable, order-independent string of meaningful kind slugs.

    The training script maps each distinct signature to one categorical value,
    so inference must produce byte-identical strings.
    """
    informative = sorted({k for k in kinds if k not in IGNORED_KINDS})
    return "|".join(informative)


# ---------------------------------------------------------------------------
# Model loading / prediction
# ---------------------------------------------------------------------------


class _Predictor:
    """Wraps a loaded artifact and exposes ``predict(record) -> (label, prob)``."""

    def __init__(self, artifact: dict[str, Any], path: Path) -> None:
        self.path = path
        self._last_mtime = self._mtime()
        if "pipeline" in artifact:
            self.kind = "pipeline"
            self._pipeline = artifact["pipeline"]
            self._classes = [str(c) for c in self._pipeline.classes_]
        elif {"model", "text_vectorizer", "kind_encoder", "category_encoder"} <= artifact.keys():
            self.kind = "legacy"
            self._model = artifact["model"]
            self._vectorizer = artifact["text_vectorizer"]
            self._kind_encoder = artifact["kind_encoder"]
            self._category_encoder = artifact["category_encoder"]
            self._classes = [str(c) for c in self._model.classes_]
        else:
            raise ValueError(f"unrecognised environment artifact keys: {sorted(artifact)}")

    def _mtime(self) -> float:
        try:
            return self.path.stat().st_mtime
        except OSError:
            return 0.0

    def reload_if_stale(self) -> bool:
        """True when the file changed on disk since we loaded it."""
        return self._mtime() != self._last_mtime

    def predict(
        self,
        *,
        title: str,
        description: str,
        opening_hours: str | None,
        kinds: list[str],
        category_kind: str,
    ) -> tuple[EnvironmentKind, float]:
        record = {
            "title": title,
            "description": description,
            "opening_hours": opening_hours or "",
            "kinds_signature": kinds_signature(kinds),
            "category_kind": category_kind or "unknown",
        }
        if self.kind == "pipeline":
            probabilities = self._pipeline.predict_proba([record])[0]
        else:  # legacy stacked sparse features
            from scipy.sparse import hstack

            text = text_of(title, description, opening_hours)
            features = hstack(
                (
                    self._vectorizer.transform([text]),
                    self._kind_encoder.transform([[kinds_signature(kinds)]]),
                    self._category_encoder.transform([[category_kind or "unknown"]]),
                )
            ).tocsr()
            probabilities = self._model.predict_proba(features)[0]
        index = int(probabilities.argmax())
        return self._classes[index], float(probabilities[index])  # type: ignore[return-value]


@functools.lru_cache(maxsize=8)
def _load_artifact(path_str: str, mtime: float) -> _Predictor | None:
    path = Path(path_str)
    try:
        import joblib

        return _Predictor(joblib.load(path), path)
    except Exception as exc:  # noqa: BLE001 - ML is optional enrichment
        logger.warning("environment model unavailable (%s): %s", path, exc)
        return None


def _get_predictor() -> _Predictor | None:
    path = settings.environment_model_file
    if not path.exists():
        return None
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    predictor = _load_artifact(str(path), mtime)
    if predictor is not None and predictor.reload_if_stale():
        # File was retrained in place; drop the cache and load the new one.
        _load_artifact.cache_clear()
        predictor = _load_artifact(str(path), mtime)
    return predictor


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_environment_with_score(
    *,
    title: str,
    description: str,
    opening_hours: str | None,
    kinds: list[str],
    category_kind: str,
) -> tuple[EnvironmentKind, float]:
    """Return ``(label, confidence)`` where confidence refers to *label*.

    Confidence semantics:
    * rules-only answer → 1.0 (deterministic)
    * model override above threshold → model probability
    * model disagrees but stays under threshold → rules win, score 1.0
    * no signal anywhere → ("unknown", 0.0)
    """
    kwargs = dict(
        title=title,
        description=description,
        opening_hours=opening_hours,
        kinds=kinds,
        category_kind=category_kind,
    )
    rules_label = classify_by_rules(title, kinds, category_kind)
    mode = settings.environment_model_mode
    if mode == "off":
        return rules_label, 1.0 if rules_label != "unknown" else 0.0

    predictor = _get_predictor()
    if predictor is None:
        return rules_label, 1.0 if rules_label != "unknown" else 0.0

    try:
        model_label, model_prob = predictor.predict(**kwargs)
    except Exception as exc:  # noqa: BLE001 - never break place collection on ML
        logger.warning("environment prediction failed for %r: %s", title, exc)
        return rules_label, 1.0 if rules_label != "unknown" else 0.0

    if mode == "shadow":
        if model_label != rules_label:
            logger.info(
                "environment disagreement title=%r rules=%s model=%s score=%.2f",
                title, rules_label, model_label, model_prob,
            )
        return rules_label, 1.0 if rules_label != "unknown" else 0.0

    # active mode
    if rules_label == "unknown":
        threshold = settings.environment_model_fallback_threshold
    else:
        threshold = settings.environment_model_threshold
    if model_prob >= threshold:
        return model_label, model_prob
    if rules_label != "unknown":
        return rules_label, 1.0
    # Rules had nothing to say and the model was unsure: keep unknown so
    # downstream code can treat it explicitly instead of a shaky guess.
    return "unknown", 0.0


def classify_environment(
    *, title: str, description: str, opening_hours: str | None, kinds: list[str], category_kind: str
) -> EnvironmentKind:
    label, _score = classify_environment_with_score(
        title=title,
        description=description,
        opening_hours=opening_hours,
        kinds=kinds,
        category_kind=category_kind,
    )
    return label
