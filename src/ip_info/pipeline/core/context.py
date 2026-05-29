from __future__ import annotations

from dataclasses import dataclass, field

from ip_info.store.protocols import DomainCache, IPDataReader, IPDataWriter
from ip_info.utils.progress import ProgressTracker


@dataclass
class PipelineContext:
    writer: IPDataWriter
    reader: IPDataReader
    progress_tracker: ProgressTracker
    domain_cache: DomainCache | None = field(default=None)
    config: dict | None = field(default=None)
