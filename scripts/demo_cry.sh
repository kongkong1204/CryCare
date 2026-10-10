#!/bin/bash
# 시연용 울음 재생기: Enter를 누를 때마다 다음 울음 샘플을 맥 스피커로 재생한다.
# 폰을 맥 스피커 가까이 두고, 앱에서 녹음 버튼을 누른 직후 Enter → 재생이 끝나면 녹음 정지.
# 사용: scripts/demo_cry.sh [샘플 경로...]
# 기본 순서는 폰 시연 대본용: ① TC3 첫 사용 → ② TC2 불확실 안내 → ③ TC5 맥락 반영
DATA="${DATA:-$HOME/Downloads/BabyCry-C5_160}"
if [ $# -gt 0 ]; then SAMPLES=("$@"); else
  SAMPLES=("$DATA/hungry/hungry_0.wav" "$DATA/hungry/hungry_1.wav" "$DATA/hungry/hungry_1.wav")
fi

i=0
while :; do
  f="${SAMPLES[$((i % ${#SAMPLES[@]}))]}"
  dur=$(afinfo "$f" | awk '/estimated duration/ {printf "%.1f", $3}')
  read -r -p "▶ Enter: $(basename "$f") 재생 (${dur}초) / q: 종료 " key
  [ "$key" = q ] && break
  afplay -v 1 "$f"
  echo "  ■ 재생 끝 → 지금 녹음 정지"
  i=$((i + 1))
done
