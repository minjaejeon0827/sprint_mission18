"""
database.py
------------
표준 라이브러리 ``sqlite3`` 만 사용하여 데이터베이스를 다루는 모듈입니다.
(요구사항: SQLAlchemy 등 ORM 사용 금지 — sqlite3.connect 만 사용)

이 모듈이 담당하는 일
  1) DB 파일에 대한 커넥션 생성 (get_connection)
  2) 앱 시작 시 테이블 생성 (init_db)
  3) FastAPI 의존성 주입용 커넥션 제공자 (get_db)

설계 포인트
  - sqlite3 는 기본적으로 "커넥션을 만든 스레드에서만 사용" 하도록 제약을 둡니다.
    FastAPI 는 여러 스레드에서 요청을 처리할 수 있으므로
    check_same_thread=False 로 이 제약을 완화합니다.
  - row_factory 를 sqlite3.Row 로 지정하면, 조회 결과를
    딕셔너리처럼 컬럼명으로 접근할 수 있어 JSON 직렬화가 편해집니다.
"""

import os
import sqlite3
from typing import Generator

# ------------------------------------------------------------------
# DB 파일 경로
#   - 환경변수 DB_PATH 가 있으면 그 값을 사용하고,
#     없으면 이 파일과 같은 폴더의 movies.db 를 사용합니다.
#   - Docker Bind Mount 로 이 폴더가 호스트와 연결되어 있으면
#     컨테이너를 지워도 movies.db 파일(데이터)은 그대로 보존됩니다.
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "movies.db"))


def get_connection() -> sqlite3.Connection:
    """
    새 SQLite 커넥션을 만들어 반환합니다.

    - check_same_thread=False : 다중 스레드 환경(FastAPI)에서 사용 허용
    - row_factory=sqlite3.Row : row["title"] 처럼 컬럼명 접근 가능
    - PRAGMA foreign_keys=ON  : 외래키 제약(리뷰→영화)을 실제로 강제
                                (SQLite 는 기본적으로 외래키가 꺼져 있음)
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """
    앱이 시작될 때 한 번 호출되어 테이블을 생성합니다.

    CREATE TABLE IF NOT EXISTS 를 사용하므로,
    서버를 여러 번 재시작해도 기존 테이블/데이터를 건드리지 않습니다.

    테이블 구조
      movies : 영화 정보
      reviews: 리뷰 정보 (movies.id 를 외래키로 참조)
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # ── 영화 테이블 ────────────────────────────────────────────
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS movies (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT    NOT NULL,
                release_date TEXT,
                director     TEXT,
                genre        TEXT,
                poster_url   TEXT,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            """
        )

        # ── 리뷰 테이블 ────────────────────────────────────────────
        #   movie_id 는 movies(id) 를 참조하는 외래키입니다.
        #   ON DELETE CASCADE : 영화를 삭제하면 그 영화의 리뷰도 함께 삭제됩니다.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id    INTEGER NOT NULL,
                author      TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                sentiment   TEXT,
                score       REAL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE
            );
            """
        )

        conn.commit()
    finally:
        conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI 의존성 주입(Depends)용 함수.

    요청이 들어올 때마다 커넥션을 하나 열고(yield),
    요청 처리가 끝나면 finally 에서 반드시 닫습니다.
    이렇게 하면 커넥션 누수(close 를 깜빡하는 실수)를 방지할 수 있습니다.
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
