import pathlib

from ip_info.utils.progress import FileProgressTracker, InMemoryProgressTracker, ProgressTracker


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

    def test_channel_isolation(self):
        """不同渠道的进度互不影响"""
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("1.1.1.1", "ipinfo_api")
        assert tracker.is_processed("1.1.1.1", "ipinfo_api") is True
        assert tracker.is_processed("1.1.1.1", "rdns_ptr") is False
        assert tracker.is_processed("1.1.1.1") is False

    def test_same_ip_different_channels(self):
        """同一 IP 在不同渠道分别标记"""
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("1.1.1.1", "ipinfo_api")
        tracker.mark_processed("1.1.1.1", "rdns_ptr")
        assert tracker.is_processed("1.1.1.1", "ipinfo_api") is True
        assert tracker.is_processed("1.1.1.1", "rdns_ptr") is True

    def test_empty_channel_backward_compat(self):
        """channel="" 与不传 channel 等价"""
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("1.1.1.1")
        assert tracker.is_processed("1.1.1.1", "") is True
        tracker.mark_processed("2.2.2.2", "")
        assert tracker.is_processed("2.2.2.2") is True


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

    def test_channel_isolation(self, tmp_path: pathlib.Path):
        """不同渠道的进度互不影响"""
        file_path = str(tmp_path / "progress.txt")
        tracker = FileProgressTracker(file_path)
        tracker.mark_processed("1.1.1.1", "ipinfo_api")
        assert tracker.is_processed("1.1.1.1", "ipinfo_api") is True
        assert tracker.is_processed("1.1.1.1", "rdns_ptr") is False

    def test_same_ip_different_channels_persists(self, tmp_path: pathlib.Path):
        """同一 IP 在不同渠道分别标记，持久化后可读"""
        file_path = str(tmp_path / "progress.txt")
        tracker = FileProgressTracker(file_path)
        tracker.mark_processed("1.1.1.1", "ipinfo_api")
        tracker.mark_processed("1.1.1.1", "rdns_ptr")
        tracker2 = FileProgressTracker(file_path)
        assert tracker2.is_processed("1.1.1.1", "ipinfo_api") is True
        assert tracker2.is_processed("1.1.1.1", "rdns_ptr") is True

    def test_backward_compat_old_format(self, tmp_path: pathlib.Path):
        """兼容旧格式：文件中只有 ip 没有 tab"""
        file_path = str(tmp_path / "progress.txt")
        # 手动写入旧格式
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("1.1.1.1\n2.2.2.2\n")
        tracker = FileProgressTracker(file_path)
        assert tracker.is_processed("1.1.1.1", "") is True
        assert tracker.is_processed("2.2.2.2", "") is True
        # 旧格式记录的 ip，查具体渠道应为 False
        assert tracker.is_processed("1.1.1.1", "ipinfo_api") is False

    def test_dedup_mark(self, tmp_path: pathlib.Path):
        """重复标记不会写入重复行"""
        file_path = str(tmp_path / "progress.txt")
        tracker = FileProgressTracker(file_path)
        tracker.mark_processed("1.1.1.1", "ipinfo_api")
        tracker.mark_processed("1.1.1.1", "ipinfo_api")
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        assert len(lines) == 1
