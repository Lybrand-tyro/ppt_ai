"""
日志配置模块
提供统一的日志管理功能
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path

class Logger:
    """日志管理器"""

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
        """设置日志记录器"""
        self._logger = logging.getLogger("ppt_ai")
        self._logger.setLevel(logging.DEBUG)

        if not self._logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)

            log_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "logs"
            log_dir.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(
                log_dir / f"ppt_ai_{datetime.now().strftime('%Y%m%d')}.log",
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)

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
            self._logger.debug(message)

    def info(self, message: str):
        if self._logger is not None:
            self._logger.info(message)

    def error(self, message: str):
        if self._logger is not None:
            self._logger.error(message)

    def warning(self, message: str):
        if self._logger is not None:
            self._logger.warning(message)

    @property
    def logger(self) -> logging.Logger:
        assert self._logger is not None
        return self._logger

logger = Logger()
