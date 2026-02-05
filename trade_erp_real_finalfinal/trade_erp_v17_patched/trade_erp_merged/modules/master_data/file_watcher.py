# -*- coding: utf-8 -*-
"""
Excel 파일 모니터링
- watchdog를 사용한 파일 변경 감지
- Excel 파일 수정 시 자동으로 캐시 동기화
- 중복 이벤트 debouncing
"""
import logging
import time
import threading
from pathlib import Path
from typing import Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

logger = logging.getLogger(__name__)


class ExcelFileWatcher(FileSystemEventHandler):
    """
    Excel 파일 변경 감지 핸들러

    기능:
    - Excel 파일 수정 감지
    - Debouncing (짧은 시간 내 중복 이벤트 무시)
    - 콜백 함수 호출
    """

    def __init__(
        self,
        filepath: Path,
        callback: Callable,
        debounce_seconds: float = 2.0
    ):
        """
        Args:
            filepath: 감시할 Excel 파일 경로
            callback: 파일 변경 시 호출할 함수
            debounce_seconds: 중복 이벤트 무시 시간 (초)
        """
        super().__init__()
        self.filepath = Path(filepath).resolve()
        self.callback = callback
        self.debounce_seconds = debounce_seconds

        self._last_modified = 0.0
        self._lock = threading.Lock()

        logger.info(f"[WATCHER] 초기화: {self.filepath.name}")

    def on_modified(self, event):
        """파일 수정 이벤트 처리"""
        if event.is_directory:
            return

        # 감시 대상 파일인지 확인
        event_path = Path(event.src_path).resolve()
        if event_path != self.filepath:
            return

        # Debouncing: 짧은 시간 내 중복 이벤트 무시
        with self._lock:
            current_time = time.time()

            if current_time - self._last_modified < self.debounce_seconds:
                logger.debug(f"[WATCHER] 중복 이벤트 무시: {self.filepath.name}")
                return

            self._last_modified = current_time

        # 콜백 실행
        try:
            logger.info(f"[WATCHER] 파일 변경 감지: {self.filepath.name}")
            self.callback()

        except Exception as e:
            logger.error(f"[WATCHER] 콜백 실행 실패: {e}", exc_info=True)


class FileWatcherManager:
    """
    파일 감시 관리자

    기능:
    - watchdog Observer 관리
    - 감시 시작/중지
    """

    def __init__(
        self,
        filepath: Path,
        callback: Callable,
        debounce_seconds: float = 2.0
    ):
        """
        Args:
            filepath: 감시할 파일 경로
            callback: 파일 변경 시 호출할 함수
            debounce_seconds: 중복 이벤트 무시 시간
        """
        self.filepath = Path(filepath).resolve()
        self.callback = callback

        # 파일이 존재하는지 확인
        if not self.filepath.exists():
            raise FileNotFoundError(f"파일이 없습니다: {self.filepath}")

        # 이벤트 핸들러 생성
        self.event_handler = ExcelFileWatcher(
            filepath=self.filepath,
            callback=callback,
            debounce_seconds=debounce_seconds
        )

        # Observer 생성
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            path=str(self.filepath.parent),
            recursive=False
        )

        self._started = False

        logger.info(f"[WATCHER_MGR] 초기화 완료: {self.filepath.name}")

    def start(self):
        """감시 시작"""
        if self._started:
            logger.warning("[WATCHER_MGR] 이미 시작됨")
            return

        self.observer.start()
        self._started = True

        logger.info(f"[WATCHER_MGR] 감시 시작: {self.filepath.name}")

    def stop(self, wait: bool = True):
        """
        감시 중지

        Args:
            wait: True면 스레드 종료까지 대기
        """
        if not self._started:
            logger.warning("[WATCHER_MGR] 시작되지 않음")
            return

        logger.info("[WATCHER_MGR] 감시 중지 중...")
        self.observer.stop()

        if wait:
            self.observer.join(timeout=5)

        self._started = False
        logger.info("[WATCHER_MGR] 감시 중지됨")

    def is_running(self) -> bool:
        """감시 중인지 확인"""
        return self._started and self.observer.is_alive()

    def __repr__(self):
        status = "running" if self.is_running() else "stopped"
        return f"FileWatcherManager(file={self.filepath.name}, status={status})"


def start_file_watcher(
    manager,
    debounce_seconds: float = 2.0
) -> FileWatcherManager:
    """
    파일 감시 시작 (헬퍼 함수)

    Args:
        manager: CachedMasterDataManager 인스턴스
        debounce_seconds: 중복 이벤트 무시 시간

    Returns:
        FileWatcherManager 인스턴스
    """
    def sync_callback():
        try:
            logger.info("[WATCHER] Excel 변경 감지 → 캐시 동기화")
            manager.sync_from_excel()
        except Exception as e:
            logger.error(f"[WATCHER] 동기화 실패: {e}")

    watcher = FileWatcherManager(
        filepath=manager.excel_filepath,
        callback=sync_callback,
        debounce_seconds=debounce_seconds
    )

    watcher.start()
    return watcher
