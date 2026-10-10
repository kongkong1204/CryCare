"""Agent 판단 과정 로그. 분석·재시도마다 서버 터미널에 소리 → 기록 → 판단 → 분기 → 제안 순으로 찍는다.
시연에서 앱 화면 옆에 띄워 판단 근거를 보여주는 용도 (스펙 §3.1).
"""
from __future__ import annotations

import logging
import sys

from .branch import B1, B2, B3, B4, conflicts, decide_branch, is_cold_start, is_low_confidence, top_prob
from .context import display_items

_SHORT = {"마지막 수유": "수유", "마지막 기저귀": "기저귀", "최근 피드백": "피드백"}
BRANCH_NAMES = {B1: "확신", B2: "불확실", B3: "첫 사용", B4: "제안 실패"}

_COLOR = sys.stderr.isatty()
_BRANCH_COLORS = {B1: "32", B2: "33", B3: "36", B4: "31"}

logger = logging.getLogger("crycare.decision")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def _branch_label(branch: str) -> str:
    return _c(f"[{BRANCH_NAMES[branch]}] {branch}", "1;" + _BRANCH_COLORS[branch])


def _reasons(classification: dict, context: dict) -> list[str]:
    """decide_branch와 같은 규칙으로, 그 분기가 나온 이유를 문장으로."""
    if is_cold_start(context):
        reasons = ["수유·기저귀·피드백 기록 없음 → 첫 사용 경로"]
        if is_low_confidence(classification):
            reasons.append(f"1순위 확률 {top_prob(classification):.2f} < 0.5 (불확실도 함께 안내)")
        return reasons
    reasons = []
    if is_low_confidence(classification):
        reasons.append(f"1순위 확률 {top_prob(classification):.2f} < 0.5")
    reasons += [f"{r} → 상충" for r in conflicts(classification, context)]
    return reasons or [f"1순위 확률 {top_prob(classification):.2f} ≥ 0.5, 기록과 상충 없음"]


def _suggestion_line(reason_error: str | None, secs: float) -> str:
    if reason_error:
        return _c(f"실패 ({reason_error[:80]}) → 분류 결과만 반환, 앱에 [다시 시도]", "31")
    return f"생성 {secs:.2f}s"


def log_analysis(record_id: int, classification: dict, context: dict, branch: str,
                 reason_error: str | None, reason_secs: float, prolonged: bool) -> None:
    probs = " · ".join(f"{p['label']} {p['prob']:.2f}" for p in classification["probabilities"][:3])
    record = " · ".join(f"{_SHORT.get(k, k)} {v.removeprefix('최근 피드백 ')}"
                        for k, v in display_items(context).items())
    decided = decide_branch(classification, context)
    lines = [
        _c(f"━━ 분석 #{record_id} " + "━" * 30, "1"),
        f"  소리  {probs}",
        f"  기록  {record}",
        *(f"  판단  {r}" for r in _reasons(classification, context)),
        f"  분기  {_branch_label(decided)}",
        f"  제안  {_suggestion_line(reason_error, reason_secs)}",
    ]
    if branch == B4:  # LLM이 실패하면 규칙 분기 대신 B4로 내려간다
        lines.append(f"  분기  → {_branch_label(B4)}")
    if prolonged:
        lines.append("  안전  " + _c("30분 안에 3번째 분석 → 의료기관·119 안내 카드", "1;31"))
    logger.info("\n".join(lines))


def log_retry(record_id: int, branch: str, reason_error: str | None, secs: float) -> None:
    logger.info("\n".join([
        _c(f"━━ 제안 다시 시도 #{record_id} " + "━" * 22, "1"),
        f"  분기  {_branch_label(branch)}",
        f"  제안  {_suggestion_line(reason_error, secs)}",
    ]))
