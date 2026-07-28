# 🎬 영화 리뷰 & 감성 분석 웹 애플리케이션

스프린트 미션 18 — 영화 정보, 사용자 리뷰, 리뷰 감성 분석을 표시하는 웹 애플리케이션입니다.

- **프론트엔드**: Streamlit
- **백엔드**: FastAPI
- **데이터베이스**: SQLite (표준 라이브러리 `sqlite3`만 사용, ORM 미사용)
- **감성 분석**: KcELECTRA 계열 한국어 모델 + 규칙 기반 폴백
- **GitHub**: [바로가기](https://github.com/minjaejeon0827/sprint_mission18)
- **Docker Hub**: [바로가기](https://hub.docker.com/r/minjaejeon0827/sprint_mission18-movie-review)

---

## 📁 디렉토리 구조

```
movie-review-app/
├── backend/                    # FastAPI 백엔드
│   ├── main.py                 # 앱 진입점 (lifespan, CORS, 라우터 등록)
│   ├── database.py             # sqlite3 기반 연결/테이블/의존성 주입
│   ├── schemas.py              # Pydantic 요청/응답 스키마
│   ├── sentiment.py            # 감성 분석 (ML 모델 + 규칙 기반 폴백)
│   ├── auth.py                 # API 키 인증
│   ├── routers/
│   │   ├── movies.py           # 영화 CRUD
│   │   └── reviews.py          # 리뷰 CRUD + 감성분석 + 평점
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── frontend/                   # Streamlit 프론트엔드
│   ├── streamlit_app.py        # 영화 목록/추가/리뷰 3개 탭
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .streamlit/
│       └── secrets.toml.example
├── docker-compose.yml          # 백엔드+프론트엔드 통합 실행
└── report/
    └── 보고서.pdf
```

---

## 🚀 실행 방법

### 방법 A. Docker Compose (권장)

```bash
docker compose up -d --build
```

- 프론트엔드: http://localhost:8501
- 백엔드 API 문서: http://localhost:8000/docs

### 방법 B. 로컬 직접 실행

**백엔드**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**프론트엔드** (다른 터미널)
```bash
cd frontend
pip install -r requirements.txt
export BACKEND_URL=http://localhost:8000
export API_KEY=my-secret-key-12345
streamlit run streamlit_app.py
```

> 💡 감성 분석 모델 없이 규칙 기반으로만 빠르게 테스트하려면 백엔드 실행 시
> `USE_ML_MODEL=0` 환경변수를 지정하세요. (모델 다운로드를 건너뜁니다.)

---

## 🔑 환경변수

| 변수 | 위치 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `API_KEYS` | 백엔드 | `my-secret-key-12345` | 유효한 API 키(쉼표로 여러 개) |
| `CORS_ORIGINS` | 백엔드 | `*` | CORS 허용 출처(쉼표 구분) |
| `USE_ML_MODEL` | 백엔드 | `1` | `0`이면 규칙 기반만 사용 |
| `SENTIMENT_MODEL` | 백엔드 | `matthewburke/korean_sentiment` | 사용할 감성 분석 모델 |
| `DB_PATH` | 백엔드 | `backend/movies.db` | SQLite 파일 경로 |
| `BACKEND_URL` | 프론트 | `http://localhost:8000` | 백엔드 주소 |
| `API_KEY` | 프론트 | `my-secret-key-12345` | 백엔드 호출용 API 키 |

---

## 📡 API 엔드포인트

모든 요청에는 `X-API-Key` 헤더가 필요합니다. (`/`, `/health` 제외)

| 메서드 | 경로 | 기능 |
| --- | --- | --- |
| POST | `/movies` | 영화 등록 |
| GET | `/movies` | 전체 영화 조회 (평균 감성 점수 포함) |
| GET | `/movies/{id}` | 특정 영화 조회 |
| DELETE | `/movies/{id}` | 특정 영화 삭제 (리뷰 함께 삭제) |
| POST | `/movies/{id}/reviews` | 리뷰 등록 (감성 자동 분석) |
| GET | `/movies/{id}/reviews` | 특정 영화의 리뷰 조회 |
| GET | `/reviews?limit=10` | 전체 리뷰 조회 (최근순) |
| GET | `/movies/{id}/rating` | 특정 영화의 평점(감성 평균) |

### 예시

```bash
# 영화 등록
curl -X POST http://localhost:8000/movies \
  -H "X-API-Key: my-secret-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"title":"인터스텔라","release_date":"2014-11-06","director":"크리스토퍼 놀란","genre":"SF, 드라마"}'

# 리뷰 등록 (감성 자동 분석)
curl -X POST http://localhost:8000/movies/1/reviews \
  -H "X-API-Key: my-secret-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"author":"홍길동","content":"정말 재밌고 감동적인 영화였어요!"}'
# → {"sentiment":"긍정","score":0.97, ...}
```

---

## 🗄️ 데이터베이스 (SQLite · sqlite3)

- `movies` 테이블: id, title, release_date, director, genre, poster_url, created_at
- `reviews` 테이블: id, movie_id(FK), author, content, sentiment, score, created_at
- `reviews.movie_id` → `movies.id` (외래키, `ON DELETE CASCADE`)

**ORM(SQLAlchemy)을 사용하지 않고 표준 라이브러리 `sqlite3`만으로** 구현했으며,
파라미터화된 쿼리(`?` 플레이스홀더)로 SQL 인젝션을 방지합니다.

---

## 🤖 감성 분석 & 경량화

1. **1순위**: KcELECTRA 계열 한국어 감성 분류 모델 (서버 시작 시 1회 로드)
2. **2순위**: 모델 로드 실패 시 규칙 기반(사전) 분석으로 자동 폴백

**경량화 전략**: 싱글턴 로드, ELECTRA 경량 아키텍처, 추론 시 그래디언트 비활성화,
입력 길이 제한, CPU 스레드 수 조정. (추가로 양자화·ONNX·배치 추론 가능)

---

## ☁️ 배포

- **프론트엔드**: GitHub 연동 → Streamlit Cloud (secrets.toml에 backend_url, api_key 설정)
- **백엔드**: Docker 이미지 빌드 → GCP Cloud Run 등 (환경변수로 API_KEYS, CORS_ORIGINS 주입)

---

## 참고

### 미션 소개

어느덧 스프린트의 마지막 미션입니다.
첫번째 미션을 기억해보세요. 우리는 파이썬 기초 문제를 풀었는데요.
어느덧 스스로 프론트엔드와 백엔드, 모델 서빙까지 전부 다룰 수 있는 AI 엔지니어가 되었습니다.
스스로와 여러분들의 동료들께 수고하셨다는 한마디 어떨까요!

마지막 미션에서는 영화 정보, 사용자 리뷰, 리뷰 감성 분석을 표시하는 웹 애플리케이션을 개발해봅니다.
프론트엔드는 **Streamlit**, 백엔드는 **FastAPI**로 구축합니다.

---

### 가이드라인

(심화)라고 작성된 부분은 선택사항입니다. 시간적으로 여유가 되면 진행해보세요.

#### 프론트엔드 (Streamlit)

##### 기능

- **영화 목록 표시**
  - 제목, 포스터 이미지, (옵션) 평균 평점 표시
- **영화 추가**
  - 입력: 제목, 개봉일, 감독, 장르, 포스터 URL(웹페이지에서 검색 후 영화 정보 이미지 클릭 시 얻게 되는 포스터 URL 주소 가져다가 사용)

(심화)

- **리뷰 등록**
  - 저장된 영화 선택
  - 작성자 이름, 리뷰 내용 입력
- **리뷰 감성 분석**
  - 리뷰 작성 후 자동 실행
  - 감성 분석 결과 표시 (예) 긍정, 부정, 중립
- **리뷰 표시**
  - 최근 10개 리뷰 표시
  - 항목: 영화 ID, 등록일, 리뷰 내용, 감성 분석 결과

##### 배포

- Streamlit Cloud

##### 참고

- 모든 데이터는 백엔드에서 관리
- Streamlit 내부에서 별도 저장 기능 사용 안 함

#### 백엔드 (FastAPI)

##### 기능

- **영화 관리**
  - 등록: 제목, 개봉일, 감독, 장르, 포스터 URL (나무위키 참고)
  - 전체/특정 영화 조회
  - 특정 영화 삭제

(심화)

- **리뷰 관리**
  - 등록, 전체/특정 영화 리뷰 조회, 삭제
- **평점 조회**
  - 리뷰 감성 분석 점수의 평균
- **리뷰 감성 분석**
  - 모델: 적절한 모델 리서치하여 적용
  - 모델 경량화 방식에 대해 고민해보기

---

### 제출 안내

미션 18 폴더 하위에 {팀명}_{이름}으로 폴더를 생성하고, 그 안에 아래 제시된 항목들을 포함해서 아래 항목들을 제출하세요.

- 보고서 pdf
  - 서비스 개요
  - 서비스 구조도
    - 프론트엔드, 백엔드, (심화) 모델 서빙 관련
    - 데이터 베이스 구조도(ERD) - 데이터베이스 안에 있는 엔티티(개체)와 속성(값), 그리고 이들이 맺는 서로의 관계를 보여줌.(각각 컬럼 이름, 타입 포함 필수)
  - FastAPI Docs 전체 캡쳐 (설명 명세 포함)
  - 서비스 동작 캡쳐 이미지
    - 영화 3개 이상 등록
    - 각 영화당 리뷰 10개 이상 등록
- 코드
  - frontend, backend 폴더로 구분하여 저장

---