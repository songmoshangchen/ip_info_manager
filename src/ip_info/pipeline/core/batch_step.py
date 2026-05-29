from typing import Protocol, runtime_checkable

from ip_info.batch.core.query import BatchResult


@runtime_checkable
class BatchStep(Protocol):
    @property
    def name(self) -> str: ...

    def run(self) -> BatchResult: ...
