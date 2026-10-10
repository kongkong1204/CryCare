"""[10/3 결과는 v1 모델(22050Hz) 기준. 지금은 backend 특징추출(v2, 16kHz)로 돌아간다]
학습·검증 대비 시연 정확도 하락 원인 점검.

학습과 같은 파이프라인을 5-fold로 다시 학습하고(out-of-fold), 테스트 fold의 오디오만
앱 녹음 조건으로 바꿔 정확도를 비교한다.
  orig      원본 그대로
  aac       앱 기본 녹음 형식: AAC m4a, 44.1kHz, 스테레오, 128kbps
  wav_mono  제안 형식: WAV(PCM) 44.1kHz 모노
  lp8k      8kHz 저역통과 (전부 16kHz 녹음처럼 만듦 — 샘플레이트 편향 확인)
  pad_snrN  앞뒤 1.5초 + 전 구간 배경잡음(SNR N dB) — trim(top_db=25) 확인
  hiss_snrN 8kHz 이상만 있는 고음역 잡음(SNR N dB) — 휴대폰 마이크 고음역 확인
사용: venv/bin/python scripts/analysis/format_check.py [데이터셋 경로]
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from joblib import Parallel, delayed
from scipy.signal import butter, sosfilt
from sklearn.decomposition import PCA
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import SVC

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.features import SR, extract_features  # noqa: E402

DATA = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "Downloads/BabyCry-C5_160")
CLASSES = ["awake", "hug", "hungry", "sleepy", "uncomfortable"]
OUT = Path(__file__).resolve().parents[2] / "evidence" / "format_check"
TMP = Path(tempfile.mkdtemp(prefix="crycare-fmt-"))
RNG = np.random.default_rng(0)


def pink(n):
    spec = np.fft.rfft(RNG.standard_normal(n))
    spec /= np.sqrt(np.maximum(np.arange(len(spec)), 1))
    x = np.fft.irfft(spec, n)
    return x / np.sqrt(np.mean(x**2))


def hiss(n, sr):
    x = sosfilt(butter(8, 8000, "highpass", fs=sr, output="sos"), RNG.standard_normal(n))
    return x / np.sqrt(np.mean(x**2))


def cry_rms(y):
    return np.sqrt(np.mean(librosa.effects.trim(y, top_db=25)[0] ** 2))


def variant(path, cond):
    """조건별 오디오 파일을 만들어 경로를 돌려준다."""
    if cond == "orig":
        return path
    out = TMP / f"{path.parent.name}_{path.stem}_{cond}"
    if cond == "aac":
        out = out.with_suffix(".m4a")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-ar", "44100", "-ac", "2",
                        "-c:a", "aac", "-b:a", "128k", str(out)], check=True)
        return out
    if cond == "wav_mono":
        out = out.with_suffix(".wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-ar", "44100", "-ac", "1",
                        "-c:a", "pcm_s16le", str(out)], check=True)
        return out
    y, sr = librosa.load(path, sr=44100)
    if cond == "lp8k":
        y = sosfilt(butter(10, 7800, "lowpass", fs=sr, output="sos"), y)
    elif cond.startswith("pad_snr"):
        pad = np.zeros(int(1.5 * sr))
        level = cry_rms(y) / 10 ** (int(cond[7:]) / 20)
        y = np.concatenate([pad, y, pad])
        y = y + level * pink(len(y))
    elif cond.startswith("hiss_snr"):
        y = y + cry_rms(y) / 10 ** (int(cond[8:]) / 20) * hiss(len(y), sr)
    out = out.with_suffix(".wav")
    sf.write(out, y.astype(np.float32), sr)
    return out


def feats(path, cond):
    p = variant(path, cond)
    f = extract_features(str(p))[0]
    if p != path:
        p.unlink()
    return f


def pipeline():
    return make_pipeline(MinMaxScaler(), PCA(n_components=0.95),
                         SVC(kernel="rbf", C=20, gamma="scale", probability=True, random_state=0))


def main():
    files = sorted(p for c in CLASSES for p in (DATA / c).glob("*.wav"))
    y = np.array([CLASSES.index(p.parent.name) for p in files])
    srs = np.array([sf.info(p).samplerate for p in files])
    conds = ["orig", "aac", "wav_mono", "lp8k", "pad_snr30", "pad_snr20", "pad_snr10", "hiss_snr30", "hiss_snr20"]
    X = {}
    for c in conds:
        print(f"특징 추출: {c}", flush=True)
        X[c] = np.array(Parallel(n_jobs=-1)(delayed(feats)(p, c) for p in files))

    pred = {c: np.empty(len(y), int) for c in conds}
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(X["orig"], y):
        m = pipeline().fit(X["orig"][tr], y[tr])
        for c in conds:
            pred[c][te] = m.predict(X[c][te])

    hi = srs == 44100
    lines = ["# 녹음 형식·무음 영향 (out-of-fold, 원본으로 학습 → 조건별 테스트)", "",
             f"샘플 {len(y)}개 (16kHz {np.sum(srs == 16000)}, 44.1kHz {hi.sum()}, 1.6kHz {np.sum(srs == 1600)})", "",
             "| 조건 | 정확도 | 원본과 예측 일치 | uncomfortable 예측 비율 | 16kHz 원본 정확도 | 44.1kHz 원본 정확도 |",
             "|---|---|---|---|---|---|"]
    for c in conds:
        p = pred[c]
        lines.append(f"| {c} | {np.mean(p == y):.3f} | {np.mean(p == pred['orig']):.3f} | "
                     f"{np.mean(p == 4):.3f} | {np.mean(p[srs == 16000] == y[srs == 16000]):.3f} | "
                     f"{np.mean(p[hi] == y[hi]):.3f} |")

    # 샘플레이트 편향: 특징만으로 원본 샘플레이트를 맞힐 수 있는가
    sr_y = hi.astype(int)
    sr_pred = np.empty(len(y), int)
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(X["orig"], sr_y):
        sr_pred[te] = pipeline().fit(X["orig"][tr], sr_y[tr]).predict(X["orig"][te])
    lines += ["", f"특징으로 원본 샘플레이트(16k vs 44.1k) 맞히기 정확도: {np.mean(sr_pred == sr_y):.3f}",
              f"클래스 무관 기준선(다수 클래스): {max(np.mean(sr_y), 1 - np.mean(sr_y)):.3f}"]

    # 특징 변화량: 원본 대비 |차이| / 원본 표준편차 (큰 순)
    names = (["zcr", "rms_mean", "rms_std", "centroid", "bandwidth", "rolloff", "contrast"]
             + [f"mfcc{i}_mean" for i in range(13)] + [f"mfcc{i}_std" for i in range(13)]
             + [f"chroma{i}" for i in range(12)])
    sd = X["orig"].std(axis=0) + 1e-12
    for c in ["aac", "pad_snr20", "hiss_snr30"]:
        d = np.median(np.abs(X[c] - X["orig"]) / sd, axis=0)
        top = np.argsort(d)[::-1][:6]
        lines.append(f"\n{c} 특징 변화 상위(중앙값, 표준편차 단위): "
                     + ", ".join(f"{names[i]} {d[i]:.2f}" for i in top))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "format_check.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
