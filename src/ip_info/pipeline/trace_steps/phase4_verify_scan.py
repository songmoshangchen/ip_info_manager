from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ip_info.batch.core.query import BatchResult
from ip_info.channel.port_scan import PortScanChannel
from ip_info.pipeline.core.batch_step import BatchStep
from ip_info.pipeline.core.channel_batch_step import ChannelBatchStep
from ip_info.pipeline.core.context import PipelineContext
from ip_info.pipeline.core.phase import PhaseResult
from ip_info.processors.dns_verify.runner import BatchDnsVerify

logger = logging.getLogger(__name__)


class VerifyScanPhase:
    def __init__(
        self,
        ips: list[str],
        context: PipelineContext,
        steps: list[BatchStep] | None = None,
        *,
        nmap_channel: PortScanChannel | None = None,
        force_days: int | None = None,
        max_age_days: int = 7,
        dns_timeout: float = 3.0,
        dns_concurrency: int = 10,
        nmap_workers: int = 1,
        no_validate: bool = False,
        skip_ips: set[str] | None = None,
    ):
        self._ips = ips
        self._context = context
        self._writer = context.writer
        self._reader = context.reader
        self._progress_tracker = context.progress_tracker
        self._domain_cache = context.domain_cache
        self._skip_ips = skip_ips or set()

        self._steps = steps or []

        if not self._steps:
            dns_verify = BatchDnsVerify(
                ips=ips,
                writer=self._writer,
                reader=self._reader,
                domain_cache=self._domain_cache,
                force_days=force_days,
                max_age_days=max_age_days,
                timeout=dns_timeout,
                concurrency=dns_concurrency,
            )
            self._steps.append(dns_verify)

            if nmap_channel is not None:
                scan_ips = [ip for ip in ips if ip not in (skip_ips or set())]
                self._steps.append(
                    ChannelBatchStep(
                        channel_name="port_scan",
                        channel=nmap_channel,
                        ips=scan_ips,
                        writer=self._writer,
                        workers=nmap_workers,
                        progress_tracker=self._progress_tracker,
                        no_validate=no_validate,
                    )
                )

    @property
    def name(self) -> str:
        return "验证与扫描"

    def run(self) -> PhaseResult:
        start_time = time.time()

        if not self._ips:
            return PhaseResult(success=True, message="无 IP 需验证/扫描", elapsed=time.time() - start_time)

        if not self._steps:
            return PhaseResult(success=True, message="无步骤需执行", elapsed=time.time() - start_time)

        if self._skip_ips:
            logger.info("跳过 %d 个动态 IP 的端口扫描", len(self._skip_ips))

        results: dict[str, BatchResult] = {}

        with ThreadPoolExecutor(max_workers=len(self._steps)) as executor:
            futures = {executor.submit(step.run): step.name for step in self._steps}
            for future in as_completed(futures):
                step_name = futures[future]
                results[step_name] = future.result()

        parts = [f"{name}: {r.success_count}成功" for name, r in results.items()]
        elapsed = time.time() - start_time

        return PhaseResult(
            success=True,
            message=", ".join(parts),
            elapsed=elapsed,
            data=results,
        )
