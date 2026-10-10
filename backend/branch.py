"""Agent 판단 분기 (스펙 §3.1). 분기 판정은 코드(규칙)에서 하고 LLM에 맡기지 않는다.
B4(LLM 실패)는 여기서가 아니라 Reason 호출의 예외 처리에서 정해진다.
우선순위: B4 > B3 > B2 > B1.
"""
from __future__ import annotations

LOW_CONFIDENCE_THRESHOLD = 0.5
# hungry 1순위인데 최근 2시간 안에 수유 기록이 있으면 맥락 상충 (수유 간격 2~3시간 기준)
RECENT_FEEDING_MINUTES = 120
# 최근 피드백에서 같은 1순위 예측이 이 횟수 이상, 과반 틀렸으면 맥락 상충
FEEDBACK_MISMATCH_MIN = 2

B1, B2, B3, B4 = "B1", "B2", "B3", "B4"


def top_prob(classification: dict) -> float:
    top = classification["prediction"]
    return next(p["prob"] for p in classification["probabilities"] if p["label"] == top)


def is_low_confidence(classification: dict) -> bool:
    return top_prob(classification) < LOW_CONFIDENCE_THRESHOLD


def is_cold_start(context: dict) -> bool:
    facts = context["facts"]
    return (
        facts["feeding_minutes"] is None
        and facts["diaper_minutes"] is None
        and not facts["feedback"]
    )


def conflicts(classification: dict, context: dict) -> list[str]:
    """분류 결과와 상황 맥락이 상충하는 이유 목록 (프롬프트에도 그대로 전달)."""
    facts = context["facts"]
    top = classification["prediction"]
    reasons = []

    feeding = facts["feeding_minutes"]
    if top == "hungry" and feeding is not None and feeding < RECENT_FEEDING_MINUTES:
        reasons.append(f"1순위가 hungry인데 기록상 {feeding}분 전에 수유함")

    same_top = [f for f in facts["feedback"] if f["prediction"] == top]
    wrong = [f for f in same_top if f["actual_label"] != top]
    if len(wrong) >= FEEDBACK_MISMATCH_MIN and len(wrong) * 2 > len(same_top):
        actuals = ", ".join(sorted({f["actual_label"] for f in wrong}))
        reasons.append(
            f"최근 피드백에서 {top} 예측 {len(same_top)}건 중 {len(wrong)}건이 실제로는 {actuals}"
        )
    return reasons


def decide_branch(classification: dict, context: dict) -> str:
    """-> "B1" | "B2" | "B3". B3와 B2가 겹치면 B3 (문구에 불확실 표기 포함은 Reason이 처리)."""
    if is_cold_start(context):
        return B3
    if is_low_confidence(classification) or conflicts(classification, context):
        return B2
    return B1
