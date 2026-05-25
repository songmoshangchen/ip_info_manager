import logging
import time
from dataclasses import dataclass, field

from ip_info.pipeline.phase import Phase, PhaseResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    success: bool = True
    total_elapsed: float = 0.0
    phase_results: dict[str, PhaseResult] = field(default_factory=dict)
    failed_phase: str = ""


class Pipeline:
    def __init__(self):
        self._phases: list[Phase] = []

    def register(self, phase: Phase) -> None:
        self._phases.append(phase)

    def run(
        self,
        from_phase: int | None = None,
        only_phase: int | None = None,
        skip_phases: set[int] | None = None,
    ) -> PipelineResult:
        start_time = time.time()
        phase_results: dict[str, PhaseResult] = {}
        skip = skip_phases or set()

        for i, phase in enumerate(self._phases, 1):
            if only_phase is not None and i != only_phase:
                continue
            if from_phase is not None and i < from_phase:
                continue
            if i in skip:
                continue

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
                )

        total_elapsed = time.time() - start_time
        return PipelineResult(
            success=True,
            total_elapsed=total_elapsed,
            phase_results=phase_results,
        )
