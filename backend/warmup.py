"""librosa(numba)는 처음 호출할 때 컴파일하느라 느리다. 짧은 합성 신호로 특징추출·예측을 한 번 돌려
첫 분석 요청이 그 시간을 떠안지 않게 한다. Docker 빌드 때도 실행해 numba 캐시를 이미지에 남긴다.
사용: python -m backend.warmup"""
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from .features import SR, extract_features
from .model import predict


def warmup() -> None:
    t = np.arange(SR) / SR
    sig = 0.3 * np.sin(2 * np.pi * 440 * t) * (1 + 0.5 * np.sin(2 * np.pi * 3 * t))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "warmup.wav"
        sf.write(path, sig.astype(np.float32), SR)
        predict(extract_features(str(path)))


if __name__ == "__main__":
    warmup()
    print("warmup ok")
