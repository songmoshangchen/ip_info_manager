from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ip_info.batch.core.query import BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.pipeline.core.batch_step import BatchStep
from ip_info.pipeline.core.channel_batch_step import ChannelBatchStep
from ip_info.pipeline.core.context import PipelineContext
from ip_info.pipeline.core.phase import PhaseResult

logger = logging.getLogger(__name__)


class DeepQueryPhase:
    def __init__(
        self,
        ips: list[str],
        context: PipelineContext,
        steps: list[BatchStep] | None = None,
        *,
        aizhan_channel: BaseChannelAdapter | None = None,
        chinaz_channel: BaseChannelAdapter | None = None,
        fofa_channel: BaseChannelAdapter | None = None,
        no_validate: bool = False,
        aizhan_workers: int = 1,
        chinaz_workers: int = 1,
        fofa_workers: int = 1,
        skip_ips: set[str] | None = None,
    ):
        self._ips = ips
        self._context = context
        self._writer = context.writer
        self._reader = context.reader
        self._progress_tracker = context.progress_tracker
        self._skip_ips = skip_ips or set()
        self._no_validate = no_validate

        self._steps = steps or []

        if not self._steps:
            query_ips = [ip for ip in ips if ip not in (skip_ips or set())]
            legacy_channels = [
                ("aizhan", aizhan_channel, aizhan_workers),
                ("chinaz", chinaz_channel, chinaz_workers),
                ("fofa_host", fofa_channel, fofa_workers),
            ]
            for name, ch, workers in legacy_channels:
                if ch is not None:
                    self._steps.append(
                        ChannelBatchStep(
                            channel_name=name,
                            channel=ch,
                            ips=query_ips,
                            writer=self._writer,
                            workers=workers,
                            progress_tracker=self._progress_tracker,
                            no_validate=no_validate,
                        )
                    )

    @property
    def name(self) -> str:
        return "深度查询"

    def run(self) -> PhaseResult:
        start_time = time.time()

        if not self._ips:
            return PhaseResult(
                success=True,
                message="无 IP 需深度查询",
                elapsed=time.time() - start_time,
            )

        query_ips = [ip for ip in self._ips if ip not in self._skip_ips]
        if self._skip_ips:
            logger.info("跳过 %d 个动态 IP 的深度查询", len(self._skip_ips))

        if not query_ips:
            return PhaseResult(
                success=True,
                message=f"全部 {len(self._skip_ips)} 个 IP 为动态 IP，跳过深度查询",
                elapsed=time.time() - start_time,
            )

        # 将过滤后的 IP 列表传播到每个 step
        step_names = []
        for step in self._steps:
            if hasattr(step, "_ips"):
                old_count = len(step._ips)
                step._ips = query_ips
                step_names.append(f"{step.name}({old_count}->{len(query_ips)})")
        logger.info(
            "深度查询 IP 过滤完成: %d/%d 个 IP 需查询, 步骤: %s",
            len(query_ips),
            len(self._ips),
            ", ".join(step_names),
        )

        if not self._steps:
            return PhaseResult(success=True, message="无步骤需执行", elapsed=time.time() - start_time)

        results: dict[str, BatchResult] = {}

        with ThreadPoolExecutor(max_workers=len(self._steps)) as executor:
            futures = {executor.submit(step.run): step.name for step in self._steps}
            for future in as_completed(futures):
                step_name = futures[future]
                results[step_name] = future.result()

        total_success = sum(r.success_count for r in results.values())
        any_success = total_success > 0
        elapsed = time.time() - start_time

        parts = [f"{name}: {r.success_count}成功" for name, r in results.items()]

        return PhaseResult(
            success=any_success,
            message=", ".join(parts),
            elapsed=elapsed,
            data=results,
        )
