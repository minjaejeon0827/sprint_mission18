"""
streamlit_app.py
-----------------
영화 리뷰 & 감성 분석 서비스의 프론트엔드(Streamlit)입니다.

특징
  - 모든 데이터는 FastAPI 백엔드에서 관리합니다.
    (Streamlit 은 화면만 담당하고, 자체 저장 기능은 사용하지 않습니다.)
  - 백엔드 주소/API 키는 st.secrets 또는 환경변수에서 읽어와
    로컬 개발과 클라우드 배포 양쪽에서 코드 수정 없이 동작합니다.

화면 구성 (탭)
  1) 영화 목록   : 등록된 영화를 카드 형태로 표시 (포스터/평점 포함)
  2) 영화 추가   : 제목/개봉일/감독/장르/포스터 URL 입력 후 등록
  3) 리뷰        : 영화 선택 → 리뷰 작성(감성 자동 분석) + 최근 10개 리뷰 표시

포스터 이미지 생성 방법
  1) 나무위키 웹페이지 접속 → 영화 검색 → 포스터 우클릭 → "이미지 주소 복사(Copy image address)"
  2) "https://www.themoviedb.org/" TMDB(영화 데이터베이스) 웹페이지 접속 → 영화 검색 → 포스터 우클릭 → "이미지 주소 복사(Copy image address)"

참고
  - Streamlit: https://docs.streamlit.io/develop/api-reference/media/st.image
"""

import os
import requests
import streamlit as st

# ==================================================================
#  설정 — 백엔드 주소 & API 키
#   우선순위: st.secrets > 환경변수 > 기본값(localhost)
# ==================================================================
def _get_secret(section: str, key: str, default: str) -> str:
    try:
        return st.secrets.get(section, {}).get(key, None) or default
    except Exception:
        return default


API_URL = _get_secret("api", "backend_url", None) or os.environ.get(
    "BACKEND_URL", "http://localhost:8000"
)
API_KEY = _get_secret("api", "api_key", None) or os.environ.get(
    "API_KEY", "my-secret-key-12345"
)
HEADERS = {"X-API-Key": API_KEY}
TIMEOUT = 15  # 감성 분석 모델 추론을 고려해 넉넉히 설정


# ==================================================================
#  API 호출 헬퍼 (에러를 사용자 친화적으로 처리)
# ==================================================================
def api_get(path: str, params=None):
    try:
        r = requests.get(f"{API_URL}{path}", headers=HEADERS, params=params, timeout=TIMEOUT)
        return r
    except requests.exceptions.RequestException as e:
        st.error(f"백엔드 서버에 연결할 수 없습니다: {e}")
        return None


def api_post(path: str, json=None):
    try:
        r = requests.post(f"{API_URL}{path}", headers=HEADERS, json=json, timeout=TIMEOUT)
        return r
    except requests.exceptions.RequestException as e:
        st.error(f"백엔드 서버에 연결할 수 없습니다: {e}")
        return None


def api_delete(path: str):
    try:
        r = requests.delete(f"{API_URL}{path}", headers=HEADERS, timeout=TIMEOUT)
        return r
    except requests.exceptions.RequestException as e:
        st.error(f"백엔드 서버에 연결할 수 없습니다: {e}")
        return None


def sentiment_badge(sentiment: str) -> str:
    """감성 라벨에 이모지를 붙여 보기 좋게 만듭니다."""
    return {
        "긍정": "😊 긍정",
        "부정": "😞 부정",
        "중립": "😐 중립",
    }.get(sentiment, sentiment or "-")
  
def show_image_responsive(image, width=None):
    """
    st.image 를 Streamlit 버전에 상관없이 안전하게 표시합니다.

    - width 를 지정하면 그 픽셀 너비로 '작게 고정'해서 표시합니다.
      (포스터가 너무 커지는 것을 막는 용도. width 는 모든 버전에서 지원)
    - width 가 없으면 컨테이너 폭에 맞춰 표시합니다.
      · Streamlit 1.36+ : use_container_width=True
      · 그 이전 버전     : use_column_width=True
      · 아주 옛 버전     : 인자 없이
    """
    if width is not None:
        st.image(image, width=width)
        return
    try:
        st.image(image, use_container_width=True)
    except TypeError:
        try:
            st.image(image, use_column_width=True)
        except TypeError:
            st.image(image)

  
# 아래 주석친 코드 필요 시 참고(2026.07.29 minjae)  
# def show_image_responsive(image):
#     """
#     st.image 를 Streamlit 버전에 상관없이 '가로 폭 꽉 채우기'로 표시합니다.

#     - Streamlit 1.36+ : st.image(..., use_container_width=True)
#     - 그 이전 버전     : st.image(..., use_column_width=True)
#     배포 환경의 Streamlit 버전이 낮아
#       "unexpected keyword argument 'use_container_width'"
#     오류가 나는 경우를 자동으로 회피합니다.
#     """
#     try:
#         st.image(image, use_container_width=True)
#     except TypeError:
#         # 구버전 폴백 (use_container_width 미지원)
#         try:
#             st.image(image, use_column_width=True)
#         except TypeError:
#             # 두 인자 모두 없는 아주 옛 버전 → 인자 없이 표시
#             st.image(image)

# ==================================================================
#  페이지 기본 설정
# ==================================================================
st.set_page_config(page_title="영화 리뷰 & 감성 분석", page_icon="🎬", layout="wide")

st.title("🎬 영화 리뷰 & 감성 분석 서비스")
st.caption("FastAPI 백엔드 + Streamlit 프론트엔드 · 리뷰 감성 자동 분석")

# 사이드바: 백엔드 연결 상태 표시
with st.sidebar:
    st.header("⚙️ 연결 정보")
    # 아래 주석친 코드 필요 시 참고(2026.07.29 minjae)
    # st.write(f"**백엔드**: `{API_URL}`")
    health = api_get("/health")
    if health is not None and health.status_code == 200:
        st.success("✅ 백엔드 연결됨")
    else:
        st.error("❌ 백엔드 연결 실패")
    st.divider()

    # ── 화면 표시 설정 (포스터 크기 조절) ──
    st.subheader("🖼️ 화면 설정")
    st.slider(
        "포스터 크기 (px)",
        min_value=80, max_value=320, value=160, step=20,
        key="poster_width",
        help="영화 포스터 이미지의 가로 크기를 조절합니다.",
    )
    st.slider(
        "한 줄에 표시할 영화 수",
        min_value=2, max_value=6, value=4, step=1,
        key="cards_per_row",
        help="한 줄에 나란히 보여줄 영화 카드 개수입니다.",
    )
    st.divider()
    st.caption("모든 데이터는 백엔드에서 관리됩니다.")


tab_list, tab_add, tab_review = st.tabs(["📋 영화 목록", "➕ 영화 추가", "📝 리뷰"])


# ------------------------------------------------------------------
#  탭 1: 영화 목록
# ------------------------------------------------------------------
with tab_list:
    st.subheader("등록된 영화")

    resp = api_get("/movies")
    if resp is not None and resp.status_code == 200:
        movies = resp.json()
        if not movies:
            st.info("아직 등록된 영화가 없습니다. '영화 추가' 탭에서 등록해보세요.")
        else:
            # 한 줄에 표시할 영화 수 & 포스터 너비 (사이드바 슬라이더에서 설정)
            per_row = st.session_state.get("cards_per_row", 4)
            poster_w = st.session_state.get("poster_width", 160)

            # per_row 열 그리드로 영화 카드 배치
            cols = st.columns(per_row)
            for idx, movie in enumerate(movies):
                with cols[idx % per_row]:
                    with st.container(border=True, width=poster_w):
                        # 포스터 표시 (안전하게)
                        #  - poster_url 이 None/빈문자열이면 건너뜀
                        #  - URL 이 있어도 깨진 주소/로딩 실패 시 앱이 죽지 않도록
                        #    try/except 로 감싸고, 실패하면 대체 문구를 보여줌
                        #  - poster_w(픽셀 너비)로 크기를 고정해 너무 커지지 않게 함
                        poster = movie.get("poster_url")
                        if poster and isinstance(poster, str) and poster.strip():
                            try:
                                # 아래 주석친 코드 필요 시 참고(2026.07.29 minjae)
                                # show_image_responsive(poster)
                                show_image_responsive(poster, width=poster_w)
                            except Exception as e:
                                st.error(str(e))
                                st.caption("🖼️ 포스터를 불러올 수 없습니다.")
                        else:
                            st.caption("🖼️ 등록된 포스터가 없습니다.")
                        st.markdown(f"### {movie['title']}")
                        st.write(f"📅 개봉일: {movie.get('release_date') or '-'}")
                        st.write(f"🎬 감독: {movie.get('director') or '-'}")
                        st.write(f"🏷️ 장르: {movie.get('genre') or '-'}")

                        # 평균 감성 점수(평점)를 별점 느낌으로 표시
                        avg = movie.get("avg_score")
                        cnt = movie.get("review_count", 0)
                        if avg is not None:
                            st.metric(
                                "평균 감성 점수",
                                f"{avg*100:.0f} / 100",
                                help=f"리뷰 {cnt}개의 긍정 확률 평균",
                            )
                        else:
                            st.caption("아직 리뷰가 없습니다.")

                        if st.button("🗑️ 삭제", key=f"del_movie_{movie['id']}"):
                            d = api_delete(f"/movies/{movie['id']}")
                            if d is not None and d.status_code == 200:
                                st.success("삭제되었습니다.")
                                st.rerun()
                            else:
                                st.error("삭제에 실패했습니다.")
    elif resp is not None:
        st.error(f"목록 조회 실패: {resp.status_code}")


# ------------------------------------------------------------------
#  탭 2: 영화 추가
# ------------------------------------------------------------------
with tab_add:
    st.subheader("새 영화 등록")

    with st.form("add_movie_form"):
        title = st.text_input("제목 *", placeholder="예: 인터스텔라")
        col1, col2 = st.columns(2)
        with col1:
            release_date = st.text_input("개봉일", placeholder="예: 2014-11-06")
            director = st.text_input("감독", placeholder="예: 크리스토퍼 놀란")
        with col2:
            genre = st.text_input("장르", placeholder="예: SF, 드라마")
            poster_url = st.text_input(
                "포스터 URL", placeholder="https://... (나무위키 등의 이미지 주소)"
            )

        submitted = st.form_submit_button("등록하기", type="primary", use_container_width=True)

        if submitted:
            if not title.strip():
                st.warning("제목은 필수 입력 항목입니다.")
            else:
                payload = {
                    "title": title.strip(),
                    "release_date": release_date.strip() or None,
                    "director": director.strip() or None,
                    "genre": genre.strip() or None,
                    "poster_url": poster_url.strip() or None,
                }
                r = api_post("/movies", json=payload)
                if r is not None and r.status_code == 201:
                    st.success(f"'{title}' 영화가 등록되었습니다! '영화 목록' 탭에서 확인하세요.")
                elif r is not None:
                    st.error(f"등록 실패: {r.status_code} - {r.text}")


# ------------------------------------------------------------------
#  탭 3: 리뷰 (등록 + 최근 10개 표시)
# ------------------------------------------------------------------
with tab_review:
    st.subheader("리뷰 작성 및 감성 분석")

    # 영화 목록을 불러와 선택 박스 구성
    resp = api_get("/movies")
    movies = resp.json() if (resp is not None and resp.status_code == 200) else []

    if not movies:
        st.info("리뷰를 작성하려면 먼저 영화를 등록해야 합니다.")
    else:
        # {표시이름: id} 매핑
        options = {f"[{m['id']}] {m['title']}": m["id"] for m in movies}
        selected_label = st.selectbox("영화 선택", list(options.keys()))
        selected_movie_id = options[selected_label]

        with st.form("add_review_form"):
            author = st.text_input("작성자 이름 *", placeholder="예: 홍길동")
            content = st.text_area(
                "리뷰 내용 *", placeholder="영화에 대한 감상을 남겨주세요.", height=120
            )
            review_submitted = st.form_submit_button(
                "리뷰 등록 (감성 자동 분석)", type="primary", use_container_width=True
            )

            if review_submitted:
                if not author.strip() or not content.strip():
                    st.warning("작성자 이름과 리뷰 내용을 모두 입력해주세요.")
                else:
                    with st.spinner("리뷰를 등록하고 감성을 분석하는 중..."):
                        r = api_post(
                            f"/movies/{selected_movie_id}/reviews",
                            json={"author": author.strip(), "content": content.strip()},
                        )
                    if r is not None and r.status_code == 201:
                        data = r.json()
                        st.success(
                            f"리뷰가 등록되었습니다! "
                            f"감성 분석 결과: **{sentiment_badge(data['sentiment'])}** "
                            f"(긍정 확률 {data['score']*100:.0f}%)"
                        )
                    elif r is not None:
                        st.error(f"등록 실패: {r.status_code} - {r.text}")

    st.divider()
    st.subheader("🕑 최근 리뷰 (최대 10개)")

    resp = api_get("/reviews", params={"limit": 10})
    if resp is not None and resp.status_code == 200:
        reviews = resp.json()
        if not reviews:
            st.info("아직 등록된 리뷰가 없습니다.")
        else:
            # 표 형태로 최근 리뷰 표시
            table_rows = []
            for rv in reviews:
                table_rows.append(
                    {
                        "리뷰 ID": rv["id"],
                        "영화 ID": rv["movie_id"],
                        "작성자": rv["author"],
                        "등록일": rv.get("created_at", "-"),
                        "리뷰 내용": rv["content"],
                        "감성": sentiment_badge(rv.get("sentiment")),
                        "점수": f"{(rv.get('score') or 0)*100:.0f}%",
                    }
                )
            st.dataframe(table_rows, use_container_width=True, hide_index=True)
    elif resp is not None:
        st.error(f"리뷰 조회 실패: {resp.status_code}")
