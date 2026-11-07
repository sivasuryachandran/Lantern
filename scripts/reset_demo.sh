#!/usr/bin/env bash
# Fresh take: stop record-bot, delete the demo DB, wait out the bot's 60 s replay window, start it again with seeded cases 14-16.
# Needs the same env as scripts/start.sh (MM_URL, MM_TEAM, LANTERN_TEST_PASSWORD). Use between takes of the video.
set -euo pipefail
cd "$(dirname "$0")/.."
pkill -f "lantern run" 2>/dev/null || true
rm -f "${LANTERN_DB:-lantern.db}"
echo "waiting 62 s so messages from the previous take are not replayed..."
sleep 62
exec scripts/start.sh
