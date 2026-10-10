#!/bin/bash
# Phase C: ngrok으로 백엔드(8000)를 외부에 공개하고 앱(.env)이 그 주소를 쓰게 한다.
# 사용: scripts/tunnel.sh   (Ctrl+C로 종료하면 mobile/.env를 원래 값으로 되돌림)
# 사전: ngrok config add-authtoken <토큰>  (https://dashboard.ngrok.com/get-started/your-authtoken)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/mobile/.env"
PORT=8000
LOG="$(mktemp -t crycare-ngrok)"

NGROK_CONFIG="$(ngrok config check 2>/dev/null | sed -n 's/^Valid configuration file at //p' || true)"
if [ -z "${NGROK_AUTHTOKEN:-}" ] && ! grep -qs authtoken "$NGROK_CONFIG"; then
  echo "✗ ngrok 인증 토큰이 없습니다. 먼저 실행하세요: ngrok config add-authtoken <토큰>"
  exit 1
fi

if ! curl -sf "http://localhost:$PORT/" >/dev/null; then
  echo "✗ 백엔드가 :$PORT 에서 응답하지 않습니다. 먼저 scripts/backend.sh 를 실행하세요."
  exit 1
fi

ORIGINAL_ENV="$(cat "$ENV_FILE" 2>/dev/null || true)"

cleanup() {
  [ -n "${NGROK_PID:-}" ] && kill "$NGROK_PID" 2>/dev/null || true
  printf '%s\n' "$ORIGINAL_ENV" > "$ENV_FILE"
  echo
  echo "터널 종료. mobile/.env 복원: $(cat "$ENV_FILE")"
  echo "→ Expo를 재시작(npx expo start -c)해야 앱에 반영됩니다."
}
trap cleanup EXIT INT TERM

ngrok http "$PORT" --log stdout > "$LOG" 2>&1 &
NGROK_PID=$!

URL=""
for _ in $(seq 1 30); do
  # ngrok 로컬 API가 아직 안 떴으면 curl이 실패한다 → 빈 값으로 두고 재시도
  URL="$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | python3 -c 'import json,sys
try:
    t=[x["public_url"] for x in json.load(sys.stdin)["tunnels"] if x["public_url"].startswith("https")]
    print(t[0] if t else "")
except Exception:
    print("")' || true)"
  [ -n "$URL" ] && break
  sleep 1
done

if [ -z "$URL" ]; then
  echo "✗ ngrok 공개 주소를 얻지 못했습니다. 로그: $LOG"
  tail -5 "$LOG"
  exit 1
fi

echo "EXPO_PUBLIC_API_URL=$URL" > "$ENV_FILE"

echo "✓ 공개 주소: $URL"
printf '✓ 터널 헬스체크: '
curl -s -m 10 -H 'ngrok-skip-browser-warning: 1' "$URL/" || echo "실패"
echo
echo "✓ mobile/.env → $(cat "$ENV_FILE")"
echo "→ Expo를 재시작(npx expo start -c)하면 앱이 터널 주소로 붙습니다. (Expo 자체는 같은 Wi-Fi 또는 --tunnel 필요)"
echo "Ctrl+C로 종료"
wait "$NGROK_PID"
