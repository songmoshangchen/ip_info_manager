import os
import sqlite3
import threading
from threading import Barrier

import pytest

from ip_info.store.protocols import DomainCache
from ip_info.store.sqlite_cache import SqliteDomainCache


class TestSqliteDomainCache:
    @pytest.fixture
    def cache(self, tmp_path):
        db_path = str(tmp_path / "test_cache.db")
        return SqliteDomainCache(db_path)

    def test_满足_DomainCache_协议(self, cache):
        assert isinstance(cache, DomainCache)

    def test_正常读写(self, cache):
        cache.set("example.com", {"status": "matched", "resolved_ips": ["1.2.3.4"]})
        result = cache.get("example.com")
        assert result == {"domain": "example.com", "status": "matched", "resolved_ips": ["1.2.3.4"]}

    def test_不存在域名返回None(self, cache):
        result = cache.get("notexist.com")
        assert result is None

    def test_覆盖写入(self, cache):
        cache.set("example.com", {"status": "first", "resolved_ips": ["1.1.1.1"]})
        cache.set("example.com", {"status": "second", "resolved_ips": ["2.2.2.2"]})
        result = cache.get("example.com")
        assert result == {"domain": "example.com", "status": "second", "resolved_ips": ["2.2.2.2"]}

    def test_并发安全(self, tmp_path):
        db_path = str(tmp_path / "concurrent_test.db")
        cache = SqliteDomainCache(db_path)
        num_threads = 10
        barrier = Barrier(num_threads)

        errors: list[Exception] = []

        def writer(thread_id: int):
            try:
                barrier.wait()
                domain = f"domain{thread_id}.com"
                cache.set(domain, {"status": "matched", "resolved_ips": [f"10.0.0.{thread_id}"]})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"并发写入出错: {errors}"
        for i in range(num_threads):
            result = cache.get(f"domain{i}.com")
            assert result is not None, f"domain{i}.com 数据丢失"
            assert result["status"] == "matched"
            assert result["resolved_ips"] == [f"10.0.0.{i}"]

    def test_数据库文件自动创建(self, tmp_path):
        db_path = str(tmp_path / "subdir" / "cache.db")
        cache = SqliteDomainCache(db_path)
        cache.set("example.com", {"status": "ok", "resolved_ips": ["1.2.3.4"]})
        assert os.path.exists(db_path)

    def test_父目录不存在时自动创建(self, tmp_path):
        db_path = str(tmp_path / "deep" / "nested" / "dir" / "cache.db")
        cache = SqliteDomainCache(db_path)
        cache.set("example.com", {"status": "matched", "resolved_ips": ["1.2.3.4"]})
        assert os.path.exists(db_path)
        result = cache.get("example.com")
        assert result is not None

    def test_get返回结构包含domain_status_resolved_ips(self, cache):
        cache.set("test.com", {"status": "changed", "resolved_ips": ["5.6.7.8", "9.10.11.12"]})
        result = cache.get("test.com")
        assert "domain" in result
        assert "status" in result
        assert "resolved_ips" in result
        assert result["domain"] == "test.com"
        assert result["status"] == "changed"
        assert result["resolved_ips"] == ["5.6.7.8", "9.10.11.12"]

    def test_set缺少status时默认空字符串(self, cache):
        cache.set("example.com", {"resolved_ips": ["1.2.3.4"]})
        result = cache.get("example.com")
        assert result["status"] == ""

    def test_set缺少resolved_ips时默认空列表(self, cache):
        cache.set("example.com", {"status": "unresolved"})
        result = cache.get("example.com")
        assert result["resolved_ips"] == []

    def test_损坏的resolved_ips数据返回None(self, tmp_path):
        db_path = str(tmp_path / "corrupt_test.db")
        SqliteDomainCache(db_path)
        # 直接写入损坏数据
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT OR REPLACE INTO domain_cache (domain, status, resolved_ips, updated_at) VALUES (?, ?, ?, ?)",
            ("bad.com", "matched", "not-valid-json", "2026-01-01T00:00:00+00:00"),
        )
        conn.commit()
        conn.close()
        # 重新创建 cache 实例以获取新连接
        cache2 = SqliteDomainCache(db_path)
        result = cache2.get("bad.com")
        assert result is None

    def test_resolved_ips为空列表(self, cache):
        cache.set("unresolved.com", {"status": "unresolved", "resolved_ips": []})
        result = cache.get("unresolved.com")
        assert result["resolved_ips"] == []
        assert result["status"] == "unresolved"

    def test_resolved_ips为多个IP(self, cache):
        ips = ["1.2.3.4", "5.6.7.8", "9.10.11.12"]
        cache.set("multi.com", {"status": "matched", "resolved_ips": ips})
        result = cache.get("multi.com")
        assert result["resolved_ips"] == ips
