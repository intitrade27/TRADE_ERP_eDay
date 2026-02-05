# -*- coding: utf-8 -*-
"""
설정 관리 모듈
- 환경변수 로드 (개별 API 키 관리)
- 오류 추적 로깅
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MASTER_DATA_DIR = DATA_DIR / "master"
UPLOADS_DIR = DATA_DIR / "uploads"
LOGS_DIR = PROJECT_ROOT / "logs"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# 디렉토리 생성
for dir_path in [LOGS_DIR, MASTER_DATA_DIR, PROCESSED_DATA_DIR, TEMPLATES_DIR, UPLOADS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 로깅 설정
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.FileHandler(LOGS_DIR / "app.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

setup_logging()
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """설정 오류"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class Settings:
    """환경설정 - 싱글톤"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if Settings._initialized:
            return
        
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"[CONFIG] .env 로드: {env_path}")
        else:
            logger.warning(f"[CONFIG] .env 파일 없음. .env.example을 복사하세요.")
        
        Settings._initialized = True
    
    def _get_env(self, key: str, default: str = None) -> Optional[str]:
    # 1순위: 시스템 환경변수 (.env 또는 OS 환경변수)
        value = os.getenv(key)
        if value:
            return value
        
        # 2순위: Streamlit Secrets (Cloud 배포용)
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and key in st.secrets:
                return str(st.secrets[key])
        except Exception:
            pass
        
        # 3순위: 기본값
        return default
    
    # ============ Unipass API (개별 키) ============
    @property
    def unipass_hs_code_api_key(self) -> Optional[str]:
        """HS CODE 조회 API 키"""
        return self._get_env("UNIPASS_HS_CODE_API_KEY")
    
    @property
    def unipass_tariff_api_key(self) -> Optional[str]:
        """관세율 조회 API 키"""
        return self._get_env("UNIPASS_TARIFF_API_KEY")
    
    @property
    def unipass_customs_check_api_key(self) -> Optional[str]:
        """세관장확인대상물품 API 키"""
        return self._get_env("UNIPASS_CUSTOMS_CHECK_API_KEY")
    
    @property
    def unipass_cargo_api_key(self) -> Optional[str]:
        """(제거됨) 화물통관진행정보 API 키"""
        return None

    # ============ 환율 API ============
    @property
    def exim_api_key(self) -> Optional[str]:
        return self._get_env("EXIM_API_KEY")
    
    # ============ OpenAI ============
    @property
    def openai_api_key(self) -> Optional[str]:
        return self._get_env("OPENAI_API_KEY")
    
    # ============ Google Calendar ============
    @property
    def google_calendar_id(self) -> str:
        return self._get_env("GOOGLE_CALENDAR_ID", "primary")
    
    @property
    def google_credentials_path(self) -> Path:
        return PROJECT_ROOT / "credentials.json"
    
    @property
    def google_token_path(self) -> Path:
        return PROJECT_ROOT / "token.json"
    
    # ============ Telegram ============
    @property
    def telegram_bot_token(self) -> Optional[str]:
        """(제거됨) Telegram Bot Token"""
        return None

    @property
    def telegram_chat_id(self) -> Optional[str]:
        """(제거됨) Telegram Chat ID"""
        return None

    # ============ KakaoTalk ============
    @property
    def kakao_rest_api_key(self) -> Optional[str]:
        """(제거됨) Kakao REST API Key"""
        return None

    @property
    def kakao_redirect_uri(self) -> str:
        """(제거됨) Kakao Redirect URI"""
        return ""

    # ============ Email (SMTP) ============
    @property
    def smtp_server(self) -> str:
        return self._get_env("SMTP_SERVER", "smtp.gmail.com")
    
    @property
    def smtp_port(self) -> int:
        return int(self._get_env("SMTP_PORT", "587"))
    
    @property
    def smtp_email(self) -> Optional[str]:
        return self._get_env("SMTP_EMAIL")
    
    @property
    def smtp_password(self) -> Optional[str]:
        return self._get_env("SMTP_PASSWORD")
    
    @property
    def alert_recipient_email(self) -> Optional[str]:
        return self._get_env("ALERT_RECIPIENT_EMAIL")
    
    # ============ Naver ============
    @property
    def naver_client_id(self) -> Optional[str]:
        return self._get_env("NAVER_CLIENT_ID")
    
    @property
    def naver_client_secret(self) -> Optional[str]:
        return self._get_env("NAVER_CLIENT_SECRET")
    
    # ============ App ============
    @property
    def app_secret_key(self) -> str:
        return self._get_env("APP_SECRET_KEY", "default_secret_change_me")
    
    @property
    def debug_mode(self) -> bool:
        return self._get_env("DEBUG_MODE", "False").lower() == "true"
    
    # ============ Validation ============
    def validate_api_keys(self) -> dict:
        """API 키 상태 확인"""
        status = {
            "unipass_hs_code": {"set": bool(self.unipass_hs_code_api_key), "required": True, "desc": "관세청 HS CODE API"},
            "unipass_tariff": {"set": bool(self.unipass_tariff_api_key), "required": True, "desc": "관세청 관세율 API"},
            "unipass_customs": {"set": bool(self.unipass_customs_check_api_key), "required": True, "desc": "관세청 세관장확인 API"},
            "exim_bank": {"set": bool(self.exim_api_key), "required": True, "desc": "수출입은행 환율 API"},
            "openai": {"set": bool(self.openai_api_key), "required": True, "desc": "OpenAI API (이미지분석)"},
            "google_calendar": {"set": self.google_credentials_path.exists(), "required": True, "desc": "Google Calendar (credentials.json)"},
            "email": {"set": bool(self.smtp_email and self.smtp_password), "required": False, "desc": "이메일 알림 (SMTP)"},
        }
        return status


settings = Settings()
