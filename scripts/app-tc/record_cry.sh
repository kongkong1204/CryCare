#!/bin/bash
# 에뮬레이터 앱에서 울음소리 길이만큼만 녹음한다.
# 녹음 시작·정지는 adb로 즉시 누르고(Maestro 흐름 사이 대기 없이), 그 사이 맥 스피커로 샘플을 재생.
# 사용: scripts/app-tc/record_cry.sh <wav 경로> [--analyze]
#   --analyze: 녹음 정지 직후 "분석하기"까지 바로 누른다 (자동화 도구 기동 대기 없이)
# CRY_TS_FILE이 지정되면 재생 시작 시각(epoch 초)을 기록한다 → 영상에 소리를 합성할 때 사용
set -euo pipefail
WAV="$1"
ADB="${ADB:-/opt/homebrew/share/android-commandlinetools/platform-tools/adb}"

# 접근성 라벨(content-desc) 또는 글자(text)로 요소 중심 좌표를 찾는다
center_of() {
  "$ADB" exec-out uiautomator dump /dev/tty 2>/dev/null \
    | grep -o "\(content-desc\|text\)=\"$1\"[^>]*bounds=\"\[[0-9]*,[0-9]*\]\[[0-9]*,[0-9]*\]\"" \
    | sed -E 's/.*\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\].*/\1 \2 \3 \4/' \
    | awk '{print int(($1+$3)/2), int(($2+$4)/2)}' | head -1
}

POS="$(center_of '녹음 시작')"
[ -n "$POS" ] || { echo "녹음 버튼을 찾지 못했습니다"; exit 1; }
DUR="$(afinfo "$WAV" | awk '/estimated duration/ {print $3}')"
echo "녹음: $(basename "$WAV") (${DUR}s)"

"$ADB" shell input tap $POS          # 녹음 시작
sleep 0.4                            # 녹음기 준비 시간
[ -n "${CRY_TS_FILE:-}" ] && python3 -c 'import time; print(time.time())' > "$CRY_TS_FILE"
afplay -v 1 "$WAV"                   # 재생이 끝날 때까지 대기
"$ADB" shell input tap $POS          # 같은 자리 = 녹음 정지

if [ "${2:-}" = "--analyze" ]; then
  for _ in $(seq 1 20); do BTN="$(center_of '분석하기')"; [ -n "$BTN" ] && break; sleep 0.2; done
  [ -n "$BTN" ] || { echo "분석하기 버튼을 찾지 못했습니다"; exit 1; }
  sleep 0.5                          # 녹음 완료 화면을 잠깐 보여준다
  "$ADB" shell input tap $BTN
fi
