"""v3 후보: 스피커·마이크 음색 변화에 강하게 증강 학습 (v2와 같은 16kHz 특징·파이프라인).

배경: 맥 스피커로 틀어 폰으로 녹음한 울음은 MFCC·스펙트럼 대비가 원본 대비 표준편차 2~4배 이동해
v2(gamma=0.1)에서 학습 분포 밖으로 밀려나 모두 비슷한 확률이 나온다.
증강: 학습 파일마다 사본 K개 — 무작위 주파수 특성(저역·고역 차단 + 부드러운 굴곡 ±8dB),
방 잔향, 음량 ±8dB, 배경잡음(SNR 20~40dB).

평가
  clean  원본 정확도 (5-fold, 중복 파일은 같은 fold, 증강 사본은 학습 fold에만)
  synth  format_check 조건(AAC·음량·무음+잡음·고음역 잡음) 평균
  phone  정답을 아는 실제 폰 녹음. 원본 파일을 학습에서 뺀 모델로 평가
사용: venv/bin/python scripts/analysis/train_v3.py [--save]
"""
import hashlib
import sqlite3
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from joblib import Parallel, delayed
from scipy.signal import butter, fftconvolve, sosfilt
from sklearn.decomposition import PCA
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import format_check as fc  # noqa: E402
from compare_v2 import extract_features_16k  # noqa: E402

SR = 16000
K = 3
CACHE = fc.OUT / "cache_v3"

# 정답을 아는 실제 폰 녹음 (맥 스피커 재생 → 아이폰 앱 녹음): (파일, 정답, 원본 파일)
PHONE = [
    (ROOT / "evidence/phone_take1/5af934b52801439fae52c8d06abd7733.m4a", "hungry", "hungry/hungry_1"),
    (ROOT / "evidence/phone_take1/e96fe276004b40b8b70c833ec1423180.m4a", "hungry", "hungry/hungry_0"),
    (ROOT / "evidence/phone_take1/51a43b9bb7194fb793d2dcf7bd940f83.m4a", "hungry", "hungry/hungry_10"),
]
REHEARSAL_RECORDS = {134: "hungry/hungry_0", 135: "hungry/hungry_10", 136: "hungry/hungry_20", 137: "hungry/hungry_30"}


def phone_set():
    items = list(PHONE)
    db = sqlite3.connect(ROOT / "crycare.db")
    for rid, src in REHEARSAL_RECORDS.items():
        row = db.execute("SELECT audio_path FROM records WHERE id = ?", (rid,)).fetchone()
        if row and Path(row[0]).exists():
            items.append((Path(row[0]), src.split("/")[0], src))
    return items


def channel(y, rng):
    """스피커·마이크·방을 거친 소리처럼 바꾼다."""
    lo, hi = rng.uniform(100, 500), rng.uniform(3500, 7500)
    y = sosfilt(butter(2, [lo, hi], "bandpass", fs=SR, output="sos"), y)
    # 부드러운 주파수 굴곡 (스피커·마이크 응답)
    S = librosa.stft(y)
    f = np.linspace(0, 1, S.shape[0])
    curve = sum(rng.uniform(-4, 4) * np.cos(np.pi * (i + 1) * f + rng.uniform(0, np.pi)) for i in range(3))
    y = librosa.istft(S * (10 ** (curve / 20))[:, None], length=len(y))
    # 방 잔향
    if rng.random() < 0.7:
        rt = rng.uniform(0.15, 0.5)
        n = int(rt * SR)
        ir = rng.standard_normal(n) * np.exp(-6.9 * np.arange(n) / n)
        ir[0] = 1.0
        wet = fftconvolve(y, ir)[: len(y)]
        wet *= np.sqrt(np.mean(y**2) / (np.mean(wet**2) + 1e-12))
        mix = rng.uniform(0.2, 0.6)
        y = (1 - mix) * y + mix * wet
    # 음량 + 배경잡음
    y = y * 10 ** (rng.uniform(-8, 8) / 20)
    rms = np.sqrt(np.mean(librosa.effects.trim(y, top_db=25)[0] ** 2))
    y = y + rms / 10 ** (rng.uniform(20, 40) / 20) * fc.pink(len(y))
    return np.clip(y, -1, 1)


def aug_feats(path, k, seed):
    y, _ = librosa.load(path, sr=SR)
    out = fc.TMP / f"{path.parent.name}_{path.stem}_aug{k}.wav"
    sf.write(out, channel(y, np.random.default_rng(seed)).astype(np.float32), SR)
    f = extract_features_16k(str(out))
    out.unlink()
    return f


def model(C, gamma):
    return make_pipeline(StandardScaler(), PCA(n_components=0.95),
                         SVC(kernel="rbf", C=C, gamma=gamma, probability=True, random_state=0))


def main():
    files = sorted(p for c in fc.CLASSES for p in (fc.DATA / c).glob("*.wav"))
    y = np.array([fc.CLASSES.index(p.parent.name) for p in files])
    groups = np.unique([hashlib.md5(np.round(sf.read(p)[0], 4).tobytes()).hexdigest() for p in files],
                       return_inverse=True)[1]
    CACHE.mkdir(parents=True, exist_ok=True)

    X = np.load(fc.OUT / "cache_v2/orig.npz")["v2"]
    A = []
    for k in range(K):
        cache = CACHE / f"aug{k}.npy"  # 중단돼도 끝난 사본은 다시 계산하지 않는다
        if not cache.exists():
            print(f"증강 사본 {k + 1}/{K} 특징 추출", flush=True)
            np.save(cache, np.array(Parallel(n_jobs=-1)(
                delayed(aug_feats)(p, k, 1000 * k + i) for i, p in enumerate(files))))
        A.append(np.load(cache))
    synth = {c: np.load(fc.OUT / f"cache_v2/{c}.npz")["v2"]
             for c in ["aac", "gain_m12", "gain_p6", "pad_snr30", "pad_snr20", "hiss_snr30"]}

    phone = phone_set()
    Xp = np.array([extract_features_16k(str(p)) for p, _, _ in phone])
    yp = np.array([fc.CLASSES.index(lab) for _, lab, _ in phone])
    src_idx = {f"{p.parent.name}/{p.stem}": i for i, p in enumerate(files)}
    held = np.isin(np.arange(len(files)), [src_idx[s] for _, _, s in phone])

    configs = [("v2 기준 (증강 없음)", 5, 0.1, False)] + [
        (f"증강 C={C} γ={g}", C, g, True) for C in (1, 5, 20) for g in (0.1, 0.03, 0.01)]
    lines = [f"# v3 후보 비교 (증강 사본 {K}개, 폰 녹음 {len(phone)}개 — 정답 모두 hungry)", "",
             "| 설정 | 원본 정확도 | 합성 조건 평균 | 폰 녹음 정답 | 폰 hungry 확률 평균 | 폰 1순위 |",
             "|---|---|---|---|---|---|"]
    for name, C, g, aug in configs:
        pred = np.empty(len(y), int)
        syn = {c: np.empty(len(y), int) for c in synth}
        for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=0).split(X, y, groups):
            Xtr = np.vstack([X[tr]] + ([a[tr] for a in A] if aug else []))
            ytr = np.tile(y[tr], 1 + (K if aug else 0))
            m = model(C, g).fit(Xtr, ytr)
            pred[te] = m.predict(X[te])
            for c in synth:
                syn[c][te] = m.predict(synth[c][te])
        keep = ~held  # 폰 녹음의 원본 파일은 학습에서 제외
        Xtr = np.vstack([X[keep]] + ([a[keep] for a in A] if aug else []))
        ytr = np.tile(y[keep], 1 + (K if aug else 0))
        P = model(C, g).fit(Xtr, ytr).predict_proba(Xp)
        top = ", ".join(f"{fc.CLASSES[i][:4]} {P[j, i]:.2f}" for j, i in enumerate(P.argmax(1)))
        lines.append(f"| {name} | {np.mean(pred == y):.3f} | {np.mean([np.mean(syn[c] == y) for c in synth]):.3f} | "
                     f"{np.sum(P.argmax(1) == yp)}/{len(yp)} | {P[:, fc.CLASSES.index('hungry')].mean():.2f} | {top} |")
        print(lines[-1], flush=True)

    out = fc.OUT / "train_v3.md"
    out.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
