import logging
import os
import time

from ip_info.batch.core.query import BatchResult
from ip_info.processors.classifier.engine import IPClassifier
from ip_info.processors.classifier.rules import load_rules
from ip_info.processors.core.base import BaseProcessor
from ip_info.store.protocols import IPDataReader, IPDataWriter
from ip_info.utils.progress import ProgressTracker

logger = logging.getLogger(__name__)


class BatchClassifier(BaseProcessor):
    """IP 自动分类批量处理器，实现 BatchRunner Protocol。"""

    channel_name = "classifier"

    def __init__(
        self,
        ips: list[str],
        writer: IPDataWriter,
        reader: IPDataReader,
        rules_dir: str,
        custom_rules_path: str | None = None,
        progress_tracker: ProgressTracker | None = None,
    ):
        super().__init__(ips=ips, writer=writer, reader=reader, progress_tracker=progress_tracker)
        self._rules_dir = rules_dir
        self._custom_rules_path = custom_rules_path

    def _process(self) -> BatchResult:
        start_time = time.time()

        pending_ips, skip_count = self._filter_pending()

        if not pending_ips:
            total_elapsed = time.time() - start_time
            return BatchResult(skip_count=skip_count, total_elapsed=total_elapsed)

        # 加载规则
        builtin_path = os.path.join(self._rules_dir, "builtin_rules.json")
        rules = load_rules(builtin_path, self._custom_rules_path)
        classifier = IPClassifier(rules)

        logger.info("内置规则分类: %s", ", ".join(classifier.categories))
        logger.info("规则总数: %d", classifier.rule_count)

        # 逐 IP 分类
        success_count = 0
        total = len(pending_ips)

        for idx, ip in enumerate(pending_ips, 1):
            ip_data = self._reader.get_ip_data(ip)

            if ip_data is None:
                skip_count += 1
                logger.debug("[%d/%d] %s — 无数据，跳过", idx, total, ip)
                continue

            result = classifier.classify(ip_data)
            self._writer.add_or_update_ip(ip, self.channel_name, result)
            success_count += 1
            self._mark_processed(ip)

            label = result["label"]
            matched_info = ""
            if result["matched_by"]:
                first = result["matched_by"][0]
                matched_info = f" <- {first['field']} ~ {first['pattern']}"
            logger.info("[%d/%d] %s -> %s%s", idx, total, ip, label, matched_info)

        total_elapsed = time.time() - start_time
        return BatchResult(
            success_count=success_count,
            skip_count=skip_count,
            total_elapsed=total_elapsed,
        )


# 兼容旧代码中的 CHANNEL_NAME 引用
CHANNEL_NAME = BatchClassifier.channel_name
