from ip_info.store.in_memory import InMemoryIPWriter
from ip_info.store.json_store import IPWriter
from ip_info.utils.progress import InMemoryProgressTracker, SqliteProgressTracker


class TestIPWriterProgressTracker:
    def test_returns_sqlite_progress_tracker(self, tmp_path):
        storage_file = str(tmp_path / "ip_data.json")
        writer = IPWriter(storage_file)
        tracker = writer.progress_tracker("fofa_host")
        assert isinstance(tracker, SqliteProgressTracker)

    def test_tracker_persists_across_instances(self, tmp_path):
        storage_file = str(tmp_path / "ip_data.json")
        writer = IPWriter(storage_file)
        tracker = writer.progress_tracker("test_ch")
        tracker.mark_processed("1.1.1.1")
        tracker.flush()

        writer2 = IPWriter(storage_file)
        tracker2 = writer2.progress_tracker("test_ch")
        assert tracker2.is_processed("1.1.1.1") is True

    def test_different_channels_share_same_persistence(self, tmp_path):
        storage_file = str(tmp_path / "ip_data.json")
        writer = IPWriter(storage_file)
        tracker1 = writer.progress_tracker("fofa_host")
        tracker2 = writer.progress_tracker("rdns_ptr")
        tracker1.mark_processed("1.1.1.1", "fofa_host")
        tracker1.flush()

        assert tracker2.is_processed("1.1.1.1", "fofa_host") is True
        assert tracker2.is_processed("1.1.1.1", "rdns_ptr") is False

    def test_tracker_functional_write_and_check(self, tmp_path):
        storage_file = str(tmp_path / "ip_data.json")
        writer = IPWriter(storage_file)
        tracker = writer.progress_tracker("test_ch")
        tracker.mark_processed("1.1.1.1")
        tracker.flush()
        assert tracker.is_processed("1.1.1.1") is True
        assert tracker.is_processed("2.2.2.2") is False


class TestInMemoryIPWriterProgressTracker:
    def test_returns_in_memory_progress_tracker(self):
        writer = InMemoryIPWriter()
        tracker = writer.progress_tracker("fofa_host")
        assert isinstance(tracker, InMemoryProgressTracker)

    def test_tracker_functional_write_and_check(self):
        writer = InMemoryIPWriter()
        tracker = writer.progress_tracker("test_ch")
        tracker.mark_processed("1.1.1.1")
        assert tracker.is_processed("1.1.1.1") is True
        assert tracker.is_processed("2.2.2.2") is False

    def test_different_channels_return_different_trackers(self):
        writer = InMemoryIPWriter()
        tracker1 = writer.progress_tracker("fofa_host")
        tracker2 = writer.progress_tracker("rdns_ptr")
        tracker1.mark_processed("1.1.1.1")
        assert tracker1.is_processed("1.1.1.1") is True
        assert tracker2.is_processed("1.1.1.1") is False
