"""
pydantic-settings를 사용한 타입 안전한 설정 관리

Production에서는 환경변수를 통해 설정을 주입받습니다.
이 모듈은 환경변수를 타입 안전하게 파싱하고 검증합니다.

사용법:
    from app.core.config import settings

    # 환경변수 값 사용
    api_key = settings.upstage_api_key
    db_url = settings.supabase_url
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    애플리케이션 설정 클래스

    pydantic-settings를 사용하여 환경변수를 자동으로 로드합니다.
    각 필드는 환경변수 이름과 1:1로 매핑됩니다. (대소문자 무시)

    예시:
        UPSTAGE_API_KEY=xxx  ->  settings.upstage_api_key
    """

    # ===== 환경 설정 =====
    # 개발/운영 환경 구분
    environment: Literal["development", "staging", "production", "test"] = "development"

    # 디버그 모드 (개발 환경에서만 True)
    debug: bool = True

    # ===== LLM API 설정 =====
    # Upstage Solar API 키 (필수)
    upstage_api_key: str = ""

    # 기본 LLM 모델명
    # Upstage Solar 모델: solar-pro, solar-mini
    llm_model: str = "solar-pro2"

    # ===== 데이터베이스 설정 =====
    # Supabase 프로젝트 URL
    supabase_url: str = ""

    # Supabase API 키 (anon key 또는 service_role key)
    supabase_key: str = ""

    # ===== API 서버 설정 =====
    # 서버 호스트
    host: str = "0.0.0.0"

    # 서버 포트
    port: int = 8000

    # pydantic-settings 설정
    model_config = SettingsConfigDict(
        # .env 파일 경로
        env_file=".env",
        # .env 파일 인코딩
        env_file_encoding="utf-8",
        # 대소문자 무시
        case_sensitive=False,
        # 추가 필드 무시 (환경변수에 정의되지 않은 값)
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    설정 객체를 반환합니다 (싱글톤 패턴)

    lru_cache 데코레이터를 사용하여 설정 객체를 캐싱합니다.
    이렇게 하면 애플리케이션 전체에서 동일한 설정 객체를 사용합니다.

    Returns:
        Settings: 설정 객체
    """
    return Settings()


# 전역 설정 객체
# 다른 모듈에서 `from app.core.config import settings`로 사용
settings = get_settings()
