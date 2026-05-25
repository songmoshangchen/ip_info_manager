import logging
import time
from datetime import datetime, timedelta, timezone

from ip_info.batch.core.query import BatchResult
from ip_info.processors.dns_verify.extractor import extract_domain_mappings
from ip_info.processors.dns_verify.verifier import (
    add_verify_stats,
    batch_verify,
    build_verify_results,
)

logger = logging.getLogger(__name__)

CHANNEL_NAME = "domain_verify"
DEFAULT_MAX_AGE_DAYS = 7


def _is_verify_expired(verify_data: dict, max_age_days: float) -> bool:
    verify_time_str = verify_data.get("verify_time", "")
    if not verify_time_str:
        return True
    try:
        verify_time = datetime.fromisoformat(verify_time_str)
        if verify_time.tzinfo is None:
            verify_time = verify_time.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - verify_time
        return age > timedelta(days=max_age_days)
    except (ValueError, TypeError):
        return True


class BatchDnsVerify:
    def __init__(
        self,
        ips: list[str],
        writer,
        reader,
        timeout: float = 3.0,
        concurrency: int = 10,
        max_age_days: float = DEFAULT_MAX_AGE_DAYS,
    ):
        self._ips = ips
        self._writer = writer
        self._reader = reader
        self._timeout = timeout
        self._concurrency = concurrency
        self._max_age_days = max_age_days

    def run(self) -> BatchResult:
        start_time = time.time()

        if not self._ips:
            total_elapsed = time.time() - start_time
            return BatchResult(total_elapsed=total_elapsed)

        all_mappings: list[dict] = []
        skip_count = 0
        expired_count = 0
        total = len(self._ips)

        for idx, ip in enumerate(self._ips, 1):
            ip_data = self._reader.get_ip_data(ip)
            if ip_data is None:
                skip_count += 1
                logger.debug("[%d/%d] %s — 无数据，跳过", idx, total, ip)
                continue

            existing_verify = ip_data.get(CHANNEL_NAME)
            if existing_verify and not _is_verify_expired(existing_verify, self._max_age_days):
                skip_count += 1
                logger.debug("[%d/%d] %s — 验证结果有效（%d天内），跳过", idx, total, ip, self._max_age_days)
                continue

            if existing_verify and _is_verify_expired(existing_verify, self._max_age_days):
                expired_count += 1
                logger.info("[%d/%d] %s — 验证结果已过期（超过%.0f天），重新验证", idx, total, ip, self._max_age_days)

            ip_data["ip"] = ip
            mappings = extract_domain_mappings(ip_data)
            if mappings:
                all_mappings.extend(mappings)
            else:
                skip_count += 1
                logger.debug("[%d/%d] %s — 无域名数据", idx, total, ip)

        if not all_mappings:
            logger.info("未提取到域名映射，跳过验证")
            total_elapsed = time.time() - start_time
            return BatchResult(skip_count=skip_count, total_elapsed=total_elapsed)

        logger.info(
            "提取 %d 个域名映射，开始验证 (并发: %d, 超时: %.1fs)",
            len(all_mappings),
            self._concurrency,
            self._timeout,
        )

        def on_progress(done, total_count):
            if done % 20 == 0 or done == total_count:
                logger.info("DNS 验证进度: %d/%d", done, total_count)

        verify_results = batch_verify(
            all_mappings,
            timeout=self._timeout,
            concurrency=self._concurrency,
            progress_callback=on_progress,
        )

        grouped = build_verify_results(all_mappings, verify_results)
        verify_data = add_verify_stats(grouped)

        success_count = 0
        for ip, data in verify_data.items():
            self._writer.add_or_update_ip(ip, CHANNEL_NAME, data)
            success_count += 1
            logger.info(
                "[IP %s] 验证完成: matched=%d, changed=%d, unresolved=%d",
                ip,
                data["matched"],
                data["changed"],
                data["unresolved"],
            )

        total_elapsed = time.time() - start_time
        return BatchResult(
            success_count=success_count,
            skip_count=skip_count,
            total_elapsed=total_elapsed,
        )
