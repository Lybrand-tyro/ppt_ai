"""
日志配置模块
提供统一的日志管理功能
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

class Logger:
    """日志管理器"""

    _instance: 'Logger | None' = None
    _logger: logging.Logger | None = None
    _last_message: str | None = None
    _last_message_type: str | None = None

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

    def _get_message_type(self, message: str) -> str:
        """获取消息类型，用于去重判断"""
        if "尝试读取日志文件" in message:
            return "read_log_file"
        elif "日志文件不存在" in message:
            return "log_file_not_exists"
        elif "读取日志失败" in message:
            return "read_log_error"
        else:
            return message

    def debug(self, message: str):
        """记录debug级别日志"""
        if self._logger is not None:
            self._logger.debug(message)
        self._last_message = message
        self._last_message_type = self._get_message_type(message)

    def info(self, message: str):
        """记录info级别日志，避免重复记录相同类型的消息"""
        message_type = self._get_message_type(message)
        if message_type != self._last_message_type:
            if self._logger is not None:
                self._logger.info(message)
            self._last_message = message
            self._last_message_type = message_type

    def error(self, message: str):
        """记录error级别日志"""
        if self._logger is not None:
            self._logger.error(message)
        self._last_message = message
        self._last_message_type = self._get_message_type(message)

    def warning(self, message: str):
        """记录warning级别日志"""
        if self._logger is not None:
            self._logger.warning(message)
        self._last_message = message
        self._last_message_type = self._get_message_type(message)

    @property
    def logger(self) -> logging.Logger:
        """获取日志记录器"""
        assert self._logger is not None
        return self._logger

logger = Logger()
