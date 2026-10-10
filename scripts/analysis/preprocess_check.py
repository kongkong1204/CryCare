"""[10/3 결과는 v1 모델(22050Hz) 기준. 지금은 backend 특징추출(v2, 16kHz)로 돌아간다]
앱 녹음 전처리(잡음 제거 → 무음 제거 → 음량 정규화)가 정확도를 회복시키는지 점검.

format_check.py와 같은 out-of-fold 설정. 모델은 원본 특징으로 학습하고(= 현재 pkl과 동일 조건),
테스트 오디오에만 열화 조건과 전처리를 적용한다.
  raw    전처리 없음
  norm   음량 정규화만
  edge   잡음 제거 + 앞뒤 무음 제거 + 음량 정규화
  split  잡음 제거 + 중간 무음까지 제거 + 음량 정규화
사용: venv/bin/python scripts/analysis/preprocess_check.py
"""
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from joblib import Parallel, delayed
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
import format_check as fc  # noqa: E402

SR = fc.SR
CACHE = fc.OUT / "cache"
TARGET_RMS = 10 ** (-24 / 20)  # 데이터셋 중앙값 수준(약 -24 dBFS)


def denoise(y):
    """가장 조용한 프레임들(하위 10%)을 잡음 스펙트럼으로 보고 주파수별로 빼낸다."""
    S = librosa.stft(y)
    mag = np.abs(S)
    noise = np.percentile(mag, 10, axis=1, keepdims=True)
    mask = np.clip(1 - 1.5 * noise / (mag + 1e-10), 0.05, 1.0)
    return librosa.istft(S * mask, length=len(y))


def remove_silence(y, internal):
    if internal:
        iv = librosa.effects.split(y, top_db=30)
        return np.concatenate([y[s:e] for s, e in iv]) if len(iv) else y
    return librosa.effects.trim(y, top_db=30)[0]


def normalize(y):
    rms = np.sqrt(np.mean(y**2))
    return np.clip(y * TARGET_RMS / rms, -1, 1) if rms > 0 else y


def preprocess(y, mode):
    if mode == "norm":
        return normalize(y)
    return normalize(remove_silence(denoise(y), internal=(mode == "split")))


def feats(path, cond, mode):
    p = variant(path, cond)
    if mode == "raw":
        f = fc.extract_features(str(p))[0]
    else:
        y, _ = librosa.load(p, sr=SR)
        out = fc.TMP / f"{path.parent.name}_{path.stem}_{cond}_{mode}.wav"
        sf.write(out, preprocess(y, mode).astype(np.float32), SR)
        f = fc.extract_features(str(out))[0]
        out.unlink()
    if p != path:
        p.unlink()
    return f


def variant(path, cond):
    """format_check.variant + 음량 조건(gain_m12 = -12dB, gain_p6 = +6dB)."""
    if not cond.startswith("gain_"):
        return fc.variant(path, cond)
    db = int(cond[6:]) * (-1 if cond[5] == "m" else 1)
    y, sr = librosa.load(path, sr=None)
    out = fc.TMP / f"{path.parent.name}_{path.stem}_{cond}.wav"
    sf.write(out, np.clip(y * 10 ** (db / 20), -1, 1).astype(np.float32), sr)
    return out


def main():
    files = sorted(p for c in fc.CLASSES for p in (fc.DATA / c).glob("*.wav"))
    y = np.array([fc.CLASSES.index(p.parent.name) for p in files])
    conds = ["orig", "aac", "gain_m12", "gain_p6", "pad_snr30", "pad_snr20", "hiss_snr30"]
    modes = ["raw", "norm", "edge", "split"]
    CACHE.mkdir(parents=True, exist_ok=True)
    X = {}
    for c in conds:
        for m in modes:
            cache = CACHE / f"{c}_{m}.npy"  # 중단돼도 끝난 조건은 다시 계산하지 않는다
            if not cache.exists():
                print(f"특징 추출: {c} / {m}", flush=True)
                np.save(cache, np.array(Parallel(n_jobs=-1)(delayed(feats)(p, c, m) for p in files)))
            X[c, m] = np.load(cache)

    acc = {}
    for k in X:
        pred = np.empty(len(y), int)
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(X["orig", "raw"], y):
            pred[te] = fc.pipeline().fit(X["orig", "raw"][tr], y[tr]).predict(X[k][te])
        acc[k] = (np.mean(pred == y), np.mean(pred == 4))

    lines = ["# 앱 녹음 전처리 효과 (out-of-fold, 원본으로 학습 → 테스트에만 열화·전처리)", "",
             "정확도 (괄호: uncomfortable 예측 비율)", "",
             "| 테스트 조건 | " + " | ".join(modes) + " |", "|---" * (len(modes) + 1) + "|"]
    for c in conds:
        lines.append(f"| {c} | " + " | ".join(f"{acc[c, m][0]:.3f} ({acc[c, m][1]:.2f})" for m in modes) + " |")
    out = fc.OUT / "preprocess_check.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
