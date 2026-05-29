import os
import tempfile

from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter
from ip_info.store.json_store import IPReader, IPWriter


class TestIPWriterAddOrUpdateIpBatch:
    def test_writes_multiple_ips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            writer = IPWriter(path)

            updates = [
                ("1.2.3.4", "rdns", {"ptr": "test.example.com"}),
                ("5.6.7.8", "rdns", {"ptr": "other.example.com"}),
                ("9.10.11.12", "rdns", {"ptr": "third.example.com"}),
            ]
            count = writer.add_or_update_ip_batch(updates)
            assert count == 3

            reader = IPReader(path)
            assert reader.get_channel_data("1.2.3.4", "rdns")["ptr"] == "test.example.com"
            assert reader.get_channel_data("5.6.7.8", "rdns")["ptr"] == "other.example.com"
            assert reader.get_channel_data("9.10.11.12", "rdns")["ptr"] == "third.example.com"

    def test_empty_list_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            writer = IPWriter(path)
            count = writer.add_or_update_ip_batch([])
            assert count == 0

    def test_single_io_for_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            writer = IPWriter(path)

            load_count = [0]
            save_count = [0]

            original_load = writer._load_data
            original_save = writer._save_data

            def counting_load():
                load_count[0] += 1
                return original_load()

            def counting_save(data):
                save_count[0] += 1
                return original_save(data)

            writer._load_data = counting_load
            writer._save_data = counting_save

            updates = [
                ("1.2.3.4", "ch1", {"a": 1}),
                ("5.6.7.8", "ch2", {"b": 2}),
                ("9.10.11.12", "ch3", {"c": 3}),
            ]
            writer.add_or_update_ip_batch(updates)

            assert load_count[0] == 1
            assert save_count[0] == 1

    def test_overwrites_existing_channel_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            writer = IPWriter(path)
            writer.add_or_update_ip("1.2.3.4", "rdns", {"old": True})

            updates = [("1.2.3.4", "rdns", {"new": True})]
            count = writer.add_or_update_ip_batch(updates)
            assert count == 1

            reader = IPReader(path)
            data = reader.get_channel_data("1.2.3.4", "rdns")
            assert "new" in data
            assert "old" not in data


class TestInMemoryIPWriterAddOrUpdateIpBatch:
    def test_writes_multiple_ips(self):
        writer = InMemoryIPWriter()

        updates = [
            ("1.2.3.4", "ch_a", {"x": 1}),
            ("5.6.7.8", "ch_b", {"y": 2}),
        ]
        count = writer.add_or_update_ip_batch(updates)
        assert count == 2

        reader = InMemoryIPReader(data=writer._store)
        assert reader.get_channel_data("1.2.3.4", "ch_a") is not None
        assert reader.get_channel_data("5.6.7.8", "ch_b") is not None

    def test_empty_returns_zero(self):
        writer = InMemoryIPWriter()
        count = writer.add_or_update_ip_batch([])
        assert count == 0
