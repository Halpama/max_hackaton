#!/usr/bin/env bash
# Pull-based deploy: VDS fetches origin/main and rebuilds when HEAD moves.
set -euo pipefail

REPO_DIR="${REPO_DIR:-/root/max_hackaton}"
BRANCH="${DEPLOY_BRANCH:-main}"
COMPOSE="${COMPOSE:-docker compose}"
LOCK=/var/lock/max_hackaton-deploy.lock

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "deploy already running"
  exit 0
fi

cd "$REPO_DIR"

# Keep secrets / egress env that live only on the server.
if [ ! -d .git ]; then
  echo "ERROR: $REPO_DIR is not a git checkout" >&2
  exit 1
fi

git remote get-url origin >/dev/null
git fetch --prune origin "$BRANCH"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "already up to date ($LOCAL)"
  exit 0
fi

echo "deploying $LOCAL -> $REMOTE"
git reset --hard "origin/$BRANCH"

# Untracked artifacts survive reset --hard. Keep the environment classifier on
# the host at backend/ml_data/environment_model.joblib (never commit *.joblib).
if [ ! -f backend/ml_data/environment_model.joblib ]; then
  echo "WARN: missing backend/ml_data/environment_model.joblib — indoor/outdoor model off until you scp it" >&2
fi

# Preserve server-only env files if git clean ever runs; do not delete them here.
$COMPOSE up -d --build
$COMPOSE ps
curl -fsS --max-time 20 http://127.0.0.1:8000/health
echo
echo "deploy ok at $(git rev-parse --short HEAD)"
