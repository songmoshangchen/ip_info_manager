import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestBaseBatchQueryLoadIPFile:

    def test_load_ip_file_deduplicates(self, tmp_path):
        from scripts.base_batch import BaseBatchQuery

        ip_file = tmp_path / "ips.txt"
        ip_file.write_text("1.1.1.1\n2.2.2.2\n1.1.1.1\n3.3.3.3\n")

        class DummyBatch(BaseBatchQuery):
            channel_name = 'test'
            def _query_ip(self, ip): return {}
            def _print_result(self, ip, data): pass

        batch = DummyBatch.__new__(DummyBatch)
        batch.ip_file = str(ip_file)
        batch.load_stats = {}
        ips = batch._load_ip_file()
        assert ips == ['1.1.1.1', '2.2.2.2', '3.3.3.3']
        assert batch.load_stats['raw_count'] == 4
        assert batch.load_stats['unique_count'] == 3
        assert batch.load_stats['duplicate_count'] == 1

    def test_load_ip_file_skips_empty_lines(self, tmp_path):
        from scripts.base_batch import BaseBatchQuery

        ip_file = tmp_path / "ips.txt"
        ip_file.write_text("1.1.1.1\n\n  \n2.2.2.2\n")

        class DummyBatch(BaseBatchQuery):
            channel_name = 'test'
            def _query_ip(self, ip): return {}
            def _print_result(self, ip, data): pass

        batch = DummyBatch.__new__(DummyBatch)
        batch.ip_file = str(ip_file)
        batch.load_stats = {}
        ips = batch._load_ip_file()
        assert ips == ['1.1.1.1', '2.2.2.2']


class TestBaseBatchQueryProgress:

    def test_load_progress_returns_empty_for_nonexistent(self, tmp_path):
        from scripts.base_batch import BaseBatchQuery

        class DummyBatch(BaseBatchQuery):
            channel_name = 'test'
            def _query_ip(self, ip): return {}
            def _print_result(self, ip, data): pass

        batch = DummyBatch.__new__(DummyBatch)
        batch.channel_name = 'test'
        batch.ip_writer = type('W', (), {'storage_file': str(tmp_path / "data")})()
        assert batch._load_progress() == set()

    def test_save_and_load_progress(self, tmp_path):
        from scripts.base_batch import BaseBatchQuery

        class DummyBatch(BaseBatchQuery):
            channel_name = 'test'
            def _query_ip(self, ip): return {}
            def _print_result(self, ip, data): pass

        batch = DummyBatch.__new__(DummyBatch)
        batch.channel_name = 'test'
        batch.ip_writer = type('W', (), {'storage_file': str(tmp_path / "data")})()
        batch._save_progress('1.1.1.1')
        batch._save_progress('2.2.2.2')
        loaded = batch._load_progress()
        assert loaded == {'1.1.1.1', '2.2.2.2'}

    def test_load_pending_ips_excludes_processed(self, tmp_path):
        from scripts.base_batch import BaseBatchQuery

        ip_file = tmp_path / "ips.txt"
        ip_file.write_text("1.1.1.1\n2.2.2.2\n3.3.3.3\n")

        class DummyBatch(BaseBatchQuery):
            channel_name = 'test'
            def _query_ip(self, ip): return {}
            def _print_result(self, ip, data): pass

        batch = DummyBatch.__new__(DummyBatch)
        batch.ip_file = str(ip_file)
        batch.channel_name = 'test'
        batch.ip_writer = type('W', (), {'storage_file': str(tmp_path / "data")})()
        batch.load_stats = {}
        batch._save_progress('1.1.1.1')
        pending = batch._load_pending_ips()
        assert pending == ['2.2.2.2', '3.3.3.3']
        assert batch.load_stats['already_processed'] == 1
        assert batch.load_stats['pending_count'] == 2


class TestBaseBatchQueryIsError:

    def test_is_error_detects_raw_error(self):
        from scripts.base_batch import BaseBatchQuery

        class DummyBatch(BaseBatchQuery):
            channel_name = 'test'
            def _query_ip(self, ip): return {}
            def _print_result(self, ip, data): pass

        batch = DummyBatch.__new__(DummyBatch)
        assert batch._is_error({'raw_error': True}) is True

    def test_is_error_detects_error(self):
        from scripts.base_batch import BaseBatchQuery

        class DummyBatch(BaseBatchQuery):
            channel_name = 'test'
            def _query_ip(self, ip): return {}
            def _print_result(self, ip, data): pass

        batch = DummyBatch.__new__(DummyBatch)
        assert batch._is_error({'error': True}) is True

    def test_is_error_returns_false_for_success(self):
        from scripts.base_batch import BaseBatchQuery

        class DummyBatch(BaseBatchQuery):
            channel_name = 'test'
            def _query_ip(self, ip): return {}
            def _print_result(self, ip, data): pass

        batch = DummyBatch.__new__(DummyBatch)
        assert batch._is_error({'country': 'CN'}) is False

    def test_is_error_returns_false_for_non_dict(self):
        from scripts.base_batch import BaseBatchQuery

        class DummyBatch(BaseBatchQuery):
            channel_name = 'test'
            def _query_ip(self, ip): return {}
            def _print_result(self, ip, data): pass

        batch = DummyBatch.__new__(DummyBatch)
        assert batch._is_error(None) is False


class TestBaseBatchQueryGetDelay:

    def test_get_delay_from_settings(self):
        from scripts.base_batch import BaseBatchQuery

        class DummyBatch(BaseBatchQuery):
            channel_name = 'rdns_ptr'
            def _query_ip(self, ip): return {}
            def _print_result(self, ip, data): pass

        batch = DummyBatch.__new__(DummyBatch)

        class FakeSettings:
            rdns_ptr_query_delay = 0.5

        batch.settings = FakeSettings()
        assert batch._get_delay() == 0.5

    def test_get_delay_default_when_missing(self):
        from scripts.base_batch import BaseBatchQuery

        class DummyBatch(BaseBatchQuery):
            channel_name = 'unknown_channel'
            def _query_ip(self, ip): return {}
            def _print_result(self, ip, data): pass

        batch = DummyBatch.__new__(DummyBatch)

        class FakeSettings:
            pass

        batch.settings = FakeSettings()
        assert batch._get_delay() == 1.0


class TestBaseBatchQueryAbstractMethods:

    def test_cannot_instantiate_directly(self):
        from scripts.base_batch import BaseBatchQuery

        with pytest.raises(TypeError):
            BaseBatchQuery(ip_file="test.txt")

    def test_subclass_must_implement_query_ip(self):
        from scripts.base_batch import BaseBatchQuery

        class IncompleteBatch(BaseBatchQuery):
            channel_name = 'test'
            def _print_result(self, ip, data): pass

        with pytest.raises(TypeError):
            IncompleteBatch(ip_file="test.txt")

    def test_subclass_must_implement_print_result(self):
        from scripts.base_batch import BaseBatchQuery

        class IncompleteBatch(BaseBatchQuery):
            channel_name = 'test'
            def _query_ip(self, ip): return {}

        with pytest.raises(TypeError):
            IncompleteBatch(ip_file="test.txt")
