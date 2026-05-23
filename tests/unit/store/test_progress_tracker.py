"""测试 IPWriter.progress_tracker() 方法"""

from ip_info.store.in_memory import InMemoryIPWriter
from ip_info.store.json_store import IPWriter
from ip_info.utils.progress import FileProgressTracker, InMemoryProgressTracker


class TestIPWriterProgressTracker:
    def test_returns_file_progress_tracker(self, tmp_path):
        storage_file = str(tmp_path / "ip_data.json")
        writer = IPWriter(storage_file)
        tracker = writer.progress_tracker("fofa_host")
        assert isinstance(tracker, FileProgressTracker)

    def test_progress_file_path_with_json_extension(self, tmp_path):
        storage_file = str(tmp_path / "ip_data.json")
        writer = IPWriter(storage_file)
        tracker = writer.progress_tracker("fofa_host")
        assert tracker._file_path == str(tmp_path / "ip_data.fofa_host.progress")

    def test_progress_file_path_without_json_extension(self, tmp_path):
        storage_file = str(tmp_path / "ip_data")
        writer = IPWriter(storage_file)
        tracker = writer.progress_tracker("rdns_ptr")
        assert tracker._file_path == str(tmp_path / "ip_data.rdns_ptr.progress")

    def test_different_channels_return_different_trackers(self, tmp_path):
        storage_file = str(tmp_path / "ip_data.json")
        writer = IPWriter(storage_file)
        tracker1 = writer.progress_tracker("fofa_host")
        tracker2 = writer.progress_tracker("rdns_ptr")
        assert tracker1._file_path != tracker2._file_path

    def test_tracker_functional_write_and_check(self, tmp_path):
        storage_file = str(tmp_path / "ip_data.json")
        writer = IPWriter(storage_file)
        tracker = writer.progress_tracker("test_ch")
        tracker.mark_processed("1.1.1.1")
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
