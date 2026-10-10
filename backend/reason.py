"""LLM Reason 단계. (분류결과, 상황맥락, 분기) -> 대응 제안 텍스트.

교체 가능 구조 (스펙 §7 필수): reason() 시그니처를 고정하고 LLM 호출은
_call_llm() 안에만 둔다. Ollama 등 로컬 LLM으로 전환할 때 _call_llm 내부만
바꾸면 되고, 나머지 코드/앱은 불변이다.
LLM 실패·타임아웃은 ReasonError로 올려 호출부가 B4로 전환한다 (스펙 §3.1, FR12).
"""
from __future__ import annotations

import os
import re

from anthropic import Anthropic

from .branch import B1, B2, B3, conflicts, is_low_confidence
from .context import display_items
from .model import CLASSES

MODEL_ID = "claude-haiku-4-5-20251001"
# 녹음 종료 -> 결과 5초 목표 (스펙 NFR). 넘기면 B4로 전환하고 재시도 버튼에 맡긴다.
LLM_TIMEOUT_SECONDS = 8.0

# 스펙 §10.2 금지어
BANNED_WORDS = ["진단", "질병", "증상 판별", "이상 탐지", "치료", "처방"]

# LLM이 **top_action: x** 처럼 꾸며 써도 잡히도록 장식 문자를 허용
_TOP_ACTION_RE = re.compile(r"^[\s*`_-]*top_action\s*:\s*[*`_]*(\w+)[\s*`_]*$", re.MULTILINE)
_TRAILING_RULE_RE = re.compile(r"(\n\s*[-*_]{3,}\s*)+$")
_BRANCH_TAG_RE = re.compile(r"^\s*\[B\d[^\]]*\]\s*")

_client: Anthropic | None = None


class ReasonError(Exception):
    """Reason 실패 (API 오류·타임아웃·키 없음 등). 호출부에서 B4로 처리한다."""


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            timeout=LLM_TIMEOUT_SECONDS,
            max_retries=0,
        )
    return _client


def _call_llm(prompt: str) -> str:
    """LLM 호출부. 로컬 LLM 전환 시 이 함수 내부만 교체한다."""
    try:
        response = _get_client().messages.create(
            model=MODEL_ID,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:  # 어떤 실패든 B4로 (엔드포인트가 500으로 죽지 않게)
        raise ReasonError(f"{type(e).__name__}: {e}") from e


_BRANCH_GUIDE = {
    B1: "- 소리 분석과 기록이 같은 쪽을 가리킨다. 1순위 니즈를 중심으로 바로 시도할 대응 하나를 구체적으로 제안하되 단정하지 마라.",
    B2: (
        "- 소리나 기록만으로는 단정하기 어렵다. 단정하지 말고 시도할 순서 2~3개를 번호 목록으로 제시하라.\n"
        "- 맥락상 가능성이 높은 것부터 순서를 정하라."
    ),
    B3: (
        "- 수유·기저귀 기록과 피드백 이력이 아직 없다. 단정하지 말고 보수적으로 안내하라.\n"
        "- 기본 확인 순서(예: 기저귀 → 수유 → 안아서 달래기)를 짧게 제시하라.\n"
        "- 마지막에 앱의 \"방금 수유함 / 방금 기저귀\" 버튼으로 기록하면 다음 제안이 더 정확해진다고 안내하라."
    ),
}


def _build_prompt(classification: dict, context: dict, branch: str) -> str:
    prob_lines = "\n".join(f"- {p['label']}: {p['prob']:.2f}" for p in classification["probabilities"])
    context_lines = "\n".join(f"- {k}: {v}" for k, v in display_items(context).items())

    guide = [_BRANCH_GUIDE[branch]]
    if branch == B3 and is_low_confidence(classification):
        guide.append("- 1순위 확률도 0.5 미만이다. 한 가지 원인으로 좁히지 마라.")
    conflict_reasons = conflicts(classification, context)
    if conflict_reasons:
        guide.append("- 분류 결과와 맥락이 상충한다. 맥락을 우선해 순서를 조정하라:\n"
                     + "\n".join(f"  · {r}" for r in conflict_reasons))

    return f"""너는 신생아 울음소리 분석 결과를 해석해 초보 양육자에게 대응을 제안하는 육아 보조 AI다.
의료기기가 아니며, 참고용 제안만 한다.

[음향 모델 분류 결과] (소리만으로 추정한 확률일 뿐 확정이 아님)
{prob_lines}

[상황 맥락] (서버가 기록으로 계산. "기록 없음"은 기록되지 않았다는 뜻이지 안 했다는 뜻이 아님)
{context_lines}

[이번 응답 방식]
{chr(10).join(guide)}

[공통 규칙]
- 맥락은 "기록상"을 전제로 방어적으로 서술하라. 최근 피드백은 경향으로만 참고하고 단정하지 마라.
- 다음 단어는 절대 쓰지 마라: {", ".join(BANNED_WORDS)}.
- 건강 이상 신호(체온·발진·구토 등)나 의료 상담 권유는 쓰지 마라. 앱 하단 고정 안내 문구가 따로 담당한다.
- 한국어로 2~4문장(번호 목록 포함), 전체 250자 이내. 양육자가 바로 시도할 수 있게 구체적으로.
- 확신 정도를 나타내는 표기(단계, 등급, [B1] 같은 꼬리표)는 쓰지 마라. 앱이 따로 표시한다.
- 앱에 평문으로 표시된다. 제목·굵게·구분선 등 마크다운(#, **, ---)을 쓰지 마라.
- 마지막 줄에 가장 먼저 시도하길 권한 니즈를 다음 형식으로 따로 적어라(앱에는 표시되지 않음):
top_action: <{"|".join(CLASSES)} 중 하나>
"""


def reason_detail(classification: dict, context: dict, branch: str) -> dict:
    """-> {"suggestion": str, "top_action": str | None}. top_action은 맥락 보정 측정용 (스펙 §11.2)."""
    text = _call_llm(_build_prompt(classification, context, branch))
    match = _TOP_ACTION_RE.search(text)
    top_action = match.group(1) if match and match.group(1) in CLASSES else None
    suggestion = _TOP_ACTION_RE.sub("", text).strip()
    suggestion = _TRAILING_RULE_RE.sub("", _BRANCH_TAG_RE.sub("", suggestion)).strip()
    # 프롬프트 지시만 믿지 않고 출력도 검사한다. 금지어가 섞이면 내보내지 않고 B4(재시도)로 (스펙 §10.2)
    banned = [w for w in BANNED_WORDS if w in suggestion]
    if banned:
        raise ReasonError(f"금지어 포함: {', '.join(banned)}")
    return {"suggestion": suggestion, "top_action": top_action}


def reason(classification: dict, context: dict, branch: str) -> str:
    """(분류결과, 상황맥락, 분기) -> 대응 제안 텍스트. 이 시그니처는 고정."""
    return reason_detail(classification, context, branch)["suggestion"]
