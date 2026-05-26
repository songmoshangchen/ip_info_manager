import pathlib
import threading

from ip_info.utils.progress import ProgressTracker


class TestSqliteProgressTracker:
    def test_satisfies_protocol(self, tmp_path: pathlib.Path):
        """SqliteProgressTracker 满足 ProgressTracker 协议。"""
        from ip_info.utils.progress import SqliteProgressTracker

        tracker = SqliteProgressTracker(str(tmp_path / "progress.db"))
        assert isinstance(tracker, ProgressTracker)

    def test_mark_and_check(self, tmp_path: pathlib.Path):
        """标记后查询返回 True，未标记返回 False。"""
        from ip_info.utils.progress import SqliteProgressTracker

        tracker = SqliteProgressTracker(str(tmp_path / "progress.db"))
        tracker.mark_processed("1.1.1.1", "ipinfo_api")
        tracker.flush()
        assert tracker.is_processed("1.1.1.1", "ipinfo_api") is True
        assert tracker.is_processed("1.1.1.1", "rdns_ptr") is False
        assert tracker.is_processed("2.2.2.2", "ipinfo_api") is False

    def test_channel_isolation(self, tmp_path: pathlib.Path):
        """不同渠道的进度互不影响。"""
        from ip_info.utils.progress import SqliteProgressTracker

        tracker = SqliteProgressTracker(str(tmp_path / "progress.db"))
        tracker.mark_processed("1.1.1.1", "ipinfo_api")
        tracker.mark_processed("1.1.1.1", "rdns_ptr")
        tracker.flush()
        assert tracker.is_processed("1.1.1.1", "ipinfo_api") is True
        assert tracker.is_processed("1.1.1.1", "rdns_ptr") is True
        assert tracker.is_processed("1.1.1.1", "aizhan") is False

    def test_flush_persists_to_db(self, tmp_path: pathlib.Path):
        """flush 后数据持久化到 SQLite，新实例可读。"""
        from ip_info.utils.progress import SqliteProgressTracker

        db_path = str(tmp_path / "progress.db")
        tracker_a = SqliteProgressTracker(db_path)
        tracker_a.mark_processed("1.1.1.1", "ipinfo_api")
        tracker_a.mark_processed("2.2.2.2", "rdns_ptr")
        tracker_a.flush()

        tracker_b = SqliteProgressTracker(db_path)
        assert tracker_b.is_processed("1.1.1.1", "ipinfo_api") is True
        assert tracker_b.is_processed("2.2.2.2", "rdns_ptr") is True
        assert tracker_b.is_processed("3.3.3.3", "ipinfo_api") is False

    def test_buffer_without_flush_not_persisted(self, tmp_path: pathlib.Path):
        """未 flush 时，新实例看不到缓冲区数据。"""
        from ip_info.utils.progress import SqliteProgressTracker

        db_path = str(tmp_path / "progress.db")
        tracker_a = SqliteProgressTracker(db_path)
        tracker_a.mark_processed("1.1.1.1", "ipinfo_api")
        # 不 flush

        tracker_b = SqliteProgressTracker(db_path)
        assert tracker_b.is_processed("1.1.1.1", "ipinfo_api") is False

    def test_buffer_visible_in_same_instance(self, tmp_path: pathlib.Path):
        """缓冲区数据在同一个实例中可见（即使未 flush）。"""
        from ip_info.utils.progress import SqliteProgressTracker

        tracker = SqliteProgressTracker(str(tmp_path / "progress.db"))
        tracker.mark_processed("1.1.1.1", "ipinfo_api")
        # 不 flush，但同一实例应该可见
        assert tracker.is_processed("1.1.1.1", "ipinfo_api") is True

    def test_dedup_mark(self, tmp_path: pathlib.Path):
        """重复标记不会产生重复记录。"""
        from ip_info.utils.progress import SqliteProgressTracker

        db_path = str(tmp_path / "progress.db")
        tracker = SqliteProgressTracker(db_path)
        tracker.mark_processed("1.1.1.1", "ipinfo_api")
        tracker.mark_processed("1.1.1.1", "ipinfo_api")
        tracker.flush()

        import sqlite3

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM progress").fetchone()[0]
        conn.close()
        assert count == 1

    def test_concurrent_safety(self, tmp_path: pathlib.Path):
        """多线程并发标记 + flush 不丢数据。"""
        from ip_info.utils.progress import SqliteProgressTracker

        db_path = str(tmp_path / "progress.db")
        tracker = SqliteProgressTracker(db_path)
        errors = []

        def worker(thread_id):
            try:
                for i in range(50):
                    ip = f"10.0.{thread_id}.{i}"
                    tracker.mark_processed(ip, "test")
                tracker.flush()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # 验证所有数据都写入了
        total = 0
        for t in range(4):
            for i in range(50):
                ip = f"10.0.{t}.{i}"
                if tracker.is_processed(ip, "test"):
                    total += 1
        assert total == 200

    def test_empty_channel_backward_compat(self, tmp_path: pathlib.Path):
        """channel="" 与不传 channel 等价。"""
        from ip_info.utils.progress import SqliteProgressTracker

        tracker = SqliteProgressTracker(str(tmp_path / "progress.db"))
        tracker.mark_processed("1.1.1.1")
        tracker.flush()
        assert tracker.is_processed("1.1.1.1", "") is True
        tracker.mark_processed("2.2.2.2", "")
        tracker.flush()
        assert tracker.is_processed("2.2.2.2") is True

    def test_import_from_file_progress(self, tmp_path: pathlib.Path):
        """可以从旧 FileProgressTracker 文件导入数据。"""
        from ip_info.utils.progress import SqliteProgressTracker

        # 先写一个旧格式的 progress 文件
        progress_file = tmp_path / "progress.txt"
        progress_file.write_text("1.1.1.1\n2.2.2.2\tipinfo_api\n", encoding="utf-8")

        db_path = str(tmp_path / "progress.db")
        tracker = SqliteProgressTracker(db_path, import_from=str(progress_file))
        # 旧格式 1.1.1.1 被导入为 (1.1.1.1, "")
        assert tracker.is_processed("1.1.1.1", "") is True
        assert tracker.is_processed("2.2.2.2", "ipinfo_api") is True
        assert tracker.is_processed("1.1.1.1", "ipinfo_api") is False
