from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class PhaseResult:
    success: bool = True
    message: str = ""
    elapsed: float = 0.0
    data: dict = field(default_factory=dict)


@runtime_checkable
class Phase(Protocol):
    @property
    def name(self) -> str: ...

    def run(self) -> PhaseResult: ...
