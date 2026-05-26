"""进度跟踪工具。

提供 ProgressTracker 协议和 File/InMemory 两种实现。
支持按 (ip, channel) 粒度跟踪进度，实现分渠道断点续传。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProgressTracker(Protocol):
    def is_processed(self, ip: str, channel: str = "") -> bool: ...
    def mark_processed(self, ip: str, channel: str = "") -> None: ...


class InMemoryProgressTracker:
    def __init__(self):
        self._processed: set[tuple[str, str]] = set()

    def is_processed(self, ip: str, channel: str = "") -> bool:
        return (ip, channel) in self._processed

    def mark_processed(self, ip: str, channel: str = "") -> None:
        self._processed.add((ip, channel))


class FileProgressTracker:
    """基于文件的进度跟踪器，按 (ip, channel) 粒度记录。

    文件格式: 每行一条记录，格式为 ip\\tchannel
    当 channel 为空时，格式为 ip（兼容旧格式）
    """

    def __init__(self, file_path: str):
        self._file_path = file_path
        self._cache: set[tuple[str, str]] | None = None

    def _load_cache(self) -> set[tuple[str, str]]:
        if self._cache is not None:
            return self._cache
        cache: set[tuple[str, str]] = set()
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if "\t" in line:
                        ip, channel = line.split("\t", 1)
                        cache.add((ip, channel))
                    else:
                        # 兼容旧格式: 只有 ip，视为 channel=""
                        cache.add((line, ""))
        except FileNotFoundError:
            pass
        self._cache = cache
        return cache

    def is_processed(self, ip: str, channel: str = "") -> bool:
        return (ip, channel) in self._load_cache()

    def mark_processed(self, ip: str, channel: str = "") -> None:
        cache = self._load_cache()
        if (ip, channel) in cache:
            return
        cache.add((ip, channel))
        with open(self._file_path, "a", encoding="utf-8") as f:
            if channel:
                f.write(f"{ip}\t{channel}\n")
            else:
                f.write(f"{ip}\n")
