"""TC8 금지어 차단: LLM 출력에 금지어가 섞이면 내보내지 않고 B4 → 재시도로 정상 제안.

실제 LLM이 금지어를 쓰게 만들 수는 없으므로, 첫 호출의 LLM 응답만 금지어가 섞인 문장으로
바꿔치기한다(서버 코드는 그대로). 재시도는 실제 LLM을 호출한다. 앱과 같은 API 경로를 그대로 탄다.
사용: venv/bin/python scripts/tc_banned.py <증거 폴더> <wav 경로>   (scripts/tc_api.sh가 호출)
"""
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402

from backend import reason  # noqa: E402
from backend.main import app  # noqa: E402

out, wav = Path(sys.argv[1]), sys.argv[2]
FAKE = "기록상 졸린 신호로 보입니다. 다만 질병이 의심되면 진단을 받아보세요.\ntop_action: sleepy"
headers = {"X-Device-Id": f"tc-TC8-{uuid.uuid4().hex[:8]}"}


def call(name, method, path, **kw):
    t = time.time()
    r = client.request(method, path, headers=headers, **kw)
    secs = time.time() - t
    (out / f"TC8_{name}.json").write_text(json.dumps(r.json(), ensure_ascii=False, indent=2))
    with (out / "timings.csv").open("a") as f:
        f.write(f"TC8,{method} {path},{r.status_code},{secs:.6f}\n")
    print(f"  {method} {path} → {r.status_code} ({secs:.2f}s)")
    return r.json()


with TestClient(app) as client:
    call("consent", "POST", "/consent", json={"version": "v4"})

    real = reason._call_llm
    reason._call_llm = lambda prompt: FAKE  # 첫 응답만 금지어가 섞인 문장으로
    print(f"  (테스트용 LLM 응답: {FAKE.splitlines()[0]})")
    with open(wav, "rb") as f:
        d = call("predict", "POST", "/predict", files={"file": (Path(wav).name, f, "audio/wav")})
    print(f"  분기: {d['branch']}  제안: {d['suggestion']}  reason_error: {d['reason_error']}")

    reason._call_llm = real  # 재시도는 실제 LLM
    d = call("retry", "POST", f"/records/{d['record_id']}/reason")
    print(f"  재시도 분기: {d['branch']}  제안: {(d['suggestion'] or '').splitlines()[0] if d['suggestion'] else None}")
