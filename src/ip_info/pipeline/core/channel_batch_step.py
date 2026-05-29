from __future__ import annotations

from ip_info.batch.core.concurrent import run_concurrent
from ip_info.batch.core.query import BatchResult
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.store.protocols import IPDataWriter
from ip_info.utils.progress import ProgressTracker


class ChannelBatchStep:
    def __init__(
        self,
        channel_name: str,
        channel: BaseChannelAdapter,
        ips: list[str],
        writer: IPDataWriter,
        *,
        workers: int = 1,
        delay: float | None = None,
        progress_tracker: ProgressTracker | None = None,
        no_validate: bool = False,
    ):
        self._channel_name = channel_name
        self._channel = channel
        self._ips = ips
        self._writer = writer
        self._workers = workers
        self._delay = delay if delay is not None else channel.default_delay
        self._progress_tracker = progress_tracker
        self._no_validate = no_validate

    @property
    def name(self) -> str:
        return self._channel_name

    @property
    def delay(self) -> float:
        return self._delay

    def run(self) -> BatchResult:
        return run_concurrent(
            ips=self._ips,
            channel=self._channel,
            writer=self._writer,
            channel_name=self._channel_name,
            workers=self._workers,
            delay=self._delay,
            no_validate=self._no_validate,
            progress_tracker=self._progress_tracker,
        )
