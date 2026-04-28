import logging
import sys
import os
from datetime import datetime
from pathlib import Path
import threading

class _DedupFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self._last_msg = {}
        self._lock = threading.Lock()

    def filter(self, record):
        key = (record.levelno, record.getMessage())
        with self._lock:
            if self._last_msg.get(key, 0) >= 2:
                return False
            self._last_msg[key] = self._last_msg.get(key, 0) + 1
        return True

    def reset(self, key=None):
        with self._lock:
            if key:
                self._last_msg.pop(key, None)
            else:
                self._last_msg.clear()

class Logger:
    _instance: 'Logger | None' = None
    _logger: logging.Logger | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self):
        self._logger = logging.getLogger("ppt_ai")
        self._logger.setLevel(logging.DEBUG)

        if not self._logger.handlers:
            self._dedup_filter = _DedupFilter()

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            console_handler.addFilter(self._dedup_filter)

            log_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "logs"
            log_dir.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(
                log_dir / f"ppt_ai_{datetime.now().strftime('%Y%m%d')}.log",
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.addFilter(self._dedup_filter)

            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)

            self._logger.addHandler(console_handler)
            self._logger.addHandler(file_handler)

    def debug(self, message: str):
        if self._logger is not None:
            self._dedup_filter.reset()
            self._logger.debug(message)

    def info(self, message: str):
        if self._logger is not None:
            self._dedup_filter.reset()
            self._logger.info(message)

    def error(self, message: str):
        if self._logger is not None:
            self._dedup_filter.reset()
            self._logger.error(message)

    def warning(self, message: str):
        if self._logger is not None:
            self._dedup_filter.reset()
            self._logger.warning(message)

    @property
    def logger(self) -> logging.Logger:
        assert self._logger is not None
        return self._logger

logger = Logger()
