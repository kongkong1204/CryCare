#!/bin/bash
# 스펙 §11.1 TC1~TC9를 API로 실행하고 증거(JSON·응답시간)를 evidence/tc/<시각>/ 에 남긴다.
# 사용: scripts/tc_api.sh            (기본: 로컬 :8000)
#       PAUSE=0 scripts/tc_api.sh    (영상용 대기 없이)
#       ONLY="TC1 TC6" scripts/tc_api.sh   (일부 TC만. TC4·TC7은 TC1이 만든 기록을 쓰므로 TC1과 함께)
# TC6은 백엔드를 잘못된 키로 재시작했다가 정상 키로 되돌린다.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${BASE:-http://localhost:8000}"
DATA="${DATA:-$HOME/Downloads/BabyCry-C5_160}"
PAUSE="${PAUSE:-2}"
OUT="$ROOT/evidence/tc/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"
TIMES="$OUT/timings.csv"
echo "tc,request,http,seconds" > "$TIMES"

B=$'\e[1m'; DIM=$'\e[2m'; G=$'\e[32m'; R=$'\e[31m'; C=$'\e[36m'; Y=$'\e[33m'; N=$'\e[0m'
PASS=0; FAIL=0

pause() { sleep "$PAUSE"; }
want() { [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $1 "* ]]; }
title() { echo; echo "${B}${C}━━ $1 ━━${N}"; echo "${DIM}$2${N}"; pause; }
step() { echo "${Y}▶${N} $1"; }
check() { # 설명 조건식
  if eval "$2"; then echo "  ${G}✓ $1${N}"; PASS=$((PASS+1)); else echo "  ${R}✗ $1${N}"; FAIL=$((FAIL+1)); fi
}
jget() { python3 -c "import json,sys; d=json.load(open('$1')); print($2)"; }

# call TC 이름 메서드 경로 [curl 추가 인자...] → $OUT/<TC>_<이름>.json
call() {
  local tc="$1" name="$2" method="$3" path="$4"; shift 4
  local file="$OUT/${tc}_${name}.json"
  local meta
  meta=$(curl -s -o "$file" -w "%{http_code} %{time_total}" -X "$method" \
    -H "X-Device-Id: $DEV" -H "ngrok-skip-browser-warning: 1" "$@" "$BASE$path")
  local code="${meta% *}" secs="${meta#* }"
  echo "$tc,$method $path,$code,$secs" >> "$TIMES"
  printf "  ${DIM}%s %s → %s (%.2fs)${N}\n" "$method" "$path" "$code" "$secs"
  LAST="$file"
}
json() { curl_json=(-H 'Content-Type: application/json' -d "$1"); }
predict() { call "$1" "$2" POST /predict -F "file=@$DATA/$3.wav"; }
# 데이터셋 파일은 모델 학습 데이터라 확률이 높게 나온다. 학습에 안 쓴 실제 녹음은 경로로 보낸다
predict_file() { call "$1" "$2" POST /predict -F "file=@$3"; }
# hungry_1을 맥 스피커로 틀고 아이폰 앱으로 녹음한 파일 (v2 1순위 확률 0.26)
PHONE_SAMPLE="${PHONE_SAMPLE:-$ROOT/evidence/phone_take1/5af934b52801439fae52c8d06abd7733.m4a}"
ago() { python3 -c "from datetime import*; print((datetime.now(timezone.utc)-timedelta(minutes=$1)).isoformat())"; }
show() { # 응답 요약
  python3 - "$1" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
top = d["probabilities"][0]
ctx = {k: v for k, v in d["context"].items() if k != "facts"}
print(f"  예측: {d['prediction']} ({top['prob']:.2f})  분기: {d['branch']}")
print(f"  맥락: {ctx}")
s = d["suggestion"] or f"(제안 없음) reason_error={d['reason_error'][:60]}"
for line in s.splitlines():
    print(f"  │ {line}")
PY
}
new_device() { DEV="tc-$1-$(uuidgen | tr 'A-Z' 'a-z' | cut -c1-8)"; json '{"version":"v4"}'; call "$1" consent POST /consent "${curl_json[@]}" >/dev/null; }

wait_health() { for _ in $(seq 1 60); do curl -sf "$BASE/" >/dev/null && return 0; sleep 1; done; return 1; }
restart_backend() { # [잘못된 키 여부]
  local pids; pids=$(lsof -ti:8000) && kill $pids; sleep 1
  cd "$ROOT"
  if [ "${1:-}" = "bad" ]; then
    ANTHROPIC_API_KEY=sk-ant-invalid nohup venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 > "$OUT/backend_bad.log" 2>&1 &
  else
    nohup venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 > "$OUT/backend.log" 2>&1 &
  fi
  disown; wait_health
}

echo "${B}CryCare ${ONLY:-TC1~TC7} (스펙 §11.1)${N}  서버: $BASE"
echo "${DIM}증거 저장: ${OUT#$ROOT/}${N}"
wait_health || { echo "${R}서버가 응답하지 않습니다${N}"; exit 1; }

# ── TC1
if want TC1; then
title "TC1 맥락 보정" "hungry 예측 + 기록상 90분 전 수유 → B2, 배고픔 외 원인부터"
new_device TC1
step "90분 전 수유 기록"; json "{\"type\":\"feeding\",\"occurred_at\":\"$(ago 90)\"}"; call TC1 event POST /events "${curl_json[@]}"
step "hungry 샘플 분석"; predict TC1 predict hungry/hungry_0; show "$LAST"
check "1순위 hungry" "[ \"\$(jget $LAST \"d['prediction']\")\" = hungry ]"
check "분기 B2 (2시간 내 수유와 상충)" "[ \"\$(jget $LAST \"d['branch']\")\" = B2 ]"
TC1_DEV=$DEV; TC1_RECORD=$(jget "$LAST" "d['record_id']"); pause
fi

# ── TC2
if want TC2; then
title "TC2 불확실 안내" "1순위 확률 0.5 미만 샘플 → B2(앱 배지 '2단계 · 확실하지 않음') + 시도 순서"
new_device TC2
step "기저귀 기록(첫 사용 아님)"; json '{"type":"diaper"}'; call TC2 event POST /events "${curl_json[@]}"
step "저신뢰 샘플 분석 (실제 폰 녹음)"; predict_file TC2 predict "$PHONE_SAMPLE"; show "$LAST"
check "1순위 확률 < 0.5" "python3 -c \"import json;import sys;sys.exit(0 if json.load(open('$LAST'))['probabilities'][0]['prob']<0.5 else 1)\""
check "분기 B2 → 앱 배지 '2단계 · 확실하지 않음'" "[ \"\$(jget $LAST \"d['branch']\")\" = B2 ]"
check "제안에 시도 순서(번호 목록)" "grep -q '1\\.' $LAST"
pause
fi

# ── TC3
if want TC3; then
title "TC3 첫 사용자" "기록·피드백 없음 → B3, 보수적 안내 + 기록 유도"
new_device TC3
step "첫 분석"; predict TC3 predict hungry/hungry_0; show "$LAST"
check "분기 B3" "[ \"\$(jget $LAST \"d['branch']\")\" = B3 ]"
check "맥락 모두 '기록 없음'" "[ \"\$(jget $LAST \"d['context']['마지막 수유']+d['context']['마지막 기저귀']\")\" = '기록 없음기록 없음' ]"
pause
fi

# ── TC4
if want TC4; then
title "TC4 피드백 저장·수정" "라벨 hungry → awake 수정 → 자동 수유 기록 정리"
DEV=$TC1_DEV
step "TC1 기록에 라벨 hungry"; json '{"actual_label":"hungry"}'; call TC4 label_hungry POST "/records/$TC1_RECORD/label" "${curl_json[@]}"
call TC4 events_after_hungry GET /events
check "피드백으로 수유 기록 자동 생성" "grep -q '\"source\": *\"feedback\"' $LAST"
step "라벨을 awake로 수정"; json '{"actual_label":"awake"}'; call TC4 label_awake POST "/records/$TC1_RECORD/label" "${curl_json[@]}"
call TC4 events_after_awake GET /events
check "자동 수유 기록 삭제됨" "! grep -q '\"source\": *\"feedback\"' $LAST"
call TC4 record GET "/records/$TC1_RECORD"
check "기록의 실제 라벨 = awake" "[ \"\$(jget $LAST \"d['actual_label']\")\" = awake ]"
pause
fi

# ── TC5
if want TC5; then
title "TC5 피드백 맥락 반영" "sleepy 예측이 실제로도 sleepy였던 이력 2건 → 재분석 시 이력이 근거가 되어 B1(확신)"
new_device TC5
for f in sleepy_0 sleepy_1; do
  step "$f 분석 → 실제 sleepy"; predict TC5 "predict_$f" "sleepy/$f"
  rid=$(jget "$LAST" "d['record_id']"); json '{"actual_label":"sleepy"}'; call TC5 "label_$f" POST "/records/$rid/label" "${curl_json[@]}"
done
step "재분석"; predict TC5 predict_again sleepy/sleepy_2; show "$LAST"
check "맥락에 최근 피드백 포함 (2건 모두 일치)" "grep -q '모두 예측과 실제가 일치' $LAST"
check "1순위 확률 ≥ 0.5" "python3 -c \"import json,sys;sys.exit(0 if json.load(open('$LAST'))['probabilities'][0]['prob']>=0.5 else 1)\""
check "분기 B1 → 앱 배지 '3단계 · 근거 일치'" "[ \"\$(jget $LAST \"d['branch']\")\" = B1 ]"
pause
fi

# ── TC6
if want TC6; then
title "TC6 LLM 오류 복구" "잘못된 API 키 → B4(분류는 정상) → 정상 키로 재시도 성공"
step "백엔드를 잘못된 키로 재시작"; restart_backend bad
new_device TC6
step "분석 (LLM 실패 예상)"; predict TC6 predict_fail sleepy/sleepy_0; show "$LAST"
check "HTTP 200 + 분류 결과 있음" "[ -n \"\$(jget $LAST \"d['prediction']\")\" ]"
check "분기 B4, 제안 null" "[ \"\$(jget $LAST \"d['branch']\")\" = B4 ] && [ \"\$(jget $LAST \"d['suggestion']\")\" = None ]"
rid=$(jget "$LAST" "d['record_id']")
step "백엔드를 정상 키로 재시작"; restart_backend
step "제안 재시도"; call TC6 retry POST "/records/$rid/reason"
echo "  │ $(jget "$LAST" "d['suggestion']" | head -3)"
check "재시도로 제안 생성" "[ \"\$(jget $LAST \"d['suggestion'] is not None\")\" = True ]"
pause
fi

# ── TC8
if want TC8; then
title "TC8 금지어 차단" "LLM 출력에 금지어(진단·질병) → 내보내지 않고 B4 → 재시도로 정상 제안"
step "첫 LLM 응답을 금지어가 섞인 문장으로 바꿔 분석 (scripts/tc_banned.py)"
(cd "$ROOT" && venv/bin/python -W ignore scripts/tc_banned.py "$OUT" "$DATA/sleepy/sleepy_0.wav" 2>/dev/null)
check "금지어 제안 차단 → 분기 B4, 제안 null" "[ \"\$(jget $OUT/TC8_predict.json \"d['branch']\")\" = B4 ] && [ \"\$(jget $OUT/TC8_predict.json \"d['suggestion']\")\" = None ]"
check "reason_error에 금지어 기록" "grep -q '금지어 포함' $OUT/TC8_predict.json"
check "재시도로 금지어 없는 제안 생성" "python3 -c \"import json,sys;s=json.load(open('$OUT/TC8_retry.json'))['suggestion'];sys.exit(0 if s and not any(w in s for w in ['진단','질병','증상 판별','이상 탐지','치료','처방']) else 1)\""
pause
fi

# ── TC9
if want TC9; then
title "TC9 오래 우는 상황" "30분 안에 3번째 분석 → prolonged_crying=true → 결과 화면 의료기관 안내 카드"
new_device TC9
step "기저귀 기록(첫 사용 아님)"; json '{"type":"diaper"}'; call TC9 event POST /events "${curl_json[@]}"
for i in 1 2 3; do
  step "${i}번째 분석"; predict TC9 "predict_$i" uncomfortable/uncomfortable_0
  echo "  prolonged_crying: $(jget "$LAST" "d['prolonged_crying']")"
done
check "1·2번째 false" "[ \"\$(jget $OUT/TC9_predict_1.json \"d['prolonged_crying']\")\" = False ] && [ \"\$(jget $OUT/TC9_predict_2.json \"d['prolonged_crying']\")\" = False ]"
check "3번째 true → 안내 카드" "[ \"\$(jget $OUT/TC9_predict_3.json \"d['prolonged_crying']\")\" = True ]"
pause
fi

# ── TC7
if want TC7; then
title "TC7 데이터 삭제" "기기 데이터 전체 삭제 → 기록 0건, 녹음 파일 삭제"
DEV=$TC1_DEV
WAVS=$(sqlite3 "$ROOT/crycare.db" "select audio_path from records where device_id='$DEV'")
step "삭제 전 녹음 파일 $(echo "$WAVS" | grep -c .)개"
call TC7 delete DELETE /data; echo "  $(cat "$LAST")"
call TC7 history_after GET /history
check "이력 0건" "[ \"\$(cat $LAST)\" = '[]' ]"
call TC7 consent_after GET /consent
check "동의 철회 (동의 기록 삭제)" "[ \"\$(jget $LAST \"d['agreed']\")\" = False ]"
check "녹음 파일 모두 삭제" "! (for w in $WAVS; do test -e \"\$w\" && echo y; done | grep -q y)"
fi

# 정리: 나머지 테스트 기기 데이터 삭제
for d in $(sqlite3 "$ROOT/crycare.db" "select device_id from consents where device_id like 'tc-%'"); do
  DEV=$d; call CLEANUP delete DELETE /data >/dev/null
  sqlite3 "$ROOT/crycare.db" "delete from consents where device_id='$d'"
done

echo
python3 - "$TIMES" <<'PY'
import csv, sys
rows = [r for r in csv.DictReader(open(sys.argv[1])) if r["request"] == "POST /predict"]
ok = sum(float(r["seconds"]) <= 5 for r in rows)
print(f"/predict {len(rows)}회 · 5초 이내 {ok}/{len(rows)} ({ok/len(rows)*100:.0f}%) · 평균 {sum(float(r['seconds']) for r in rows)/len(rows):.2f}s")
PY
echo "${B}결과: ${G}통과 $PASS${N}${B} / ${R}실패 $FAIL${N}"
echo "${DIM}증거: ${OUT#$ROOT/}${N}"
[ "$FAIL" -eq 0 ]
