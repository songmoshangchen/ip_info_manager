"""Issue 4: 查询进度查看 CLI 工具的单元测试。"""

import json
import sqlite3


# ---------------------------------------------------------------------------
# Helper: 创建测试用的 progress.db
# ---------------------------------------------------------------------------
def _create_progress_db(db_path: str, records: list[tuple[str, str]]) -> None:
    """创建 progress.db 并插入记录。"""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS progress (ip TEXT NOT NULL, channel TEXT NOT NULL, PRIMARY KEY (ip, channel))"
    )
    conn.executemany("INSERT OR IGNORE INTO progress (ip, channel) VALUES (?, ?)", records)
    conn.commit()
    conn.close()


def _create_domain_cache_db(db_path: str, records: list[tuple[str, str, str, str]]) -> None:
    """创建 domain_cache.db 并插入记录。"""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS domain_cache "
        "(domain TEXT PRIMARY KEY, status TEXT NOT NULL, "
        "resolved_ips TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    conn.executemany(
        "INSERT OR REPLACE INTO domain_cache (domain, status, resolved_ips, updated_at) VALUES (?, ?, ?, ?)",
        records,
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Tracer bullet: 核心查询函数
# ---------------------------------------------------------------------------
class TestQueryProgress:
    """测试 query_status 的核心查询逻辑。"""

    def test_query_channel_counts_from_progress_db(self, tmp_path):
        """给定 progress.db，能统计各渠道已完成数。"""
        db_path = str(tmp_path / "progress.db")
        _create_progress_db(
            db_path,
            [
                ("1.1.1.1", "ipinfo_api"),
                ("2.2.2.2", "ipinfo_api"),
                ("1.1.1.1", "rdns_ptr"),
                ("3.3.3.3", "aizhan"),
            ],
        )

        from ip_info.utils.query_status import query_channel_counts

        result = query_channel_counts(db_path)
        assert result == {"ipinfo_api": 2, "rdns_ptr": 1, "aizhan": 1}

    def test_query_channel_counts_empty_db(self, tmp_path):
        """空 progress.db 返回空字典。"""
        db_path = str(tmp_path / "progress.db")
        _create_progress_db(db_path, [])

        from ip_info.utils.query_status import query_channel_counts

        result = query_channel_counts(db_path)
        assert result == {}

    def test_query_channel_counts_nonexistent_db(self, tmp_path):
        """不存在的 progress.db 返回空字典。"""
        db_path = str(tmp_path / "nonexistent.db")

        from ip_info.utils.query_status import query_channel_counts

        result = query_channel_counts(db_path)
        assert result == {}


class TestComputeProgress:
    """测试进度计算逻辑。"""

    def test_compute_progress_basic(self):
        """给定 IP 总数和渠道完成数，计算剩余和完成率。"""
        from ip_info.utils.query_status import compute_progress

        result = compute_progress(total_ips=100, channel_counts={"ipinfo_api": 80, "rdns_ptr": 100})
        assert result["ipinfo_api"] == {"completed": 80, "remaining": 20, "percentage": 80.0}
        assert result["rdns_ptr"] == {"completed": 100, "remaining": 0, "percentage": 100.0}

    def test_compute_progress_no_records(self):
        """没有完成记录时，所有渠道剩余等于总数。"""
        from ip_info.utils.query_status import compute_progress

        result = compute_progress(total_ips=50, channel_counts={})
        assert result == {}

    def test_compute_progress_completed_exceeds_total(self):
        """完成数超过总数时（异常情况），完成率上限 100%。"""
        from ip_info.utils.query_status import compute_progress

        result = compute_progress(total_ips=10, channel_counts={"ipinfo_api": 15})
        assert result["ipinfo_api"]["percentage"] == 100.0
        assert result["ipinfo_api"]["remaining"] == 0


class TestQueryDomainCacheCount:
    """测试域名缓存计数。"""

    def test_domain_cache_count(self, tmp_path):
        """给定 domain_cache.db，能统计记录数。"""
        db_path = str(tmp_path / "domain_cache.db")
        _create_domain_cache_db(
            db_path,
            [
                ("dns.google", "matched", '["8.8.8.8"]', "2026-05-26T10:00:00"),
                ("example.com", "changed", '["1.2.3.4"]', "2026-05-26T10:00:00"),
            ],
        )

        from ip_info.utils.query_status import query_domain_cache_count

        assert query_domain_cache_count(db_path) == 2

    def test_domain_cache_count_empty(self, tmp_path):
        """空 domain_cache.db 返回 0。"""
        db_path = str(tmp_path / "domain_cache.db")
        _create_domain_cache_db(db_path, [])

        from ip_info.utils.query_status import query_domain_cache_count

        assert query_domain_cache_count(db_path) == 0

    def test_domain_cache_count_nonexistent(self, tmp_path):
        """不存在的 domain_cache.db 返回 0。"""
        from ip_info.utils.query_status import query_domain_cache_count

        assert query_domain_cache_count(str(tmp_path / "nonexistent.db")) == 0


class TestLoadIpCount:
    """测试从项目目录获取 IP 总数。"""

    def test_load_ip_count_from_ips_txt(self, tmp_path):
        """从 ips.txt 读取 IP 总数。"""
        (tmp_path / "ips.txt").write_text("1.1.1.1\n2.2.2.2\n3.3.3.3\n")

        from ip_info.utils.query_status import load_ip_count

        assert load_ip_count(str(tmp_path)) == 3

    def test_load_ip_count_from_ip_data_json(self, tmp_path):
        """从 ip_data.json 读取 IP 总数（当 ips.txt 不存在时）。"""
        (tmp_path / "ip_data.json").write_text(json.dumps({"1.1.1.1": {}, "2.2.2.2": {}}))

        from ip_info.utils.query_status import load_ip_count

        assert load_ip_count(str(tmp_path)) == 2

    def test_load_ip_count_empty_dir(self, tmp_path):
        """空目录返回 0。"""
        from ip_info.utils.query_status import load_ip_count

        assert load_ip_count(str(tmp_path)) == 0


class TestFormatOutput:
    """测试输出格式化。"""

    def test_format_table(self):
        """终端表格输出格式。"""
        from ip_info.utils.query_status import format_table

        result = format_table(
            project="data/0518-0524",
            total_ips=100,
            progress={
                "ipinfo_api": {"completed": 80, "remaining": 20, "percentage": 80.0},
                "rdns_ptr": {"completed": 100, "remaining": 0, "percentage": 100.0},
            },
            domain_cache_count=50,
        )
        assert "data/0518-0524" in result
        assert "100" in result
        assert "ipinfo_api" in result
        assert "80.0%" in result
        assert "100.0%" in result
        assert "50" in result

    def test_format_json(self):
        """JSON 输出格式。"""
        from ip_info.utils.query_status import format_json

        result = format_json(
            project="data/0518-0524",
            total_ips=100,
            progress={
                "ipinfo_api": {"completed": 80, "remaining": 20, "percentage": 80.0},
            },
            domain_cache_count=50,
        )
        data = json.loads(result)
        assert data["project"] == "data/0518-0524"
        assert data["total_ips"] == 100
        assert data["channels"]["ipinfo_api"]["percentage"] == 80.0
        assert data["domain_cache_count"] == 50


class TestListProjects:
    """测试 --list 目录扫描功能。"""

    def test_list_projects_finds_projects_with_progress_db(self, tmp_path):
        """扫描目录时只列出包含 progress.db 的子目录。"""
        # 创建两个子目录，一个有 progress.db，一个没有
        proj1 = tmp_path / "0518-0524"
        proj1.mkdir()
        _create_progress_db(
            str(proj1 / "progress.db"),
            [("1.1.1.1", "ipinfo_api"), ("2.2.2.2", "ipinfo_api")],
        )
        (proj1 / "ips.txt").write_text("1.1.1.1\n2.2.2.2\n3.3.3.3\n")

        proj2 = tmp_path / "empty_project"
        proj2.mkdir()
        # 没有 progress.db

        from ip_info.utils.query_status import list_projects

        result = list_projects(str(tmp_path))
        assert "0518-0524" in result
        assert "empty_project" not in result

    def test_list_projects_empty_data_dir(self, tmp_path):
        """空数据目录返回提示。"""
        from ip_info.utils.query_status import list_projects

        result = list_projects(str(tmp_path))
        assert "未找到" in result

    def test_list_projects_nonexistent_dir(self):
        """不存在的目录返回错误提示。"""
        from ip_info.utils.query_status import list_projects

        result = list_projects("/nonexistent/path")
        assert "不存在" in result


class TestQueryProjectIntegration:
    """测试 query_project 集成函数。"""

    def test_query_project_table_output(self, tmp_path):
        """query_project 返回终端表格格式。"""
        _create_progress_db(
            str(tmp_path / "progress.db"),
            [("1.1.1.1", "ipinfo_api"), ("2.2.2.2", "rdns_ptr")],
        )
        (tmp_path / "ips.txt").write_text("1.1.1.1\n2.2.2.2\n3.3.3.3\n")

        from ip_info.utils.query_status import query_project

        result = query_project(str(tmp_path))
        assert "ipinfo_api" in result
        assert "rdns_ptr" in result

    def test_query_project_json_output(self, tmp_path):
        """query_project 返回 JSON 格式。"""
        _create_progress_db(
            str(tmp_path / "progress.db"),
            [("1.1.1.1", "ipinfo_api")],
        )
        (tmp_path / "ips.txt").write_text("1.1.1.1\n2.2.2.2\n")

        from ip_info.utils.query_status import query_project

        result = query_project(str(tmp_path), as_json=True)
        data = json.loads(result)
        assert "channels" in data
        assert "ipinfo_api" in data["channels"]

    def test_query_project_channel_filter(self, tmp_path):
        """query_project 过滤指定渠道。"""
        _create_progress_db(
            str(tmp_path / "progress.db"),
            [("1.1.1.1", "ipinfo_api"), ("2.2.2.2", "rdns_ptr")],
        )
        (tmp_path / "ips.txt").write_text("1.1.1.1\n2.2.2.2\n")

        from ip_info.utils.query_status import query_project

        result = query_project(str(tmp_path), channel_filter="ipinfo_api", as_json=True)
        data = json.loads(result)
        assert "ipinfo_api" in data["channels"]
        assert "rdns_ptr" not in data["channels"]
