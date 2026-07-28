"""
routers/reviews.py
-------------------
리뷰(Review) 관련 엔드포인트 모음입니다. (심화 기능)
모든 DB 접근은 표준 라이브러리 sqlite3 만 사용합니다. (ORM 미사용)

엔드포인트
  POST   /movies/{movie_id}/reviews         리뷰 등록 (등록 시 감성 분석 자동 실행)
  GET    /movies/{movie_id}/reviews         특정 영화의 리뷰 목록 조회
  GET    /reviews                           전체 리뷰 조회 (최근순, limit 지원)
  GET    /movies/{movie_id}/rating          특정 영화의 평점(감성 점수 평균) 조회
  DELETE /reviews/{review_id}               리뷰 삭제
"""

import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query

from database import get_db
from auth import verify_api_key
from schemas import ReviewCreate, ReviewResponse, RatingResponse
from sentiment import analyze_sentiment

router = APIRouter(tags=["reviews"])


def _row_to_review(row: sqlite3.Row) -> dict:
    """sqlite3.Row → 응답용 dict 변환 헬퍼."""
    return {
        "id": row["id"],
        "movie_id": row["movie_id"],
        "author": row["author"],
        "content": row["content"],
        "sentiment": row["sentiment"],
        "score": row["score"],
        "created_at": row["created_at"],
    }


def _ensure_movie_exists(conn: sqlite3.Connection, movie_id: int) -> sqlite3.Row:
    """영화가 존재하는지 확인하고, 없으면 404 를 발생시킵니다."""
    row = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="해당 영화를 찾을 수 없습니다.")
    return row


# ------------------------------------------------------------------
#  리뷰 등록 — 감성 분석 자동 실행
# ------------------------------------------------------------------
@router.post(
    "/movies/{movie_id}/reviews",
    response_model=ReviewResponse,
    status_code=201,
)
def create_review(
    movie_id: int,
    review: ReviewCreate,
    conn: sqlite3.Connection = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    리뷰를 등록합니다.
    등록 직전에 감성 분석(analyze_sentiment)을 실행해
    그 결과(sentiment, score)를 리뷰와 함께 저장합니다.
    """
    _ensure_movie_exists(conn, movie_id)

    # 1) 감성 분석 실행 (긍정/부정/중립 + 긍정 확률)
    result = analyze_sentiment(review.content)

    # 2) 리뷰 저장 (파라미터화된 쿼리로 SQL 인젝션 방지)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO reviews (movie_id, author, content, sentiment, score)
        VALUES (?, ?, ?, ?, ?)
        """,
        (movie_id, review.author, review.content, result["sentiment"], result["score"]),
    )
    conn.commit()

    new_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM reviews WHERE id = ?", (new_id,)).fetchone()
    return _row_to_review(row)


# ------------------------------------------------------------------
#  특정 영화의 리뷰 목록
# ------------------------------------------------------------------
@router.get("/movies/{movie_id}/reviews", response_model=list[ReviewResponse])
def get_reviews_by_movie(
    movie_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """특정 영화에 달린 리뷰를 최신순으로 조회합니다."""
    _ensure_movie_exists(conn, movie_id)
    rows = conn.execute(
        "SELECT * FROM reviews WHERE movie_id = ? ORDER BY id DESC",
        (movie_id,),
    ).fetchall()
    return [_row_to_review(r) for r in rows]


# ------------------------------------------------------------------
#  전체 리뷰 (최근 N개) — 프론트의 "최근 10개 리뷰 표시"에 사용
# ------------------------------------------------------------------
@router.get("/reviews", response_model=list[ReviewResponse])
def get_all_reviews(
    limit: int = Query(default=10, ge=1, le=100, description="가져올 리뷰 개수"),
    conn: sqlite3.Connection = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    전체 리뷰를 최신순으로 조회합니다.
    기본값 limit=10 → 프론트엔드의 '최근 10개 리뷰' 요구사항에 대응합니다.
    """
    rows = conn.execute(
        "SELECT * FROM reviews ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [_row_to_review(r) for r in rows]


# ------------------------------------------------------------------
#  평점(감성 점수 평균) 조회
# ------------------------------------------------------------------
@router.get("/movies/{movie_id}/rating", response_model=RatingResponse)
def get_movie_rating(
    movie_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    특정 영화의 평점을 조회합니다.
    평점 = 그 영화에 달린 모든 리뷰의 감성 점수(score, 긍정 확률) 평균.
    리뷰가 없으면 avg_score 는 None, review_count 는 0 입니다.
    """
    _ensure_movie_exists(conn, movie_id)
    row = conn.execute(
        """
        SELECT COUNT(id) AS cnt, AVG(score) AS avg_score
        FROM reviews
        WHERE movie_id = ?
        """,
        (movie_id,),
    ).fetchone()

    avg = row["avg_score"]
    return {
        "movie_id": movie_id,
        "avg_score": round(avg, 4) if avg is not None else None,
        "review_count": row["cnt"] or 0,
    }


# ------------------------------------------------------------------
#  리뷰 삭제
# ------------------------------------------------------------------
@router.delete("/reviews/{review_id}")
def delete_review(
    review_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """특정 리뷰를 삭제합니다. 없으면 404."""
    row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="해당 리뷰를 찾을 수 없습니다.")

    conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    conn.commit()
    return {"message": "리뷰가 삭제되었습니다."}
