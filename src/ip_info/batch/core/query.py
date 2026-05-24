import logging
import time
from dataclasses import dataclass

from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.errors import ChannelError, ChannelPermanentError
from ip_info.store.protocols import IPDataWriter
from ip_info.utils.progress import ProgressTracker

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    success_count: int = 0
    fail_count: int = 0
    skip_count: int = 0
    total_elapsed: float = 0.0
    stopped_early: bool = False
    stop_reason: str = ""


class BaseBatchQuery:
    def __init__(
        self,
        channel_name: str,
        channel: BaseChannelAdapter,
        writer: IPDataWriter,
        ips: list[str],
        *,
        delay: float = 0,
        no_validate: bool = False,
        progress_tracker: ProgressTracker | None = None,
        max_consecutive_network_failures: int = 5,
    ):
        self._channel_name = channel_name
        self._channel = channel
        self._writer = writer
        self._delay = delay
        self._no_validate = no_validate
        self._progress_tracker = progress_tracker
        self._max_failures = max_consecutive_network_failures
        seen: set[str] = set()
        self._all_ips: list[str] = []
        for ip in ips:
            if ip not in seen:
                seen.add(ip)
                self._all_ips.append(ip)
        self._pending_ips: list[str] = self._compute_pending()

    @property
    def total_count(self) -> int:
        return len(self._all_ips)

    @property
    def pending_count(self) -> int:
        return len(self._pending_ips)

    def _compute_pending(self) -> list[str]:
        if self._progress_tracker is None:
            return list(self._all_ips)
        return [ip for ip in self._all_ips if not self._progress_tracker.is_processed(ip)]

    def run(self) -> BatchResult:
        start_time = time.time()
        success_count = 0
        fail_count = 0
        consecutive_failures = 0
        skip_count = self.total_count - self.pending_count

        if not self._no_validate:
            self._channel.validate()

        if self._channel.disabled:
            logger.warning(
                "[%s] 渠道已禁用，跳过查询。可能原因：验证失败或凭证无效",
                self._channel_name,
            )
            total_elapsed = time.time() - start_time
            return BatchResult(
                fail_count=len(self._pending_ips),
                skip_count=skip_count,
                total_elapsed=total_elapsed,
            )

        for idx, ip in enumerate(self._pending_ips, start=1):
            total = len(self._pending_ips)
            try:
                data = self._channel.fetch(ip, delay=self._delay)
            except ChannelPermanentError as e:
                fail_count += 1
                logger.warning(
                    "[%s] 进度: %d/%d - 查询失败(永久错误): %s - %s",
                    self._channel_name,
                    idx,
                    total,
                    ip,
                    e,
                )
                break
            except ChannelError as e:
                fail_count += 1
                consecutive_failures += 1
                logger.warning(
                    "[%s] 进度: %d/%d - 查询失败: %s - %s",
                    self._channel_name,
                    idx,
                    total,
                    ip,
                    e,
                )
                if consecutive_failures >= self._max_failures:
                    logger.warning(
                        "[%s] 连续 %d 次失败，触发熔断",
                        self._channel_name,
                        consecutive_failures,
                    )
                    break
                continue

            self._writer.add_or_update_ip(ip, self._channel_name, data)
            success_count += 1
            consecutive_failures = 0
            logger.info(
                "[%s] 进度: %d/%d - 查询成功: %s",
                self._channel_name,
                idx,
                total,
                ip,
            )
            if self._progress_tracker is not None:
                self._progress_tracker.mark_processed(ip)

        if self._channel.disabled:
            stop_reason = "permanent_error"
            stopped_early = True
        elif consecutive_failures >= self._max_failures:
            stop_reason = "circuit_break"
            stopped_early = True
        else:
            stop_reason = ""
            stopped_early = False

        total_elapsed = time.time() - start_time
        return BatchResult(
            success_count=success_count,
            fail_count=fail_count,
            skip_count=skip_count,
            total_elapsed=total_elapsed,
            stopped_early=stopped_early,
            stop_reason=stop_reason,
        )
