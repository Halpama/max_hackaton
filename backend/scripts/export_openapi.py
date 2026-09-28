#!/usr/bin/env python3
"""Export FastAPI OpenAPI schema to repo root (openapi.json / openapi.yaml)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("AUTH_MODE", "dev")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.main import app  # noqa: E402

schema = app.openapi()
(ROOT / "openapi.json").write_text(
    json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
try:
    import yaml

    (ROOT / "openapi.yaml").write_text(
        yaml.safe_dump(schema, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
except ImportError:
    print("PyYAML not installed — wrote openapi.json only", file=sys.stderr)

print(f"paths={len(schema.get('paths', {}))} → {ROOT / 'openapi.json'}")
