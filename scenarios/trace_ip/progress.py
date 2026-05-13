import atexit
import json
import logging
import os
from datetime import datetime

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from writer import IPWriter

logger = logging.getLogger('ip_info_manager.scenarios.trace_ip')


class ProgressManager:

    _PHASE_CONFIG = {
        1: 'trace_phase1.progress',
        3: 'trace_phase3.progress',
        5: 'trace_phase5.progress',
    }

    _PHASE_MARKERS = {
        1: 'trace_phase1_done',
        2: 'trace_phase2_done',
        3: 'trace_phase3_done',
        4: 'trace_phase4_done',
        5: 'trace_phase5_done',
        6: 'trace_phase6_done',
        7: 'trace_phase7_done',
    }

    def __init__(self, output_dir: str, prefix: str):
        self._output_dir = output_dir
        self._prefix = prefix
        self._cache: dict = {}
        self._pending: dict = {}

    def load_completed(self, phase: int) -> set:
        if phase in self._cache:
            return self._cache[phase]

        completed = set()
        progress_file = self._get_progress_file(phase)
        if progress_file and os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        ip = line.strip()
                        if ip:
                            completed.add(ip)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("进度文件损坏，将从空进度开始: %s", e)

        self._cache[phase] = completed
        self._pending[phase] = set()
        return completed

    def record(self, ip: str, phase: int):
        if phase not in self._cache:
            self.load_completed(phase)
        self._cache[phase].add(ip)
        self._pending.setdefault(phase, set()).add(ip)

    def flush(self):
        for phase, new_ips in self._pending.items():
            if not new_ips:
                continue
            progress_file = self._get_progress_file(phase)
            if not progress_file:
                continue
            try:
                with open(progress_file, 'a', encoding='utf-8') as f:
                    for ip in new_ips:
                        f.write(ip + '\n')
                self._pending[phase] = set()
            except IOError as e:
                logger.error("写入进度文件失败: %s", e)

    def is_phase_done(self, phase: int) -> bool:
        marker = self._get_marker_file(phase)
        return os.path.exists(marker) if marker else False

    def mark_phase_done(self, phase: int):
        marker = self._get_marker_file(phase)
        if marker:
            with open(marker, 'w', encoding='utf-8') as f:
                f.write(datetime.now().isoformat())

    def clear_from(self, phase: int):
        for p in range(phase, 8):
            marker = self._get_marker_file(p)
            if marker and os.path.exists(marker):
                os.remove(marker)
            progress_file = self._get_progress_file(p)
            if progress_file and os.path.exists(progress_file):
                os.remove(progress_file)
            self._cache.pop(p, None)
            self._pending.pop(p, None)

    def _get_progress_file(self, phase: int) -> str | None:
        suffix = self._PHASE_CONFIG.get(phase)
        if not suffix:
            return None
        return os.path.join(self._output_dir, f'{self._prefix}.{suffix}')

    def _get_marker_file(self, phase: int) -> str | None:
        suffix = self._PHASE_MARKERS.get(phase)
        if not suffix:
            return None
        return os.path.join(self._output_dir, f'{self._prefix}.{suffix}')


class BatchIPWriter:

    def __init__(self, writer: IPWriter):
        self._writer = writer
        self._batch: dict = {}

    def __enter__(self) -> 'BatchIPWriter':
        self._batch = {}
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._batch:
            self.flush_batch()
        return False

    def add(self, ip: str, channel: str, data: dict):
        if ip not in self._batch:
            self._batch[ip] = {}
        self._batch[ip][channel] = data

    def flush_batch(self):
        if not self._batch:
            return
        all_data = self._writer._load_data()
        for ip, channels in self._batch.items():
            if ip not in all_data:
                all_data[ip] = {"ip": ip}
            for channel, data in channels.items():
                all_data[ip][channel] = data
        self._writer._save_data(all_data)
        self._batch = {}
