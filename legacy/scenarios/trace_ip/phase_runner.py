from __future__ import annotations

import logging

logger = logging.getLogger('ip_info_manager.scenarios.trace_ip')


class PhaseRunner:

    def __init__(
        self,
        ips: list,
        phase_num: int,
        channels: list,
        data_store,
        progress_ips: set | None = None,
    ):
        self._ips = ips
        self.phase_num = phase_num
        self.channels = channels
        self._store = data_store
        self._progress_ips = progress_ips or set()

    def compute_processed_from_store(self) -> set:
        processed = set()
        for ip in self._ips:
            ip_data = self._store.get_ip_data(ip)
            if ip_data is None:
                continue
            if all(ch in ip_data for ch in self.channels):
                processed.add(ip)
        return processed

    def get_pending_ips(self) -> list:
        processed = self.compute_processed_from_store() | self._progress_ips
        return [ip for ip in self._ips if ip not in processed]

    def run(self, query_fn):
        pending_ips = self.get_pending_ips()
        if not pending_ips:
            logger.info("Phase %d: 所有IP已处理，跳过", self.phase_num)
            return

        logger.info("Phase %d: 总计 %d IP, 待处理 %d",
                     self.phase_num, len(self._ips), len(pending_ips))

        for ip in pending_ips:
            channel_specs = self._build_channel_specs(ip)
            results = query_fn(ip, channel_specs)
            if results:
                for channel, data in results.items():
                    self._store.add_or_update_ip(ip, channel, data)

    def _build_channel_specs(self, ip: str) -> list:
        return [{'channel': ch} for ch in self.channels]
