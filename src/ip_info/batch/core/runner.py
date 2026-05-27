from typing import Protocol, runtime_checkable

from ip_info.batch.core.query import BatchResult


@runtime_checkable
class BatchRunner(Protocol):
    def run(self) -> BatchResult: ...
