# ============================================================
#  backend 폴더 Dockerfile
#  (Docker build → push → GCP 리눅스 서버 배포용 · 포트 8000)
# ============================================================

# 가벼운 파이썬 베이스 이미지
FROM python:3.11-slim

WORKDIR /app

# ── 레이어 캐싱 최적화 ──────────────────────────────────
#  의존성 파일을 먼저 복사해 설치하면,
#  코드만 바뀌었을 때 pip install 을 다시 하지 않고 캐시를 재사용합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 모델을 이미지에 미리 다운로드
RUN python -c "from transformers import pipeline; pipeline('sentiment-analysis', model='matthewburke/korean_sentiment')"

# ── 나머지 소스 코드 복사 ───────────────────────────────
#  main.py, database.py, sentiment.py, routers/ 등 전부 포함됩니다.
COPY . .

# 로그가 실시간으로 보이도록 (docker logs / 서버 로그)
ENV PYTHONUNBUFFERED=1

# ── 포트 8000 ───────────────────────────────────────────
EXPOSE 8000

# ── 실행 명령 ───────────────────────────────────────────
#  컨테이너가 시작될 때 uvicorn 으로 서버를 8000 포트로 실행합니다.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
