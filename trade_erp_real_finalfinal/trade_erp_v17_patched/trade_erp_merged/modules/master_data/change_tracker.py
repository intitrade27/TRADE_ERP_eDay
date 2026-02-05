# -*- coding: utf-8 -*-
"""
변경사항 추적 시스템
- CREATE/UPDATE/DELETE 작업 추적
- 타임스탬프 기록
- Excel 동기화 상태 관리
"""
import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """변경 유형"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class Change:
    """
    단일 변경 기록

    Attributes:
        change_type: 변경 유형 (CREATE/UPDATE/DELETE)
        trade_id: 거래 ID
        data: 변경된 데이터 (UPDATE: 변경된 필드만, CREATE: 전체 데이터)
        timestamp: 변경 시각
        synced: Excel에 동기화 여부
        row_index: Excel 행 번호 (옵션, 빠른 업데이트용)
    """
    change_type: ChangeType
    trade_id: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    synced: bool = False
    row_index: Optional[int] = None

    def __repr__(self):
        return (f"Change(type={self.change_type.value}, "
                f"trade_id={self.trade_id}, "
                f"synced={self.synced}, "
                f"time={self.timestamp.strftime('%H:%M:%S')})")


class ChangeTracker:
    """
    변경사항 추적 및 관리

    기능:
    - CRUD 작업 추적
    - 동기화 대기 중인 변경사항 조회
    - 변경사항 병합 (같은 거래 ID에 대한 중복 변경 최적화)
    """

    def __init__(self):
        self.changes: List[Change] = []
        self._change_count = 0

    def track_create(self, trade_id: str, data: Dict[str, Any]) -> Change:
        """
        CREATE 작업 추적

        Args:
            trade_id: 거래 ID
            data: 생성된 전체 데이터

        Returns:
            Change 객체
        """
        change = Change(
            change_type=ChangeType.CREATE,
            trade_id=trade_id,
            data=data.copy(),
            timestamp=datetime.now(),
            synced=False
        )
        self.changes.append(change)
        self._change_count += 1

        logger.info(f"[TRACKER] CREATE 추적: {trade_id} (총 {len(self.changes)}건)")
        return change

    def track_update(
        self,
        trade_id: str,
        data: Dict[str, Any],
        row_index: Optional[int] = None
    ) -> Change:
        """
        UPDATE 작업 추적

        Args:
            trade_id: 거래 ID
            data: 변경된 필드 (전체가 아닌 변경된 필드만)
            row_index: Excel 행 번호 (빠른 업데이트용)

        Returns:
            Change 객체
        """
        # 기존 UPDATE 변경사항이 있으면 병합
        existing = self._find_pending_update(trade_id)
        if existing:
            # 기존 변경사항에 새로운 필드 추가/덮어쓰기
            existing.data.update(data)
            existing.timestamp = datetime.now()
            if row_index is not None:
                existing.row_index = row_index

            logger.info(f"[TRACKER] UPDATE 병합: {trade_id}")
            return existing

        # 새로운 UPDATE 추가
        change = Change(
            change_type=ChangeType.UPDATE,
            trade_id=trade_id,
            data=data.copy(),
            timestamp=datetime.now(),
            synced=False,
            row_index=row_index
        )
        self.changes.append(change)
        self._change_count += 1

        logger.info(f"[TRACKER] UPDATE 추적: {trade_id} (총 {len(self.changes)}건)")
        return change

    def track_delete(self, trade_id: str, row_index: Optional[int] = None) -> Change:
        """
        DELETE 작업 추적

        Args:
            trade_id: 거래 ID
            row_index: Excel 행 번호

        Returns:
            Change 객체
        """
        # 해당 trade_id의 모든 미동기화 변경사항 제거
        # (어차피 삭제되므로 이전 CREATE/UPDATE는 무의미)
        self._remove_pending_changes(trade_id)

        change = Change(
            change_type=ChangeType.DELETE,
            trade_id=trade_id,
            data={},
            timestamp=datetime.now(),
            synced=False,
            row_index=row_index
        )
        self.changes.append(change)
        self._change_count += 1

        logger.info(f"[TRACKER] DELETE 추적: {trade_id} (총 {len(self.changes)}건)")
        return change

    def get_pending_changes(self) -> List[Change]:
        """
        동기화 대기 중인 변경사항 조회

        Returns:
            동기화되지 않은 Change 목록 (시간순 정렬)
        """
        pending = [c for c in self.changes if not c.synced]
        return sorted(pending, key=lambda c: c.timestamp)

    def mark_synced(self, change: Change):
        """
        변경사항을 동기화 완료로 표시

        Args:
            change: Change 객체
        """
        change.synced = True
        logger.debug(f"[TRACKER] 동기화 완료: {change.trade_id} ({change.change_type.value})")

    def mark_all_synced(self):
        """모든 변경사항을 동기화 완료로 표시"""
        for change in self.changes:
            change.synced = True
        logger.info(f"[TRACKER] 전체 동기화 완료: {len(self.changes)}건")

    def clear_synced(self):
        """
        동기화 완료된 변경사항 제거

        메모리 관리를 위해 주기적으로 호출
        """
        before_count = len(self.changes)
        self.changes = [c for c in self.changes if not c.synced]
        removed = before_count - len(self.changes)

        if removed > 0:
            logger.info(f"[TRACKER] 동기화 완료 변경사항 제거: {removed}건")

    def get_statistics(self) -> Dict[str, Any]:
        """
        통계 정보 반환

        Returns:
            {
                'total': 전체 변경 횟수,
                'pending': 대기 중인 변경사항 수,
                'creates': CREATE 수,
                'updates': UPDATE 수,
                'deletes': DELETE 수
            }
        """
        pending = self.get_pending_changes()

        return {
            'total': self._change_count,
            'pending': len(pending),
            'creates': len([c for c in pending if c.change_type == ChangeType.CREATE]),
            'updates': len([c for c in pending if c.change_type == ChangeType.UPDATE]),
            'deletes': len([c for c in pending if c.change_type == ChangeType.DELETE]),
        }

    def _find_pending_update(self, trade_id: str) -> Optional[Change]:
        """
        대기 중인 UPDATE 변경사항 찾기

        Args:
            trade_id: 거래 ID

        Returns:
            Change 객체 또는 None
        """
        for change in reversed(self.changes):
            if (not change.synced and
                change.change_type == ChangeType.UPDATE and
                change.trade_id == trade_id):
                return change
        return None

    def _remove_pending_changes(self, trade_id: str):
        """
        특정 거래 ID의 미동기화 변경사항 제거

        Args:
            trade_id: 거래 ID
        """
        before_count = len(self.changes)
        self.changes = [
            c for c in self.changes
            if not (c.trade_id == trade_id and not c.synced)
        ]
        removed = before_count - len(self.changes)

        if removed > 0:
            logger.debug(f"[TRACKER] {trade_id}의 미동기화 변경사항 제거: {removed}건")

    def __repr__(self):
        stats = self.get_statistics()
        return (f"ChangeTracker("
                f"total={stats['total']}, "
                f"pending={stats['pending']}, "
                f"C={stats['creates']}, "
                f"U={stats['updates']}, "
                f"D={stats['deletes']})")
