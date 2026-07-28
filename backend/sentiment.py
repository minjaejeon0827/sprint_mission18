"""
sentiment.py
-------------
리뷰 텍스트의 감성(긍정/부정/중립)을 분석하는 모듈입니다.

[설계 철학 — 2단계 폴백 구조]
  1순위: Hugging Face 사전학습 한국어 감성 분류 모델 (Transformers)
         - 기본값: 'matthewburke/korean_sentiment' (KcELECTRA 기반, 경량)
         - 환경변수 SENTIMENT_MODEL 로 교체 가능
  2순위: 모델 로드 실패 시(오프라인/저사양 서버 등) → 규칙 기반(사전) 분석
         - 외부 의존성 없이 항상 동작하는 안전장치(fallback)

[모델 경량화(요구사항)에 대한 고민 — 실제 적용된 전략]
  (1) 모델을 서버 시작 시 "한 번만" 로드하고 메모리에 상주시켜 재사용
      → 요청마다 재로드하는 낭비를 제거 (lifespan / 싱글턴)
  (2) BERT-base(약 110M) 대신 ELECTRA-small 계열의 경량 모델 사용 가능
      → 파라미터 수가 적어 CPU 추론도 실용적인 속도
  (3) torch.no_grad() 로 추론 시 그래디언트 계산을 끔 → 메모리/속도 개선
  (4) 입력 길이를 max_length 로 제한(truncation) → 긴 리뷰도 안정적 처리
  (5) (추가 확장) 동적 양자화(quantization), ONNX 변환, 배치 추론 등을
      README/보고서에 명시 — 실서비스에서는 이 방향으로 더 경량화 가능
"""

import os
import re
from typing import Dict

# ------------------------------------------------------------------
# 환경변수
#   USE_ML_MODEL=0 으로 두면 아예 규칙 기반만 사용 (모델 다운로드 안 함)
#   SENTIMENT_MODEL 로 사용할 허깅페이스 모델을 지정
# ------------------------------------------------------------------
USE_ML_MODEL = os.environ.get("USE_ML_MODEL", "1") == "1"
SENTIMENT_MODEL = os.environ.get(
    "SENTIMENT_MODEL", "matthewburke/korean_sentiment"
)

# 라벨 표기 (한국어)
POSITIVE = "긍정"
NEGATIVE = "부정"
NEUTRAL = "중립"


# ==================================================================
#  규칙 기반 분석기 (폴백 / 항상 동작)
# ==================================================================
# 영화 리뷰에서 자주 등장하는 긍/부정 표현 사전.
# 완벽하진 않지만, ML 모델을 못 쓰는 환경에서도 서비스가
# 멈추지 않도록 하는 "안전장치" 역할을 합니다.
_POSITIVE_WORDS = [
    "재밌", "재미있", "최고", "명작", "감동", "훌륭", "완벽", "추천",
    "좋았", "좋은", "좋아", "인생", "대박", "몰입", "여운", "만족",
    "볼만", "수작", "걸작", "웃겼", "행복", "따뜻", "신선", "탄탄",
    "빠져", "황홀", "짱", "굿", "최애", "꿀잼", "흥미", "멋있", "멋진",
]
_NEGATIVE_WORDS = [
    "재미없", "노잼", "별로", "최악", "실망", "지루", "아깝", "졸작",
    "형편없", "끔찍", "억지", "불편", "그저그", "그냥", "낭비", "후회",
    "산만", "어색", "루즈", "뻔한", "유치", "발연기", "쓰레기", "망작",
    "짜증", "답답", "허무", "느슨", "과하", "실패",
]


def _rule_based(text: str) -> Dict:
    """
    사전 기반으로 긍/부정 단어 등장 횟수를 세어 감성을 판정합니다.

    반환: {"sentiment": ..., "score": 0~1, "engine": "rule"}
      score 는 긍정 정도를 0~1 로 환산한 값입니다.
    """
    pos = sum(1 for w in _POSITIVE_WORDS if w in text)
    neg = sum(1 for w in _NEGATIVE_WORDS if w in text)

    total = pos + neg
    if total == 0:
        # 판단 근거가 없으면 중립 (score 0.5)
        return {"sentiment": NEUTRAL, "score": 0.5, "engine": "rule"}

    score = pos / total  # 긍정 비율
    if score >= 0.6:
        sentiment = POSITIVE
    elif score <= 0.4:
        sentiment = NEGATIVE
    else:
        sentiment = NEUTRAL
    return {"sentiment": sentiment, "score": round(score, 4), "engine": "rule"}


# ==================================================================
#  ML 모델 분석기 (싱글턴 로딩)
# ==================================================================
# 파이프라인 객체를 모듈 전역에 캐시해 "한 번만" 로드합니다.
_pipeline = None
_pipeline_load_failed = False


def _load_pipeline():
    """
    Transformers 감성 분석 파이프라인을 지연 로딩(lazy load)합니다.

    - 최초 1회만 실제 로드가 일어나고, 이후에는 캐시된 객체를 재사용합니다.
    - 로드에 실패하면 _pipeline_load_failed 를 True 로 표시하고
      이후에는 규칙 기반으로만 동작합니다.
    """
    global _pipeline, _pipeline_load_failed

    if _pipeline is not None:
        return _pipeline
    if _pipeline_load_failed or not USE_ML_MODEL:
        return None

    try:
        # 무거운 import 는 실제 필요할 때만 수행
        from transformers import pipeline
        import torch

        # device=-1 은 CPU. GPU 가 있으면 0 이상으로 바꾸면 됩니다.
        _pipeline = pipeline(
            task="sentiment-analysis",
            model=SENTIMENT_MODEL,
            device=-1,
            truncation=True,
            max_length=256,   # 입력 길이 제한 → 안정성/속도 확보(경량화)
        )
        # 스레드 수를 제한해 CPU 환경에서 과도한 점유를 막음
        try:
            torch.set_num_threads(max(1, os.cpu_count() // 2))
        except Exception:
            pass
        return _pipeline
    except Exception as exc:  # 네트워크 불가, 메모리 부족 등
        print(f"[sentiment] ML 모델 로드 실패 → 규칙 기반으로 대체합니다: {exc}")
        _pipeline_load_failed = True
        return None


def _normalize_label(label: str, score: float) -> Dict:
    """
    허깅페이스 모델마다 라벨 표기가 달라서(LABEL_0/1, positive/negative 등)
    이를 우리 서비스의 표준 표기(긍정/부정/중립)로 통일합니다.

    score 는 "긍정 확률(0~1)" 로 통일합니다.
    """
    label_low = str(label).lower()

    # 모델이 내놓은 확신도(score)는 "예측한 라벨"에 대한 확률입니다.
    # 이를 항상 '긍정 확률'로 환산합니다.
    is_positive = label_low in ("label_1", "positive", "pos", "1", "긍정")
    is_negative = label_low in ("label_0", "negative", "neg", "0", "부정")

    if is_positive:
        pos_prob = float(score)
    elif is_negative:
        pos_prob = 1.0 - float(score)
    else:
        pos_prob = 0.5  # 알 수 없는 라벨 → 중립 취급

    # 긍정 확률을 기준으로 3분류
    if pos_prob >= 0.6:
        sentiment = POSITIVE
    elif pos_prob <= 0.4:
        sentiment = NEGATIVE
    else:
        sentiment = NEUTRAL

    return {"sentiment": sentiment, "score": round(pos_prob, 4), "engine": "ml"}


def analyze_sentiment(text: str) -> Dict:
    """
    외부에 공개되는 메인 함수.
    리뷰 텍스트를 받아 감성 분석 결과를 딕셔너리로 반환합니다.

    반환 형태:
      {
        "sentiment": "긍정" | "부정" | "중립",
        "score": 0.0 ~ 1.0,     # 긍정 확률
        "engine": "ml" | "rule" # 어떤 엔진으로 분석했는지
      }
    """
    text = (text or "").strip()
    if not text:
        return {"sentiment": NEUTRAL, "score": 0.5, "engine": "rule"}

    # 1순위: ML 모델
    pipe = _load_pipeline()
    if pipe is not None:
        try:
            # 공백/특수문자만 잔뜩 있는 경우를 대비해 가볍게 정리
            cleaned = re.sub(r"\s+", " ", text)
            result = pipe(cleaned)[0]  # {'label': ..., 'score': ...}
            return _normalize_label(result["label"], result["score"])
        except Exception as exc:
            print(f"[sentiment] ML 추론 중 오류 → 규칙 기반으로 대체: {exc}")

    # 2순위: 규칙 기반 폴백
    return _rule_based(text)


def warmup() -> str:
    """
    서버 시작 시 호출해 모델을 미리 로드(예열)합니다.
    첫 요청이 느려지는 콜드 스타트를 완화하는 용도입니다.

    반환: 현재 사용 중인 엔진 이름 ("ml" 또는 "rule")
    """
    pipe = _load_pipeline()
    if pipe is not None:
        # 짧은 문장으로 한 번 추론해 내부 그래프를 초기화
        try:
            analyze_sentiment("예열용 문장입니다.")
        except Exception:
            pass
        return "ml"
    return "rule"
