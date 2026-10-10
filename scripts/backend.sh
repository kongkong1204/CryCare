#!/bin/bash
# 백엔드 실행. 8000번을 이미 쓰는 프로세스(이전 서버)가 있으면 종료하고 다시 띄운다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT=8000

if PIDS="$(lsof -ti:$PORT)"; then
  echo "기존 :$PORT 프로세스 종료: $PIDS"
  kill $PIDS
  sleep 1
fi

cd "$ROOT"
exec venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port "$PORT"
