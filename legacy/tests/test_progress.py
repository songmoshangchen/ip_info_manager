import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scenarios.trace_ip.progress import ProgressManager


class TestChannelLevelProgress:

    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self._prefix = 'test_project'
        self._pm = ProgressManager(self._tmpdir, self._prefix)

    def _channel_progress_path(self, phase, channel):
        return os.path.join(
            self._tmpdir,
            f'{self._prefix}.trace_phase{phase}.{channel}.progress')

    def _phase_progress_path(self, phase):
        return os.path.join(
            self._tmpdir,
            f'{self._prefix}.trace_phase{phase}.progress')

    def _write_file(self, path, lines):
        with open(path, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line + '\n')

    # ── Cycle 1: record(ip, phase, channel) ──

    def test_record_with_channel_creates_channel_progress_file(self):
        self._pm.record('1.2.3.4', 1, 'ipinfo_api')
        self._pm.flush()

        path = self._channel_progress_path(1, 'ipinfo_api')
        assert os.path.exists(path)

        with open(path, 'r', encoding='utf-8') as f:
            ips = [line.strip() for line in f if line.strip()]
        assert ips == ['1.2.3.4']

    def test_record_with_channel_still_writes_phase_progress(self):
        self._pm.record('1.2.3.4', 1, 'ipinfo_api')
        self._pm.flush()

        phase_path = self._phase_progress_path(1)
        assert os.path.exists(phase_path)

        with open(phase_path, 'r', encoding='utf-8') as f:
            ips = [line.strip() for line in f if line.strip()]
        assert '1.2.3.4' in ips

    def test_record_without_channel_uses_phase_progress_only(self):
        self._pm.record('1.2.3.4', 1)
        self._pm.flush()

        assert os.path.exists(self._phase_progress_path(1))
        assert not os.path.exists(self._channel_progress_path(1, 'ipinfo_api'))

    # ── Cycle 2: load_completed(phase, channels) ──

    def test_load_completed_with_channels_returns_intersection(self):
        self._write_file(self._channel_progress_path(1, 'ipinfo_api'),
                         ['1.2.3.4', '5.6.7.8'])
        self._write_file(self._channel_progress_path(1, 'rdns_ptr'),
                         ['1.2.3.4', '5.6.7.8', '9.10.11.12'])

        pm = ProgressManager(self._tmpdir, self._prefix)
        completed = pm.load_completed(1, channels=['ipinfo_api', 'rdns_ptr'])

        assert completed == {'1.2.3.4', '5.6.7.8'}

    def test_load_completed_partial_channel_missing_ip(self):
        self._write_file(self._channel_progress_path(1, 'ipinfo_api'),
                         ['1.2.3.4', '5.6.7.8'])
        self._write_file(self._channel_progress_path(1, 'rdns_ptr'),
                         ['1.2.3.4'])

        pm = ProgressManager(self._tmpdir, self._prefix)
        completed = pm.load_completed(1, channels=['ipinfo_api', 'rdns_ptr'])

        assert '1.2.3.4' in completed
        assert '5.6.7.8' not in completed

    # ── Cycle 3: 向后兼容——无渠道级文件时退化为阶段级 ──

    def test_load_completed_fallback_to_phase_when_no_channel_files(self):
        self._write_file(self._phase_progress_path(1),
                         ['1.2.3.4', '5.6.7.8'])

        pm = ProgressManager(self._tmpdir, self._prefix)
        completed = pm.load_completed(1, channels=['ipinfo_api', 'rdns_ptr'])

        assert completed == {'1.2.3.4', '5.6.7.8'}

    def test_load_completed_without_channels_uses_phase_progress(self):
        self._write_file(self._phase_progress_path(1),
                         ['1.2.3.4', '5.6.7.8'])

        pm = ProgressManager(self._tmpdir, self._prefix)
        completed = pm.load_completed(1)

        assert completed == {'1.2.3.4', '5.6.7.8'}

    # ── Cycle 4: clear_from 同时清理渠道级文件 ──

    def test_clear_from_removes_channel_progress_files(self):
        self._write_file(self._phase_progress_path(1), ['1.2.3.4'])
        self._write_file(self._channel_progress_path(1, 'ipinfo_api'), ['1.2.3.4'])
        self._write_file(self._channel_progress_path(1, 'rdns_ptr'), ['1.2.3.4'])
        self._write_file(self._phase_progress_path(3), ['1.2.3.4'])
        self._write_file(self._channel_progress_path(3, 'aizhan'), ['1.2.3.4'])

        pm = ProgressManager(self._tmpdir, self._prefix)
        pm.clear_from(1)

        assert not os.path.exists(self._phase_progress_path(1))
        assert not os.path.exists(self._channel_progress_path(1, 'ipinfo_api'))
        assert not os.path.exists(self._channel_progress_path(1, 'rdns_ptr'))
        assert not os.path.exists(self._phase_progress_path(3))
        assert not os.path.exists(self._channel_progress_path(3, 'aizhan'))

    def test_clear_from_preserves_phases_before(self):
        self._write_file(self._phase_progress_path(1), ['1.2.3.4'])
        self._write_file(self._channel_progress_path(1, 'ipinfo_api'), ['1.2.3.4'])
        self._write_file(self._phase_progress_path(3), ['5.6.7.8'])
        self._write_file(self._channel_progress_path(3, 'aizhan'), ['5.6.7.8'])

        pm = ProgressManager(self._tmpdir, self._prefix)
        pm.clear_from(3)

        assert os.path.exists(self._phase_progress_path(1))
        assert os.path.exists(self._channel_progress_path(1, 'ipinfo_api'))
        assert not os.path.exists(self._phase_progress_path(3))
        assert not os.path.exists(self._channel_progress_path(3, 'aizhan'))

    # ── 多 IP 多渠道场景 ──

    def test_multiple_ips_multiple_channels(self):
        self._pm.record('1.1.1.1', 1, 'ipinfo_api')
        self._pm.record('1.1.1.1', 1, 'rdns_ptr')
        self._pm.record('2.2.2.2', 1, 'ipinfo_api')
        self._pm.flush()

        pm = ProgressManager(self._tmpdir, self._prefix)
        completed = pm.load_completed(1, channels=['ipinfo_api', 'rdns_ptr'])

        assert '1.1.1.1' in completed
        assert '2.2.2.2' not in completed

    def test_phase3_three_channels_intersection(self):
        self._write_file(self._channel_progress_path(3, 'aizhan'),
                         ['1.1.1.1', '2.2.2.2'])
        self._write_file(self._channel_progress_path(3, 'chinaz'),
                         ['1.1.1.1', '2.2.2.2', '3.3.3.3'])
        self._write_file(self._channel_progress_path(3, 'fofa_host'),
                         ['1.1.1.1'])

        pm = ProgressManager(self._tmpdir, self._prefix)
        completed = pm.load_completed(3, channels=['aizhan', 'chinaz', 'fofa_host'])

        assert completed == {'1.1.1.1'}
