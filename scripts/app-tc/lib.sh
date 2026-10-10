#!/bin/bash
# app-tc 촬영 스크립트 공통: 에뮬레이터 화면 녹화(adb screenrecord) + 상단 자막 + 울음 합성
# 사용: source "$(dirname "$0")/lib.sh"  (ROOT, HERE, EXPO_URL, SAMPLE을 먼저 정한 뒤)
SDK=/opt/homebrew/share/android-commandlinetools
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}"
export PATH="$SDK/platform-tools:$PATH" MAESTRO_CLI_NO_ANALYTICS=1
: "${EXPO_URL:?EXPO_URL=exp://... 를 지정하세요}"
# 화면당 10초 이내가 되도록 짧은(8.4초) 울음 샘플을 기본으로 쓴다
SAMPLE="${SAMPLE:-$HOME/Downloads/BabyCry-C5_160/uncomfortable/uncomfortable_38.wav}"
FONT="$(ls ~/Library/Fonts/D2Coding*.ttc | head -1)"
# 자막(drawtext)은 freetype이 포함된 ffmpeg-full 필요: brew install ffmpeg-full
FFMPEG=/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg
OUT="$ROOT/evidence/video"
WORK="$(mktemp -d -t crycare-app-tc)"
mkdir -p "$OUT"

log() { echo "[$(date +%H:%M:%S)] $*"; }
flow() { maestro test -e EXPO_URL="$EXPO_URL" "$@" >"$WORK/maestro.log" 2>&1 || { tail -20 "$WORK/maestro.log"; exit 1; }; }
hold() { sleep "${1:-2}"; }   # 영상에서 화면을 읽을 시간

# 클립 녹화: clip_start 이름 / clip_stop 이름 "자막"
# adb screenrecord는 소리를 담지 않으므로(에뮬레이터는 기기 소리 녹화 자체가 불가),
# 재생한 울음 wav를 재생 시각에 맞춰 영상에 합성한다.
now() { python3 -c 'import time; print(time.time())'; }
clip_start() {
  local name="$1"
  adb shell rm -f "/sdcard/$name.mp4"
  adb shell screenrecord --time-limit 180 "/sdcard/$name.mp4" &
  REC_PID=$!
  now > "$WORK/$name.start"   # 화면 녹화 시작 시각 (울음 합성 기준점)
  sleep 1
}
clip_stop() {
  local name="$1" caption="$2"
  hold 1.5
  adb shell pkill -INT screenrecord || true
  wait "$REC_PID" 2>/dev/null || true
  sleep 1
  adb pull "/sdcard/$name.mp4" "$WORK/$name.raw.mp4" >/dev/null
  printf '%s' "$caption" > "$WORK/$name.txt"

  # 앞쪽 정지 구간(자동화 도구 준비 시간)은 0.5초만 남기고 잘라낸다
  local lead
  lead=$("$FFMPEG" -hide_banner -i "$WORK/$name.raw.mp4" -vf "freezedetect=n=0.003:d=0.8" -map 0:v -f null - 2>&1 \
    | python3 -c "
import re, sys
log = sys.stdin.read()
s = re.findall(r'freeze_start: ([0-9.]+)', log); e = re.findall(r'freeze_end: ([0-9.]+)', log)
print(max(0.0, float(e[0]) - 0.5) if s and e and float(s[0]) < 0.3 else 0.0)")

  # 소리: 울음 원본(재생 시각에 맞춤) 또는 무음. 44.1kHz 스테레오로 통일 (모노·스테레오 혼합 시 플레이어에서 무음)
  local inputs=(-ss "$lead" -i "$WORK/$name.raw.mp4") mix
  if [ -f "$WORK/$name.cry" ]; then
    local delay_ms
    delay_ms=$(python3 -c "print(max(0, int((float(open('$WORK/$name.cry').read()) - float(open('$WORK/$name.start').read()) - $lead) * 1000)))")
    inputs+=(-i "$SAMPLE")
    mix="[1:a]adelay=${delay_ms}:all=1,aresample=44100,aformat=channel_layouts=stereo,apad[a]"
  else
    inputs+=(-f lavfi -i "anullsrc=r=44100:cl=stereo")
    mix="[1:a]anull[a]"
  fi

  # 상단 자막 바 + 720px 폭, 30fps 고정
  "$FFMPEG" -y -loglevel error "${inputs[@]}" -filter_complex "$mix" -map 0:v -map "[a]" -vf \
    "scale=720:-2,drawbox=x=0:y=0:w=iw:h=118:color=black@0.8:t=fill,drawtext=fontfile=$FONT:textfile=$WORK/$name.txt:fontcolor=white:fontsize=26:x=24:y=(118-th)/2:line_spacing=8" \
    -shortest -r 30 -pix_fmt yuv420p -c:v libx264 -crf 20 -c:a aac -b:a 128k -ac 2 -movflags faststart "$OUT/app_$name.mp4"
  log "클립 저장: evidence/video/app_$name.mp4 ($(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/app_$name.mp4" | cut -c1-4)초, 앞 ${lead}초 잘라냄)"
}

