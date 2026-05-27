import json
import sqlite3

from ip_info.utils.cache_converter import (
    export_domain_cache_to_json,
    export_progress_to_json,
    import_domain_cache_from_json,
    import_progress_from_json,
    import_progress_from_text,
    merge_progress_dbs,
)


class TestExportProgressToJson:
    def test_导出空数据库(self, tmp_path):
        db_path = str(tmp_path / "progress.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
        )
        conn.commit()
        conn.close()

        output_path = str(tmp_path / "export.json")
        stats = export_progress_to_json(db_path, output_path)

        assert stats.exported == 0
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["version"] == 1
        assert data["records"] == []
        assert "exported_at" in data
        assert data["source"] == db_path

    def test_导出有数据的数据库(self, tmp_path):
        db_path = str(tmp_path / "progress.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
        )
        conn.executemany(
            "INSERT INTO progress (ip, channel) VALUES (?, ?)",
            [("8.8.8.8", "ipinfo_api"), ("8.8.8.8", "rdns_ptr"), ("1.1.1.1", "aizhan")],
        )
        conn.commit()
        conn.close()

        output_path = str(tmp_path / "export.json")
        stats = export_progress_to_json(db_path, output_path)

        assert stats.exported == 3
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["records"]) == 3
        assert {"ip": "8.8.8.8", "channel": "ipinfo_api"} in data["records"]
        assert {"ip": "8.8.8.8", "channel": "rdns_ptr"} in data["records"]
        assert {"ip": "1.1.1.1", "channel": "aizhan"} in data["records"]


class TestImportProgressFromJson:
    def test_导入到空数据库(self, tmp_path):
        db_path = str(tmp_path / "progress.db")
        json_path = str(tmp_path / "import.json")

        records = [
            {"ip": "8.8.8.8", "channel": "ipinfo_api"},
            {"ip": "8.8.8.8", "channel": "rdns_ptr"},
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "exported_at": "2026-05-26T12:00:00", "source": "test", "records": records}, f)

        stats = import_progress_from_json(json_path, db_path)

        assert stats.imported == 2
        assert stats.skipped == 0
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT ip, channel FROM progress ORDER BY ip, channel").fetchall()
        conn.close()
        assert len(rows) == 2

    def test_重复导入幂等(self, tmp_path):
        db_path = str(tmp_path / "progress.db")
        json_path = str(tmp_path / "import.json")

        records = [{"ip": "8.8.8.8", "channel": "ipinfo_api"}]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "exported_at": "2026-05-26T12:00:00", "source": "test", "records": records}, f)

        import_progress_from_json(json_path, db_path)
        stats = import_progress_from_json(json_path, db_path)

        assert stats.imported == 0
        assert stats.skipped == 1

    def test_部分重复导入(self, tmp_path):
        db_path = str(tmp_path / "progress.db")
        json_path = str(tmp_path / "import.json")

        records = [
            {"ip": "8.8.8.8", "channel": "ipinfo_api"},
            {"ip": "1.1.1.1", "channel": "rdns_ptr"},
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "exported_at": "2026-05-26T12:00:00", "source": "test", "records": records}, f)

        # 先导入第一条
        first_json = str(tmp_path / "first.json")
        with open(first_json, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": 1,
                    "exported_at": "2026-05-26T12:00:00",
                    "source": "test",
                    "records": [records[0]],
                },
                f,
            )
        import_progress_from_json(first_json, db_path)

        # 再导入全部
        stats = import_progress_from_json(json_path, db_path)
        assert stats.imported == 1
        assert stats.skipped == 1


class TestImportProgressFromText:
    def test_导入tab分隔格式(self, tmp_path):
        text_path = str(tmp_path / "legacy.progress")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("8.8.8.8\tipinfo_api\n1.1.1.1\trdns_ptr\n")

        db_path = str(tmp_path / "progress.db")
        stats = import_progress_from_text(text_path, db_path)

        assert stats.imported == 2
        assert stats.skipped == 0

    def test_导入旧格式只有IP(self, tmp_path):
        text_path = str(tmp_path / "legacy.progress")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("8.8.8.8\n1.1.1.1\n")

        db_path = str(tmp_path / "progress.db")
        stats = import_progress_from_text(text_path, db_path)

        assert stats.imported == 2
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT ip, channel FROM progress ORDER BY ip").fetchall()
        conn.close()
        assert rows == [("1.1.1.1", ""), ("8.8.8.8", "")]

    def test_混合格式(self, tmp_path):
        text_path = str(tmp_path / "legacy.progress")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("8.8.8.8\n1.1.1.1\trdns_ptr\n2.2.2.2\tipinfo_api\n")

        db_path = str(tmp_path / "progress.db")
        stats = import_progress_from_text(text_path, db_path)

        assert stats.imported == 3
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT ip, channel FROM progress ORDER BY ip, channel").fetchall()
        conn.close()
        assert rows == [("1.1.1.1", "rdns_ptr"), ("2.2.2.2", "ipinfo_api"), ("8.8.8.8", "")]

    def test_跳过空行(self, tmp_path):
        text_path = str(tmp_path / "legacy.progress")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("8.8.8.8\n\n1.1.1.1\trdns_ptr\n")

        db_path = str(tmp_path / "progress.db")
        stats = import_progress_from_text(text_path, db_path)

        assert stats.imported == 2

    def test_重复导入幂等(self, tmp_path):
        text_path = str(tmp_path / "legacy.progress")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("8.8.8.8\tipinfo_api\n")

        db_path = str(tmp_path / "progress.db")
        import_progress_from_text(text_path, db_path)
        stats = import_progress_from_text(text_path, db_path)

        assert stats.imported == 0
        assert stats.skipped == 1

    def test_文件不存在(self, tmp_path):
        db_path = str(tmp_path / "progress.db")
        stats = import_progress_from_text(str(tmp_path / "nonexistent.progress"), db_path)

        assert stats.imported == 0
        assert stats.skipped == 0


class TestMergeProgressDbs:
    def test_合并两个数据库(self, tmp_path):
        src_db = str(tmp_path / "src.db")
        dst_db = str(tmp_path / "dst.db")

        conn = sqlite3.connect(src_db)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
        )
        conn.executemany(
            "INSERT INTO progress (ip, channel) VALUES (?, ?)",
            [("8.8.8.8", "ipinfo_api"), ("1.1.1.1", "rdns_ptr")],
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(dst_db)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
        )
        conn.executemany(
            "INSERT INTO progress (ip, channel) VALUES (?, ?)",
            [("8.8.8.8", "ipinfo_api"), ("2.2.2.2", "aizhan")],
        )
        conn.commit()
        conn.close()

        stats = merge_progress_dbs(src_db, dst_db)

        assert stats.imported == 1
        assert stats.skipped == 1

        conn = sqlite3.connect(dst_db)
        rows = conn.execute("SELECT ip, channel FROM progress ORDER BY ip, channel").fetchall()
        conn.close()
        assert len(rows) == 3

    def test_合并到空数据库(self, tmp_path):
        src_db = str(tmp_path / "src.db")
        dst_db = str(tmp_path / "dst.db")

        conn = sqlite3.connect(src_db)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
        )
        conn.executemany(
            "INSERT INTO progress (ip, channel) VALUES (?, ?)",
            [("8.8.8.8", "ipinfo_api"), ("1.1.1.1", "rdns_ptr")],
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(dst_db)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
        )
        conn.commit()
        conn.close()

        stats = merge_progress_dbs(src_db, dst_db)

        assert stats.imported == 2
        assert stats.skipped == 0


class TestExportDomainCacheToJson:
    def test_导出空数据库(self, tmp_path):
        db_path = str(tmp_path / "domain_cache.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_cache (domain TEXT PRIMARY KEY, status TEXT NOT NULL, "
            "resolved_ips TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        conn.commit()
        conn.close()

        output_path = str(tmp_path / "export.json")
        stats = export_domain_cache_to_json(db_path, output_path)

        assert stats.exported == 0
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["version"] == 1
        assert data["records"] == []

    def test_导出有数据的数据库(self, tmp_path):
        db_path = str(tmp_path / "domain_cache.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_cache (domain TEXT PRIMARY KEY, status TEXT NOT NULL, "
            "resolved_ips TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO domain_cache (domain, status, resolved_ips, updated_at) VALUES (?, ?, ?, ?)",
            ("dns.google", "matched", '["8.8.8.8", "8.8.4.4"]', "2026-05-26T10:00:00"),
        )
        conn.commit()
        conn.close()

        output_path = str(tmp_path / "export.json")
        stats = export_domain_cache_to_json(db_path, output_path)

        assert stats.exported == 1
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
        record = data["records"][0]
        assert record["domain"] == "dns.google"
        assert record["status"] == "matched"
        assert record["resolved_ips"] == ["8.8.8.8", "8.8.4.4"]
        assert record["updated_at"] == "2026-05-26T10:00:00"


class TestImportDomainCacheFromJson:
    def test_导入到空数据库(self, tmp_path):
        db_path = str(tmp_path / "domain_cache.db")
        json_path = str(tmp_path / "import.json")

        records = [
            {
                "domain": "dns.google",
                "status": "matched",
                "resolved_ips": ["8.8.8.8", "8.8.4.4"],
                "updated_at": "2026-05-26T10:00:00",
            }
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "exported_at": "2026-05-26T12:00:00", "source": "test", "records": records}, f)

        stats = import_domain_cache_from_json(json_path, db_path)

        assert stats.imported == 1
        assert stats.skipped == 0

        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT domain, status, resolved_ips, updated_at FROM domain_cache").fetchone()
        conn.close()
        assert row[0] == "dns.google"
        assert row[1] == "matched"
        assert json.loads(row[2]) == ["8.8.8.8", "8.8.4.4"]

    def test_重复导入幂等(self, tmp_path):
        db_path = str(tmp_path / "domain_cache.db")
        json_path = str(tmp_path / "import.json")

        records = [
            {
                "domain": "dns.google",
                "status": "matched",
                "resolved_ips": ["8.8.8.8"],
                "updated_at": "2026-05-26T10:00:00",
            }
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "exported_at": "2026-05-26T12:00:00", "source": "test", "records": records}, f)

        import_domain_cache_from_json(json_path, db_path)
        stats = import_domain_cache_from_json(json_path, db_path)

        # INSERT OR IGNORE 跳过已存在的 domain
        assert stats.imported == 0
        assert stats.skipped == 1

    def test_部分重复导入(self, tmp_path):
        db_path = str(tmp_path / "domain_cache.db")
        json_path = str(tmp_path / "import.json")

        records = [
            {
                "domain": "dns.google",
                "status": "matched",
                "resolved_ips": ["8.8.8.8"],
                "updated_at": "2026-05-26T10:00:00",
            },
            {
                "domain": "example.com",
                "status": "unresolved",
                "resolved_ips": [],
                "updated_at": "2026-05-26T11:00:00",
            },
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "exported_at": "2026-05-26T12:00:00", "source": "test", "records": records}, f)

        # 先导入第一条
        first_json = str(tmp_path / "first.json")
        with open(first_json, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": 1,
                    "exported_at": "2026-05-26T12:00:00",
                    "source": "test",
                    "records": [records[0]],
                },
                f,
            )
        import_domain_cache_from_json(first_json, db_path)

        # 再导入全部
        stats = import_domain_cache_from_json(json_path, db_path)
        assert stats.imported == 1
        assert stats.skipped == 1


class TestRoundTrip:
    def test_progress导出再导入(self, tmp_path):
        db_path = str(tmp_path / "progress.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
        )
        conn.executemany(
            "INSERT INTO progress (ip, channel) VALUES (?, ?)",
            [("8.8.8.8", "ipinfo_api"), ("8.8.8.8", "rdns_ptr"), ("1.1.1.1", "")],
        )
        conn.commit()
        conn.close()

        json_path = str(tmp_path / "export.json")
        export_progress_to_json(db_path, json_path)

        new_db = str(tmp_path / "restored.db")
        stats = import_progress_from_json(json_path, new_db)

        assert stats.imported == 3
        assert stats.skipped == 0

        conn = sqlite3.connect(new_db)
        rows = conn.execute("SELECT ip, channel FROM progress ORDER BY ip, channel").fetchall()
        conn.close()
        assert len(rows) == 3

    def test_domain_cache导出再导入(self, tmp_path):
        db_path = str(tmp_path / "domain_cache.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_cache (domain TEXT PRIMARY KEY, status TEXT NOT NULL, "
            "resolved_ips TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO domain_cache (domain, status, resolved_ips, updated_at) VALUES (?, ?, ?, ?)",
            ("dns.google", "matched", '["8.8.8.8", "8.8.4.4"]', "2026-05-26T10:00:00"),
        )
        conn.commit()
        conn.close()

        json_path = str(tmp_path / "export.json")
        export_domain_cache_to_json(db_path, json_path)

        new_db = str(tmp_path / "restored.db")
        stats = import_domain_cache_from_json(json_path, new_db)

        assert stats.imported == 1
        assert stats.skipped == 0

        conn = sqlite3.connect(new_db)
        row = conn.execute("SELECT domain, status, resolved_ips, updated_at FROM domain_cache").fetchone()
        conn.close()
        assert row[0] == "dns.google"
        assert json.loads(row[2]) == ["8.8.8.8", "8.8.4.4"]


class TestDeleteProgress:
    def test_delete_channel(self, tmp_path):
        """删除指定渠道的进度记录。"""
        from ip_info.utils.cache_converter import delete_progress_channel

        db_path = str(tmp_path / "progress.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
        )
        conn.executemany(
            "INSERT INTO progress (ip, channel) VALUES (?, ?)",
            [("1.1.1.1", "port_scan"), ("2.2.2.2", "port_scan"), ("1.1.1.1", "ipinfo_api")],
        )
        conn.commit()
        conn.close()

        deleted = delete_progress_channel(db_path, "port_scan")
        assert deleted == 2

        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT ip, channel FROM progress").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0] == ("1.1.1.1", "ipinfo_api")

    def test_delete_channel_nonexistent(self, tmp_path):
        """删除不存在的渠道返回 0。"""
        from ip_info.utils.cache_converter import delete_progress_channel

        db_path = str(tmp_path / "progress.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
        )
        conn.executemany(
            "INSERT INTO progress (ip, channel) VALUES (?, ?)",
            [("1.1.1.1", "ipinfo_api")],
        )
        conn.commit()
        conn.close()

        deleted = delete_progress_channel(db_path, "nonexistent")
        assert deleted == 0

    def test_delete_all(self, tmp_path):
        """删除所有进度记录。"""
        from ip_info.utils.cache_converter import delete_progress_all

        db_path = str(tmp_path / "progress.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
        )
        conn.executemany(
            "INSERT INTO progress (ip, channel) VALUES (?, ?)",
            [("1.1.1.1", "ipinfo_api"), ("2.2.2.2", "rdns_ptr")],
        )
        conn.commit()
        conn.close()

        deleted = delete_progress_all(db_path)
        assert deleted == 2

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM progress").fetchone()[0]
        conn.close()
        assert count == 0


class TestCleanChannelForIps:
    def _setup_project(self, tmp_path):
        """创建测试项目：progress.db + ip_data.json。"""
        db_path = str(tmp_path / "progress.db")
        json_path = str(tmp_path / "ip_data.json")

        # progress.db
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
        )
        conn.executemany(
            "INSERT INTO progress (ip, channel) VALUES (?, ?)",
            [
                ("1.1.1.1", "port_scan"),
                ("2.2.2.2", "port_scan"),
                ("3.3.3.3", "port_scan"),
                ("1.1.1.1", "ipinfo_api"),
                ("2.2.2.2", "ipinfo_api"),
            ],
        )
        conn.commit()
        conn.close()

        # ip_data.json
        data = {
            "1.1.1.1": {"ip": "1.1.1.1", "port_scan": {"ports": [80]}, "ipinfo_api": {"country": "US"}},
            "2.2.2.2": {"ip": "2.2.2.2", "port_scan": {"ports": [443]}, "ipinfo_api": {"country": "AU"}},
            "3.3.3.3": {"ip": "3.3.3.3", "port_scan": {"ports": [22]}},
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        return db_path, json_path

    def test_clean_all_ips_for_channel(self, tmp_path):
        """清空所有 IP 的指定渠道（形式3）。"""
        from ip_info.utils.cache_converter import clean_channel_for_ips

        db_path, json_path = self._setup_project(tmp_path)

        result = clean_channel_for_ips(json_path, db_path, "port_scan")

        assert result["progress_deleted"] == 3
        assert result["data_deleted"] == 3

        # 验证 progress.db
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT ip, channel FROM progress ORDER BY ip, channel").fetchall()
        conn.close()
        assert len(rows) == 2  # 只剩 ipinfo_api
        assert all(r[1] == "ipinfo_api" for r in rows)

        # 验证 ip_data.json
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "port_scan" not in data["1.1.1.1"]
        assert "port_scan" not in data["2.2.2.2"]
        assert "port_scan" not in data["3.3.3.3"]
        assert "ipinfo_api" in data["1.1.1.1"]

    def test_clean_specific_ips_for_channel(self, tmp_path):
        """指定 IP 清理渠道（形式2）。"""
        from ip_info.utils.cache_converter import clean_channel_for_ips

        db_path, json_path = self._setup_project(tmp_path)

        result = clean_channel_for_ips(json_path, db_path, "port_scan", ips=["1.1.1.1", "2.2.2.2"])

        assert result["progress_deleted"] == 2
        assert result["data_deleted"] == 2

        # 验证 progress.db
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT ip, channel FROM progress WHERE channel = 'port_scan'").fetchall()
        conn.close()
        assert len(rows) == 1  # 3.3.3.3 保留
        assert rows[0][0] == "3.3.3.3"

        # 验证 ip_data.json
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "port_scan" not in data["1.1.1.1"]
        assert "port_scan" not in data["2.2.2.2"]
        assert "port_scan" in data["3.3.3.3"]

    def test_clean_nonexistent_channel(self, tmp_path):
        """清理不存在的渠道返回 0。"""
        from ip_info.utils.cache_converter import clean_channel_for_ips

        db_path, json_path = self._setup_project(tmp_path)

        result = clean_channel_for_ips(json_path, db_path, "nonexistent")

        assert result["progress_deleted"] == 0
        assert result["data_deleted"] == 0
