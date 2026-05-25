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


def _is_expired(data: dict, max_age_days: int) -> bool:
    verify_time_str = data.get("verify_time", "")
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
        max_age_days: int = DEFAULT_MAX_AGE_DAYS,
        force_days: int | None = None,
        domain_cache=None,
    ):
        if not isinstance(max_age_days, int) or max_age_days < 1:
            raise ValueError(f"max_age_days must be a positive integer (>= 1), got {max_age_days}")
        if force_days is not None and (not isinstance(force_days, int) or force_days < 0):
            raise ValueError(f"force_days must be a non-negative integer (>= 0) if provided, got {force_days}")

        self._ips = ips
        self._writer = writer
        self._reader = reader
        self._timeout = timeout
        self._concurrency = concurrency
        self._max_age_days = max_age_days
        self._force_days = force_days
        self._domain_cache = domain_cache

    def run(self) -> BatchResult:
        start_time = time.time()

        if not self._ips:
            total_elapsed = time.time() - start_time
            return BatchResult(total_elapsed=total_elapsed)

        all_mappings: list[dict] = []
        skip_count = 0
        total = len(self._ips)

        for idx, ip in enumerate(self._ips, 1):
            ip_data = self._reader.get_ip_data(ip)
            if ip_data is None:
                skip_count += 1
                logger.debug("[%d/%d] %s — 无数据，跳过", idx, total, ip)
                continue

            existing_verify = ip_data.get(CHANNEL_NAME)
            if existing_verify and self._force_days != 0 and not _is_expired(existing_verify, self._max_age_days):
                skip_count += 1
                logger.debug("[%d/%d] %s — 验证结果有效（%d天内），跳过", idx, total, ip, self._max_age_days)
                continue

            if existing_verify:
                if self._force_days is not None and (
                    self._force_days == 0 or _is_expired(existing_verify, self._force_days)
                ):
                    logger.info(
                        "[%d/%d] %s — 验证结果已过期，force_days=%d，重新验证",
                        idx,
                        total,
                        ip,
                        self._force_days,
                    )
                else:
                    skip_count += 1
                    logger.warning(
                        "[%d/%d] %s — 验证结果已过期（超过%d天），跳过",
                        idx,
                        total,
                        ip,
                        self._max_age_days,
                    )
                    continue

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

        mappings_to_verify: list[dict] = []
        cached_results: list[tuple[dict, dict]] = []

        if self._domain_cache is not None:
            for mapping in all_mappings:
                domain = mapping["domain"]
                cached = self._domain_cache.get(domain)
                if cached is not None and not _is_expired(cached, self._max_age_days):
                    cached_results.append((mapping, cached))
                else:
                    mappings_to_verify.append(mapping)
        else:
            mappings_to_verify = all_mappings

        verify_results = []
        if mappings_to_verify:
            logger.info(
                "提取 %d 个域名映射，开始验证 (并发: %d, 超时: %.1fs)",
                len(mappings_to_verify),
                self._concurrency,
                self._timeout,
            )

            def on_progress(done, total_count):
                if done % 20 == 0 or done == total_count:
                    logger.info("DNS 验证进度: %d/%d", done, total_count)

            verify_results = batch_verify(
                mappings_to_verify,
                timeout=self._timeout,
                concurrency=self._concurrency,
                progress_callback=on_progress,
            )

            if self._domain_cache is not None:
                for i, mapping in enumerate(mappings_to_verify):
                    self._domain_cache.set(mapping["domain"], verify_results[i])

        combined_candidates = mappings_to_verify
        combined_results = verify_results
        for mapping, cached_result in cached_results:
            combined_candidates.append(mapping)
            combined_results.append(cached_result)

        grouped = build_verify_results(combined_candidates, combined_results)
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
