"""v1(crycare_final_v1.pkl: 22050Hz + MinMaxScaler) vs v2(현재 pkl: 16kHz + StandardScaler) 비교.

format_check.py와 같은 out-of-fold 설정으로, 원본으로 학습하고 테스트 오디오만 앱 녹음 조건으로 바꾼다.
중복 파일(내용이 같은 wav)은 같은 fold로 묶는다.
사용: venv/bin/python scripts/analysis/compare_v2.py
"""
import hashlib
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from joblib import Parallel, delayed
from sklearn.decomposition import PCA
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.svm import SVC

sys.path.insert(0, str(Path(__file__).resolve().parent))
import format_check as fc  # noqa: E402

CACHE = fc.OUT / "cache_v2"
CONDS = ["orig", "aac", "gain_m12", "gain_p6", "pad_snr30", "pad_snr20", "hiss_snr30"]


def extract_features_22k(path):
    """v1(crycare_final_v1.pkl) 특징추출. 22050Hz."""
    return extract_features_16k(path, SR=22050)


def extract_features_16k(path, SR=16000):
    """v2 학습 코드(crycare_train.py)와 동일. SR만 16000."""
    sig, _ = librosa.load(path, sr=SR)
    sig, _ = librosa.effects.trim(sig, top_db=25)
    f = [librosa.feature.zero_crossing_rate(sig).mean(),
         librosa.feature.rms(y=sig).mean(), librosa.feature.rms(y=sig).std(),
         librosa.feature.spectral_centroid(y=sig, sr=SR).mean(),
         librosa.feature.spectral_bandwidth(y=sig, sr=SR).mean(),
         librosa.feature.spectral_rolloff(y=sig, sr=SR).mean(),
         librosa.feature.spectral_contrast(y=sig, sr=SR).mean()]
    mfcc = librosa.feature.mfcc(y=sig, sr=SR, n_mfcc=13)
    f += list(mfcc.mean(axis=1)) + list(mfcc.std(axis=1))
    f += list(librosa.feature.chroma_stft(y=sig, sr=SR).mean(axis=1))
    return np.array(f)


def variant(path, cond):
    """format_check.variant + 음량 조건(gain_m12, gain_p6)."""
    if not cond.startswith("gain_"):
        return fc.variant(path, cond)
    db = int(cond[6:]) * (-1 if cond[5] == "m" else 1)
    y, sr = librosa.load(path, sr=None)
    out = fc.TMP / f"{path.parent.name}_{path.stem}_{cond}.wav"
    sf.write(out, np.clip(y * 10 ** (db / 20), -1, 1).astype(np.float32), sr)
    return out


def feats_both(path, cond):
    p = variant(path, cond)
    f1 = extract_features_22k(str(p))
    f2 = extract_features_16k(str(p))
    if p != path:
        p.unlink()
    return f1, f2


def pipe(scaler, C=20, gamma="scale"):
    return make_pipeline(scaler(), PCA(n_components=0.95),
                         SVC(kernel="rbf", C=C, gamma=gamma, random_state=0))


def main():
    files = sorted(p for c in fc.CLASSES for p in (fc.DATA / c).glob("*.wav"))
    y = np.array([fc.CLASSES.index(p.parent.name) for p in files])
    groups = np.unique([hashlib.md5(np.round(sf.read(p)[0], 4).tobytes()).hexdigest() for p in files],
                       return_inverse=True)[1]
    CACHE.mkdir(parents=True, exist_ok=True)
    X = {}
    for c in CONDS:
        cache = CACHE / f"{c}.npz"  # 중단돼도 끝난 조건은 다시 계산하지 않는다
        if not cache.exists():
            print(f"특징 추출: {c}", flush=True)
            r = Parallel(n_jobs=-1)(delayed(feats_both)(p, c) for p in files)
            np.savez(cache, v1=np.array([a for a, _ in r]), v2=np.array([b for _, b in r]))
        z = np.load(cache)
        X["v1", c], X["v2", c] = z["v1"], z["v2"]

    # 하이퍼파라미터는 각 pkl과 동일 (v1 C=20 gamma=scale, v2 C=5 gamma=0.1)
    models = {"v1 (22050Hz, MinMax, C=20)": ("v1", MinMaxScaler, {}),
              "v2 (16kHz, Standard, C=5 γ=0.1)": ("v2", StandardScaler, {"C": 5, "gamma": 0.1})}
    lines = ["# v1 vs v2 비교 (out-of-fold 5-fold × 시드 3, 중복 파일은 같은 fold)", "",
             "| 모델 | " + " | ".join(CONDS) + " |", "|---" * (len(CONDS) + 1) + "|"]
    f1_lines = []
    for name, (v, scaler, hp) in models.items():
        acc = {c: [] for c in CONDS}
        f1s = []
        for seed in range(3):
            pred = {c: np.empty(len(y), int) for c in CONDS}
            cv = StratifiedGroupKFold(5, shuffle=True, random_state=seed)
            for tr, te in cv.split(X[v, "orig"], y, groups):
                m = pipe(scaler, **hp).fit(X[v, "orig"][tr], y[tr])
                for c in CONDS:
                    pred[c][te] = m.predict(X[v, c][te])
            for c in CONDS:
                acc[c].append(np.mean(pred[c] == y))
            f1s.append(f1_score(y, pred["orig"], average=None))
        lines.append(f"| {name} | " + " | ".join(f"{np.mean(acc[c]):.3f}" for c in CONDS) + " |")
        f1_lines.append(f"- {name} 클래스별 F1 (원본): "
                        + ", ".join(f"{k} {v_:.2f}" for k, v_ in zip(fc.CLASSES, np.mean(f1s, 0))))

    # 샘플레이트 편향: 특징만으로 원본이 44.1kHz인지 맞히는 정확도
    hi = np.array([sf.info(p).samplerate == 44100 for p in files]).astype(int)
    sr_lines = []
    for name, (v, scaler, hp) in models.items():
        pred = np.empty(len(y), int)
        for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=0).split(X[v, "orig"], hi, groups):
            pred[te] = pipe(scaler, **hp).fit(X[v, "orig"][tr], hi[tr]).predict(X[v, "orig"][te])
        sr_lines.append(f"- {name}: 원본 샘플레이트 식별 정확도 {np.mean(pred == hi):.3f} (기준선 {1 - hi.mean():.3f})")

    lines += ["", *f1_lines, "", *sr_lines]
    out = fc.OUT / "compare_v2.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
