#!/usr/bin/env python
"""Train and evaluate the outdoor/indoor classifier.

Run from backend/:
    python scripts/train_environment_model.py

The split is by city to measure generalisation beyond the collected cities.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.preprocessing import MultiLabelBinarizer, OneHotEncoder

LABELS = ("indoor", "mixed", "outdoor")
TRAIN_CITIES = {"Москва", "Казань", "Санкт-Петербург"}
VALIDATION_CITIES = {"Нижний Новгород"}
TEST_CITIES = {"Сочи"}


def load_records(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def text_of(record: dict[str, Any]) -> str:
    return " ".join(
        str(record.get(field) or "")
        for field in ("title", "description", "opening_hours")
    )


def build_features(
    records: list[dict[str, Any]],
    *,
    text_vectorizer: TfidfVectorizer | None = None,
    kind_encoder: MultiLabelBinarizer | None = None,
    category_encoder: OneHotEncoder | None = None,
    fit: bool,
) -> tuple[Any, TfidfVectorizer, MultiLabelBinarizer, OneHotEncoder]:
    texts = [text_of(record) for record in records]
    kinds = [record.get("kinds") or [] for record in records]
    categories = np.array(
        [[str(record.get("category_kind") or "unknown")] for record in records]
    )

    if fit:
        text_vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), min_df=1, max_features=20_000, sublinear_tf=True
        )
        kind_encoder = MultiLabelBinarizer()
        category_encoder = OneHotEncoder(handle_unknown="ignore")
        text_features = text_vectorizer.fit_transform(texts)
        kind_features = kind_encoder.fit_transform(kinds)
        category_features = category_encoder.fit_transform(categories)
    else:
        assert text_vectorizer and kind_encoder and category_encoder
        text_features = text_vectorizer.transform(texts)
        kind_features = kind_encoder.transform(kinds)
        category_features = category_encoder.transform(categories)

    return (
        hstack((text_features, kind_features, category_features)).tocsr(),
        text_vectorizer,
        kind_encoder,
        category_encoder,
    )


def rule_baseline(record: dict[str, Any]) -> str:
    kinds = set(record.get("kinds") or [])
    title = str(record.get("title") or "").lower()
    if kinds & {"museums", "theatre", "concert-hall", "observatory"}:
        if kinds & {"park", "palace", "homesteads", "suburb", "temple", "church", "monastery"}:
            return "mixed"
        return "indoor"
    if kinds & {"restaurants", "bar", "anticafe"}:
        return "mixed" if "террас" in title or "suburb" in kinds else "indoor"
    if kinds & {"park", "bridge", "fountain", "beach", "photo-places"}:
        return "outdoor"
    if record.get("category_kind") == "food":
        return "indoor"
    return "outdoor"


def evaluate(name: str, records: list[dict[str, Any]], predictions: list[str]) -> None:
    truth = [record["manual_environment"] for record in records]
    print(f"\n{name}: {len(records)} records")
    print(f"accuracy: {accuracy_score(truth, predictions):.3f}")
    print(f"macro_f1: {f1_score(truth, predictions, labels=list(LABELS), average='macro'):.3f}")
    print(classification_report(truth, predictions, labels=list(LABELS), zero_division=0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="ml_data/environment_labeled.jsonl")
    parser.add_argument("--model", default="ml_data/environment_model.joblib")
    args = parser.parse_args()

    records = load_records(Path(args.input))
    train = [r for r in records if r.get("city") in TRAIN_CITIES]
    validation = [r for r in records if r.get("city") in VALIDATION_CITIES]
    test = [r for r in records if r.get("city") in TEST_CITIES]
    if not train or not validation or not test:
        raise SystemExit("train/validation/test city split is empty")

    print(f"train={len(train)}, validation={len(validation)}, test={len(test)}")
    evaluate("rule baseline / validation", validation, [rule_baseline(r) for r in validation])
    evaluate("rule baseline / test", test, [rule_baseline(r) for r in test])

    x_train, text_vectorizer, kind_encoder, category_encoder = build_features(train, fit=True)
    x_validation, *_ = build_features(
        validation,
        text_vectorizer=text_vectorizer,
        kind_encoder=kind_encoder,
        category_encoder=category_encoder,
        fit=False,
    )
    x_test, *_ = build_features(
        test,
        text_vectorizer=text_vectorizer,
        kind_encoder=kind_encoder,
        category_encoder=category_encoder,
        fit=False,
    )

    model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    model.fit(x_train, [record["manual_environment"] for record in train])
    evaluate("logistic regression / validation", validation, model.predict(x_validation).tolist())
    evaluate("logistic regression / test", test, model.predict(x_test).tolist())

    artifact = {
        "model": model,
        "text_vectorizer": text_vectorizer,
        "kind_encoder": kind_encoder,
        "category_encoder": category_encoder,
        "labels": LABELS,
    }
    model_path = Path(args.model)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path)
    print(f"saved model to {model_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())