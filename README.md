# CryCare

신생아 울음소리를 5가지 니즈로 분류하고, 수유·기저귀 기록과 피드백 이력을 함께 따져 **무엇을 먼저 시도할지** 제안하는 육아 보조 AI Agent입니다.

> CryCare는 육아를 돕는 참고용 도구이며 의료기기가 아닙니다. 질병의 진단·치료·예방 목적으로 사용할 수 없습니다.
> 평소와 다르게 오래 달래지지 않는 울음, 발열(특히 생후 3개월 미만 38℃ 이상), 처지거나 깨우기 어려움, 호흡 곤란·입술이 파래짐, 반복 구토, 수유 거부가 있으면 앱 결과와 관계없이 즉시 의료기관 진료를 받으세요(응급 시 119).

## 설치·실행 방법

설치 파일과 서버가 준비돼 있어 Android 폰에 APK만 설치하면 바로 쓸 수 있습니다(iOS 미지원).

| 항목 | 내용 |
|---|---|
| APK | https://expo.dev/artifacts/eas/njdDGu67J5KrQOiaJBZYz8YfHZBDOo_hG7gGZoDdDzU.apk (약 106MB, v1.0.0) |
| 서버 | https://crycare-api-631565758538.asia-northeast3.run.app (Google Cloud Run 서울 리전, 상태 확인: 주소를 브라우저로 열면 `{"status":"ok",...}`) |

1. Android 폰에서 위 APK 링크를 열어 내려받습니다.
2. 설치할 때 "출처를 알 수 없는 앱" 경고가 나오면 **설정 → 이 출처 허용**을 켭니다(브라우저·파일 앱 등 내려받은 앱 기준).
3. 앱을 열어 안내를 읽고 동의합니다. 마이크 권한을 허용합니다.
4. 분석 탭에서 녹음 버튼을 눌러 울음소리를 녹음하고, 멈춘 뒤 [분석]을 누릅니다. 결과 화면에서 "실제 니즈는?" 피드백을 남기면 다음 분석에 반영됩니다.

**참고**
- **첫 요청은 느릴 수 있습니다.** 서버는 요청이 없으면 꺼져 있다가 첫 요청 때 켜집니다(무료 운영, 켜지는 데 약 30초). 앱을 열면 서버를 먼저 깨우므로, 앱을 연 뒤 잠시 후 녹음하면 대부분 기다리지 않습니다. 이후에는 5초 안에 결과가 나옵니다.
- **녹음 팁**: 조용한 곳에서 폰 마이크를 아기(또는 재생 스피커) 가까이 두고, 울음이 그치면 바로 정지하세요. 주변 소음이 크면 정확도가 떨어집니다.
- **기록 초기화**: 서버는 재시작·재배포되면 저장된 기록(동의·이력·녹음)이 지워집니다. 이때 앱은 동의 화면을 다시 보여 주며, 다시 동의하면 그대로 이용할 수 있습니다.
- **제안 생성 한도**: 비용 보호를 위해 대응 제안(LLM)은 서버 전체 하루 100회까지 만듭니다. 넘으면 분류 결과만 표시되고 제안 자리에 "다시 시도"가 뜹니다(한국 시간 자정에 초기화).

## 동작 방식

```
앱 녹음 ──▶ 음향 특징 45개 ──▶ SVM 5클래스 분류 ──▶ 판단 분기(코드 규칙) ──▶ 대응 제안(LLM) ──▶ 결과·피드백
                                                  ▲
                         수유·기저귀 경과시간 + 최근 피드백 이력 (서버가 계산)
```

- **시스템 구성**: Android APK ↔ Google Cloud Run 서울 리전(FastAPI 컨테이너) ↔ Anthropic API. 로컬 개발은 맥북 + ngrok.
- **분류**: awake(깨어있음) · hug(안아달라) · hungry(배고픔) · sleepy(졸림) · uncomfortable(불편함)
- **판단 분기**: 분기는 LLM이 아니라 코드 규칙(`backend/branch.py`)이 정하고, LLM은 분기에 맞는 문장만 만듭니다.

| 분기 | 조건 | 앱 표시 | 제안 |
|---|---|---|---|
| B1 확신 | 1순위 확률 ≥ 0.5, 기록과 상충 없음 | 3단계 · 근거 일치 | 1순위 니즈 중심 단일 제안 |
| B2 불확실 | 1순위 < 0.5, 또는 기록과 상충(예: 2시간 내 수유했는데 hungry) | 2단계 · 확실하지 않음 | 시도 순서 2~3개 |
| B3 첫 사용 | 수유·기저귀·피드백 기록 없음 | 1단계 · 기록 부족 | 기본 확인 순서 + 기록 유도 |
| B4 제안 실패 | LLM 오류·타임아웃(8초)·금지어 포함·하루 호출 한도(100회) 초과 | 제안 없음 | 분류 결과만 표시, 다시 시도 |

- **Memory**: 피드백("실제로는 무엇이었나요?")으로 남긴 예측 vs 실제 이력을 다음 분석의 맥락에 넣습니다. `hungry` 피드백은 수유 기록을 자동으로 추가합니다.
- **안전 대책**: LLM 출력 금지어 검사(→ B4), 30분 안에 3번 이상 분석하면 의료기관 안내 카드, 업로드 10MB·60초 제한, 서버 전체 LLM 하루 100회 한도.

## 모델

| 항목 | 내용 |
|---|---|
| 특징 | 16kHz, 앞뒤 무음 제거 후 ZCR·RMS·스펙트럼 5종·MFCC 13×(평균·표준편차)·Chroma 12 = 45차원 (`backend/features.py`) |
| 파이프라인 | StandardScaler → PCA(95%) → SVM(RBF, C=5, γ=0.1) |
| 성능 | Nested CV 정확도 0.698 ± 0.055 |
| 데이터 | BabyCry-C5_160 — babycry (Kaggle, chris0223, https://www.kaggle.com/datasets/chris0223/babycry) 기반, 5클래스 784개 |

스펙트로그램+CNN은 0.59에서 정체해, 데이터 규모에 맞는 음향 특징+SVM을 택했습니다. 데이터셋의 샘플레이트가 클래스마다 달라(uncomfortable의 65%가 44.1kHz) 모델이 고음역 유무를 단서로 쓰는 편향을 확인했고, 16kHz로 통일해 줄였습니다(`scripts/analysis/`).

**모델 파일(`crycare_final.pkl`)은 공개 저장소에 포함하지 않습니다.** 실행하려면 저장소 루트에 두어야 합니다.

## 실행 방법

### 준비물
- Python 3.9+, Node.js 20+, FFmpeg(권장: m4a 녹음 디코딩)
- Anthropic API 키
- 휴대폰에 Expo Go 앱
- (외부 공개 시) ngrok 계정

### 1. 백엔드

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env            # ANTHROPIC_API_KEY 입력
# crycare_final.pkl 을 저장소 루트에 둔다
scripts/backend.sh              # http://localhost:8000 (8000번을 쓰던 이전 서버는 종료 후 재실행)
```

`curl localhost:8000/` 이 `{"status":"ok", ...}` 를 돌려주면 정상입니다.

### 2. 앱

```bash
cd mobile
npm install
cp .env.example .env            # EXPO_PUBLIC_API_URL=http://<맥북 LAN IP>:8000
npx expo start
```

휴대폰의 Expo Go로 QR 코드를 스캔합니다(같은 Wi-Fi).

### 3. 외부 공개 (다른 네트워크의 휴대폰에서 쓸 때)

```bash
ngrok config add-authtoken <토큰>
scripts/tunnel.sh                       # ngrok 주소를 mobile/.env 에 넣고, 종료하면 되돌림
cd mobile && npx expo start --tunnel -c
```

첫 분석이 가장 느리므로 시연 전에 한 번 분석해 두세요.

### 4. 클라우드 배포 (Google Cloud Run 서울)

`Dockerfile`로 이미지를 만듭니다(Python 3.9, FFmpeg, requirements 고정 버전). 모델 파일은 이미지에만 들어가고 git에는 올리지 않으며, `.gcloudignore`가 업로드 목록에 `crycare_final.pkl`을 포함시킵니다.

```bash
docker build -t crycare-backend . && docker run -p 8080:8080 --env-file .env crycare-backend   # 로컬 확인(선택)

gcloud run deploy crycare-api --source . --region asia-northeast3 \
  --memory 2Gi --cpu 1 --min-instances 0 --max-instances 1 --concurrency 8 --timeout 60 --cpu-boost \
  --allow-unauthenticated --set-secrets ANTHROPIC_API_KEY=anthropic-api-key:latest
```

- API 키는 Secret Manager(`anthropic-api-key`)에만 둡니다.
- 인스턴스는 1개로 고정합니다(SQLite가 인스턴스마다 따로 생기지 않게).
- **Cloud Run 디스크는 재시작·재배포 때 초기화됩니다.** DB와 녹음은 컨테이너 안(`CRYCARE_DB_PATH`, `CRYCARE_AUDIO_DIR`로 변경 가능)에 저장되므로 그때 지워집니다.
- 비용 보호: 예산(₩5,000)을 넘으면 `infra/budget_killswitch/` 함수가 프로젝트 결제를 해제해 서비스를 멈춥니다.

### 5. Android APK (EAS Build)

```bash
cd mobile
npx eas-cli@latest build -p android --profile preview   # eas.json의 preview: APK, 서버 주소 = 배포 URL
```

## API

모든 요청에 헤더 `X-Device-Id`(앱이 최초 실행 시 만든 UUID)를 붙입니다. 데이터는 기기 단위로만 조회·수정·삭제되며, 수집·수정 요청은 동의 기록이 없으면 403입니다.

| 메서드·경로 | 설명 |
|---|---|
| `GET /` | 헬스체크 |
| `POST /consent` · `GET /consent` | 동의 기록·확인 |
| `POST /predict` | 녹음 분석: 분류 + 분기 + 제안 + 저장 |
| `POST /records/{id}/reason` | 제안 다시 시도(B4 이후) |
| `POST /records/{id}/label` | 피드백(실제 니즈) 입력·수정 |
| `GET /records/{id}` · `GET /history` | 기록 상세·이력 |
| `GET /context` | 현재 경과시간·피드백 요약 |
| `POST /events` · `GET /events` · `PATCH /events/{id}` · `DELETE /events/{id}` | 수유·기저귀 기록 |
| `DELETE /data` | 기기 데이터 전체 삭제(녹음 파일 포함) |

## 테스트

```bash
scripts/tc_api.sh                       # 테스트 케이스 실행, 증거(JSON·응답시간)를 evidence/tc/ 에 저장
ONLY="TC1 TC5" PAUSE=0 scripts/tc_api.sh
```

| TC | 시나리오 | 확인 내용 |
|---|---|---|
| TC1 | 맥락 보정 | hungry + 90분 전 수유 → B2 |
| TC2 | 불확실 안내 | 실제 폰 녹음(1순위 < 0.5) → B2 + 시도 순서 |
| TC3 | 첫 사용자 | 기록 없음 → B3 |
| TC4 | 피드백 수정 | hungry → awake 수정 시 자동 수유 기록 삭제 |
| TC5 | 피드백 맥락 반영 | 예측=실제 이력 2건 → 맥락 포함, B1 |
| TC6 | LLM 오류 복구 | 잘못된 키 → B4 → 재시도 성공 |
| TC7 | 데이터 삭제 | 이력 0건, 녹음 파일 삭제 |
| TC8 | 금지어 차단 | 금지어 섞인 LLM 응답 → B4 → 재시도 |
| TC9 | 오래 우는 상황 | 30분 내 3번째 분석 → 안내 카드 |

TC1~TC9 모두 `scripts/tc_api.sh`로 실행합니다. TC2는 `evidence/` 의 실제 폰 녹음 파일을 써서, 그 파일이 없는 환경에서는 `PHONE_SAMPLE` 로 다른 녹음을 지정해야 합니다.

## 개인정보

- 최초 실행 시 보호자(법정대리인) 동의 후에만 수집합니다. 이름·연락처는 받지 않고 무작위 기기 UUID로만 구분합니다.
- 수집: 울음 녹음, 분석 결과, 수유·기저귀 시각, 피드백. 녹음은 서버 디스크에만 저장합니다.
- 처리 위탁: 서버는 Google Cloud(서울 리전)에서 운영하며, 녹음과 기록은 그 서버에 보관됩니다.
- 제안 생성을 위해 분석 결과(확률)·경과시간·피드백 요약을 Anthropic API로 보냅니다. 녹음 파일과 기기 UUID는 보내지 않습니다.
- 보관: 마지막 이용일로부터 1년(서버 시작 시 지난 데이터 파기). 앱 About 탭의 "내 데이터 전체 삭제"로 즉시 삭제할 수 있습니다.

## 구조

```
backend/        FastAPI 서버
  main.py         API, 업로드 제한, 오래 우는 상황 판정
  features.py     45차원 특징추출 (학습 코드와 동일)
  model.py        pkl 로드·예측 (학습 SR과 다르면 시작 차단)
  branch.py       판단 분기 B1~B3 규칙
  context.py      경과시간·피드백 이력 맥락
  reason.py       LLM 제안 생성 (교체 가능한 _call_llm), 금지어 검사
  db.py           SQLite (기록·케어 이벤트·동의·LLM 하루 호출 수)
  warmup.py       시작 시 특징추출·예측 1회 (첫 분석 지연 완화)
mobile/         React Native(Expo) 앱: 동의 · 분석 · 결과 · 이력 · About (eas.json: APK 빌드)
infra/          budget_killswitch: 예산 초과 시 결제 해제 함수 (Cloud Functions)
Dockerfile      Cloud Run용 백엔드 이미지
scripts/        실행(backend.sh, tunnel.sh), 테스트(tc_api.sh), 분석(analysis/), 시연 촬영
```

## 출처

| 구분 | 항목 |
|---|---|
| 생성형 AI | Claude Haiku 4.5(서비스 내 대응 제안), Claude Code(개발 보조) |
| 데이터 | babycry (Kaggle, chris0223, https://www.kaggle.com/datasets/chris0223/babycry). 라이선스가 명시되지 않아 연구·비상업 목적으로만 사용하며, 데이터는 이 저장소에 포함하지 않습니다. |
| 오픈소스 | librosa, scikit-learn, NumPy, SciPy, soundfile, joblib, FastAPI, uvicorn, python-dotenv, anthropic SDK, SQLite, React Native, Expo, Expo Router, expo-audio, Docker, FFmpeg |
| 외부 서비스 | Anthropic API, Google Cloud(Cloud Run·Cloud Build·Secret Manager·Cloud Functions), Expo EAS Build, ngrok, Google Colab(학습) |
