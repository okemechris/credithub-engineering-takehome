#!/usr/bin/env bash
# One-command local deploy: seeds the DB, starts the API, then the frontend.
# Backend runs in the background; Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")"

# --- backend ---
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --port 8000 &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT

# --- frontend ---
cd frontend
npm install
npm run dev
