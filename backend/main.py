"""
main.py
--------
FastAPI 애플리케이션의 진입점입니다.

역할
  1) 앱 시작(lifespan) 시 DB 테이블 생성 + 감성 분석 모델 예열
  2) CORS 미들웨어 설정 (Streamlit 프론트엔드가 API 를 호출할 수 있도록)
  3) 영화/리뷰 라우터 등록
  4) 헬스 체크(/health) 엔드포인트 제공

실행 방법
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
자동 문서
  http://localhost:8000/docs
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import movies, reviews
import sentiment


# ------------------------------------------------------------------
# lifespan : 서버 "시작"과 "종료" 시점에 할 일을 정의
#   - 시작 시: 테이블 생성 + 감성 모델 예열(warmup)
#   - Chapter 10 에서 배운 lifespan 패턴을 그대로 적용
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 서버 시작 시 1회 실행 ──
    print("[startup] 데이터베이스 초기화 중...")
    init_db()
    print("[startup] 감성 분석 모델 예열 중... (모델 다운로드 시 시간이 걸릴 수 있습니다)")
    engine = sentiment.warmup()
    print(f"[startup] 감성 분석 엔진 준비 완료: {engine}")

    yield  # ← 이 지점부터 요청을 받기 시작

    # ── 서버 종료 시 실행 ──
    print("[shutdown] 서버를 종료합니다.")


app = FastAPI(
    title="영화 리뷰 & 감성 분석 API",
    description=(
        "영화 정보를 관리하고, 사용자 리뷰를 등록하며, "
        "리뷰 감성(긍정/부정/중립)을 자동 분석하는 백엔드 API 입니다. "
        "데이터베이스는 표준 라이브러리 sqlite3 만으로 구현되었습니다."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ------------------------------------------------------------------
# CORS 설정
#   - 환경변수 CORS_ORIGINS 로 허용 출처를 지정 (쉼표 구분)
#   - 없으면 개발 편의를 위해 모든 출처("*") 허용
#   - 실제 배포 시에는 Streamlit 앱 주소만 넣는 것을 권장
# ------------------------------------------------------------------
_origins_env = os.environ.get("CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in _origins_env.split(",")] if _origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# 라우터 등록
# ------------------------------------------------------------------
app.include_router(movies.router)
app.include_router(reviews.router)


# ------------------------------------------------------------------
# 기본 / 헬스 체크 엔드포인트 (인증 불필요)
# ------------------------------------------------------------------
@app.get("/", tags=["default"])
def read_root():
    """루트 — 서비스가 살아있는지 간단히 확인."""
    return {"message": "영화 리뷰 & 감성 분석 API 입니다. /docs 에서 문서를 확인하세요."}


@app.get("/health", tags=["default"])
def health_check():
    """헬스 체크 — 로드밸런서/모니터링용."""
    return {"status": "ok"}
