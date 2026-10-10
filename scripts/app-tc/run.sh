#!/bin/bash
# 에뮬레이터 앱 시연 영상 자동 촬영: 최초 실행 동의(FR14) → 첫 녹음·분석(TC3)
# 결과: evidence/video/app_<클립>.mp4 + 합본 evidence/video/app_demo.mp4
#
# 사전: Android 에뮬레이터 실행 중, Metro(npx expo start --tunnel) 실행 중, 백엔드 :8000 실행 중
#       brew install ffmpeg-full maestro
# 사용: EXPO_URL=exp://xxxx.exp.direct scripts/app-tc/run.sh
# 나머지 TC(1·2·4·5·6·7)는 scripts/tc_api.sh 터미널 영상으로 증거를 남긴다.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HERE="$ROOT/scripts/app-tc"
source "$HERE/lib.sh"

log "준비: Expo Go 초기화(새 기기 = 새 UUID) 후 앱 열기"
adb shell pm clear host.exp.exponent >/dev/null
adb shell pm grant host.exp.exponent android.permission.RECORD_AUDIO

flow "$HERE/open.yaml"

# ── 동의 (FR14)
clip_start consent
flow "$HERE/consent.yaml"
clip_stop consent $'FR14 최초 실행 동의\n육아 보조·이상 징후 고지, 개인정보 동의'

log "준비: Expo Go 앱별 마이크 허용 (촬영 밖)"
flow "$HERE/prime_mic.yaml"

# ── TC3 첫 사용자 (분석 탭 정리는 촬영 전에 끝내 둔다)
flow "$HERE/home.yaml"
clip_start tc3
CRY_TS_FILE="$WORK/tc3.cry" "$HERE/record_cry.sh" "$SAMPLE" --analyze
flow "$HERE/analyze.yaml"
hold 3
flow "$HERE/tc3_result.yaml"
clip_stop tc3 $'TC3 첫 사용자: 기록·피드백 없음\n→ 1단계·기록 부족(B3), 기록 유도'

# 합본
for n in consent tc3; do echo "file '$OUT/app_$n.mp4'"; done > "$WORK/list.txt"
# 클립 간 형식 차이로 재생이 깨지지 않도록 복사(-c copy)가 아니라 재인코딩으로 합친다
"$FFMPEG" -y -loglevel error -f concat -safe 0 -i "$WORK/list.txt" \
  -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac -b:a 128k -ac 2 -movflags faststart "$OUT/app_demo.mp4"
log "합본: evidence/video/app_demo.mp4 ($(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/app_demo.mp4" | cut -d. -f1)초)"
