"""load_ips 工具函数的单元测试。"""

import logging
from pathlib import Path

import pytest

from ip_info.utils.load_ips import load_ips


@pytest.fixture
def tmp_ip_file(tmp_path: Path):
    """创建临时 IP 文件的辅助 fixture。"""

    def _write(content: str) -> str:
        p = tmp_path / "ips.txt"
        p.write_text(content, encoding="utf-8")
        return str(p)

    return _write


# ── 基础功能测试 ──────────────────────────────────────────────


class TestBasicLoading:
    """基础加载功能：去空行、去重、过滤注释行。"""

    def test_skip_empty_lines(self, tmp_ip_file):
        path = tmp_ip_file("1.2.3.4\n\n5.6.7.8\n")
        assert load_ips(path) == ["1.2.3.4", "5.6.7.8"]

    def test_dedup_preserves_order(self, tmp_ip_file):
        path = tmp_ip_file("1.2.3.4\n5.6.7.8\n1.2.3.4\n")
        assert load_ips(path) == ["1.2.3.4", "5.6.7.8"]

    def test_skip_comment_lines(self, tmp_ip_file):
        path = tmp_ip_file("# comment\n1.2.3.4\n# another\n5.6.7.8\n")
        assert load_ips(path) == ["1.2.3.4", "5.6.7.8"]

    def test_utf8_bom(self, tmp_ip_file):
        p = Path(tmp_ip_file("1.2.3.4\n"))
        # 写入 UTF-8 BOM
        p.write_bytes(b"\xef\xbb\xbf1.2.3.4\n")
        assert load_ips(str(p)) == ["1.2.3.4"]


# ── IP 格式校验测试 ────────────────────────────────────────────


class TestIPValidation:
    """IP 格式校验：无效 IP 应被跳过并记录 WARNING。"""

    def test_mixed_valid_and_invalid(self, tmp_ip_file, caplog):
        """混合有效和无效 IP，只保留有效。"""
        path = tmp_ip_file("1.2.3.4\nabc\n999.999.999.999\n8.8.8.8\n")
        with caplog.at_level(logging.WARNING, logger="ip_info.utils.load_ips"):
            result = load_ips(path)
        assert result == ["1.2.3.4", "8.8.8.8"]
        assert len(caplog.records) == 2
        for record in caplog.records:
            assert record.levelno == logging.WARNING

    def test_all_valid_no_warning(self, tmp_ip_file, caplog):
        """全部有效 IP，不产生 WARNING。"""
        path = tmp_ip_file("1.2.3.4\n8.8.8.8\n::1\n")
        with caplog.at_level(logging.WARNING, logger="ip_info.utils.load_ips"):
            result = load_ips(path)
        assert result == ["1.2.3.4", "8.8.8.8", "::1"]
        assert len(caplog.records) == 0

    def test_all_invalid_returns_empty(self, tmp_ip_file, caplog):
        """全部无效 IP，返回空列表。"""
        path = tmp_ip_file("abc\n999.999.999.999\nhello\n")
        with caplog.at_level(logging.WARNING, logger="ip_info.utils.load_ips"):
            result = load_ips(path)
        assert result == []
        assert len(caplog.records) == 3

    def test_comments_and_blanks_unaffected_by_validation(self, tmp_ip_file, caplog):
        """注释行和空行不受 IP 校验影响。"""
        path = tmp_ip_file("# comment\n\n1.2.3.4\n  \n# another\n8.8.8.8\n")
        with caplog.at_level(logging.WARNING, logger="ip_info.utils.load_ips"):
            result = load_ips(path)
        assert result == ["1.2.3.4", "8.8.8.8"]
        assert len(caplog.records) == 0

    def test_ipv6_valid(self, tmp_ip_file, caplog):
        """IPv6 地址应通过校验。"""
        path = tmp_ip_file("::1\n2001:db8::1\nfe80::1\n")
        with caplog.at_level(logging.WARNING, logger="ip_info.utils.load_ips"):
            result = load_ips(path)
        assert result == ["::1", "2001:db8::1", "fe80::1"]
        assert len(caplog.records) == 0

    def test_invalid_ip_warning_contains_ip(self, tmp_ip_file, caplog):
        """WARNING 日志应包含无效 IP 地址。"""
        path = tmp_ip_file("not-an-ip\n1.2.3.4\n")
        with caplog.at_level(logging.WARNING, logger="ip_info.utils.load_ips"):
            load_ips(path)
        assert len(caplog.records) == 1
        assert "not-an-ip" in caplog.records[0].message
