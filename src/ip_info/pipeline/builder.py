from __future__ import annotations

import logging
from dataclasses import dataclass

from ip_info.pipeline.context import PipelineContext
from ip_info.pipeline.phase import PhaseResult

logger = logging.getLogger(__name__)


@dataclass
class Pipeline:
    phases: list
    context: PipelineContext

    def run(self) -> list[PhaseResult]:
        results = []
        for phase in self.phases:
            logger.info("执行阶段: %s", phase.name)
            result = phase.run()
            results.append(result)
            logger.info("阶段完成: %s — %s", phase.name, result.message)
        return results


class PipelineBuilder:
    def __init__(self, context: PipelineContext):
        self._context = context
        self._ips: list[str] = []
        self._phases: list = []
        self._channels: dict = {}
        self._skip_channels: set[str] = set()
        self._skip_dynamic: bool = False

    @property
    def ips(self) -> list[str]:
        return self._ips

    @property
    def phases(self) -> list:
        return self._phases

    @property
    def context(self) -> PipelineContext:
        return self._context

    def with_ips(self, ips: list[str]) -> PipelineBuilder:
        self._ips = ips
        return self

    def with_channel(self, name: str, channel) -> PipelineBuilder:
        self._channels[name] = channel
        return self

    def skip_channel(self, name: str) -> PipelineBuilder:
        self._skip_channels.add(name)
        if name in self._channels:
            self._channels[name].disabled = True
        return self

    def skip_dynamic_ips(self) -> PipelineBuilder:
        self._skip_dynamic = True
        return self

    def get_channel(self, name: str):
        return self._channels.get(name)

    def add_phase(self, phase) -> PipelineBuilder:
        self._phases.append(phase)
        return self

    def build(self) -> Pipeline:
        return Pipeline(phases=list(self._phases), context=self._context)
