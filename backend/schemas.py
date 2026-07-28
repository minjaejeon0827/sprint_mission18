"""
schemas.py
-----------
API 로 주고받는 데이터의 "모양"을 정의하는 Pydantic 모델 모음입니다.

두 종류의 모델이 있습니다.
  - ...Create  : 클라이언트 -> 서버 로 들어오는 "요청 바디" 검증용
  - ...Response: 서버 -> 클라이언트 로 나가는 "응답 형태" 정의용

DB 테이블 구조(sqlite3)와는 별개입니다.
sqlite3 는 파이썬 dict 를 그대로 다루므로, 여기서 정의한 스키마는
순수하게 "입력 검증 + 응답 문서화" 목적으로만 쓰입니다.

[실전 포인트]
  - Field(min_length=...) 로 빈 문자열/과도한 길이를 자동으로 걸러냅니다.
  - field_validator 로 앞뒤 공백을 정리하고, 공백만 입력된 경우를 막습니다.
  - 잘못된 입력은 FastAPI 가 자동으로 422 오류로 응답합니다.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ==================================================================
#  영화 (Movie)
# ==================================================================
class MovieCreate(BaseModel):
    """영화 등록 요청 바디"""
    title: str = Field(min_length=1, max_length=200, description="영화 제목")
    release_date: Optional[str] = Field(
        default=None, max_length=20, description="개봉일 (예: 2024-05-01)"
    )
    director: Optional[str] = Field(
        default=None, max_length=100, description="감독"
    )
    genre: Optional[str] = Field(
        default=None, max_length=100, description="장르"
    )
    poster_url: Optional[str] = Field(
        default=None, max_length=1000, description="포스터 이미지 URL"
    )

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        """제목의 앞뒤 공백을 제거하고, 공백만 있는 경우를 막습니다."""
        v = v.strip()
        if not v:
            raise ValueError("제목은 공백일 수 없습니다.")
        return v

    @field_validator("release_date", "director", "genre", "poster_url")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        """선택 항목은 앞뒤 공백을 정리하고, 빈 문자열이면 None 으로 통일합니다."""
        if v is None:
            return None
        v = v.strip()
        return v or None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "인터스텔라",
                "release_date": "2014-11-06",
                "director": "크리스토퍼 놀란",
                "genre": "SF, 드라마",
                "poster_url": "https://example.com/poster.jpg",
            }
        }
    }


class MovieResponse(BaseModel):
    """영화 응답 형태"""
    id: int
    title: str
    release_date: Optional[str] = None
    director: Optional[str] = None
    genre: Optional[str] = None
    poster_url: Optional[str] = None
    created_at: Optional[str] = None
    # (심화) 해당 영화의 평균 감성 점수 — 리뷰가 없으면 None
    avg_score: Optional[float] = None
    review_count: int = 0


# ==================================================================
#  리뷰 (Review)
# ==================================================================
class ReviewCreate(BaseModel):
    """리뷰 등록 요청 바디"""
    author: str = Field(min_length=1, max_length=100, description="작성자 이름")
    content: str = Field(min_length=1, max_length=2000, description="리뷰 내용")

    @field_validator("author", "content")
    @classmethod
    def not_blank(cls, v: str) -> str:
        """작성자/내용의 앞뒤 공백을 제거하고, 공백만 있는 경우를 막습니다."""
        v = v.strip()
        if not v:
            raise ValueError("공백만으로는 입력할 수 없습니다.")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "author": "홍길동",
                "content": "시간 가는 줄 모르고 봤어요. 인생 영화입니다!",
            }
        }
    }


class ReviewResponse(BaseModel):
    """리뷰 응답 형태 (감성 분석 결과 포함)"""
    id: int
    movie_id: int
    author: str
    content: str
    sentiment: Optional[str] = None      # "긍정" / "부정" / "중립"
    score: Optional[float] = None        # 0.0 ~ 1.0 (긍정 확률)
    created_at: Optional[str] = None


# ==================================================================
#  평점 (Rating)
# ==================================================================
class RatingResponse(BaseModel):
    """특정 영화의 평점(감성 점수 평균) 응답"""
    movie_id: int
    avg_score: Optional[float] = None    # 감성 점수 평균 (0~1), 리뷰 없으면 None
    review_count: int = 0
