"""
日志配置模块
提供统一的日志管理功能
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

class Logger:
    """日志管理器"""

    _instance: Optional['Logger'] = None
    _logger: Optional[logging.Logger] = None

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

            log_dir = Path("logs")
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

    @property
    def logger(self) -> logging.Logger:
        """获取日志记录器"""
        return self._logger

logger = Logger().logger
