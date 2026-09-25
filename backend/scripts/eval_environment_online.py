#!/usr/bin/env python
"""Evaluate the SAVED model through the production code path.

Unlike train_environment_model.py (which evaluates a freshly trained pipeline),
this script loads ml_data/environment_model.joblib exactly the way the running
backend does — via app.services.environment.classify_environment_with_score —
so it measures what the deployed classifier actually produces.

Run from backend/::

    python scripts/eval_environment_online.py
    ENVIRONMENT_MODEL_MODE=active python scripts/eval_environment_online.py

Exit code 0 if end-to-end accuracy is at least --min-accuracy (default 0.80),
1 otherwise — convenient for CI / pre-deploy checks.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, classification_report

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import environment as env  # noqa: E402
from scripts.train_environment_model import (  # noqa: E402
    LABELS,
    load_records,
    rule_baseline,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="ml_data/environment_labels_filled.csv")
    parser.add_argument("--min-accuracy", type=float, default=0.80)
    args = parser.parse_args()

    mode = os.environ.get("ENVIRONMENT_MODEL_MODE", "shadow")
    print(f"ENVIRONMENT_MODEL_MODE={mode} (set 'active' to let the model override rules)")

    records = [r for r in load_records(Path(args.input)) if r.get("manual_environment") in LABELS]
    if not records:
        raise SystemExit("no labeled records found")

    truth, rules_out, online_out = [], [], []
    disagreements = 0
    for r in records:
        label = r["manual_environment"]
        rule = rule_baseline(r)
        # Production entry point used by places.py (respects MODE/threshold env).
        pred, _score = env.classify_environment_with_score(
            title=str(r.get("title") or ""),
            description=str(r.get("description") or ""),
            opening_hours=str(r.get("opening_hours") or "") or None,
            kinds=list(r.get("kinds") or []),
            category_kind=str(r.get("category_kind") or ""),
        )
        truth.append(label)
        rules_out.append(rule if rule != "unknown" else "outdoor")
        online_out.append(pred)
        if pred != rule and rule != "unknown":
            disagreements += 1

    truth_np = np.array(truth)
    acc_rules = accuracy_score(truth_np, rules_out)
    acc_online = accuracy_score(truth_np, online_out)
    print(f"\nrecords: {len(records)}")
    print(f"rules only:            accuracy={acc_rules:.3f}")
    print(f"production path ({mode}): accuracy={acc_online:.3f}")
    print(f"model overrode rules on {disagreements} records")
    print(classification_report(truth_np, online_out, labels=list(LABELS), zero_division=0))

    ok = acc_online >= args.min_accuracy
    print(f"{'PASS' if ok else 'FAIL'}: accuracy {acc_online:.3f} vs min {args.min_accuracy:.2f}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
