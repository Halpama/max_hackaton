#!/usr/bin/env python
"""Train and evaluate the indoor/outdoor/mixed environment classifier.

Run from backend/::

    python scripts/train_environment_model.py
    # or with your own freshly labeled data:
    python scripts/train_environment_model.py --input ml_data/environment_labeled.jsonl \
        --model ml_data/environment_model.joblib

The artifact is a single scikit-learn ``Pipeline`` that consumes records as
dicts with the fields ``title``, ``description``, ``opening_hours``,
``kinds_signature`` and ``category_kind`` — exactly what
``app.services.environment`` builds at inference time, so training and serving
can never drift apart.

The split is by city to measure generalisation beyond the collected cities.
Add new cities to TRAIN_CITIES (or pass ``--city-split train`` for extra
cities found in the data) before retraining on a bigger dataset.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import OneHotEncoder

# Keep these imports after path setup so the script can run standalone too.
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.environment import ItemSelector, kinds_signature  # noqa: E402

LABELS = ("indoor", "mixed", "outdoor")
TRAIN_CITIES = {"Москва", "Казань", "Санкт-Петербург"}
VALIDATION_CITIES = {"Нижний Новгород"}
TEST_CITIES = {"Сочи"}


def load_records(path: Path) -> list[dict[str, Any]]:
    """Load labeled records from JSONL or CSV (e.g. the reviewed
    ``ml_data/environment_labels_filled.csv`` export).

    CSV notes: semicolon-delimited exports are detected automatically, a UTF-8
    BOM is tolerated, and the ``kinds`` column may be either a comma-separated
    string ("a,b,c") or a JSON list ("[\"a\", \"b\"]").
    """
    suffix = path.suffix.lower()
    if suffix in (".csv", ".tsv"):
        import csv

        with path.open(encoding="utf-8-sig", newline="") as stream:
            sample = stream.read(4096)
            stream.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
                dialect.delimiter = "\t" if suffix == ".tsv" else ","
            rows: list[dict[str, Any]] = []
            for raw in csv.DictReader(stream, dialect=dialect):
                record = {k: (v.strip() if isinstance(v, str) else v)
                          for k, v in raw.items() if k}
                kinds_raw = record.get("kinds") or ""
                if isinstance(kinds_raw, str):
                    kinds_raw = kinds_raw.strip()
                    if kinds_raw.startswith("["):
                        try:
                            kinds_raw = json.loads(kinds_raw)
                        except json.JSONDecodeError:
                            kinds_raw = []
                    else:
                        kinds_raw = [p.strip() for p in kinds_raw.split(",") if p.strip()]
                record["kinds"] = list(kinds_raw)
                confidence = record.get("auto_confidence")
                if isinstance(confidence, str):
                    try:
                        record["auto_confidence"] = float(confidence)
                    except ValueError:
                        pass
                rows.append(record)
        return rows
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def to_pipeline_record(record: dict[str, Any]) -> dict[str, str]:
    """Map a raw labeled record to the feature dict the pipeline expects."""
    return {
        "title": str(record.get("title") or ""),
        "description": str(record.get("description") or ""),
        "opening_hours": str(record.get("opening_hours") or ""),
        "kinds_signature": kinds_signature(list(record.get("kinds") or [])),
        "category_kind": str(record.get("category_kind") or "unknown"),
    }


def build_pipeline() -> Pipeline:
    text = TfidfVectorizer(
        ngram_range=(1, 2), sublinear_tf=True, min_df=1, max_features=20_000
    )
    text_branch = Pipeline(
        [
            ("select", ItemSelector("title", as_list=True)),
            ("tfidf", text),
        ]
    )
    # Description carries separate signal; union both text branches.
    description_branch = Pipeline(
        [
            ("select", ItemSelector("description", as_list=True)),
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, max_features=20_000)),
        ]
    )
    hours_branch = Pipeline(
        [
            ("select", ItemSelector("opening_hours", as_list=True)),
            ("tfidf", TfidfVectorizer(analyzer="word", ngram_range=(1, 1), sublinear_tf=True, max_features=2_000)),
        ]
    )
    kinds_branch = Pipeline(
        [
            ("select", ItemSelector("kinds_signature")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    category_branch = Pipeline(
        [
            ("select", ItemSelector("category_kind")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    features = FeatureUnion(
        [
            ("title_text", text_branch),
            ("description_text", description_branch),
            ("hours_text", hours_branch),
            ("kinds", kinds_branch),
            ("category", category_branch),
        ]
    )
    return Pipeline(
        [
            ("features", features),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, random_state=42)),
        ]
    )


def rule_baseline(record: dict[str, Any]) -> str:
    from app.services.environment import classify_by_rules

    return classify_by_rules(
        str(record.get("title") or ""),
        list(record.get("kinds") or []),
        str(record.get("category_kind") or ""),
    )


def evaluate(name: str, records: list[dict[str, Any]], predictions: list[str]) -> float:
    truth = [record["manual_environment"] for record in records]
    macro = f1_score(truth, predictions, labels=list(LABELS), average="macro")
    print(f"\n{name}: {len(records)} records")
    print(f"accuracy: {accuracy_score(truth, predictions):.3f}")
    print(f"macro_f1: {macro:.3f}")
    print(classification_report(truth, predictions, labels=list(LABELS), zero_division=0))
    return macro


def threshold_scan(model: Pipeline, records: list[dict[str, Any]]) -> None:
    """Show accuracy if the model may only override rules above prob p."""
    truth = np.array([r["manual_environment"] for r in records])
    x = [to_pipeline_record(r) for r in records]
    probs = model.predict_proba(x)
    classes = list(model.classes_)
    model_pred = np.array([classes[i] for i in probs.argmax(axis=1)])
    model_max = probs.max(axis=1)
    rules = np.array([rule_baseline(r) for r in records])
    rules = np.where(rules == "unknown", "outdoor", rules)  # rules abstain -> worst case guess
    print("threshold scan (override rules only when confident):")
    for p in (0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95):
        blended = np.where(model_max >= p, model_pred, rules)
        acc = accuracy_score(truth, blended)
        overrides = int(np.sum((model_max >= p) & (model_pred != rules)))
        print(f"  p={p:.2f}: accuracy={acc:.3f} overrides={overrides}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="ml_data/environment_labeled.jsonl")
    parser.add_argument("--model", default="ml_data/environment_model.joblib")
    parser.add_argument(
        "--city-split",
        choices=("default", "stratified"),
        default="default",
        help="'default' keeps the fixed per-city split; 'stratified' puts ~15%% "
        "of every city into validation and test (use once you have many cities).",
    )
    args = parser.parse_args()

    records = load_records(Path(args.input))
    labeled = [r for r in records if r.get("manual_environment") in LABELS]
    if len(labeled) < 60:
        raise SystemExit(f"need at least 60 labeled records, got {len(labeled)}")

    if args.city_split == "default":
        train = [r for r in labeled if r.get("city") in TRAIN_CITIES]
        validation = [r for r in labeled if r.get("city") in VALIDATION_CITIES]
        test = [r for r in labeled if r.get("city") in TEST_CITIES]
        if not train or not validation or not test:
            raise SystemExit("train/validation/test city split is empty")
    else:
        rng = np.random.default_rng(42)
        validation, test, train = [], [], []
        for r in rng.permutation(labeled):
            roll = rng.random()
            if roll < 0.15:
                validation.append(r)
            elif roll < 0.30:
                test.append(r)
            else:
                train.append(r)

    print(f"train={len(train)}, validation={len(validation)}, test={len(test)}")
    evaluate("rules only / validation", validation, [rule_baseline(r) for r in validation])

    x_train = [to_pipeline_record(r) for r in train]
    y_train = [r["manual_environment"] for r in train]
    x_val = [to_pipeline_record(r) for r in validation]
    x_test = [to_pipeline_record(r) for r in test]

    model = build_pipeline()
    model.fit(x_train, y_train)
    val_macro = evaluate(
        "pipeline / validation", validation, model.predict(x_val).tolist()
    )
    evaluate("pipeline / test", test, model.predict(x_test).tolist())
    threshold_scan(model, validation + test)

    model_path = Path(args.model)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": model, "labels": LABELS, "val_macro_f1": val_macro}, model_path)
    print(f"saved model to {model_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
