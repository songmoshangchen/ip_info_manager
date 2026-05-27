from __future__ import annotations

import logging
import os
import time

from ip_info.batch.core.query import BatchResult
from ip_info.processors.core.base import BaseProcessor
from ip_info.processors.tagger.manifest import load_manifest, validate_manifest
from ip_info.processors.tagger.matcher import ip_to_int, match_sorted_ips_streaming
from ip_info.store.protocols import IPDataReader, IPDataWriter
from ip_info.utils.progress import ProgressTracker

logger = logging.getLogger(__name__)


class BatchTagger(BaseProcessor):
    """IP 标签打标批量处理器，实现 BatchRunner Protocol"""

    channel_name = "tagger"

    def __init__(
        self,
        ips: list[str],
        writer: IPDataWriter,
        config_dir: str,
        reader: IPDataReader | None = None,
        level: int | None = None,
        mode: str = "accumulate",
        progress_tracker: ProgressTracker | None = None,
    ):
        super().__init__(ips=ips, writer=writer, reader=reader, progress_tracker=progress_tracker)
        self._config_dir = config_dir
        self._level = level
        self._mode = mode

    def _process(self) -> BatchResult:
        start_time = time.time()

        pending_ips, skip_count = self._filter_pending()

        if not pending_ips:
            total_elapsed = time.time() - start_time
            return BatchResult(skip_count=skip_count, total_elapsed=total_elapsed)

        # 加载并验证 manifest
        manifest_path = os.path.join(self._config_dir, "manifest.json")
        manifest = load_manifest(manifest_path, level=self._level)
        validate_manifest(manifest, self._config_dir)

        # 将 IP 转为整数，过滤无效 IP
        valid_items: list[tuple[str, int]] = []
        for ip_str in pending_ips:
            val = ip_to_int(ip_str)
            if val is not None:
                valid_items.append((ip_str, val))
            else:
                logger.warning("跳过无效 IP: %s", ip_str)

        valid_items.sort(key=lambda x: x[1])

        if not valid_items:
            total_elapsed = time.time() - start_time
            return BatchResult(skip_count=skip_count, total_elapsed=total_elapsed)

        # 处理所有标签源
        ip_tags: dict[str, list[str]] = {}
        total = len(manifest)

        for idx, item in enumerate(manifest):
            label = item["label"]
            source_file = item["file"]
            dataset_path = os.path.join(self._config_dir, source_file)

            t0 = time.time()
            matched = match_sorted_ips_streaming(valid_items, dataset_path)
            elapsed = time.time() - t0
            logger.info("[%d/%d] %s (%s): %d 命中, %.2fs", idx + 1, total, label, source_file, len(matched), elapsed)

            for match_idx in matched:
                ip_str = valid_items[match_idx][0]
                if ip_str not in ip_tags:
                    ip_tags[ip_str] = []
                if label not in ip_tags[ip_str]:
                    ip_tags[ip_str].append(label)

        # 写入结果
        success_count = 0
        for ip_str, tags in ip_tags.items():
            if not tags:
                continue

            if self._mode == "overwrite":
                self._writer.add_or_update_ip(ip_str, self.channel_name, {"tags": tags})
            else:  # accumulate
                existing_data = self._read_channel_data(ip_str)
                if existing_data is not None and "tags" in existing_data:
                    merged = list(set(existing_data["tags"]) | set(tags))
                    self._writer.add_or_update_ip(ip_str, self.channel_name, {"tags": merged})
                else:
                    self._writer.add_or_update_ip(ip_str, self.channel_name, {"tags": tags})

            success_count += 1
            self._mark_processed(ip_str)

        # 未匹配的 IP 也标记为已处理
        for ip_str, _ in valid_items:
            if ip_str not in ip_tags:
                self._mark_processed(ip_str)

        total_elapsed = time.time() - start_time
        return BatchResult(
            success_count=success_count,
            skip_count=skip_count,
            total_elapsed=total_elapsed,
        )

    def _read_channel_data(self, ip: str) -> dict | None:
        """读取 IP 的渠道数据。"""
        if self._reader is not None:
            return self._reader.get_channel_data(ip, self.channel_name)
        return None


# 兼容旧代码中的 CHANNEL_NAME 引用
CHANNEL_NAME = BatchTagger.channel_name
