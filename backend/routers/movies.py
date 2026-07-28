"""
routers/movies.py
------------------
영화(Movie) 관련 엔드포인트 모음입니다.
모든 DB 접근은 표준 라이브러리 sqlite3 만 사용합니다. (ORM 미사용)

엔드포인트
  POST   /movies            영화 등록
  GET    /movies            전체 영화 조회 (평균 감성 점수 포함)
  GET    /movies/{movie_id} 특정 영화 조회
  DELETE /movies/{movie_id} 특정 영화 삭제 (연결된 리뷰도 함께 삭제)
"""

import sqlite3
from fastapi import APIRouter, Depends, HTTPException

from database import get_db
from auth import verify_api_key
from schemas import MovieCreate, MovieResponse

router = APIRouter(prefix="/movies", tags=["movies"])


def _row_to_movie(row: sqlite3.Row, avg_score=None, review_count: int = 0) -> dict:
    """sqlite3.Row 객체를 응답용 dict 로 변환하는 헬퍼."""
    return {
        "id": row["id"],
        "title": row["title"],
        "release_date": row["release_date"],
        "director": row["director"],
        "genre": row["genre"],
        "poster_url": row["poster_url"],
        "created_at": row["created_at"],
        "avg_score": round(avg_score, 4) if avg_score is not None else None,
        "review_count": review_count,
    }


@router.post("", response_model=MovieResponse, status_code=201)
def create_movie(
    movie: MovieCreate,
    conn: sqlite3.Connection = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    영화를 등록합니다.
    파라미터화된 쿼리(?, ?)를 사용해 SQL 인젝션을 방지합니다.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO movies (title, release_date, director, genre, poster_url)
        VALUES (?, ?, ?, ?, ?)
        """,
        (movie.title, movie.release_date, movie.director, movie.genre, movie.poster_url),
    )
    conn.commit()

    # 방금 삽입된 행의 자동 생성 id 를 가져와 전체 정보를 다시 조회
    new_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM movies WHERE id = ?", (new_id,)).fetchone()
    return _row_to_movie(row)


@router.get("", response_model=list[MovieResponse])
def get_movies(
    conn: sqlite3.Connection = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    전체 영화 목록을 조회합니다.
    각 영화에 대해 리뷰 개수와 감성 점수 평균(평점)을 함께 계산해 붙입니다.

    LEFT JOIN 을 사용하므로, 리뷰가 하나도 없는 영화도 목록에서 빠지지 않습니다.
    (이 경우 avg_score 는 NULL, review_count 는 0 이 됩니다.)
    """
    rows = conn.execute(
        """
        SELECT
            m.*,
            COUNT(r.id)   AS review_count,
            AVG(r.score)  AS avg_score
        FROM movies AS m
        LEFT JOIN reviews AS r ON r.movie_id = m.id
        GROUP BY m.id
        ORDER BY m.id DESC
        """
    ).fetchall()

    result = []
    for row in rows:
        result.append(
            _row_to_movie(
                row,
                avg_score=row["avg_score"],
                review_count=row["review_count"] or 0,
            )
        )
    return result


@router.get("/{movie_id}", response_model=MovieResponse)
def get_movie(
    movie_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """특정 영화를 조회합니다. 없으면 404."""
    row = conn.execute(
        """
        SELECT
            m.*,
            COUNT(r.id)  AS review_count,
            AVG(r.score) AS avg_score
        FROM movies AS m
        LEFT JOIN reviews AS r ON r.movie_id = m.id
        WHERE m.id = ?
        GROUP BY m.id
        """,
        (movie_id,),
    ).fetchone()

    # LEFT JOIN + GROUP BY 특성상, 존재하지 않는 id 는 행이 없거나
    # id 가 NULL 인 형태로 나올 수 있어 두 경우 모두 처리합니다.
    if row is None or row["id"] is None:
        raise HTTPException(status_code=404, detail="해당 영화를 찾을 수 없습니다.")

    return _row_to_movie(
        row,
        avg_score=row["avg_score"],
        review_count=row["review_count"] or 0,
    )


@router.delete("/{movie_id}")
def delete_movie(
    movie_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """
    특정 영화를 삭제합니다.
    외래키 ON DELETE CASCADE 설정 덕분에, 이 영화에 달린 리뷰도 함께 삭제됩니다.
    """
    row = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="해당 영화를 찾을 수 없습니다.")

    conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
    conn.commit()
    return {"message": f"'{row['title']}' 영화가 삭제되었습니다."}
