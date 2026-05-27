import os
import sys
import json
import threading
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestIPWriterThreadSafety:

    def test_concurrent_writes_no_data_loss(self, tmp_path):
        from writer import IPWriter
        storage = tmp_path / "data"
        storage.mkdir()

        mock_settings = MagicMock()
        mock_settings.storage_dir = ''
        mock_settings.storage_name = 'test_ips'
        mock_settings.ipinfo_query_delay = 0

        with patch('writer.Settings', return_value=mock_settings):
            w = IPWriter(storage_dir=str(storage))

        num_threads = 10
        num_ips_per_thread = 5
        barrier = threading.Barrier(num_threads)

        def write_ips(thread_id):
            barrier.wait()
            for i in range(num_ips_per_thread):
                ip = f"1.1.{thread_id}.{i}"
                w.add_or_update_ip(ip, 'test_channel', {'thread': thread_id, 'idx': i})

        threads = [threading.Thread(target=write_ips, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with open(w.storage_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        expected_count = num_threads * num_ips_per_thread
        actual_ips = [k for k in data.keys() if k != 'ip']
        assert len(actual_ips) == expected_count, f"Expected {expected_count} IPs, got {len(actual_ips)}"

    def test_has_lock_attribute(self, tmp_path):
        from writer import IPWriter
        mock_settings = MagicMock()
        mock_settings.storage_dir = ''
        mock_settings.storage_name = 'test_ips'

        with patch('writer.Settings', return_value=mock_settings):
            w = IPWriter(storage_dir=str(tmp_path))

        assert hasattr(w, '_lock')
        assert isinstance(w._lock, type(threading.Lock()))
