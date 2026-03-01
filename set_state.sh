#!/usr/bin/env bash
# Update Star Office UI state. Usage: set_state.sh <state> [detail]
# States: idle, writing, researching, executing, syncing, error
set -e
STATE="${1:-idle}"
DETAIL="${2:-}"
URL="${STAR_OFFICE_URL:-http://127.0.0.1:19791/state}"
curl -s -X POST "$URL" -H "Content-Type: application/json" \
  -d "$(printf '%s' "{\"state\":\"$STATE\",\"detail\":\"$DETAIL\"}")" >/dev/null || true
