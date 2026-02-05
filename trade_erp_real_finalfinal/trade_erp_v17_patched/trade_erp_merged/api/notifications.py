# -*- coding: utf-8 -*-
"""
알림 모듈 (정리판)
- 이메일 (SMTP)만 유지
- 카카오톡/텔레그램 연동은 요구사항에 따라 제거됨
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings

logger = logging.getLogger(__name__)


# ============================================================
# 이메일 알림
# ============================================================
class EmailNotifier:
    """이메일 알림 (SMTP)"""

    def __init__(self):
        self.server = settings.smtp_server
        self.port = settings.smtp_port
        self.email = settings.smtp_email
        self.password = settings.smtp_password
        self.recipient = settings.alert_recipient_email

    def is_configured(self) -> bool:
        return bool(self.email and self.password and self.recipient)

    def send_email(self, subject: str, body: str, html: bool = False) -> bool:
        """이메일 발송"""
        if not self.is_configured():
            logger.warning("[EMAIL] 이메일 설정 미완료")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email
            msg['To'] = self.recipient

            content_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, content_type, 'utf-8'))

            with smtplib.SMTP(self.server, self.port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)

            logger.info(f"[EMAIL] 발송 완료: {subject}")
            return True
        except Exception as e:
            logger.error(f"[EMAIL] 발송 실패: {e}")
            return False

    def send_deadline_alert(self, trade_id: str, deadline_type: str, deadline_date: datetime, dday: int) -> bool:
        """마감일 경고 이메일"""
        type_name = "적재 마감" if deadline_type == "export_loading" else "컨테이너 반납"

        subject = f"[무역ERP] {type_name} D-{dday} 알림 - {trade_id}"
        body = f"""
        <html>
        <body>
        <h2>⚠️ 마감일 알림</h2>
        <table border="1" cellpadding="10">
            <tr><td><b>거래번호</b></td><td>{trade_id}</td></tr>
            <tr><td><b>유형</b></td><td>{type_name}</td></tr>
            <tr><td><b>마감일</b></td><td>{deadline_date.strftime('%Y-%m-%d')}</td></tr>
            <tr><td><b>D-Day</b></td><td style="color:red;font-weight:bold;">D-{dday}</td></tr>
        </table>
        <p>기한 내 처리 부탁드립니다.</p>
        </body>
        </html>
        """
        return self.send_email(subject, body, html=True)


# ============================================================
# 통합 알림 관리자 (이메일만)
# ============================================================
class NotificationManager:
    """통합 알림 관리"""

    def __init__(self):
        self.email = EmailNotifier()

    def send_deadline_alert(
        self,
        trade_id: str,
        deadline_type: str,
        deadline_date: datetime,
        dday: int,
        channels: List[str] = None
    ) -> dict:
        """
        마감일 알림 발송

        Args:
            channels: ["email"]만 지원. None이면 email 발송.
        """
        if channels is None:
            channels = ["email"]

        results = {}
        if "email" in channels and self.email.is_configured():
            results["email"] = self.email.send_deadline_alert(trade_id, deadline_type, deadline_date, dday)

        return results


# ============================================================
# 편의 함수 (기존 호환: 카카오/텔레그램은 False 반환)
# ============================================================
def send_email(subject: str, body: str, html: bool = False) -> bool:
    return EmailNotifier().send_email(subject, body, html)

def send_kakao_message(text: str) -> bool:
    logger.warning("[KAKAO] 기능 제거됨 (요구사항 반영)")
    return False

def send_telegram_message(message: str) -> bool:
    logger.warning("[TELEGRAM] 기능 제거됨 (요구사항 반영)")
    return False

def send_deadline_alert(trade_id: str, deadline_type: str, deadline_date: datetime, dday: int) -> dict:
    return NotificationManager().send_deadline_alert(trade_id, deadline_type, deadline_date, dday)
