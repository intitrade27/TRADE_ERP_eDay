# -*- coding: utf-8 -*-
"""
Google Calendar API 모듈
- 캘린더 연동, 일정 CRUD
- D-Day 마감일 자동 계산
- Streamlit Cloud Secrets 지원 (v2.0)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import os
import json
import tempfile

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings
from config.constants import EXPORT_LOADING_DEADLINE_DAYS, ALERT_DAYS

logger = logging.getLogger(__name__)

# ============================================================
# Streamlit Cloud 배포 지원 함수
# ============================================================

def _get_credentials_path() -> Optional[str]:
    """
    credentials.json 경로 반환
    
    우선순위:
    1. 로컬 파일 (개발환경) - settings.google_credentials_path
    2. Streamlit Secrets에서 임시 파일 생성 (Cloud 배포)
    
    Returns:
        str: credentials.json 파일 경로 또는 None
    """
    # 1순위: 로컬 파일이 있으면 사용 (기존 방식 - 개발환경)
    local_path = settings.google_credentials_path
    if local_path.exists():
        logger.info(f"[GCAL] 로컬 credentials.json 사용: {local_path}")
        return str(local_path)
    
    # 2순위: Streamlit Secrets에서 읽기 (Cloud 배포)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and "google_credentials" in st.secrets:
            logger.info("[GCAL] Streamlit Secrets에서 credentials 로드 중...")
            
            # Secrets 내용을 딕셔너리로 변환
            gc = st.secrets["google_credentials"]
            
            # redirect_uris 처리 (리스트 또는 문자열)
            redirect_uris = gc.get("redirect_uris", ["http://localhost"])
            if isinstance(redirect_uris, str):
                redirect_uris = [redirect_uris]
            else:
                redirect_uris = list(redirect_uris)
            
            creds_dict = {
                "installed": {
                    "client_id": gc["client_id"],
                    "project_id": gc["project_id"],
                    "auth_uri": gc["auth_uri"],
                    "token_uri": gc["token_uri"],
                    "auth_provider_x509_cert_url": gc["auth_provider_x509_cert_url"],
                    "client_secret": gc["client_secret"],
                    "redirect_uris": redirect_uris
                }
            }
            
            # 임시 파일로 저장
            temp_path = "/tmp/gcloud_credentials.json"
            with open(temp_path, "w") as f:
                json.dump(creds_dict, f)
            
            logger.info(f"[GCAL] Secrets에서 임시 credentials 생성: {temp_path}")
            return temp_path
            
    except ImportError:
        logger.debug("[GCAL] Streamlit 미설치 - Secrets 사용 불가")
    except KeyError as e:
        logger.warning(f"[GCAL] Secrets에 google_credentials 키 누락: {e}")
    except Exception as e:
        logger.warning(f"[GCAL] Secrets에서 credentials 로드 실패: {e}")
    
    logger.warning("[GCAL] credentials.json을 찾을 수 없습니다.")
    return None


def _get_token_path() -> str:
    """
    token.json 경로 반환
    
    우선순위:
    1. 로컬 파일 (개발환경)
    2. Streamlit Secrets에서 임시 파일 생성 (Cloud 배포)
    3. 임시 디렉토리 경로 (신규 토큰 저장용)
    
    Returns:
        str: token.json 파일 경로
    """
    # 1순위: 로컬 파일 (개발환경)
    local_path = settings.google_token_path
    if local_path.exists():
        logger.info(f"[GCAL] 로컬 token.json 사용: {local_path}")
        return str(local_path)
    
    # 2순위: Streamlit Secrets에서 읽기 (Cloud 배포)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and "google_token" in st.secrets:
            logger.info("[GCAL] Streamlit Secrets에서 token 로드 중...")
            
            gt = st.secrets["google_token"]
            
            # scopes 처리 (리스트 또는 문자열)
            scopes = gt.get("scopes", ["https://www.googleapis.com/auth/calendar"])
            if isinstance(scopes, str):
                scopes = [scopes]
            else:
                scopes = list(scopes)
            
            token_dict = {
                "token": gt["token"],
                "refresh_token": gt["refresh_token"],
                "token_uri": gt["token_uri"],
                "client_id": gt["client_id"],
                "client_secret": gt["client_secret"],
                "scopes": scopes,
                "expiry": gt.get("expiry", "")
            }
            
            # 임시 파일로 저장
            temp_path = "/tmp/gcloud_token.json"
            with open(temp_path, "w") as f:
                json.dump(token_dict, f)
            
            logger.info(f"[GCAL] Secrets에서 임시 token 생성: {temp_path}")
            return temp_path
            
    except ImportError:
        logger.debug("[GCAL] Streamlit 미설치 - Secrets 사용 불가")
    except KeyError as e:
        logger.debug(f"[GCAL] Secrets에 google_token 키 누락: {e}")
    except Exception as e:
        logger.debug(f"[GCAL] Secrets에서 token 로드 실패: {e}")
    
    # 3순위: 로컬 경로 반환 (신규 토큰 저장용)
    # Cloud 환경에서는 /tmp 사용, 로컬에서는 설정 경로 사용
    if os.path.exists("/tmp"):
        return "/tmp/gcloud_token.json"
    
    return str(local_path)


# ============================================================
# 기존 클래스 (수정된 인증 로직)
# ============================================================

class GoogleCalendarError(Exception):
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        logger.error(f"[GCAL_ERROR] {error_code}: {message}")
        super().__init__(self.message)


class GoogleCalendarAPI:
    """Google Calendar API 래퍼"""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self):
        self.service = None
        self.calendar_id = settings.google_calendar_id
        self._authenticate()
    
    def _authenticate(self):
        """OAuth2 인증 (Streamlit Cloud Secrets 지원)"""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            logger.error("[GCAL] google-auth 패키지가 설치되지 않았습니다.")
            logger.error("[GCAL] pip install google-auth google-auth-oauthlib google-api-python-client")
            return
        
        creds = None
        
        # ★ 수정: 동적 경로 함수 사용
        token_path = _get_token_path()
        credentials_path = _get_credentials_path()
        
        # 기존 토큰 로드
        if token_path and os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
                logger.info(f"[GCAL] 토큰 로드 성공: {token_path}")
            except Exception as e:
                logger.warning(f"[GCAL] 토큰 로드 실패: {e}")
                creds = None
        
        # 토큰 갱신 또는 새로 발급
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("[GCAL] 토큰 갱신 성공")
                except Exception as e:
                    logger.warning(f"[GCAL] 토큰 갱신 실패: {e}")
                    creds = None
            
            # 새 토큰 발급 필요
            if not creds:
                if not credentials_path:
                    logger.error("[GCAL] credentials.json 파일이 없습니다.")
                    logger.error("[GCAL] 로컬: credentials.json 파일 배치")
                    logger.error("[GCAL] Cloud: Streamlit Secrets에 google_credentials 설정")
                    return
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=52202)
                    logger.info("[GCAL] 새 토큰 발급 성공")
                except Exception as e:
                    logger.error(f"[GCAL] OAuth 인증 실패: {e}")
                    return
            
            # 토큰 저장 (로컬 환경에서만)
            if token_path:
                try:
                    # Cloud 환경(/tmp)이 아닌 경우에만 저장 시도
                    if not token_path.startswith("/tmp"):
                        with open(token_path, 'w') as token:
                            token.write(creds.to_json())
                        logger.info(f"[GCAL] 토큰 저장: {token_path}")
                    else:
                        # Cloud 환경에서는 임시 저장
                        with open(token_path, 'w') as token:
                            token.write(creds.to_json())
                        logger.info(f"[GCAL] 토큰 임시 저장: {token_path}")
                except Exception as e:
                    logger.warning(f"[GCAL] 토큰 저장 실패: {e}")
        
        try:
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("[GCAL] Google Calendar 인증 완료")
        except Exception as e:
            logger.error(f"[GCAL] Calendar 서비스 빌드 실패: {e}")
            self.service = None
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.service is not None
    
    def get_events(self, start_date: datetime = None, end_date: datetime = None, max_results: int = 50) -> List[Dict]:
        """일정 조회"""
        if not self.service:
            return []
        
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=30)
        
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return [{
                'id': e.get('id'),
                'title': e.get('summary', ''),
                'description': e.get('description', ''),
                'start': e.get('start', {}).get('dateTime') or e.get('start', {}).get('date'),
                'end': e.get('end', {}).get('dateTime') or e.get('end', {}).get('date'),
                'location': e.get('location', ''),
            } for e in events]
        except Exception as e:
            logger.error(f"[GCAL] 일정 조회 실패: {e}")
            return []
    
    def create_event(
        self,
        title: str,
        start_date: datetime,
        end_date: datetime = None,
        description: str = "",
        location: str = "",
        reminders: List[int] = None,  # 알림 시간 (분 단위)
    ) -> Optional[str]:
        """일정 생성"""
        if not self.service:
            raise GoogleCalendarError("Google Calendar 연결 안됨", "NOT_CONNECTED")
        
        if not end_date:
            end_date = start_date + timedelta(hours=1)
        
        event = {
            'summary': title,
            'description': description,
            'location': location,
            'start': {'dateTime': start_date.isoformat(), 'timeZone': 'Asia/Seoul'},
            'end': {'dateTime': end_date.isoformat(), 'timeZone': 'Asia/Seoul'},
        }
        
        # 알림 설정
        if reminders:
            event['reminders'] = {
                'useDefault': False,
                'overrides': [{'method': 'popup', 'minutes': m} for m in reminders]
            }
        
        try:
            result = self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
            logger.info(f"[GCAL] 일정 생성: {title}")
            return result.get('id')
        except Exception as e:
            raise GoogleCalendarError(f"일정 생성 실패: {e}", "CREATE_ERROR")
    
    def update_event(self, event_id: str, **kwargs) -> bool:
        """일정 수정"""
        if not self.service:
            return False
        
        try:
            event = self.service.events().get(calendarId=self.calendar_id, eventId=event_id).execute()
            
            if 'title' in kwargs:
                event['summary'] = kwargs['title']
            if 'description' in kwargs:
                event['description'] = kwargs['description']
            if 'start_date' in kwargs:
                event['start'] = {'dateTime': kwargs['start_date'].isoformat(), 'timeZone': 'Asia/Seoul'}
            if 'end_date' in kwargs:
                event['end'] = {'dateTime': kwargs['end_date'].isoformat(), 'timeZone': 'Asia/Seoul'}
            
            self.service.events().update(calendarId=self.calendar_id, eventId=event_id, body=event).execute()
            logger.info(f"[GCAL] 일정 수정: {event_id}")
            return True
        except Exception as e:
            logger.error(f"[GCAL] 일정 수정 실패: {e}")
            return False
    
    def delete_event(self, event_id: str) -> bool:
        """일정 삭제"""
        if not self.service:
            return False
        
        try:
            self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
            logger.info(f"[GCAL] 일정 삭제: {event_id}")
            return True
        except Exception as e:
            logger.error(f"[GCAL] 일정 삭제 실패: {e}")
            return False


class DeadlineManager:
    """마감일 관리 (D-Day 계산)"""
    
    def __init__(self):
        self.calendar = GoogleCalendarAPI()
    
    def calculate_export_loading_deadline(self, clearance_date: datetime) -> datetime:
        """
        수출 적재 마감일 계산
        법적 기한: 수출신고 수리일 + 30일
        """
        return clearance_date + timedelta(days=EXPORT_LOADING_DEADLINE_DAYS)
    
    def calculate_container_return_deadline(self, arrival_date: datetime, free_time_days: int) -> datetime:
        """
        컨테이너 반납 마감일 계산
        입항일(ETA) + Free Time
        """
        return arrival_date + timedelta(days=free_time_days)
    
    def get_dday(self, deadline: datetime) -> int:
        """D-Day 계산 (음수면 지남)"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deadline_day = deadline.replace(hour=0, minute=0, second=0, microsecond=0)
        return (deadline_day - today).days
    
    def create_deadline_event(
        self,
        trade_id: str,
        deadline_type: str,  # "export_loading" or "container_return"
        deadline_date: datetime,
        description: str = "",
    ) -> Optional[str]:
        """마감일 캘린더 등록"""
        title_map = {
            "export_loading": f"[수출] 적재마감 - {trade_id}",
            "container_return": f"[수입] 컨테이너반납 - {trade_id}",
        }
        
        title = title_map.get(deadline_type, f"마감일 - {trade_id}")
        
        # D-7, D-3, D-1 알림 설정 (분 단위로 변환)
        reminders = [d * 24 * 60 for d in ALERT_DAYS]  # 7일=10080분, 3일=4320분, 1일=1440분
        
        return self.calendar.create_event(
            title=title,
            start_date=deadline_date,
            description=description,
            reminders=reminders,
        )
    
    def get_upcoming_deadlines(self, days: int = 14) -> List[Dict]:
        """다가오는 마감일 조회"""
        events = self.calendar.get_events(
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=days)
        )
        
        deadlines = []
        for event in events:
            if '[수출]' in event['title'] or '[수입]' in event['title']:
                start = event['start']
                if start:
                    if 'T' in start:
                        deadline_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    else:
                        deadline_dt = datetime.strptime(start, '%Y-%m-%d')
                    
                    deadlines.append({
                        **event,
                        'dday': self.get_dday(deadline_dt),
                        'deadline_date': deadline_dt,
                    })
        
        return sorted(deadlines, key=lambda x: x['dday'])


# ============================================================
# 편의 함수 (기존 100% 호환)
# ============================================================

def get_calendar_events(start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
    return GoogleCalendarAPI().get_events(start_date, end_date)

def create_calendar_event(title: str, start_date: datetime, **kwargs) -> Optional[str]:
    return GoogleCalendarAPI().create_event(title, start_date, **kwargs)

def calculate_loading_deadline(clearance_date: datetime) -> datetime:
    return DeadlineManager().calculate_export_loading_deadline(clearance_date)

def calculate_return_deadline(arrival_date: datetime, free_time: int) -> datetime:
    return DeadlineManager().calculate_container_return_deadline(arrival_date, free_time)
