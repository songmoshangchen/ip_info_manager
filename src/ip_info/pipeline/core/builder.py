from __future__ import annotations

import logging

from ip_info.pipeline.core.context import PipelineContext
from ip_info.pipeline.core.filter_ips import filter_dynamic_ips
from ip_info.pipeline.core.pipeline import FilterFn, Pipeline

logger = logging.getLogger(__name__)


class PipelineBuilder:
    def __init__(self, context: PipelineContext):
        self._context = context
        self._ips: list[str] = []
        self._phases: list = []
        self._channels: dict = {}
        self._skip_channels: set[str] = set()
        self._filters: list[tuple[str, FilterFn]] = []

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
        def _filter_dynamic_ips_for_pipeline(ips, context):
            dynamic_list, non_dynamic_list = filter_dynamic_ips(ips, context.reader)
            if context.config is None:
                context.config = {}
            context.config["dynamic_ips"] = set(dynamic_list)
            return non_dynamic_list

        self._filters.append(("分类与标签", _filter_dynamic_ips_for_pipeline))
        return self

    def get_channel(self, name: str):
        return self._channels.get(name)

    def add_phase(self, phase) -> PipelineBuilder:
        self._phases.append(phase)
        return self

    def with_filter(self, after_phase_name: str, filter_fn: FilterFn) -> PipelineBuilder:
        """Register a filter that runs after the named phase.

        Args:
            after_phase_name: The Phase name after which the filter runs.
            filter_fn: A callable(ips, context) -> filtered_ips.
        """
        self._filters.append((after_phase_name, filter_fn))
        return self

    def build(self) -> Pipeline:
        pipeline = Pipeline(filters=self._filters)
        for phase in self._phases:
            pipeline.register(phase)
        return pipeline
