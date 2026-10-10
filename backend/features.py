"""오디오 -> 45차원 특징벡터. 학습 코드와 완전히 동일해야 한다 (스펙 §9)."""
import librosa
import numpy as np

# v2 모델(16kHz 학습). 44.1kHz 녹음의 8kHz 이상 고음역을 버려 샘플레이트 편향을 줄인다 (스펙 §10.4)
SR = 16000


def extract_features(path: str) -> np.ndarray:
    sig, _ = librosa.load(path, sr=SR)
    sig, _ = librosa.effects.trim(sig, top_db=25)  # 무음 제거
    f = [librosa.feature.zero_crossing_rate(sig).mean(),
         librosa.feature.rms(y=sig).mean(), librosa.feature.rms(y=sig).std(),
         librosa.feature.spectral_centroid(y=sig, sr=SR).mean(),
         librosa.feature.spectral_bandwidth(y=sig, sr=SR).mean(),
         librosa.feature.spectral_rolloff(y=sig, sr=SR).mean(),
         librosa.feature.spectral_contrast(y=sig, sr=SR).mean()]
    mfcc = librosa.feature.mfcc(y=sig, sr=SR, n_mfcc=13)
    f += list(mfcc.mean(axis=1)) + list(mfcc.std(axis=1))
    f += list(librosa.feature.chroma_stft(y=sig, sr=SR).mean(axis=1))
    return np.array(f).reshape(1, -1)
