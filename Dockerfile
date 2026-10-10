# CryCare 백엔드 (Cloud Run 서울). 학습·로컬과 같은 Python 3.9 + requirements 고정 버전 (스펙 §4·§9)
FROM python:3.9-slim

# NUMBA_CPU_NAME=generic: 빌드 머신과 실행 머신(Cloud Run)의 CPU가 달라도 numba 캐시를 그대로 쓰게 한다
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NUMBA_CACHE_DIR=/app/.numba_cache \
    NUMBA_CPU_NAME=generic

# ffmpeg: 앱 녹음(m4a) 디코딩, libsndfile1: soundfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
# 모델은 이미지에만 넣고 git에는 올리지 않는다. 빠지면 여기서 빌드가 실패한다
COPY crycare_final.pkl .

# numba 컴파일 결과를 이미지에 캐시해 콜드스타트를 줄인다
RUN python -m backend.warmup

# Cloud Run이 넣어주는 $PORT 사용 (로컬 기본 8080)
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
