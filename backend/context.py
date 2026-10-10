"""상황 맥락 스냅샷 (스펙 §6). 경과시간(U1=방식c)과 최근 피드백 이력(FR9)을 서버가 계산한다.
기기 시간대 꼬임을 막기 위해 시각은 모두 UTC ISO8601로 저장·비교한다.
SVM 입력이 아니라 Reason의 맥락 입력일 뿐이다.

반환 dict 중 문자열 값은 앱·프롬프트에 그대로 보여주는 표시용이고,
"facts"는 분기 판정(decide_branch)용 구조화 값이다. 둘 다 records.context에 함께 저장해
재시도(B4 이후) 때 분석 시점 맥락을 그대로 재사용한다.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from . import db

EVENT_LABELS = {"feeding": "마지막 수유", "diaper": "마지막 기저귀"}
FEEDBACK_KEY = "최근 피드백"
FEEDBACK_WINDOW = 5


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: str) -> datetime:
    ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def normalize_ts(value: str | None) -> str:
    """입력 시각을 UTC ISO8601로 통일 (문자열 정렬 = 시간 정렬이 되도록)."""
    ts = parse_ts(value) if value else now_utc()
    return ts.astimezone(timezone.utc).isoformat()


def _format_elapsed(minutes: int) -> str:
    if minutes < 1:
        return "방금"
    if minutes < 60:
        return f"{minutes}분 전"
    hours, rem = divmod(minutes, 60)
    return f"{hours}시간 {rem}분 전" if rem else f"{hours}시간 전"


def _summarize_feedback(feedback: list[dict]) -> str:
    if not feedback:
        return "기록 없음"
    mismatches = Counter(
        (f["prediction"], f["actual_label"]) for f in feedback if f["prediction"] != f["actual_label"]
    )
    total = len(feedback)
    if not mismatches:
        return f"최근 피드백 {total}건 모두 예측과 실제가 일치"
    details = ", ".join(f"{pred}로 예측 → 실제 {actual} {n}건" for (pred, actual), n in mismatches.most_common())
    return f"최근 피드백 {total}건 중 {sum(mismatches.values())}건 불일치 ({details})"


def build_context(device_id: str, now: datetime | None = None) -> dict:
    now = now or now_utc()
    context: dict = {}
    facts: dict = {}
    for event_type, label in EVENT_LABELS.items():
        occurred_at = db.latest_event(device_id, event_type)
        if occurred_at:
            minutes = max(int((now - parse_ts(occurred_at)).total_seconds() // 60), 0)
            context[label] = _format_elapsed(minutes)
        else:
            minutes = None
            context[label] = "기록 없음"
        facts[f"{event_type}_minutes"] = minutes

    feedback = [
        {"prediction": row["prediction"], "actual_label": row["actual_label"]}
        for row in db.recent_feedback(device_id, FEEDBACK_WINDOW)
    ]
    context[FEEDBACK_KEY] = _summarize_feedback(feedback)
    facts["feedback"] = feedback

    context["facts"] = facts
    return context


def display_items(context: dict) -> dict[str, str]:
    """앱·프롬프트 표시용 항목만 (facts 제외)."""
    return {k: v for k, v in context.items() if isinstance(v, str)}
