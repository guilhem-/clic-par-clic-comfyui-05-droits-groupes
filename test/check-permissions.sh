#!/usr/bin/env bash
# Calls Open WebUI's public image route with two accounts and prints the HTTP status:
#   - a member of the group (expected: 200, an image is generated);
#   - a user outside the group (expected: 403, refused before reaching ComfyUI).
# The route checks the "Image Generation" permission itself; the internal function that tools
# call (image_generations) does not, hence the check inside open-webui/image_workshop.py.
#
# Usage: MEMBER_TOKEN=... OUTSIDER_TOKEN=... ./test/check-permissions.sh
# (tokens: Settings > Account > API keys of each account, or the session token)
set -euo pipefail

OWUI_URL="${OWUI_URL:-http://127.0.0.1:8080}"
: "${MEMBER_TOKEN:?MEMBER_TOKEN missing: token of a member of the group}"
: "${OUTSIDER_TOKEN:?OUTSIDER_TOKEN missing: token of a user outside the group}"

BODY='{"prompt": "A ceramic mug on a wooden desk, morning light, no text at all", "size": "1024x1024"}'

try() {
  local label="$1" token="$2" expected="$3" status
  status=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$OWUI_URL/api/v1/images/generations" \
    -H "Authorization: Bearer $token" -H 'Content-Type: application/json' -d "$BODY")
  if [ "$status" = "$expected" ]; then result="OK"; else result="UNEXPECTED"; fi
  printf '%-28s HTTP %s (expected %s) %s\n' "$label" "$status" "$expected" "$result"
}

try "Outside the group:" "$OUTSIDER_TOKEN" 403
try "Member of the group:" "$MEMBER_TOKEN" 200
