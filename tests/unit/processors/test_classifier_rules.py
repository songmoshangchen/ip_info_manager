import json
from collections import OrderedDict

from ip_info.processors.classifier.rules import load_rules


def _write_json(path, data):
    """辅助函数：写入 JSON 文件。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


class TestLoadRules:
    """load_rules 函数测试。"""

    def test_normal_loading_returns_ordered_dict_with_builtin_rules(self, tmp_path):
        """正常加载返回 OrderedDict，包含 builtin 规则。"""
        builtin_data = {
            "cloud_provider": {
                "label": "云服务商",
                "description": "公有云/私有云主机",
                "patterns": [{"field": "rdns_ptr.hostname", "match": ".amazonaws.com", "type": "suffix"}],
            },
            "cdn": {
                "label": "CDN/WAF",
                "description": "CDN或WAF节点",
                "patterns": [{"field": "rdns_ptr.hostname", "match": ".cloudflare.com", "type": "suffix"}],
            },
        }
        builtin_path = tmp_path / "builtin_rules.json"
        _write_json(builtin_path, builtin_data)

        result = load_rules(str(builtin_path))

        assert isinstance(result, OrderedDict)
        assert len(result) == 2
        assert list(result.keys()) == ["cloud_provider", "cdn"]

    def test_builtin_rules_have_source_field(self, tmp_path):
        """builtin 规则条目包含 _source 字段，值为 "builtin"。"""
        builtin_data = {
            "cloud_provider": {"label": "云服务商", "patterns": []},
        }
        builtin_path = tmp_path / "builtin_rules.json"
        _write_json(builtin_path, builtin_data)

        result = load_rules(str(builtin_path))

        assert result["cloud_provider"]["_source"] == "builtin"

    def test_custom_rules_merge_after_builtin(self, tmp_path):
        """custom 规则合并到 builtin 规则之后。"""
        builtin_data = {
            "cloud_provider": {"label": "云服务商", "patterns": []},
        }
        custom_data = {
            "excluded_domain": {"label": "排除域名", "patterns": []},
        }
        builtin_path = tmp_path / "builtin_rules.json"
        custom_path = tmp_path / "custom_rules.json"
        _write_json(builtin_path, builtin_data)
        _write_json(custom_path, custom_data)

        result = load_rules(str(builtin_path), str(custom_path))

        assert list(result.keys()) == ["cloud_provider", "excluded_domain"]
        assert result["cloud_provider"]["_source"] == "builtin"
        assert result["excluded_domain"]["_source"] == "custom"

    def test_custom_file_not_found_returns_builtin_only(self, tmp_path):
        """custom 文件不存在时，仅返回 builtin 规则，不报错。"""
        builtin_data = {
            "cloud_provider": {"label": "云服务商", "patterns": []},
        }
        builtin_path = tmp_path / "builtin_rules.json"
        _write_json(builtin_path, builtin_data)
        missing_custom = str(tmp_path / "nonexistent.json")

        result = load_rules(str(builtin_path), missing_custom)

        assert len(result) == 1
        assert "cloud_provider" in result

    def test_custom_path_none_returns_builtin_only(self, tmp_path):
        """custom_path 为 None 时，仅返回 builtin 规则。"""
        builtin_data = {
            "cdn": {"label": "CDN/WAF", "patterns": []},
        }
        builtin_path = tmp_path / "builtin_rules.json"
        _write_json(builtin_path, builtin_data)

        result = load_rules(str(builtin_path), None)

        assert len(result) == 1
        assert "cdn" in result

    def test_empty_builtin_file_returns_empty_ordered_dict(self, tmp_path):
        """空的 builtin 文件返回空 OrderedDict。"""
        builtin_path = tmp_path / "builtin_rules.json"
        builtin_path.write_text("", encoding="utf-8")

        result = load_rules(str(builtin_path))

        assert isinstance(result, OrderedDict)
        assert len(result) == 0

    def test_empty_custom_file_returns_builtin_only(self, tmp_path):
        """空的 custom 文件：仅返回 builtin 规则。"""
        builtin_data = {
            "cloud_provider": {"label": "云服务商", "patterns": []},
        }
        builtin_path = tmp_path / "builtin_rules.json"
        custom_path = tmp_path / "custom_rules.json"
        _write_json(builtin_path, builtin_data)
        custom_path.write_text("", encoding="utf-8")

        result = load_rules(str(builtin_path), str(custom_path))

        assert len(result) == 1
        assert "cloud_provider" in result

    def test_custom_key_overrides_builtin_with_custom_source(self, tmp_path):
        """当 custom 和 builtin 有相同 key 时，custom 覆盖 builtin，_source 为 "custom"。"""
        builtin_data = {
            "cloud_provider": {"label": "云服务商（旧）", "patterns": [{"field": "a", "match": "x"}]},
        }
        custom_data = {
            "cloud_provider": {"label": "云服务商（新）", "patterns": [{"field": "b", "match": "y"}]},
        }
        builtin_path = tmp_path / "builtin_rules.json"
        custom_path = tmp_path / "custom_rules.json"
        _write_json(builtin_path, builtin_data)
        _write_json(custom_path, custom_data)

        result = load_rules(str(builtin_path), str(custom_path))

        assert len(result) == 1
        assert result["cloud_provider"]["_source"] == "custom"
        assert result["cloud_provider"]["label"] == "云服务商（新）"

    def test_preserves_insertion_order(self, tmp_path):
        """合并后保持插入顺序（builtin 在前，custom 在后）。"""
        builtin_data = OrderedDict(
            [
                ("cat_a", {"label": "A", "patterns": []}),
                ("cat_b", {"label": "B", "patterns": []}),
            ]
        )
        custom_data = OrderedDict(
            [
                ("cat_c", {"label": "C", "patterns": []}),
                ("cat_d", {"label": "D", "patterns": []}),
            ]
        )
        builtin_path = tmp_path / "builtin_rules.json"
        custom_path = tmp_path / "custom_rules.json"
        _write_json(builtin_path, builtin_data)
        _write_json(custom_path, custom_data)

        result = load_rules(str(builtin_path), str(custom_path))

        assert list(result.keys()) == ["cat_a", "cat_b", "cat_c", "cat_d"]
