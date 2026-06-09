from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ip_info.batch.core.query import BatchResult
from ip_info.pipeline.core.batch_step import BatchStep
from ip_info.pipeline.core.context import PipelineContext
from ip_info.pipeline.core.phase import PhaseResult

logger = logging.getLogger(__name__)


class BasicCollectPhase:
    def __init__(
        self,
        ips: list[str],
        context: PipelineContext,
        steps: list[BatchStep] | None = None,
        *,
        ipinfo_channel=None,
        rdns_channel=None,
        no_validate: bool = False,
        ipinfo_workers: int = 1,
        rdns_workers: int = 1,
    ):
        self._ips = ips
        self._context = context
        self._writer = context.writer
        self._reader = context.reader
        self._progress_tracker = context.progress_tracker
        self._steps = steps or []
        self._no_validate = no_validate
        self._skip_ips: set[str] = set()

        if not self._steps and ipinfo_channel and rdns_channel:
            from ip_info.pipeline.core.channel_batch_step import ChannelBatchStep

            self._steps = [
                ChannelBatchStep(
                    channel_name="ipinfo_api",
                    channel=ipinfo_channel,
                    ips=ips,
                    writer=self._writer,
                    workers=ipinfo_workers,
                    progress_tracker=self._progress_tracker,
                    no_validate=no_validate,
                ),
                ChannelBatchStep(
                    channel_name="rdns_ptr",
                    channel=rdns_channel,
                    ips=ips,
                    writer=self._writer,
                    workers=rdns_workers,
                    progress_tracker=self._progress_tracker,
                    no_validate=no_validate,
                ),
            ]

    @property
    def name(self) -> str:
        return "基础情报采集"

    def run(self) -> PhaseResult:
        start_time = time.time()

        if not self._ips:
            return PhaseResult(success=True, message="无 IP 需处理", elapsed=time.time() - start_time)

        if not self._steps:
            return PhaseResult(success=True, message="无步骤需执行", elapsed=time.time() - start_time)

        results: dict[str, BatchResult] = {}

        with ThreadPoolExecutor(max_workers=len(self._steps)) as executor:
            futures = {executor.submit(step.run): step.name for step in self._steps}
            for future in as_completed(futures):
                step_name = futures[future]
                results[step_name] = future.result()

        total_fail = sum(r.fail_count for r in results.values())
        total_success = sum(r.success_count for r in results.values())
        any_stopped = any(r.stopped_early for r in results.values())
        # 无失败即成功；渠道禁用(stopped_early)但其他渠道有成功也算成功
        success = total_fail == 0 and (not any_stopped or total_success > 0)

        parts = [f"{name}: {r.success_count}成功" for name, r in results.items()]
        elapsed = time.time() - start_time

        return PhaseResult(
            success=success,
            message=", ".join(parts),
            elapsed=elapsed,
            data=results,
        )
