import logging
import time
from dataclasses import dataclass, field
from typing import Callable

from ip_info.pipeline.phase import Phase, PhaseResult

logger = logging.getLogger(__name__)

# Inter-phase filter: (phase_name, filter_fn)
# filter_fn(current_ips, context) -> filtered_ips
FilterFn = Callable[[list[str], object], list[str]]
InterPhaseFilter = tuple[str, FilterFn]


@dataclass
class PipelineResult:
    success: bool = True
    total_elapsed: float = 0.0
    phase_results: dict[str, PhaseResult] = field(default_factory=dict)
    failed_phase: str = ""
    filter_results: dict[str, list[str]] = field(default_factory=dict)


class Pipeline:
    def __init__(self, filters: list[InterPhaseFilter] | None = None):
        self._phases: list[Phase] = []
        self._filters: dict[str, list[FilterFn]] = {}
        if filters:
            for phase_name, filter_fn in filters:
                self._filters.setdefault(phase_name, []).append(filter_fn)

    def register(self, phase: Phase) -> None:
        self._phases.append(phase)

    def add_filter(self, phase_name: str, filter_fn: FilterFn) -> None:
        self._filters.setdefault(phase_name, []).append(filter_fn)

    def run(
        self,
        from_phase: int | None = None,
        only_phase: int | None = None,
        skip_phases: set[int] | None = None,
        current_ips: list[str] | None = None,
    ) -> PipelineResult:
        start_time = time.time()
        phase_results: dict[str, PhaseResult] = {}
        filter_results: dict[str, list[str]] = {}
        skip = skip_phases or set()
        ips = current_ips

        for i, phase in enumerate(self._phases, 1):
            if only_phase is not None and i != only_phase:
                continue
            if from_phase is not None and i < from_phase:
                continue
            if i in skip:
                continue

            # Update phase ips if filters have modified them
            if ips is not None and hasattr(phase, "_ips"):
                phase._ips = ips

            logger.info("阶段 %d: %s", i, phase.name)
            result = phase.run()
            logger.info("阶段 %d 完成: %s (%.1fs)", i, result.message, result.elapsed)
            phase_results[phase.name] = result

            if not result.success:
                total_elapsed = time.time() - start_time
                return PipelineResult(
                    success=False,
                    total_elapsed=total_elapsed,
                    phase_results=phase_results,
                    failed_phase=phase.name,
                    filter_results=filter_results,
                )

            # Apply inter-phase filters after this phase
            if phase.name in self._filters:
                if ips is None:
                    ips = getattr(phase, "_ips", [])
                for filter_fn in self._filters[phase.name]:
                    ips = filter_fn(ips, phase._context if hasattr(phase, "_context") else None)
                    filter_results[f"{phase.name}:{filter_fn.__name__}"] = ips
                    logger.info("过滤器 %s 在阶段 '%s' 后执行: %d IP", filter_fn.__name__, phase.name, len(ips))

                # Propagate skip_ips from context.config to subsequent phases
                # (Option C: Pipeline modifies Phase._skip_ips between phases)
                if hasattr(phase, "_context") and phase._context is not None:
                    ctx_config = getattr(phase._context, "config", None)
                    if ctx_config and "dynamic_ips" in ctx_config:
                        dynamic = ctx_config["dynamic_ips"]
                        for later_phase in self._phases[i:]:
                            if hasattr(later_phase, "_skip_ips"):
                                later_phase._skip_ips = dynamic

        total_elapsed = time.time() - start_time
        return PipelineResult(
            success=True,
            total_elapsed=total_elapsed,
            phase_results=phase_results,
            filter_results=filter_results,
        )
