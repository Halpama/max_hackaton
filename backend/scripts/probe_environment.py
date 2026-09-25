"""Probe a single place through the exact production classification path.

Usage examples:
    python scripts/probe_environment.py --title "ГЭС-2" --kinds culture,museum \
        --description "Дом культуры, выставки в бывшей электростанции"
    python scripts/probe_environment.py --title "Парк Горького" --kinds parks
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--opening-hours", default=None)
    parser.add_argument("--kinds", default="", help="comma-separated 2GIS kinds")
    parser.add_argument("--category", default="", help="category_kind, e.g. culture")
    parser.add_argument(
        "--mode",
        default=None,
        help="override ENVIRONMENT_MODEL_MODE for this run (off/shadow/active)",
    )
    args = parser.parse_args()

    if args.mode:
        os.environ["ENVIRONMENT_MODEL_MODE"] = args.mode

    from app.services.environment import (
        _get_predictor,
        classify_by_rules,
        classify_environment_with_score,
    )
    from app.core.config import settings

    kinds = [k.strip() for k in args.kinds.split(",") if k.strip()]
    kwargs = dict(
        title=args.title,
        description=args.description,
        opening_hours=args.opening_hours,
        kinds=kinds,
        category_kind=args.category,
    )

    rules_label = classify_by_rules(args.title, kinds, args.category)
    predictor = _get_predictor()
    raw = predictor.predict(**kwargs) if predictor is not None else None
    final_label, score = classify_environment_with_score(**kwargs)

    print(f"mode          : {settings.environment_model_mode}")
    print(f"title         : {args.title!r}")
    print(f"kinds         : {kinds}")
    print(f"rules label   : {rules_label}")
    if raw is None:
        print("model         : <not loaded>")
    else:
        print(f"model label   : {raw[0]} (probability {raw[1]:.2f})")
    print(f"FINAL label   : {final_label} (confidence {score:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
