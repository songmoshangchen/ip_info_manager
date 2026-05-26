"""进度跟踪工具。

提供 ProgressTracker 协议和 File/InMemory/Sqlite 三种实现。
支持按 (ip, channel) 粒度跟踪进度，实现分渠道断点续传。
"""

from __future__ import annotations

import os
import sqlite3
import threading
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

    .. deprecated::
        推荐使用 SqliteProgressTracker，支持缓冲写入和并发安全。
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


class SqliteProgressTracker:
    """基于 SQLite 的进度跟踪器，按 (ip, channel) 粒度记录。

    特性:
    - 缓冲区 + flush 批量写入，由调用方控制写入频次
    - threading.local + WAL 模式，并发安全
    - 支持从旧 FileProgressTracker 文件导入数据
    """

    def __init__(self, db_path: str, import_from: str | None = None):
        self._db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()
        self._cache: set[tuple[str, str]] | None = None
        self._buffer: list[tuple[str, str]] = []

        parent_dir = os.path.dirname(db_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        self._init_db()

        if import_from:
            self._import_from_file(import_from)

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                ip TEXT NOT NULL,
                channel TEXT NOT NULL,
                PRIMARY KEY (ip, channel)
            )
        """)
        conn.commit()

    def _load_cache(self) -> set[tuple[str, str]]:
        if self._cache is not None:
            return self._cache
        conn = self._get_conn()
        rows = conn.execute("SELECT ip, channel FROM progress").fetchall()
        self._cache = {(ip, channel) for ip, channel in rows}
        return self._cache

    def _import_from_file(self, file_path: str) -> None:
        """从旧 FileProgressTracker 文件导入数据。"""
        records: list[tuple[str, str]] = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if "\t" in line:
                        ip, channel = line.split("\t", 1)
                        records.append((ip, channel))
                    else:
                        records.append((line, ""))
        except FileNotFoundError:
            return

        if records:
            conn = self._get_conn()
            conn.executemany(
                "INSERT OR IGNORE INTO progress (ip, channel) VALUES (?, ?)",
                records,
            )
            conn.commit()
            self._cache = None  # 清缓存，下次重新加载

    def is_processed(self, ip: str, channel: str = "") -> bool:
        cache = self._load_cache()
        if (ip, channel) in cache:
            return True
        # 检查缓冲区
        return (ip, channel) in self._buffer

    def mark_processed(self, ip: str, channel: str = "") -> None:
        key = (ip, channel)
        cache = self._load_cache()
        if key in cache:
            return
        if key not in self._buffer:
            self._buffer.append(key)

    def flush(self) -> None:
        """将缓冲区数据批量写入 SQLite。"""
        if not self._buffer:
            return
        with self._lock:
            records = self._buffer[:]
            self._buffer.clear()
            conn = self._get_conn()
            conn.executemany(
                "INSERT OR IGNORE INTO progress (ip, channel) VALUES (?, ?)",
                records,
            )
            conn.commit()
            # 更新内存缓存
            cache = self._load_cache()
            cache.update(records)
