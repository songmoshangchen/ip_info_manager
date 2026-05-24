import logging
import os
import time

from ip_info.batch.core.query import BatchResult
from ip_info.processors.classifier.engine import IPClassifier
from ip_info.processors.classifier.rules import load_rules
from ip_info.store.protocols import IPDataReader, IPDataWriter

logger = logging.getLogger(__name__)

CHANNEL_NAME = "classifier"


class BatchClassifier:
    """IP 自动分类批量处理器，实现 BatchRunner Protocol。"""

    def __init__(
        self,
        ips: list[str],
        writer: IPDataWriter,
        reader: IPDataReader,
        rules_dir: str,
        custom_rules_path: str | None = None,
    ):
        self._ips = ips
        self._writer = writer
        self._reader = reader
        self._rules_dir = rules_dir
        self._custom_rules_path = custom_rules_path

    def run(self) -> BatchResult:
        start_time = time.time()

        if not self._ips:
            total_elapsed = time.time() - start_time
            return BatchResult(total_elapsed=total_elapsed)

        # 加载规则
        builtin_path = os.path.join(self._rules_dir, "builtin_rules.json")
        rules = load_rules(builtin_path, self._custom_rules_path)
        classifier = IPClassifier(rules)

        logger.info("内置规则分类: %s", ", ".join(classifier.categories))
        logger.info("规则总数: %d", classifier.rule_count)

        # 逐 IP 分类
        success_count = 0
        skip_count = 0
        total = len(self._ips)

        for idx, ip in enumerate(self._ips, 1):
            ip_data = self._reader.get_ip_data(ip)

            if ip_data is None:
                skip_count += 1
                logger.debug("[%d/%d] %s — 无数据，跳过", idx, total, ip)
                continue

            result = classifier.classify(ip_data)
            self._writer.add_or_update_ip(ip, CHANNEL_NAME, result)
            success_count += 1

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
