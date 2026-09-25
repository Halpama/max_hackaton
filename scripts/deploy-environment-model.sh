#!/usr/bin/env bash
# Copy the outdoor/indoor classifier artifact to the VDS (not tracked in git).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-$ROOT/backend/ml_data/environment_model.joblib}"
HOST="${DEPLOY_HOST:?set DEPLOY_HOST, e.g. root@stand.example}"
REMOTE_DIR="${REMOTE_DIR:-/root/max_hackaton/backend/ml_data}"

if [[ ! -f "$SRC" ]]; then
  echo "missing model file: $SRC" >&2
  echo "usage: $0 [path/to/environment_model.joblib]" >&2
  exit 1
fi

ssh "$HOST" "mkdir -p '$REMOTE_DIR'"
scp "$SRC" "$HOST:$REMOTE_DIR/environment_model.joblib"
ssh "$HOST" "chmod 600 '$REMOTE_DIR/environment_model.joblib' && ls -lh '$REMOTE_DIR/environment_model.joblib'"
echo "done — restart api if ENVIRONMENT_MODEL_MODE=active and the process cached a miss:"
echo "  ssh $HOST 'cd /root/max_hackaton && docker compose restart api'"
