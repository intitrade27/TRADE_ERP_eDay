# -*- coding: utf-8 -*-
"""
동기화 스케줄러
- 백그라운드 스레드에서 정기적으로 Excel 동기화
- 사용자 설정 가능한 동기화 간격
- 스케줄러 시작/중지 제어
"""
import logging
import threading
import time
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class SyncScheduler:
    """
    백그라운드 동기화 스케줄러

    기능:
    - 지정된 간격(초)마다 sync_callback 호출
    - 데몬 스레드로 실행 (메인 프로그램 종료 시 자동 종료)
    - 안전한 시작/중지
    """

    def __init__(
        self,
        sync_callback: Callable,
        interval_seconds: int = 300,  # 기본 5분
        name: str = "SyncScheduler"
    ):
        """
        Args:
            sync_callback: 동기화 함수 (인자 없음, 예: manager.sync_to_excel)
            interval_seconds: 동기화 간격 (초)
            name: 스케줄러 이름
        """
        self.sync_callback = sync_callback
        self.interval_seconds = interval_seconds
        self.name = name

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

        logger.info(f"[{self.name}] 생성 (간격: {interval_seconds}초)")

    def start(self):
        """스케줄러 시작"""
        if self._running:
            logger.warning(f"[{self.name}] 이미 실행 중")
            return

        self._stop_event.clear()
        self._running = True

        self._thread = threading.Thread(
            target=self._run_loop,
            name=self.name,
            daemon=True  # 메인 프로그램 종료 시 자동 종료
        )
        self._thread.start()

        logger.info(f"[{self.name}] 시작됨 (간격: {self.interval_seconds}초)")

    def stop(self, wait: bool = True):
        """
        스케줄러 중지

        Args:
            wait: True면 스레드 종료까지 대기
        """
        if not self._running:
            logger.warning(f"[{self.name}] 실행 중이 아님")
            return

        logger.info(f"[{self.name}] 중지 중...")
        self._stop_event.set()
        self._running = False

        if wait and self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        logger.info(f"[{self.name}] 중지됨")

    def is_running(self) -> bool:
        """실행 중인지 확인"""
        return self._running and self._thread and self._thread.is_alive()

    def _run_loop(self):
        """메인 루프 (백그라운드 스레드에서 실행)"""
        logger.info(f"[{self.name}] 루프 시작")

        while not self._stop_event.is_set():
            try:
                # 동기화 실행
                start_time = time.time()
                self.sync_callback()

                elapsed = time.time() - start_time
                logger.info(
                    f"[{self.name}] 동기화 완료 "
                    f"({elapsed:.2f}초, {datetime.now().strftime('%H:%M:%S')})"
                )

            except Exception as e:
                logger.error(f"[{self.name}] 동기화 실패: {e}", exc_info=True)

            # 대기 (중지 이벤트 체크하면서)
            self._stop_event.wait(self.interval_seconds)

        logger.info(f"[{self.name}] 루프 종료")

    def __repr__(self):
        status = "running" if self.is_running() else "stopped"
        return f"SyncScheduler(name={self.name}, interval={self.interval_seconds}s, status={status})"


def start_periodic_sync(
    manager,
    interval_minutes: int = 5,
    name: str = "AutoSync"
) -> SyncScheduler:
    """
    정기 동기화 시작 (헬퍼 함수)

    Args:
        manager: CachedMasterDataManager 인스턴스
        interval_minutes: 동기화 간격 (분)
        name: 스케줄러 이름

    Returns:
        SyncScheduler 인스턴스
    """
    def sync_callback():
        try:
            manager.sync_to_excel(force=False)
        except Exception as e:
            logger.error(f"[{name}] 자동 동기화 실패: {e}")

    scheduler = SyncScheduler(
        sync_callback=sync_callback,
        interval_seconds=interval_minutes * 60,
        name=name
    )

    scheduler.start()
    return scheduler
