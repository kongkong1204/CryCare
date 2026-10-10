#!/bin/bash
# 에뮬레이터 시연 클립: TC4 피드백 수정 → 자동 수유 기록 정리, TC7 데이터 전체 삭제
# 사전: 에뮬레이터 앱이 동의를 마친 상태이고, 그 기기에 피드백 "배고픔" 기록 2건이 있어야 한다.
#       (데이터셋 파일을 /predict로 직접 분석해 만든다 — 에뮬레이터 마이크는 무음이라 녹음 대신 사용)
# 결과: evidence/video/app_tc4.mp4, app_tc7.mp4
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HERE="$ROOT/scripts/app-tc"
source "$HERE/lib.sh"

adb shell cmd uimode night yes >/dev/null   # 폰 촬영본(다크 모드)과 맞춘다
flow "$HERE/relaunch.yaml"

clip_start tc4a
flow "$HERE/tc4_list.yaml"
hold 2
clip_stop tc4a $'TC4 피드백 저장: "배고픔" 피드백 2건\n→ 수유 기록 자동 추가 (피드백으로 자동 기록)'

clip_start tc4b
flow "$HERE/tc4_edit.yaml"
hold 1
clip_stop tc4b $'TC4 피드백 수정: 잘못 입력한 "배고픔"을\n"졸림"으로 덮어쓰기'

clip_start tc4c
flow "$HERE/tc4_after.yaml"
hold 2
clip_stop tc4c $'TC4 정합 처리: 수정한 기록의 자동 수유 기록 삭제\n→ 2건 → 1건'

clip_start tc7
flow "$HERE/tc7.yaml"
hold 1
clip_stop tc7 $'TC7 데이터 삭제: 내 데이터 전체 삭제\n→ 서버 기록·녹음 영구 삭제, 이력 0건'
