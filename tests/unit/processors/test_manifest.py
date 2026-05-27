import json

import pytest

from ip_info.processors.tagger.manifest import load_manifest, validate_manifest


def _write_manifest(path, data):
    """辅助函数：写入 manifest JSON 文件。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


class TestLoadManifest:
    """load_manifest 函数测试。"""

    def test_normal_loading_returns_list_of_dicts(self, tmp_path):
        """正常加载返回字典列表。"""
        manifest_data = [
            {"file": "a.ipset", "label": "标签A", "level": 1},
            {"file": "b.ipset", "label": "标签B", "level": 2},
        ]
        manifest_path = tmp_path / "manifest.json"
        _write_manifest(manifest_path, manifest_data)

        result = load_manifest(str(manifest_path))

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["label"] == "标签A"
        assert result[1]["label"] == "标签B"

    def test_level_filtering_only_returns_items_with_level_le_given(self, tmp_path):
        """level 过滤：仅返回 level <= 给定值的条目。"""
        manifest_data = [
            {"file": "a.ipset", "label": "标签A", "level": 1},
            {"file": "b.ipset", "label": "标签B", "level": 2},
            {"file": "c.ipset", "label": "标签C", "level": 3},
        ]
        manifest_path = tmp_path / "manifest.json"
        _write_manifest(manifest_path, manifest_data)

        result = load_manifest(str(manifest_path), level=2)

        assert len(result) == 2
        assert all(item["level"] <= 2 for item in result)
        labels = [item["label"] for item in result]
        assert "标签A" in labels
        assert "标签B" in labels
        assert "标签C" not in labels

    def test_level_none_returns_all_items(self, tmp_path):
        """level=None 返回所有条目。"""
        manifest_data = [
            {"file": "a.ipset", "label": "标签A", "level": 1},
            {"file": "b.ipset", "label": "标签B", "level": 3},
        ]
        manifest_path = tmp_path / "manifest.json"
        _write_manifest(manifest_path, manifest_data)

        result = load_manifest(str(manifest_path), level=None)

        assert len(result) == 2

    def test_duplicate_label_raises_value_error(self, tmp_path):
        """重复标签名抛出 ValueError，包含重复名称。"""
        manifest_data = [
            {"file": "a.ipset", "label": "重复标签", "level": 1},
            {"file": "b.ipset", "label": "重复标签", "level": 2},
        ]
        manifest_path = tmp_path / "manifest.json"
        _write_manifest(manifest_path, manifest_data)

        with pytest.raises(ValueError, match="重复标签"):
            load_manifest(str(manifest_path))

    def test_missing_manifest_file_raises_file_not_found_error(self, tmp_path):
        """manifest 文件不存在抛出 FileNotFoundError。"""
        missing_path = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError, match="清单文件不存在"):
            load_manifest(str(missing_path))

    def test_item_without_level_defaults_to_1(self, tmp_path):
        """没有 level 字段的条目默认为 1，level 过滤时按默认值处理。"""
        manifest_data = [
            {"file": "a.ipset", "label": "标签A"},
            {"file": "b.ipset", "label": "标签B", "level": 2},
        ]
        manifest_path = tmp_path / "manifest.json"
        _write_manifest(manifest_path, manifest_data)

        result = load_manifest(str(manifest_path), level=1)

        assert len(result) == 1
        assert result[0]["label"] == "标签A"


class TestValidateManifest:
    """validate_manifest 函数测试。"""

    def test_all_files_present_no_exception(self, tmp_path):
        """所有文件都存在时不抛异常。"""
        manifest_data = [
            {"file": "a.ipset", "label": "标签A", "level": 1},
            {"file": "b.ipset", "label": "标签B", "level": 2},
        ]
        # 创建配置文件
        (tmp_path / "a.ipset").write_text("1.2.3.4", encoding="utf-8")
        (tmp_path / "b.ipset").write_text("5.6.7.8", encoding="utf-8")

        validate_manifest(manifest_data, str(tmp_path))
        # 无异常即通过

    def test_missing_files_raises_file_not_found_error_with_names(self, tmp_path):
        """缺失文件时抛出 FileNotFoundError，包含缺失文件名。"""
        manifest_data = [
            {"file": "a.ipset", "label": "标签A", "level": 1},
            {"file": "missing.ipset", "label": "缺失标签", "level": 2},
        ]
        # 只创建 a.ipset
        (tmp_path / "a.ipset").write_text("1.2.3.4", encoding="utf-8")

        with pytest.raises(FileNotFoundError, match="missing.ipset"):
            validate_manifest(manifest_data, str(tmp_path))

    def test_multiple_missing_files_all_listed(self, tmp_path):
        """多个文件缺失时，错误信息包含所有缺失文件名。"""
        manifest_data = [
            {"file": "missing1.ipset", "label": "缺失1", "level": 1},
            {"file": "missing2.ipset", "label": "缺失2", "level": 2},
        ]

        with pytest.raises(FileNotFoundError, match="missing1.ipset") as exc_info:
            validate_manifest(manifest_data, str(tmp_path))

        assert "missing2.ipset" in str(exc_info.value)

    def test_empty_manifest_no_exception(self, tmp_path):
        """空 manifest 列表不抛异常。"""
        validate_manifest([], str(tmp_path))
