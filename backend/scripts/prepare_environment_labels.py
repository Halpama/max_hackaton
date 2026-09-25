#!/usr/bin/env python
"""Prepare a human-labeling CSV from the collected environment JSONL.

Run from backend/:
    python scripts/prepare_environment_labels.py

The source JSONL is never modified. Review ``manual_environment`` in the CSV
and use only these values: indoor, outdoor, mixed, unknown.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

VALID_LABELS = {"indoor", "outdoor", "mixed", "unknown"}
MIXED_TOKENS = {"park", "palace", "homesteads", "suburb", "temple", "church", "monastery"}
OUTDOOR_TOKENS = {"park", "bridge", "fountain", "beach", "photo-places", "sights"}


def priority(record: dict[str, Any]) -> tuple[int, str, str]:
    """Put uncertain or contradictory weak labels first for efficient review."""
    kinds = set(record.get("kinds") or [])
    auto = record.get("auto_environment") or "unknown"

    if auto == "unknown":
        rank = 0
    elif auto == "mixed":
        rank = 1
    elif record.get("category_kind") == "food" and "suburb" in kinds:
        rank = 1
    elif "museums" in kinds and kinds & MIXED_TOKENS:
        rank = 1
    elif auto == "outdoor" and kinds & {"museums", "art-space"}:
        rank = 1
    else:
        rank = 2

    return rank, str(record.get("city") or ""), str(record.get("title") or "")


def suggested_manual_label(record: dict[str, Any]) -> str:
    """Leave obvious examples prefilled; ambiguous rows remain blank."""
    kinds = set(record.get("kinds") or [])
    title = str(record.get("title") or "").lower()
    category = record.get("category_kind")

    if kinds & {"museums", "theatre", "concert-hall", "observatory"}:
        if kinds & MIXED_TOKENS or any(word in title for word in ("заповедник", "парк", "кремль")):
            return "mixed"
        return "indoor"
    if kinds & {"restaurants", "bar", "anticafe"}:
        return "mixed" if "suburb" in kinds or "террас" in title else "indoor"
    if kinds & {"park", "bridge", "fountain", "beach", "photo-places"}:
        return "outdoor"
    if category == "food":
        return "indoor"
    return ""


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid JSON on line {line_number}: {exc}") from exc
            if not isinstance(record, dict) or not record.get("id"):
                raise SystemExit(f"record on line {line_number} has no id")
            records.append(record)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="ml_data/environment_places.jsonl")
    parser.add_argument("--output", default="ml_data/environment_labels.csv")
    parser.add_argument(
        "--no-prefill",
        action="store_true",
        help="leave all manual_environment cells empty, including obvious examples",
    )
    args = parser.parse_args()

    records = sorted(load_records(Path(args.input)), key=priority)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id",
        "city",
        "title",
        "kinds",
        "category_kind",
        "description",
        "opening_hours",
        "source",
        "auto_environment",
        "auto_confidence",
        "auto_reason",
        "review_priority",
        "manual_environment",
    ]

    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            label = "" if args.no_prefill else suggested_manual_label(record)
            if label not in VALID_LABELS and label:
                label = ""
            writer.writerow(
                {
                    "id": record.get("id", ""),
                    "city": record.get("city", ""),
                    "title": record.get("title", ""),
                    "kinds": ",".join(record.get("kinds") or []),
                    "category_kind": record.get("category_kind", ""),
                    "description": record.get("description", ""),
                    "opening_hours": record.get("opening_hours") or "",
                    "source": record.get("source", ""),
                    "auto_environment": record.get("auto_environment", "unknown"),
                    "auto_confidence": record.get("auto_confidence", 0),
                    "auto_reason": record.get("auto_reason", ""),
                    "review_priority": priority(record)[0],
                    "manual_environment": label,
                }
            )

    print(f"wrote {len(records)} labeling rows to {output}")
    print("Fill manual_environment with: indoor, outdoor, mixed, unknown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())