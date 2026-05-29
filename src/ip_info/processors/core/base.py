"""Processor 通用基类和工具。"""

from __future__ import annotations

import time

from ip_info.batch.core.query import BatchResult
from ip_info.store.protocols import IPDataReader, IPDataWriter
from ip_info.utils.progress import ProgressTracker, flush_progress


class BaseProcessor:
    """Processor 基类，提供 ips/writer/reader/progress_tracker 的通用管理。

    子类需要实现:
    - channel_name: str 类属性
    - _process(): 核心处理逻辑
    """

    channel_name: str = ""

    @property
    def name(self) -> str:
        return self.channel_name

    def __init__(
        self,
        ips: list[str],
        writer: IPDataWriter,
        reader: IPDataReader | None = None,
        progress_tracker: ProgressTracker | None = None,
    ):
        self._ips = ips
        self._writer = writer
        self._reader = reader
        self._progress_tracker = progress_tracker

    def _filter_pending(self) -> tuple[list[str], int]:
        """过滤已处理的 IP，返回 (pending_ips, skip_count)。"""
        if self._progress_tracker is None:
            return list(self._ips), 0
        pending = []
        skip_count = 0
        for ip in self._ips:
            if self._progress_tracker.is_processed(ip, self.channel_name):
                skip_count += 1
            else:
                pending.append(ip)
        return pending, skip_count

    def _mark_processed(self, ip: str) -> None:
        """标记 IP 为已处理。"""
        if self._progress_tracker is not None:
            self._progress_tracker.mark_processed(ip, self.channel_name)

    def _flush_progress(self) -> None:
        """刷新进度到持久化存储（如果 tracker 支持 flush）。"""
        flush_progress(self._progress_tracker)

    def run(self) -> BatchResult:
        """通用执行流程：过滤 → 处理 → 刷新进度。"""
        start_time = time.time()

        if not self._ips:
            return BatchResult(total_elapsed=time.time() - start_time)

        result = self._process()
        self._flush_progress()
        return result

    def _process(self) -> BatchResult:
        """子类实现的核心处理逻辑。"""
        raise NotImplementedError
