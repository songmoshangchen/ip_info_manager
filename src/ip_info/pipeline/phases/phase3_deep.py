import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ip_info.batch.core.concurrent import run_concurrent
from ip_info.batch.core.query import BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.pipeline.phase import PhaseResult
from ip_info.store.protocols import IPDataReader, IPDataWriter
from ip_info.utils.progress import ProgressTracker

logger = logging.getLogger(__name__)


class DeepQueryPhase:
    def __init__(
        self,
        ips: list[str],
        writer: IPDataWriter,
        reader: IPDataReader,
        aizhan_channel: BaseChannelAdapter,
        chinaz_channel: BaseChannelAdapter,
        fofa_channel: BaseChannelAdapter,
        *,
        no_validate: bool = False,
        aizhan_workers: int = 1,
        chinaz_workers: int = 1,
        fofa_workers: int = 1,
        skip_ips: set[str] | None = None,
        progress_tracker: ProgressTracker | None = None,
    ):
        self._ips = ips
        self._writer = writer
        self._reader = reader
        self._aizhan_channel = aizhan_channel
        self._chinaz_channel = chinaz_channel
        self._fofa_channel = fofa_channel
        self._no_validate = no_validate
        self._aizhan_workers = aizhan_workers
        self._chinaz_workers = chinaz_workers
        self._fofa_workers = fofa_workers
        self._skip_ips = skip_ips or set()
        self._progress_tracker = progress_tracker

    @property
    def name(self) -> str:
        return "深度查询"

    def run(self) -> PhaseResult:
        start_time = time.time()

        if not self._ips:
            return PhaseResult(success=True, message="无 IP 需深度查询", elapsed=time.time() - start_time)

        query_ips = [ip for ip in self._ips if ip not in self._skip_ips]
        if self._skip_ips:
            logger.info("跳过 %d 个动态 IP 的深度查询", len(self._skip_ips))

        if not query_ips:
            return PhaseResult(
                success=True,
                message=f"全部 {len(self._skip_ips)} 个 IP 为动态 IP，跳过深度查询",
                elapsed=time.time() - start_time,
            )

        if not self._no_validate:
            self._aizhan_channel.validate()
            self._chinaz_channel.validate()
            self._fofa_channel.validate()

        channels = [
            ("aizhan", self._aizhan_channel, self._aizhan_workers),
            ("chinaz", self._chinaz_channel, self._chinaz_workers),
            ("fofa_host", self._fofa_channel, self._fofa_workers),
        ]

        results: dict[str, BatchResult | None] = {}

        def run_channel(name: str, channel: BaseChannelAdapter, workers: int) -> tuple[str, BatchResult | None]:
            if channel.disabled:
                total = len(query_ips)
                done = sum(1 for ip in query_ips if self._reader.get_channel_data(ip, name) is not None)
                pending = total - done
                logger.warning(
                    "%s 渠道已禁用，跳过 (共 %d 个 IP, 已有结果 %d, 剩余 %d 未查询)",
                    name,
                    total,
                    done,
                    pending,
                )
                return (name, None)
            result = run_concurrent(
                ips=query_ips,
                channel=channel,
                writer=self._writer,
                channel_name=name,
                workers=workers,
                delay=channel.default_delay,
                no_validate=True,
                progress_tracker=self._progress_tracker,
            )
            return (name, result)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(run_channel, name, ch, workers): name for name, ch, workers in channels}
            for future in as_completed(futures):
                name, result = future.result()
                results[name] = result

        total_success = sum(r.success_count for r in results.values() if r is not None)
        any_success = total_success > 0
        elapsed = time.time() - start_time

        parts = []
        for name, result in results.items():
            if result is not None:
                parts.append(f"{name}: {result.success_count}成功")
            else:
                parts.append(f"{name}: 跳过")

        return PhaseResult(
            success=any_success,
            message=", ".join(parts),
            elapsed=elapsed,
            data=results,
        )
