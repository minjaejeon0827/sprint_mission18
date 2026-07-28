"""
auth.py
--------
API 키 기반의 간단한 인증 모듈입니다.

동작 방식
  - 클라이언트는 요청 헤더에 X-API-Key 를 담아 보냅니다.
  - 헤더가 아예 없으면 401 (누구인지도 모름),
    값이 등록 목록에 없으면 403 (신원은 밝혔으나 권한 없음) 을 반환합니다.

보안 원칙
  - 유효한 키 목록(VALID_API_KEYS)은 코드에 하드코딩하지 않고
    환경변수 API_KEYS 에서 읽어옵니다. (쉼표로 여러 개 지정 가능)
  - 로컬 개발 편의를 위해, 환경변수가 없으면 기본 키를 하나 둡니다.
    실제 배포 시에는 반드시 환경변수로 교체해야 합니다.
  - 키 비교는 hmac.compare_digest 로 상수 시간 비교하여
    타이밍 공격(입력이 얼마나 일치하는지 시간으로 추측하는 공격)을 방지합니다.
"""

import os
import hmac
import logging
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

logger = logging.getLogger("uvicorn.error")

# 헤더 이름 정의. auto_error=False 로 두면 헤더가 없어도
# FastAPI 가 자동 에러를 내지 않고, 우리가 직접 401/403 을 구분합니다.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# 환경변수에서 유효 키를 읽어옴 (쉼표 구분). 없으면 개발용 기본값 사용.
_DEFAULT_KEY = "my-secret-key-12345"
_env_keys = os.environ.get("API_KEYS", _DEFAULT_KEY)
VALID_API_KEYS = {k.strip() for k in _env_keys.split(",") if k.strip()}

# 운영 중 실수를 조기에 발견하기 위한 경고 로그
if not VALID_API_KEYS:
    logger.warning("[auth] 유효한 API 키가 하나도 설정되지 않았습니다. 모든 요청이 거부됩니다.")
elif VALID_API_KEYS == {_DEFAULT_KEY}:
    logger.warning(
        "[auth] 개발용 기본 API 키를 사용 중입니다. "
        "실제 배포 시에는 환경변수 API_KEYS 로 반드시 교체하세요."
    )


def _is_valid(api_key: str) -> bool:
    """
    등록된 키들과 상수 시간 비교로 대조합니다.
    (단순 `in` 비교보다 타이밍 공격에 안전합니다.)
    """
    return any(hmac.compare_digest(api_key, valid) for valid in VALID_API_KEYS)


def verify_api_key(api_key: str = Depends(api_key_header)) -> str:
    """
    API 키를 검증하는 의존성 함수.
    보호가 필요한 엔드포인트에 Depends(verify_api_key) 로 붙여 사용합니다.

      - 헤더 없음        -> 401 Unauthorized
      - 헤더는 있으나 무효 -> 403 Forbidden
    """
    if api_key is None:
        raise HTTPException(status_code=401, detail="X-API-Key 헤더가 필요합니다.")
    if not _is_valid(api_key):
        raise HTTPException(status_code=403, detail="유효하지 않은 API 키입니다.")
    return api_key
