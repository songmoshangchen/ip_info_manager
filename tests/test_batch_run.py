import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.base_batch import BaseBatchQuery


class _DummyWriter:
    def __init__(self, storage_file):
        self.storage_file = storage_file
        self.writes = []

    def add_or_update_ip(self, ip, channel, data):
        self.writes.append((ip, channel, data))
        return True


class _DummyPid:
    def __init__(self):
        self.pid_written = False
        self.heartbeats = 0
        self.removed = False

    def write_pid(self, *a, **kw):
        self.pid_written = True

    def update_heartbeat(self, **kw):
        self.heartbeats += 1

    def remove_pid(self):
        self.removed = True


class _DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg, *a):
        self.messages.append(('info', msg))

    def warning(self, msg, *a):
        self.messages.append(('warning', msg))

    def debug(self, msg, *a):
        self.messages.append(('debug', msg))

    def error(self, msg, *a):
        self.messages.append(('error', msg))


class _ConcreteBatch(BaseBatchQuery):
    channel_name = 'test'

    def _query_ip(self, ip):
        return self._results.get(ip, {})

    def _print_result(self, ip, data):
        self._printed.append((ip, data))

    def _get_delay(self):
        return getattr(self, '_test_delay', 0)


def _build_batch(tmp_path, ips_text, results=None, pending_ips=None, load_stats=None, channel_name='test'):
    ip_file = tmp_path / "ips.txt"
    ip_file.write_text(ips_text)

    batch = _ConcreteBatch.__new__(_ConcreteBatch)
    batch.ip_file = str(ip_file)
    batch.channel_name = channel_name
    batch.no_validate = True
    batch._results = results or {}
    batch._printed = []
    batch.load_stats = load_stats or {
        'raw_count': len(ips_text.strip().split('\n')) if ips_text.strip() else 0,
        'unique_count': len(ips_text.strip().split('\n')) if ips_text.strip() else 0,
        'duplicate_count': 0,
        'already_processed': 0,
        'pending_count': len(pending_ips) if pending_ips else 0,
    }
    batch.pending_ips = pending_ips if pending_ips is not None else []

    writer = _DummyWriter(str(tmp_path / "data.json"))
    batch.ip_writer = writer
    batch._writer = writer
    batch._pid_mgr = _DummyPid()
    logger = _DummyLogger()
    batch.logger = logger
    batch._test_logger = logger
    batch._test_delay = 0
    return batch


class TestBaseBatchRunBasic:

    def test_run_queries_all_pending_ips(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n2.2.2.2\n",
                             pending_ips=['1.1.1.1', '2.2.2.2'],
                             results={'1.1.1.1': {'country': 'CN'}, '2.2.2.2': {'country': 'US'}})
        batch.run()
        assert len(batch._writer.writes) == 2

    def test_run_writes_correct_channel_name(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n",
                             pending_ips=['1.1.1.1'],
                             results={'1.1.1.1': {'country': 'CN'}},
                             channel_name='fofa_host')
        batch.run()
        assert batch._writer.writes[0][1] == 'fofa_host'

    def test_run_writes_data_for_each_ip(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n",
                             pending_ips=['1.1.1.1'],
                             results={'1.1.1.1': {'country': 'CN'}})
        batch.run()
        assert batch._writer.writes[0][2] == {'country': 'CN'}

    def test_run_saves_progress_for_each_ip(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n2.2.2.2\n",
                             pending_ips=['1.1.1.1', '2.2.2.2'])
        batch.run()
        progress = batch._load_progress()
        assert progress == {'1.1.1.1', '2.2.2.2'}

    def test_run_handles_error_response(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n",
                             pending_ips=['1.1.1.1'],
                             results={'1.1.1.1': {'raw_error': True, 'error_message': 'timeout'}})
        batch.run()
        assert len(batch._writer.writes) == 1
        assert batch._writer.writes[0][2]['raw_error'] is True

    def test_run_prints_result_on_success(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n",
                             pending_ips=['1.1.1.1'],
                             results={'1.1.1.1': {'country': 'CN'}})
        batch.run()
        assert len(batch._printed) == 1
        assert batch._printed[0] == ('1.1.1.1', {'country': 'CN'})

    def test_run_prints_result_on_error(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n",
                             pending_ips=['1.1.1.1'],
                             results={'1.1.1.1': {'raw_error': True, 'error_message': 'fail'}})
        batch.run()
        assert len(batch._printed) == 1
        assert batch._printed[0][1]['raw_error'] is True

    def test_run_empty_pending_does_nothing(self, tmp_path):
        batch = _build_batch(tmp_path, "", pending_ips=[],
                             load_stats={'raw_count': 0, 'unique_count': 0, 'duplicate_count': 0,
                                         'already_processed': 0, 'pending_count': 0})
        batch.run()
        assert len(batch._writer.writes) == 0


class TestBaseBatchRunPid:

    def test_run_writes_pid_on_start(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n", pending_ips=['1.1.1.1'])
        batch.run()
        assert batch._pid_mgr.pid_written is True

    def test_run_updates_heartbeat_per_ip(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n2.2.2.2\n",
                             pending_ips=['1.1.1.1', '2.2.2.2'])
        batch.run()
        assert batch._pid_mgr.heartbeats == 2

    def test_run_removes_pid_on_completion(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n", pending_ips=['1.1.1.1'])
        batch.run()
        assert batch._pid_mgr.removed is True

    def test_run_removes_pid_on_keyboard_interrupt(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n", pending_ips=['1.1.1.1'])

        def query_with_interrupt(ip):
            raise KeyboardInterrupt()

        batch._query_ip = query_with_interrupt
        with pytest.raises(SystemExit):
            batch.run()
        assert batch._pid_mgr.removed is True


class TestBaseBatchRunDelay:

    def test_run_applies_delay_between_queries(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n2.2.2.2\n",
                             pending_ips=['1.1.1.1', '2.2.2.2'])
        batch._test_delay = 0.05

        start = time.monotonic()
        batch.run()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.08


class TestBaseBatchRunStats:

    def test_run_counts_success_and_failure(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n2.2.2.2\n3.3.3.3\n",
                             pending_ips=['1.1.1.1', '2.2.2.2', '3.3.3.3'],
                             results={'1.1.1.1': {'ok': True},
                                      '2.2.2.2': {'raw_error': True, 'error_message': 'fail'},
                                      '3.3.3.3': {'ok': True}})
        batch.run()
        assert batch.run_stats['success_count'] == 2
        assert batch.run_stats['fail_count'] == 1

    def test_run_stats_tracks_total_elapsed(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n", pending_ips=['1.1.1.1'])
        batch.run()
        assert 'total_elapsed' in batch.run_stats
        assert batch.run_stats['total_elapsed'] >= 0


class TestBaseBatchValidateHook:

    def test_run_calls_do_validate_when_not_skipped(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n", pending_ips=['1.1.1.1'])
        batch.no_validate = False
        batch._validate_called = False

        def mock_validate():
            batch._validate_called = True

        batch._do_validate = mock_validate
        batch.run()
        assert batch._validate_called is True

    def test_run_skips_validate_when_flag_set(self, tmp_path):
        batch = _build_batch(tmp_path, "1.1.1.1\n", pending_ips=['1.1.1.1'])
        batch.no_validate = True
        batch._validate_called = False

        def mock_validate():
            batch._validate_called = True

        batch._do_validate = mock_validate
        batch.run()
        assert batch._validate_called is False


class TestMigratedBatchFofaHost:

    def test_fofa_host_inherits_base_batch(self):
        from scripts.batch_fofa_host import BatchFofaHostQuery
        assert issubclass(BatchFofaHostQuery, BaseBatchQuery)

    def test_fofa_host_channel_name(self):
        from scripts.batch_fofa_host import BatchFofaHostQuery
        assert BatchFofaHostQuery.channel_name == 'fofa_host'

    def test_fofa_host_has_run_method(self):
        from scripts.batch_fofa_host import BatchFofaHostQuery
        assert hasattr(BatchFofaHostQuery, 'run')


class TestMigratedBatchRdnsPtr:

    def test_rdns_ptr_inherits_base_batch(self):
        from scripts.batch_rdns_ptr import BatchRDNSQuery
        assert issubclass(BatchRDNSQuery, BaseBatchQuery)

    def test_rdns_ptr_channel_name(self):
        from scripts.batch_rdns_ptr import BatchRDNSQuery
        assert BatchRDNSQuery.channel_name == 'rdns_ptr'


class TestMigratedBatchAizhan:

    def test_inherits_base_batch(self):
        from scripts.batch_aizhan import BatchAizhanQuery
        assert issubclass(BatchAizhanQuery, BaseBatchQuery)

    def test_channel_name(self):
        from scripts.batch_aizhan import BatchAizhanQuery
        assert BatchAizhanQuery.channel_name == 'aizhan'


class TestMigratedBatchChinaz:

    def test_inherits_base_batch(self):
        from scripts.batch_chinaz import BatchChinazQuery
        assert issubclass(BatchChinazQuery, BaseBatchQuery)

    def test_channel_name(self):
        from scripts.batch_chinaz import BatchChinazQuery
        assert BatchChinazQuery.channel_name == 'chinaz'


class TestMigratedBatchFofaSearch:

    def test_inherits_base_batch(self):
        from scripts.batch_fofa_search import BatchFofaSearchQuery
        assert issubclass(BatchFofaSearchQuery, BaseBatchQuery)

    def test_channel_name(self):
        from scripts.batch_fofa_search import BatchFofaSearchQuery
        assert BatchFofaSearchQuery.channel_name == 'fofa_search'


class TestMigratedBatchIpinfoApi:

    def test_inherits_base_batch(self):
        from scripts.batch_ipinfo_api import BatchIPInfoQuery
        assert issubclass(BatchIPInfoQuery, BaseBatchQuery)

    def test_channel_name(self):
        from scripts.batch_ipinfo_api import BatchIPInfoQuery
        assert BatchIPInfoQuery.channel_name == 'ipinfo_api'


class TestMigratedBatchSslCert:

    def test_inherits_base_batch(self):
        from scripts.batch_ssl_cert import BatchSslCertQuery
        assert issubclass(BatchSslCertQuery, BaseBatchQuery)

    def test_channel_name(self):
        from scripts.batch_ssl_cert import BatchSslCertQuery
        assert BatchSslCertQuery.channel_name == 'ssl_cert'


class TestMigratedBatchWhois:

    def test_inherits_base_batch(self):
        from scripts.batch_whois import BatchWhoisQuery
        assert issubclass(BatchWhoisQuery, BaseBatchQuery)

    def test_channel_name(self):
        from scripts.batch_whois import BatchWhoisQuery
        assert BatchWhoisQuery.channel_name == 'whois'


class TestMigratedBatchZoomeye:

    def test_inherits_base_batch(self):
        from scripts.batch_zoomeye import BatchZoomeyeQuery
        assert issubclass(BatchZoomeyeQuery, BaseBatchQuery)

    def test_channel_name(self):
        from scripts.batch_zoomeye import BatchZoomeyeQuery
        assert BatchZoomeyeQuery.channel_name == 'zoomeye'
