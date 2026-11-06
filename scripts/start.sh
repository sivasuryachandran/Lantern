#!/usr/bin/env bash
# Start record-bot against the local Mattermost using a login session for the record-bot account.
# Needs LANTERN_TEST_PASSWORD (the throwaway password of the fictional test accounts).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; [ -x "$PY" ] || PY=.venv/Scripts/python
export MM_URL="${MM_URL:-http://localhost:8065}" MM_TEAM="${MM_TEAM:-switch}"
: "${LANTERN_TEST_PASSWORD:?set LANTERN_TEST_PASSWORD}"
if [ -z "${MM_TOKEN:-}" ]; then
  body="{\"login_id\":\"record-bot\",\"password\":\"$LANTERN_TEST_PASSWORD\"}"
  MM_TOKEN="$(curl -s -i -X POST "$MM_URL/api/v4/users/login" -d "$body" | awk -F': ' 'tolower($1)=="token"{print $2}' | tr -d '\r')"
  export MM_TOKEN
fi
[ -n "$MM_TOKEN" ] || { echo "could not log record-bot in"; exit 1; }
db="${LANTERN_DB:-lantern.db}"
[ -f "$db" ] || "$PY" scripts/seed_demo_db.py "$db"
exec "$PY" -m lantern run
