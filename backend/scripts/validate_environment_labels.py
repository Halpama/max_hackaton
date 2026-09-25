#!/usr/bin/env python
"""Validate manual environment labels and build a training JSONL.

Run after filling ``manual_environment`` in the labeling CSV:
    python scripts/validate_environment_labels.py
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

VALID_LABELS = {"indoor", "outdoor", "mixed", "unknown"}
TRAIN_LABELS = VALID_LABELS - {"unknown"}


def load_rows(path: Path, delimiter: str) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="ml_data/environment_labels.csv")
    parser.add_argument("--output", default="ml_data/environment_labeled.jsonl")
    parser.add_argument(
        "--delimiter",
        default=";",
        help="CSV delimiter (default: ';', as used by the labeling spreadsheet)",
    )
    parser.add_argument("--allow-unknown", action="store_true")
    args = parser.parse_args()

    rows = load_rows(Path(args.input), args.delimiter)
    errors: list[str] = []
    usable: list[dict[str, Any]] = []
    labels: Counter[str] = Counter()
    cities: Counter[str] = Counter()
    seen_ids: set[str] = set()

    for line_number, row in enumerate(rows, 2):
        place_id = (row.get("id") or "").strip()
        label = (row.get("manual_environment") or "").strip().lower()
        city = (row.get("city") or "").strip()

        if not place_id:
            errors.append(f"line {line_number}: empty id")
        elif place_id in seen_ids:
            errors.append(f"line {line_number}: duplicate id {place_id}")
        else:
            seen_ids.add(place_id)

        if label not in VALID_LABELS:
            errors.append(
                f"line {line_number}: manual_environment must be "
                f"indoor/outdoor/mixed/unknown, got {label or '<empty>'}"
            )
            continue

        labels[label] += 1
        cities[city] += 1
        if label in TRAIN_LABELS or args.allow_unknown:
            record = dict(row)
            record["manual_environment"] = label
            record["kinds"] = [item for item in (row.get("kinds") or "").split(",") if item]
            record["has_photo"] = bool(row.get("has_photo"))
            usable.append(record)

    print(f"rows: {len(rows)}")
    print(f"valid labeled rows: {len(usable)}")
    print("labels:")
    for label in sorted(labels):
        print(f"  {label}: {labels[label]}")
    print(f"cities: {len(cities)}")

    if errors:
        print(f"errors: {len(errors)}")
        for error in errors[:20]:
            print(f"  {error}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        return 1

    if len(labels) < 3:
        print("error: need all three train classes: indoor, outdoor, mixed")
        return 1
    if min(labels[label] for label in TRAIN_LABELS) < 20:
        print("error: each train class needs at least 20 labeled rows")
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as stream:
        for record in usable:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"wrote training records to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())