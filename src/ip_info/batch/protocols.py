from typing import Protocol, runtime_checkable


@runtime_checkable
class ProgressTracker(Protocol):
    def is_processed(self, ip: str) -> bool: ...
    def mark_processed(self, ip: str) -> None: ...
