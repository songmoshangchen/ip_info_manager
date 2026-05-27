"""quick_query 工具函数的单元测试。"""

from pathlib import Path
from unittest.mock import patch

from ip_info.utils.quick_query import generate_output_dir, parse_ips_from_args, parse_phases

# ── parse_ips_from_args 测试 ──────────────────────────────────────


class TestParseIpsFromArgs:
    """parse_ips_from_args: 从命令行参数列表中解析有效 IP。"""

    def test_single_valid_ip(self):
        assert parse_ips_from_args(["8.8.8.8"]) == ["8.8.8.8"]

    def test_multiple_valid_ips(self):
        result = parse_ips_from_args(["8.8.8.8", "1.1.1.1", "9.9.9.9"])
        assert result == ["8.8.8.8", "1.1.1.1", "9.9.9.9"]

    def test_dedup_preserves_order(self):
        result = parse_ips_from_args(["8.8.8.8", "1.1.1.1", "8.8.8.8"])
        assert result == ["8.8.8.8", "1.1.1.1"]

    def test_skip_invalid_ips(self):
        result = parse_ips_from_args(["8.8.8.8", "not-an-ip", "1.1.1.1"])
        assert result == ["8.8.8.8", "1.1.1.1"]

    def test_empty_args(self):
        assert parse_ips_from_args([]) == []

    def test_all_invalid(self):
        assert parse_ips_from_args(["abc", "999.999.999.999"]) == []

    def test_ipv6_valid(self):
        result = parse_ips_from_args(["::1", "2001:db8::1"])
        assert result == ["::1", "2001:db8::1"]

    def test_flags_not_treated_as_ips(self):
        """以 -- 开头的参数不应被当作 IP。"""
        result = parse_ips_from_args(["8.8.8.8", "--phase", "1,3"])
        assert result == ["8.8.8.8"]


# ── generate_output_dir 测试 ──────────────────────────────────────


class TestGenerateOutputDir:
    """generate_output_dir: 自动生成时间戳命名的输出目录。"""

    def test_default_base_dir(self, tmp_path):
        """不指定 base_dir 时，使用 data/quick 作为基础目录。"""
        with patch("ip_info.utils.quick_query.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20260526_143000"
            result = generate_output_dir()
        assert "data" in result and "quick" in result
        assert "20260526_143000" in result

    def test_custom_base_dir(self, tmp_path):
        """指定 base_dir 时，使用该目录作为基础。"""
        with patch("ip_info.utils.quick_query.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20260526_143000"
            result = generate_output_dir(base_dir=str(tmp_path / "custom"))
        assert str(tmp_path / "custom") in result
        assert "20260526_143000" in result

    def test_directory_is_created(self, tmp_path):
        """生成的目录应该被自动创建。"""
        with patch("ip_info.utils.quick_query.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20260526_143000"
            result = generate_output_dir(base_dir=str(tmp_path / "quick"))
        assert Path(result).exists()

    def test_timestamp_format(self, tmp_path):
        """时间戳格式应为 YYYYMMDD_HHMMSS。"""
        with patch("ip_info.utils.quick_query.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20260526_143000"
            result = generate_output_dir(base_dir=str(tmp_path))
        dir_name = Path(result).name
        assert dir_name == "20260526_143000"
        # 验证格式: 8位数字_6位数字
        parts = dir_name.split("_")
        assert len(parts) == 2
        assert len(parts[0]) == 8 and parts[0].isdigit()
        assert len(parts[1]) == 6 and parts[1].isdigit()


# ── parse_phases 测试 ──────────────────────────────────────────────


class TestParsePhases:
    """parse_phases: 解析 --phase 参数，自动补全依赖。"""

    def test_single_phase(self):
        assert parse_phases("1") == {1}

    def test_multiple_phases_no_dependency(self):
        """无依赖关系的多个 Phase。"""
        assert parse_phases("1,2") == {1, 2}

    def test_all_phases(self):
        assert parse_phases("1,2,3,4") == {1, 2, 3, 4}

    def test_phase3_adds_phase2_and_phase1_dependency(self):
        """Phase 3 依赖 Phase 2（间接依赖 Phase 1），应自动补全。"""
        assert parse_phases("3") == {1, 2, 3}

    def test_phase4_adds_all_dependencies(self):
        """Phase 4 传递依赖 Phase 3→2→1，应自动补全所有。"""
        assert parse_phases("4") == {1, 2, 3, 4}

    def test_phase1_and_phase3(self):
        """--phase 1,3 应自动补全 Phase 2。"""
        assert parse_phases("1,3") == {1, 2, 3}

    def test_phase1_and_phase4(self):
        """--phase 1,4 应自动补全 Phase 2 和 Phase 3。"""
        assert parse_phases("1,4") == {1, 2, 3, 4}

    def test_empty_string_returns_all(self):
        """空字符串返回所有 Phase (1-4)。"""
        assert parse_phases("") == {1, 2, 3, 4}

    def test_none_returns_all(self):
        """None 返回所有 Phase (1-4)。"""
        assert parse_phases(None) == {1, 2, 3, 4}

    def test_phase2_always_includes_phase1(self):
        """Phase 2 需要 Phase 1 的结果。"""
        assert parse_phases("2") == {1, 2}

    def test_duplicate_phases(self):
        """重复的 Phase 编号应去重。"""
        assert parse_phases("1,1,2,2") == {1, 2}

    def test_invalid_phase_number_ignored(self):
        """无效的 Phase 编号应被忽略。"""
        assert parse_phases("1,5,9") == {1}

    def test_spaces_in_input(self):
        """输入中的空格应被正确处理。"""
        assert parse_phases("1, 3") == {1, 2, 3}
