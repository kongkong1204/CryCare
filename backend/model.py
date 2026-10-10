"""crycare_final.pkl 로드 및 예측. 파이프라인(StandardScaler->PCA->SVM) 전체가 저장돼 있어
45차원 특징만 넣으면 바로 예측된다 (스펙 §9)."""
from pathlib import Path

import joblib

from .features import SR

_MODEL_PATH = Path(__file__).resolve().parent.parent / "crycare_final.pkl"
_bundle = joblib.load(_MODEL_PATH)
_pipeline = _bundle["model"]
CLASSES = _bundle["classes"]
NESTED_CV_ACC = _bundle.get("nested_cv_acc")

# 학습 때 샘플레이트와 특징추출이 다르면 조용히 틀린 예측을 내므로 시작할 때 막는다 (스펙 §9)
if _bundle.get("sr", 22050) != SR:
    raise RuntimeError(f"모델 학습 샘플레이트({_bundle.get('sr', 22050)})와 특징추출 SR({SR})이 다릅니다")


def predict(features) -> dict:
    probs = _pipeline.predict_proba(features)[0]
    ranked = sorted(zip(CLASSES, probs), key=lambda x: x[1], reverse=True)
    return {
        "prediction": ranked[0][0],
        "probabilities": [
            {"label": label, "prob": round(float(p), 4)} for label, p in ranked
        ],
    }
