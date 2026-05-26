import threading

from ip_info.store.json_store import IPReader, IPWriter


class TestIPWriterThreadSafe:
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

        reader = IPReader(storage_file)
        expected_count = thread_count * ips_per_thread
        all_ips = reader.list_all_ips()
        assert len(all_ips) == expected_count, f"期望 {expected_count} 条记录，实际 {len(all_ips)} 条"
