"""进度跟踪工具。

提供 ProgressTracker 协议和 File/InMemory 两种实现。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProgressTracker(Protocol):
    def is_processed(self, ip: str) -> bool: ...
    def mark_processed(self, ip: str) -> None: ...


class InMemoryProgressTracker:
    def __init__(self):
        self._processed: set[str] = set()

    def is_processed(self, ip: str) -> bool:
        return ip in self._processed

    def mark_processed(self, ip: str) -> None:
        self._processed.add(ip)


class FileProgressTracker:
    def __init__(self, file_path: str):
        self._file_path = file_path

    def is_processed(self, ip: str) -> bool:
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                return ip in (line.strip() for line in f)
        except FileNotFoundError:
            return False

    def mark_processed(self, ip: str) -> None:
        with open(self._file_path, "a", encoding="utf-8") as f:
            f.write(f"{ip}\n")
