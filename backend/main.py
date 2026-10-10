import json
import logging
import os
import time
import uuid
from datetime import timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv

load_dotenv()

import librosa
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import db
from .decision_log import log_analysis, log_retry
from .branch import B4, decide_branch
from .context import build_context, normalize_ts, now_utc, parse_ts
from .features import extract_features
from .model import CLASSES, predict
from .reason import ReasonError, reason
from .warmup import warmup

# 배포 환경에서 바꿀 수 있게 환경변수로 받는다. 기본값은 저장소 data/audio
AUDIO_DIR = Path(os.environ.get("CRYCARE_AUDIO_DIR") or Path(__file__).resolve().parent.parent / "data" / "audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# 스펙 §10.1: 마지막 이용일로부터 1년 보관 후 파기
RETENTION = timedelta(days=365)

# 업로드 제한: 공개 주소(ngrok)로 큰 파일이 들어와 서버가 멈추지 않게 한다
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_AUDIO_SECONDS = 60
AUDIO_SUFFIXES = {".m4a", ".wav", ".aac", ".caf", ".mp4", ".3gp"}

# 오래 우는 상황 안내 (스펙 §10.2 이상 징후 "오래 달래지지 않는 울음"):
# 이 시간 안에 이 횟수 이상 분석하면 결과 화면에 의료기관 안내를 띄운다
PROLONGED_WINDOW = timedelta(minutes=30)
PROLONGED_COUNT = 3

# 공개 URL 비용 상한: 서버 전체 하루(한국 시간) LLM 호출 횟수. 넘으면 분류만 반환하고 B4
LLM_DAILY_LIMIT = int(os.environ.get("CRYCARE_LLM_DAILY_LIMIT", "100"))
KST = timezone(timedelta(hours=9))

logger = logging.getLogger("crycare")

app = FastAPI(title="CryCare API")

# 시연 전용(단일 앱, 인증 없음). §2 범위: 상용 전환 시 재검토.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()
    _purge_expired()
    warmup()


def _purge_device(dev: str) -> tuple[int, int]:
    """기기 데이터 영구 삭제. wav 파일을 먼저 지우고, 하나라도 실패하면 DB는 그대로 두고 오류를 낸다."""
    failed = []
    for path in db.list_audio_paths(dev):
        try:
            Path(path).unlink(missing_ok=True)
        except OSError as e:
            failed.append(f"{Path(path).name}: {e}")
    if failed:
        raise OSError(failed)
    return db.delete_device_data(dev)


def _purge_expired() -> None:
    cutoff = (now_utc() - RETENTION).isoformat()
    for dev in db.inactive_devices(cutoff):
        try:
            _purge_device(dev)
            db.delete_consent(dev)
            logger.info("보관기간 경과 데이터 파기: %s", dev)
        except OSError as e:
            logger.error("보관기간 경과 데이터 파기 실패 %s: %s", dev, e)


def device_id(x_device_id: str = Header(..., min_length=8, max_length=64)) -> str:
    """모든 데이터는 기기 단위로 구분한다. 앱이 최초 실행 시 만든 UUID를 보낸다 (스펙 §5)."""
    return x_device_id.strip()


def consented_device(dev: str = Depends(device_id)) -> str:
    """수집은 최초 실행 동의 후에만 (스펙 §6, FR14). 조회·삭제는 동의 없이도 허용."""
    if db.get_consent(dev) is None:
        raise HTTPException(status_code=403, detail="consent_required")
    return dev


# 기기 시계 오차 허용 범위. 이보다 미래인 케어 기록 시각은 거부한다
FUTURE_TOLERANCE = timedelta(minutes=2)


def _parse_ts_or_400(value: Optional[str]) -> str:
    try:
        ts = normalize_ts(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"occurred_at must be ISO8601: {value}")
    if ts > (now_utc() + FUTURE_TOLERANCE).isoformat():
        raise HTTPException(status_code=400, detail="occurred_at cannot be in the future")
    return ts


@app.get("/")
def health():
    return {"status": "ok", "classes": CLASSES}


class ConsentIn(BaseModel):
    version: str


@app.post("/consent")
def consent(body: ConsentIn, dev: str = Depends(device_id)):
    """최초 실행 동의 기록 (스펙 §8-0, FR14)."""
    db.upsert_consent(dev, normalize_ts(None), body.version)
    return {"ok": True}


@app.get("/consent")
def get_consent(dev: str = Depends(device_id)):
    """앱이 로컬 동의 상태를 서버와 맞춰보기 위한 조회 (서버 DB가 초기화된 경우 등)."""
    row = db.get_consent(dev)
    return {"agreed": row is not None, **(dict(row) if row else {})}


# ---------- 케어 이벤트 ----------

EventType = Literal["feeding", "diaper"]


class EventIn(BaseModel):
    type: EventType
    occurred_at: Optional[str] = None


class EventPatch(BaseModel):
    occurred_at: str


@app.post("/events")
def create_event(event: EventIn, dev: str = Depends(consented_device)):
    event_id = db.insert_event(dev, event.type, _parse_ts_or_400(event.occurred_at))
    return {"id": event_id}


@app.get("/events")
def get_events(limit: int = 20, dev: str = Depends(device_id)):
    return [dict(row) for row in db.list_events(dev, limit)]


@app.patch("/events/{event_id}")
def patch_event(event_id: int, body: EventPatch, dev: str = Depends(consented_device)):
    if not db.update_event(dev, event_id, _parse_ts_or_400(body.occurred_at)):
        raise HTTPException(status_code=404, detail="event not found")
    return {"ok": True}


@app.delete("/events/{event_id}")
def remove_event(event_id: int, dev: str = Depends(device_id)):
    if not db.delete_event(dev, event_id):
        raise HTTPException(status_code=404, detail="event not found")
    return {"ok": True}


@app.get("/context")
def get_context(dev: str = Depends(device_id)):
    """분석(홈) 화면이 녹음 전에 경과시간을 보여주기 위한 조회용 (§8)."""
    return build_context(dev)


# ---------- 분석 ----------

async def _run_reason(classification: dict, context: dict) -> tuple[str, Optional[str], Optional[str]]:
    """분기 판정 + Reason. LLM이 실패하면 B4로 전환한다. -> (branch, suggestion, reason_error)"""
    branch = decide_branch(classification, context)
    if not db.take_llm_quota(now_utc().astimezone(KST).date().isoformat(), LLM_DAILY_LIMIT):
        return B4, None, f"daily_limit: 오늘 제안 생성 한도({LLM_DAILY_LIMIT}회)를 넘었습니다"
    try:
        suggestion = await run_in_threadpool(reason, classification, context, branch)
    except ReasonError as e:
        return B4, None, str(e)
    return branch, suggestion, None


@app.post("/predict")
async def predict_endpoint(
    file: UploadFile = File(...),
    events: Optional[str] = Form(None),
    dev: str = Depends(consented_device),
):
    # 원탭 정정 이벤트(§6, 경로1)가 함께 왔으면 경과시간 계산 전에 먼저 반영
    if events:
        try:
            parsed = [EventIn(**e) for e in json.loads(events)]
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"invalid events: {e}")
        for e in parsed:
            db.insert_event(dev, e.type, _parse_ts_or_400(e.occurred_at))

    suffix = (Path(file.filename or "").suffix or ".m4a").lower()
    if suffix not in AUDIO_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 오디오 형식입니다: {suffix}")
    audio_path = AUDIO_DIR / f"{uuid.uuid4().hex}{suffix}"
    if not _save_upload(file, audio_path):
        raise HTTPException(status_code=413, detail=f"녹음 파일이 너무 큽니다 (최대 {MAX_UPLOAD_BYTES // 1024 // 1024}MB)")

    try:
        duration = await run_in_threadpool(librosa.get_duration, path=str(audio_path))
        if duration > MAX_AUDIO_SECONDS:
            raise HTTPException(status_code=400, detail=f"녹음이 너무 깁니다 (최대 {MAX_AUDIO_SECONDS}초)")
        features = await run_in_threadpool(extract_features, str(audio_path))
    except HTTPException:
        audio_path.unlink(missing_ok=True)
        raise
    except Exception as e:
        audio_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"오디오를 읽을 수 없습니다: {type(e).__name__}")

    context = build_context(dev)
    classification = predict(features)
    started = time.monotonic()
    branch, suggestion, reason_error = await _run_reason(classification, context)

    created_at = normalize_ts(None)
    since = (parse_ts(created_at) - PROLONGED_WINDOW).isoformat()
    prolonged_crying = db.count_records_since(dev, since) + 1 >= PROLONGED_COUNT

    record_id = db.insert_record(
        dev,
        created_at,
        str(audio_path),
        classification["prediction"],
        json.dumps(classification["probabilities"], ensure_ascii=False),
        json.dumps(context, ensure_ascii=False),
        branch,
        suggestion,
    )

    log_analysis(record_id, classification, context, branch, reason_error,
                 time.monotonic() - started, prolonged_crying)

    return {
        "record_id": record_id,
        "prediction": classification["prediction"],
        "probabilities": classification["probabilities"],
        "context": context,
        "branch": branch,
        "suggestion": suggestion,
        "reason_error": reason_error,
        "prolonged_crying": prolonged_crying,
    }


def _save_upload(file: UploadFile, path: Path) -> bool:
    """업로드를 조금씩 저장한다. 크기 제한을 넘으면 지우고 False."""
    size = 0
    with path.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                break
            out.write(chunk)
    if size > MAX_UPLOAD_BYTES:
        path.unlink(missing_ok=True)
        return False
    return True


def _get_record_or_404(dev: str, record_id: int):
    record = db.get_record(dev, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="record not found")
    return record


@app.get("/records/{record_id}")
def get_record(record_id: int, dev: str = Depends(device_id)):
    """이력 상세 (라벨 수정 화면용). 녹음 경로는 내보내지 않는다."""
    record = _get_record_or_404(dev, record_id)
    return {
        "id": record["id"],
        "created_at": record["created_at"],
        "prediction": record["prediction"],
        "probabilities": json.loads(record["probabilities"]),
        "context": json.loads(record["context"]),
        "branch": record["branch"],
        "suggestion": record["suggestion"],
        "actual_label": record["actual_label"],
        "memo": record["memo"],
        "label_updated_at": record["label_updated_at"],
    }


@app.post("/records/{record_id}/reason")
async def retry_reason(record_id: int, dev: str = Depends(consented_device)):
    """제안 재시도 (B4 이후, FR12). 분석 시점 맥락 스냅샷을 그대로 사용한다."""
    record = _get_record_or_404(dev, record_id)
    classification = {
        "prediction": record["prediction"],
        "probabilities": json.loads(record["probabilities"]),
    }
    context = json.loads(record["context"])
    started = time.monotonic()
    branch, suggestion, reason_error = await _run_reason(classification, context)
    db.update_reason(dev, record_id, branch, suggestion)
    log_retry(record_id, branch, reason_error, time.monotonic() - started)
    return {"suggestion": suggestion, "branch": branch, "reason_error": reason_error}


class LabelIn(BaseModel):
    actual_label: str
    memo: Optional[str] = None


# 불확실한 매핑으로 과잉 추론하지 않도록, 확실한 것만 등록 (§6)
LABEL_TO_EVENT = {"hungry": "feeding"}


@app.post("/records/{record_id}/label")
def label_record(record_id: int, body: LabelIn, dev: str = Depends(consented_device)):
    """피드백 라벨 입력·수정(덮어쓰기). 자동 이벤트도 함께 정합 처리 (FR6, FR11)."""
    if body.actual_label not in CLASSES:
        raise HTTPException(status_code=400, detail=f"actual_label must be one of {CLASSES}")
    ok = db.set_label(
        dev,
        record_id,
        body.actual_label,
        body.memo,
        normalize_ts(None),
        LABEL_TO_EVENT.get(body.actual_label),
    )
    if not ok:
        raise HTTPException(status_code=404, detail="record not found")
    return {"ok": True}


@app.get("/history")
def history(limit: int = 20, dev: str = Depends(device_id)):
    return [dict(row) for row in db.list_history(dev, limit)]


@app.delete("/data")
def delete_data(dev: str = Depends(device_id)):
    """기기 데이터 전체 삭제 (FR13) = 동의 철회. 동의 기록도 기기 식별자를 담고 있으므로 함께 지운다.
    wav 삭제에 실패하면 DB는 그대로 두고 오류를 낸다."""
    try:
        deleted_records, deleted_events = _purge_device(dev)
    except OSError as e:
        raise HTTPException(status_code=500, detail={"audio_delete_failed": e.args[0]})
    db.delete_consent(dev)
    return {"deleted_records": deleted_records, "deleted_events": deleted_events}
