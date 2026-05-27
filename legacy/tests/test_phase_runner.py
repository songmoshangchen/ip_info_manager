import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from protocols import InMemoryIPWriter, InMemoryIPReader
from scenarios.trace_ip.phase_runner import PhaseRunner


@pytest.fixture
def store():
    writer = InMemoryIPWriter()
    writer.add_or_update_ip('1.1.1.1', 'ipinfo_api', {'country': 'CN'})
    writer.add_or_update_ip('2.2.2.2', 'ipinfo_api', {'country': 'US'})
    writer.add_or_update_ip('3.3.3.3', 'ipinfo_api', {'country': 'JP'})
    return writer


class TestPhaseRunnerInit:

    def test_init_stores_config(self, store):
        runner = PhaseRunner(
            ips=['1.1.1.1', '2.2.2.2'],
            phase_num=1,
            channels=['ipinfo_api', 'rdns_ptr'],
            data_store=store,
        )
        assert runner.phase_num == 1
        assert runner.channels == ['ipinfo_api', 'rdns_ptr']


class TestPhaseRunnerProcessedFromStore:

    def test_detects_already_processed_ips(self, store):
        store.add_or_update_ip('1.1.1.1', 'rdns_ptr', {'has_ptr': True})
        store.add_or_update_ip('2.2.2.2', 'rdns_ptr', {'has_ptr': False})

        runner = PhaseRunner(
            ips=['1.1.1.1', '2.2.2.2', '3.3.3.3'],
            phase_num=1,
            channels=['rdns_ptr'],
            data_store=store,
        )
        processed = runner.compute_processed_from_store()
        assert '1.1.1.1' in processed
        assert '2.2.2.2' in processed
        assert '3.3.3.3' not in processed

    def test_requires_all_channels_for_processed(self, store):
        store.add_or_update_ip('1.1.1.1', 'ipinfo_api', {'country': 'CN'})

        runner = PhaseRunner(
            ips=['1.1.1.1'],
            phase_num=1,
            channels=['ipinfo_api', 'rdns_ptr'],
            data_store=store,
        )
        processed = runner.compute_processed_from_store()
        assert '1.1.1.1' not in processed

    def test_empty_store_returns_no_processed(self):
        store = InMemoryIPWriter()
        runner = PhaseRunner(
            ips=['1.1.1.1'],
            phase_num=1,
            channels=['rdns_ptr'],
            data_store=store,
        )
        assert runner.compute_processed_from_store() == set()


class TestPhaseRunnerPendingIPs:

    def test_excludes_processed_ips(self, store):
        store.add_or_update_ip('1.1.1.1', 'rdns_ptr', {'has_ptr': True})
        store.add_or_update_ip('2.2.2.2', 'rdns_ptr', {'has_ptr': False})

        runner = PhaseRunner(
            ips=['1.1.1.1', '2.2.2.2', '3.3.3.3'],
            phase_num=1,
            channels=['rdns_ptr'],
            data_store=store,
        )
        pending = runner.get_pending_ips()
        assert pending == ['3.3.3.3']

    def test_all_processed_returns_empty(self, store):
        store.add_or_update_ip('1.1.1.1', 'rdns_ptr', {'has_ptr': True})
        store.add_or_update_ip('2.2.2.2', 'rdns_ptr', {'has_ptr': False})
        store.add_or_update_ip('3.3.3.3', 'rdns_ptr', {'has_ptr': False})

        runner = PhaseRunner(
            ips=['1.1.1.1', '2.2.2.2', '3.3.3.3'],
            phase_num=1,
            channels=['rdns_ptr'],
            data_store=store,
        )
        assert runner.get_pending_ips() == []

    def test_with_progress_file_ips(self, store):
        store.add_or_update_ip('1.1.1.1', 'rdns_ptr', {'has_ptr': True})

        runner = PhaseRunner(
            ips=['1.1.1.1', '2.2.2.2', '3.3.3.3'],
            phase_num=1,
            channels=['rdns_ptr'],
            data_store=store,
            progress_ips={'2.2.2.2'},
        )
        pending = runner.get_pending_ips()
        assert pending == ['3.3.3.3']


class TestPhaseRunnerRun:

    def test_run_calls_query_fn_for_each_pending_ip(self, store):
        queried_ips = []

        def query_fn(ip, channel_specs):
            queried_ips.append(ip)
            return {'rdns_ptr': {'has_ptr': True}}

        runner = PhaseRunner(
            ips=['1.1.1.1', '2.2.2.2'],
            phase_num=1,
            channels=['rdns_ptr'],
            data_store=store,
        )
        runner.run(query_fn=query_fn)
        assert sorted(queried_ips) == ['1.1.1.1', '2.2.2.2']

    def test_run_skips_already_processed(self, store):
        store.add_or_update_ip('1.1.1.1', 'rdns_ptr', {'has_ptr': True})
        queried_ips = []

        def query_fn(ip, channel_specs):
            queried_ips.append(ip)
            return {'rdns_ptr': {'has_ptr': True}}

        runner = PhaseRunner(
            ips=['1.1.1.1', '2.2.2.2'],
            phase_num=1,
            channels=['rdns_ptr'],
            data_store=store,
        )
        runner.run(query_fn=query_fn)
        assert queried_ips == ['2.2.2.2']

    def test_run_writes_results_to_store(self, store):
        def query_fn(ip, channel_specs):
            return {'rdns_ptr': {'has_ptr': True, 'hostname': f'host-{ip}'}}

        runner = PhaseRunner(
            ips=['1.1.1.1'],
            phase_num=1,
            channels=['rdns_ptr'],
            data_store=store,
        )
        runner.run(query_fn=query_fn)

        assert store.get_channel_data('1.1.1.1', 'rdns_ptr')['hostname'] == 'host-1.1.1.1'

    def test_run_handles_query_fn_returning_none(self, store):
        queried_ips = []

        def query_fn(ip, channel_specs):
            queried_ips.append(ip)
            return None

        runner = PhaseRunner(
            ips=['1.1.1.1'],
            phase_num=1,
            channels=['rdns_ptr'],
            data_store=store,
        )
        runner.run(query_fn=query_fn)
        assert queried_ips == ['1.1.1.1']
        assert store.get_channel_data('1.1.1.1', 'rdns_ptr') is None

    def test_run_handles_query_fn_returning_empty_dict(self, store):
        def query_fn(ip, channel_specs):
            return {}

        runner = PhaseRunner(
            ips=['1.1.1.1'],
            phase_num=1,
            channels=['rdns_ptr'],
            data_store=store,
        )
        runner.run(query_fn=query_fn)
        assert store.get_channel_data('1.1.1.1', 'rdns_ptr') is None
