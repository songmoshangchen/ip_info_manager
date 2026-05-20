import threading

import pytest

from ip_info.store.json_store import IPWriter


class TestIPWriterThreadSafe:

    def test_has_lock_attribute(self, tmp_path):
        writer = IPWriter(storage_file=str(tmp_path / "lock_test.json"))
        assert hasattr(writer, "_lock")
        assert isinstance(writer._lock, type(threading.Lock()))

    def test_concurrent_writes_no_data_loss(self, tmp_path):
        storage_file = str(tmp_path / "concurrent.json")
        writer = IPWriter(storage_file=storage_file)

        thread_count = 10
        ips_per_thread = 5
        errors = []

        def write_ips(thread_id):
            try:
                for i in range(ips_per_thread):
                    ip = f"{thread_id}.{i}.0.0"
                    writer.add_or_update_ip(ip, "ipinfo", {"thread": thread_id, "index": i})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_ips, args=(t,)) for t in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

        reader_ips = writer._load_data()
        expected_count = thread_count * ips_per_thread
        assert len(reader_ips) == expected_count, f"期望 {expected_count} 条记录，实际 {len(reader_ips)} 条"
