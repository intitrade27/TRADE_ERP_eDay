# -*- coding: utf-8 -*-
"""
마감일 관리 및 D-Day 카운트
- 수출: 적재 마감일 (수리일 + 30일)
- 수입: 컨테이너 반납 마감일 (ETA + Free Time)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.constants import EXPORT_LOADING_DEADLINE_DAYS, ALERT_DAYS
from api.google_calendar import GoogleCalendarAPI, DeadlineManager
from api.notifications import NotificationManager

logger = logging.getLogger(__name__)


class DeadlineTracker:
    """마감일 추적 및 알림"""
    
    def __init__(self):
        self.calendar = GoogleCalendarAPI()
        self.notifier = NotificationManager()
        self.deadline_mgr = DeadlineManager()
    
    def set_export_loading_deadline(
        self,
        trade_id: str,
        clearance_date: datetime = None,
        manual_deadline: datetime = None,
        item_name: str = "",
    ) -> Dict[str, Any]:
        """
        수출 적재 마감일 설정
        
        Args:
            trade_id: 거래 ID
            clearance_date: 수출신고 수리일 (자동계산: +30일)
            manual_deadline: 직접 입력 마감일
            item_name: 품목명
        """
        if manual_deadline:
            deadline = manual_deadline
            source = "직접입력"
        elif clearance_date:
            deadline = clearance_date + timedelta(days=EXPORT_LOADING_DEADLINE_DAYS)
            source = f"수리일({clearance_date.strftime('%Y-%m-%d')}) + 30일"
        else:
            raise ValueError("수리일 또는 마감일을 입력하세요.")
        
        dday = self._calculate_dday(deadline)
        
        # 캘린더 등록
        event_id = None
        if self.calendar.is_connected():
            description = f"거래번호: {trade_id}\n품목: {item_name}\n산출: {source}"
            event_id = self.calendar.create_event(
                title=f"[수출] 적재마감 - {trade_id}",
                start_date=deadline,
                description=description,
                reminders=[d * 24 * 60 for d in ALERT_DAYS],  # D-7, D-3, D-1 알림
            )
        
        result = {
            'trade_id': trade_id,
            'deadline_type': 'export_loading',
            'deadline': deadline.strftime('%Y-%m-%d'),
            'dday': dday,
            'source': source,
            'event_id': event_id,
        }
        
        logger.info(f"[DEADLINE] 수출 적재 마감일 설정: {trade_id} → {deadline.strftime('%Y-%m-%d')} (D-{dday})")
        return result
    
    def set_container_return_deadline(
        self,
        trade_id: str,
        arrival_date: datetime,
        free_time_days: int,
        item_name: str = "",
    ) -> Dict[str, Any]:
        """
        수입 컨테이너 반납 마감일 설정
        
        Args:
            trade_id: 거래 ID
            arrival_date: 입항일 (ETA)
            free_time_days: Free Time (일)
            item_name: 품목명
        """
        deadline = arrival_date + timedelta(days=free_time_days)
        dday = self._calculate_dday(deadline)
        
        # 캘린더 등록
        event_id = None
        if self.calendar.is_connected():
            description = f"거래번호: {trade_id}\n품목: {item_name}\n입항일: {arrival_date.strftime('%Y-%m-%d')}\nFree Time: {free_time_days}일"
            event_id = self.calendar.create_event(
                title=f"[수입] 컨테이너반납 - {trade_id}",
                start_date=deadline,
                description=description,
                reminders=[d * 24 * 60 for d in ALERT_DAYS],
            )
        
        result = {
            'trade_id': trade_id,
            'deadline_type': 'container_return',
            'deadline': deadline.strftime('%Y-%m-%d'),
            'dday': dday,
            'arrival_date': arrival_date.strftime('%Y-%m-%d'),
            'free_time_days': free_time_days,
            'event_id': event_id,
        }
        
        logger.info(f"[DEADLINE] 컨테이너 반납 마감일 설정: {trade_id} → {deadline.strftime('%Y-%m-%d')} (D-{dday})")
        return result
    
    def _calculate_dday(self, deadline: datetime) -> int:
        """D-Day 계산"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deadline_day = deadline.replace(hour=0, minute=0, second=0, microsecond=0)
        return (deadline_day - today).days
    
    def check_and_send_alerts(self, deadlines: List[Dict]) -> List[Dict]:
        """
        마감일 체크 및 알림 발송
        D-7, D-3, D-1 시점에 알림
        """
        alerts_sent = []
        
        for dl in deadlines:
            deadline_date = datetime.strptime(dl['deadline'], '%Y-%m-%d')
            dday = self._calculate_dday(deadline_date)
            
            if dday in ALERT_DAYS:
                # 이메일 + 카카오톡 알림 발송
                result = self.notifier.send_deadline_alert(
                    trade_id=dl['trade_id'],
                    deadline_type=dl['deadline_type'],
                    deadline_date=deadline_date,
                    dday=dday,
                )
                
                alerts_sent.append({
                    'trade_id': dl['trade_id'],
                    'dday': dday,
                    'result': result,
                })
                
                logger.info(f"[ALERT] D-{dday} 알림 발송: {dl['trade_id']}")
        
        return alerts_sent
    
    def get_upcoming_deadlines(self, days: int = 14) -> List[Dict]:
        """다가오는 마감일 조회"""
        return self.deadline_mgr.get_upcoming_deadlines(days)


# 편의 함수
def set_export_deadline(trade_id: str, clearance_date: datetime = None, manual_deadline: datetime = None) -> Dict:
    return DeadlineTracker().set_export_loading_deadline(trade_id, clearance_date, manual_deadline)

def set_import_deadline(trade_id: str, arrival_date: datetime, free_time_days: int) -> Dict:
    return DeadlineTracker().set_container_return_deadline(trade_id, arrival_date, free_time_days)

def get_dday(deadline_str: str) -> int:
    deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return (deadline - today).days
