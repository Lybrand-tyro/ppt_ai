"""
配置历史记录管理
通用 JSON 文件持久化，替代重复的 I/O 代码
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from .logger import logger


class JsonHistoryStore:
    """通用 JSON 历史记录存储"""

    def __init__(self, file_path: str, max_entries: int = 20):
        self._file_path = file_path
        self._max_entries = max_entries

    def load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self._file_path):
            try:
                with open(self._file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save(self, history: List[Dict[str, Any]]):
        with open(self._file_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def add(self, entry: Dict[str, Any], dedup_key: Optional[str] = None):
        """添加历史记录

        Args:
            entry: 记录条目
            dedup_key: 去重字段名，若指定则相同 key 值的记录会被替换
        """
        history = self.load()

        if dedup_key and dedup_key in entry:
            for i, item in enumerate(history):
                if item.get(dedup_key) == entry[dedup_key]:
                    history[i] = entry
                    self.save(history)
                    return

        history.insert(0, entry)
        if len(history) > self._max_entries:
            history = history[:self._max_entries]
        self.save(history)

    @staticmethod
    def mask_api_key(api_key: str) -> str:
        """遮蔽 API Key，仅显示首尾4位"""
        if len(api_key) > 8:
            return api_key[:4] + "***" + api_key[-4:]
        return "***" if api_key else ""
