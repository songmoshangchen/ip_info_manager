import pathlib

from ip_info.batch.progress import FileProgressTracker, InMemoryProgressTracker
from ip_info.batch.protocols import ProgressTracker


class TestInMemoryProgressTracker:
    def test_satisfies_protocol(self):
        assert isinstance(InMemoryProgressTracker(), ProgressTracker)

    def test_mark_processed_and_is_processed(self):
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("1.1.1.1")
        assert tracker.is_processed("1.1.1.1") is True

    def test_unmarked_returns_false(self):
        tracker = InMemoryProgressTracker()
        assert tracker.is_processed("2.2.2.2") is False

    def test_mark_multiple_ips(self):
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("1.1.1.1")
        tracker.mark_processed("2.2.2.2")
        tracker.mark_processed("3.3.3.3")
        assert tracker.is_processed("1.1.1.1") is True
        assert tracker.is_processed("2.2.2.2") is True
        assert tracker.is_processed("3.3.3.3") is True
        assert tracker.is_processed("4.4.4.4") is False


class TestFileProgressTracker:
    def test_satisfies_protocol(self):
        assert isinstance(FileProgressTracker("dummy.txt"), ProgressTracker)

    def test_file_not_exists_returns_false(self, tmp_path: pathlib.Path):
        tracker = FileProgressTracker(str(tmp_path / "nonexistent.txt"))
        assert tracker.is_processed("1.1.1.1") is False

    def test_persistence_across_instances(self, tmp_path: pathlib.Path):
        file_path = str(tmp_path / "progress.txt")
        tracker_a = FileProgressTracker(file_path)
        tracker_a.mark_processed("1.1.1.1")
        tracker_b = FileProgressTracker(file_path)
        assert tracker_b.is_processed("1.1.1.1") is True

    def test_mark_multiple_ips_persists(self, tmp_path: pathlib.Path):
        file_path = str(tmp_path / "progress.txt")
        tracker = FileProgressTracker(file_path)
        tracker.mark_processed("1.1.1.1")
        tracker.mark_processed("2.2.2.2")
        tracker.mark_processed("3.3.3.3")
        tracker2 = FileProgressTracker(file_path)
        assert tracker2.is_processed("1.1.1.1") is True
        assert tracker2.is_processed("2.2.2.2") is True
        assert tracker2.is_processed("3.3.3.3") is True
        assert tracker2.is_processed("4.4.4.4") is False
