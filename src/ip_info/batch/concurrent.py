import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ip_info.batch.protocols import ProgressTracker
from ip_info.batch.query import BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.errors import ChannelError, ChannelPermanentError
from ip_info.store.protocols import IPDataWriter

logger = logging.getLogger(__name__)


def run_concurrent(
    ips: list[str],
    channel: BaseChannelAdapter,
    writer: IPDataWriter,
    channel_name: str,
    *,
    workers: int = 1,
    delay: float = 0,
    no_validate: bool = False,
    progress_tracker: ProgressTracker | None = None,
    max_consecutive_network_failures: int = 5,
) -> BatchResult:
    """并发批量查询，封装 ThreadPoolExecutor + 熔断保护 + 进度跟踪。

    workers <= 1 时退化为 BaseBatchQuery.run() 单线程模式。
    """
    # 去重
    seen: set[str] = set()
    unique_ips: list[str] = []
    for ip in ips:
        if ip not in seen:
            seen.add(ip)
            unique_ips.append(ip)

    # 过滤已处理
    if progress_tracker is not None:
        pending_ips = [ip for ip in unique_ips if not progress_tracker.is_processed(ip)]
    else:
        pending_ips = list(unique_ips)

    # 渠道验证
    if not no_validate:
        channel.validate()

    if channel.disabled:
        return BatchResult()

    # 单线程退化
    if workers <= 1:
        from ip_info.batch.query import BaseBatchQuery

        query = BaseBatchQuery(
            channel_name=channel_name,
            channel=channel,
            writer=writer,
            ips=unique_ips,
            delay=delay,
            no_validate=True,  # 已验证
            progress_tracker=progress_tracker,
            max_consecutive_network_failures=max_consecutive_network_failures,
        )
        return query.run()

    # 并发查询
    start_time = time.time()
    success_count = 0
    fail_count = 0
    consecutive_failures = 0
    lock = threading.Lock()
    stop_event = threading.Event()
    stop_reason = ""

    def _query_one(ip: str) -> tuple[str, dict | None, Exception | None]:
        """查询单个 IP，返回 (ip, data, error)"""
        if stop_event.is_set():
            return (ip, None, None)
        try:
            data = channel.fetch(ip, delay=delay)
            return (ip, data, None)
        except (ChannelError, ChannelPermanentError) as e:
            return (ip, None, e)
        except Exception:
            raise

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_query_one, ip): ip for ip in pending_ips}

        for future in as_completed(futures):
            if stop_event.is_set():
                break

            ip, data, error = future.result()

            if error is not None:
                with lock:
                    fail_count += 1
                    if isinstance(error, ChannelPermanentError):
                        channel.disabled = True
                        stop_event.set()
                        stop_reason = "permanent_error"
                    else:
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_network_failures:
                            stop_event.set()
                            stop_reason = "circuit_break"
                continue

            if data is None:
                # 被 stop_event 跳过的
                continue

            writer.add_or_update_ip(ip, channel_name, data)
            with lock:
                success_count += 1
                consecutive_failures = 0
            if progress_tracker is not None:
                progress_tracker.mark_processed(ip)

    # 取消剩余任务
    stop_event.set()

    total_elapsed = time.time() - start_time
    stopped_early = bool(stop_reason)

    return BatchResult(
        success_count=success_count,
        fail_count=fail_count,
        total_elapsed=total_elapsed,
        stopped_early=stopped_early,
        stop_reason=stop_reason,
    )
