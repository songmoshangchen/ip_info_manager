"""verify_mapping 工具函数的单元测试。"""

import json
from unittest.mock import patch

from ip_info.utils.verify_mapping import (
    extract_mappings_from_ip_data,
    format_report,
    parse_mappings_from_args,
    parse_mappings_from_file,
)

# ── parse_mappings_from_args 测试 ──────────────────────────────────────


class TestParseMappingsFromArgs:
    """parse_mappings_from_args: 从命令行参数解析 IP-域名对。"""

    def test_single_pair(self):
        result = parse_mappings_from_args(["8.8.8.8 dns.google"])
        assert result == [{"ip": "8.8.8.8", "domain": "dns.google"}]

    def test_multiple_pairs(self):
        result = parse_mappings_from_args(["8.8.8.8 dns.google", "1.1.1.1 one.one.one.one"])
        assert result == [
            {"ip": "8.8.8.8", "domain": "dns.google"},
            {"ip": "1.1.1.1", "domain": "one.one.one.one"},
        ]

    def test_empty_args(self):
        assert parse_mappings_from_args([]) == []

    def test_invalid_format_skipped(self):
        result = parse_mappings_from_args(["8.8.8.8", "just-a-domain"])
        assert result == []

    def test_extra_whitespace(self):
        result = parse_mappings_from_args(["  8.8.8.8   dns.google  "])
        assert result == [{"ip": "8.8.8.8", "domain": "dns.google"}]

    def test_too_many_parts_takes_first_two(self):
        result = parse_mappings_from_args(["8.8.8.8 dns.google extra"])
        assert result == [{"ip": "8.8.8.8", "domain": "dns.google"}]

    def test_dedup_preserves_order(self):
        result = parse_mappings_from_args(["8.8.8.8 dns.google", "8.8.8.8 dns.google"])
        assert result == [{"ip": "8.8.8.8", "domain": "dns.google"}]


# ── parse_mappings_from_file 测试 ──────────────────────────────────────


class TestParseMappingsFromFile:
    """parse_mappings_from_file: 从文本文件解析 IP-域名对。"""

    def test_basic_file(self, tmp_path):
        f = tmp_path / "mappings.txt"
        f.write_text("8.8.8.8 dns.google\n1.1.1.1 one.one.one.one\n", encoding="utf-8")
        result = parse_mappings_from_file(str(f))
        assert result == [
            {"ip": "8.8.8.8", "domain": "dns.google"},
            {"ip": "1.1.1.1", "domain": "one.one.one.one"},
        ]

    def test_skips_empty_lines(self, tmp_path):
        f = tmp_path / "mappings.txt"
        f.write_text("8.8.8.8 dns.google\n\n1.1.1.1 one.one.one.one\n", encoding="utf-8")
        result = parse_mappings_from_file(str(f))
        assert len(result) == 2

    def test_skips_comment_lines(self, tmp_path):
        f = tmp_path / "mappings.txt"
        f.write_text("# comment\n8.8.8.8 dns.google\n", encoding="utf-8")
        result = parse_mappings_from_file(str(f))
        assert result == [{"ip": "8.8.8.8", "domain": "dns.google"}]

    def test_skips_invalid_lines(self, tmp_path):
        f = tmp_path / "mappings.txt"
        f.write_text("8.8.8.8 dns.google\njust-a-domain\n1.1.1.1 one.one.one.one\n", encoding="utf-8")
        result = parse_mappings_from_file(str(f))
        assert len(result) == 2

    def test_file_not_found(self, tmp_path):
        result = parse_mappings_from_file(str(tmp_path / "nonexistent.txt"))
        assert result == []


# ── extract_mappings_from_ip_data 测试 ──────────────────────────────────────


class TestExtractMappingsFromIpData:
    """extract_mappings_from_ip_data: 从 ip_data.json 提取 IP-域名映射。"""

    def test_basic_extraction(self, tmp_path):
        data = {
            "8.8.8.8": {
                "ip": "8.8.8.8",
                "aizhan": {"domains": ["dns.google", "dns.google2"]},
            },
        }
        f = tmp_path / "ip_data.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        result = extract_mappings_from_ip_data(str(f))
        assert len(result) == 2
        assert result[0] == {"ip": "8.8.8.8", "domain": "dns.google", "sources": ["aizhan"]}
        assert result[1] == {"ip": "8.8.8.8", "domain": "dns.google2", "sources": ["aizhan"]}

    def test_multiple_channels(self, tmp_path):
        data = {
            "8.8.8.8": {
                "ip": "8.8.8.8",
                "aizhan": {"domains": ["a.com"]},
                "chinaz": {"domains": ["b.com"]},
            },
        }
        f = tmp_path / "ip_data.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        result = extract_mappings_from_ip_data(str(f))
        assert len(result) == 2
        sources = {r["sources"][0] for r in result}
        assert sources == {"aizhan", "chinaz"}

    def test_no_domain_channels(self, tmp_path):
        data = {
            "8.8.8.8": {
                "ip": "8.8.8.8",
                "ipinfo": {"country": "US"},
            },
        }
        f = tmp_path / "ip_data.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        result = extract_mappings_from_ip_data(str(f))
        assert result == []

    def test_empty_file(self, tmp_path):
        f = tmp_path / "ip_data.json"
        f.write_text("{}", encoding="utf-8")
        result = extract_mappings_from_ip_data(str(f))
        assert result == []

    def test_file_not_found(self, tmp_path):
        result = extract_mappings_from_ip_data(str(tmp_path / "nonexistent.json"))
        assert result == []

    def test_domain_as_dict(self, tmp_path):
        data = {
            "8.8.8.8": {
                "ip": "8.8.8.8",
                "aizhan": {"domains": [{"domain": "dns.google"}]},
            },
        }
        f = tmp_path / "ip_data.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        result = extract_mappings_from_ip_data(str(f))
        assert len(result) == 1
        assert result[0]["domain"] == "dns.google"


# ── format_report 测试 ──────────────────────────────────────────────


class TestFormatReport:
    """format_report: 格式化验证报告。"""

    def test_basic_report(self):
        verify_results = [
            {"domain": "a.com", "target_ip": "1.1.1.1", "status": "matched", "resolved_ips": ["1.1.1.1"]},
            {"domain": "b.com", "target_ip": "2.2.2.2", "status": "changed", "resolved_ips": ["9.9.9.9"]},
            {"domain": "c.com", "target_ip": "3.3.3.3", "status": "unresolved", "resolved_ips": []},
            {"domain": "d.com", "target_ip": "4.4.4.4", "status": "timeout", "resolved_ips": []},
        ]
        with patch("ip_info.utils.verify_mapping.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2026-05-26 11:00:00"
            report = format_report(verify_results)
        assert "域名映射验证报告" in report
        assert "总映射数: 4" in report
        assert "仍然匹配: 1" in report
        assert "已变更:   1" in report
        assert "无法解析: 1" in report
        assert "解析超时: 1" in report

    def test_changed_detail(self):
        verify_results = [
            {"domain": "b.com", "target_ip": "2.2.2.2", "status": "changed", "resolved_ips": ["9.9.9.9"]},
        ]
        with patch("ip_info.utils.verify_mapping.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2026-05-26 11:00:00"
            report = format_report(verify_results)
        assert "已变更的域名" in report
        assert "b.com" in report
        assert "9.9.9.9" in report

    def test_empty_results(self):
        with patch("ip_info.utils.verify_mapping.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2026-05-26 11:00:00"
            report = format_report([])
        assert "总映射数: 0" in report

    def test_all_matched(self):
        verify_results = [
            {"domain": "a.com", "target_ip": "1.1.1.1", "status": "matched", "resolved_ips": ["1.1.1.1"]},
        ]
        with patch("ip_info.utils.verify_mapping.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2026-05-26 11:00:00"
            report = format_report(verify_results)
        assert "仍然匹配: 1" in report
        assert "已变更" not in report or "已变更:   0" in report
