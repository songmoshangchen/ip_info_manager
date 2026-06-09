from collections import OrderedDict

import pytest

from ip_info.processors.classifier.engine import IPClassifier

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def basic_rules():
    """基础规则：包含 suffix / contains 两种匹配类型。"""
    return OrderedDict(
        {
            "cloud_provider": {
                "label": "云服务商",
                "description": "公有云/私有云主机",
                "need_deep_query": True,
                "_source": "builtin",
                "patterns": [
                    {"field": "rdns_ptr.hostname", "match": ".amazonaws.com", "type": "suffix", "note": "AWS"},
                    {"field": "ipinfo_api.as_name", "match": "Amazon", "type": "contains", "note": "AWS"},
                ],
            },
            "cdn": {
                "label": "CDN/WAF",
                "description": "CDN节点",
                "need_deep_query": False,
                "_source": "builtin",
                "patterns": [
                    {"field": "rdns_ptr.hostname", "match": ".cloudflare.com", "type": "suffix", "note": "Cloudflare"},
                ],
            },
        }
    )


@pytest.fixture
def classifier(basic_rules):
    return IPClassifier(basic_rules)


@pytest.fixture
def all_type_rules():
    """包含全部 5 种匹配类型的规则。"""
    return OrderedDict(
        {
            "test_cat": {
                "label": "测试",
                "description": "测试匹配类型",
                "_source": "builtin",
                "patterns": [
                    {"field": "data.value", "match": ".com", "type": "suffix"},
                    {"field": "data.value", "match": "test", "type": "contains"},
                    {"field": "data.value", "match": "hello", "type": "prefix"},
                    {"field": "data.value", "match": "exact_match", "type": "exact"},
                    {"field": "data.value", "match": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", "type": "regex"},
                ],
            },
        }
    )


@pytest.fixture
def all_type_classifier(all_type_rules):
    return IPClassifier(all_type_rules)


# ---------------------------------------------------------------------------
# Test: suffix / contains / prefix / exact / regex 匹配
# ---------------------------------------------------------------------------


class TestClassifyMatchTypes:
    """classify() 五种匹配类型的基本测试。"""

    def test_suffix_match(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "ec2-1-2-3-4.amazonaws.com"}}
        result = classifier.classify(ip_data)
        assert result["category"] == "cloud_provider"
        assert result["matched_by"][0]["type"] == "suffix"

    def test_contains_match(self, classifier):
        ip_data = {"ipinfo_api": {"as_name": "Amazon.com, Inc."}}
        result = classifier.classify(ip_data)
        assert result["category"] == "cloud_provider"
        assert result["matched_by"][0]["type"] == "contains"

    def test_prefix_match(self, all_type_classifier):
        ip_data = {"data": {"value": "hello_world"}}
        result = all_type_classifier.classify(ip_data)
        assert result["category"] == "test_cat"
        assert result["matched_by"][0]["type"] == "prefix"

    def test_exact_match(self, all_type_classifier):
        ip_data = {"data": {"value": "exact_match"}}
        result = all_type_classifier.classify(ip_data)
        assert result["category"] == "test_cat"
        assert result["matched_by"][0]["type"] == "exact"

    def test_regex_match(self, all_type_classifier):
        ip_data = {"data": {"value": "192.168.1.1"}}
        result = all_type_classifier.classify(ip_data)
        assert result["category"] == "test_cat"
        assert result["matched_by"][0]["type"] == "regex"


# ---------------------------------------------------------------------------
# Test: 无匹配 / other
# ---------------------------------------------------------------------------


class TestClassifyNoMatch:
    def test_no_match_returns_other(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "unknown.example.com"}}
        result = classifier.classify(ip_data)
        assert result["category"] == "other"
        assert result["label"] == "其他"
        assert result["matched_by"] == []

    def test_empty_ip_data_returns_other(self, classifier):
        result = classifier.classify({})
        assert result["category"] == "other"

    def test_missing_intermediate_field_returns_other(self, classifier):
        ip_data = {"other_channel": {"data": "value"}}
        result = classifier.classify(ip_data)
        assert result["category"] == "other"

    def test_field_value_is_none_returns_other(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": None}}
        result = classifier.classify(ip_data)
        assert result["category"] == "other"


# ---------------------------------------------------------------------------
# Test: first-match 策略
# ---------------------------------------------------------------------------


class TestClassifyFirstMatch:
    def test_first_matching_rule_wins(self, classifier):
        """同时匹配多条规则时，先出现的规则优先。"""
        ip_data = {
            "rdns_ptr": {"hostname": "ec2.amazonaws.com"},
            "ipinfo_api": {"as_name": "Amazon AWS"},
        }
        result = classifier.classify(ip_data)
        assert result["category"] == "cloud_provider"
        assert len(result["matched_by"]) == 1
        # suffix 规则排在 contains 之前，应命中 suffix
        assert result["matched_by"][0]["type"] == "suffix"

    def test_first_category_wins_over_second(self, classifier):
        """同一 ip_data 匹配多个 category 时，先出现的 category 优先。"""
        ip_data = {
            "rdns_ptr": {"hostname": "ec2.amazonaws.com"},
        }
        # cloud_provider 的 suffix 规则先匹配，不会落到 cdn
        result = classifier.classify(ip_data)
        assert result["category"] == "cloud_provider"


# ---------------------------------------------------------------------------
# Test: 大小写不敏感
# ---------------------------------------------------------------------------


class TestClassifyCaseInsensitive:
    def test_case_insensitive_contains(self, classifier):
        ip_data = {"ipinfo_api": {"as_name": "AMAZON.COM"}}
        result = classifier.classify(ip_data)
        assert result["category"] == "cloud_provider"

    def test_case_insensitive_suffix(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "EC2-1-2-3-4.AMAZONAWS.COM"}}
        result = classifier.classify(ip_data)
        assert result["category"] == "cloud_provider"


# ---------------------------------------------------------------------------
# Test: 嵌套字段路径提取
# ---------------------------------------------------------------------------


class TestClassifyFieldExtraction:
    def test_nested_field_path(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "ec2.amazonaws.com"}}
        result = classifier.classify(ip_data)
        assert result["category"] == "cloud_provider"

    def test_deeply_nested_field(self):
        rules = OrderedDict(
            {
                "deep": {
                    "label": "深层",
                    "description": "",
                    "patterns": [
                        {"field": "a.b.c", "match": "target", "type": "contains"},
                    ],
                },
            }
        )
        clf = IPClassifier(rules)
        result = clf.classify({"a": {"b": {"c": "target_value"}}})
        assert result["category"] == "deep"

    def test_non_dict_intermediate_returns_other(self):
        """中间字段不是 dict 时应返回 other。"""
        rules = OrderedDict(
            {
                "cat": {
                    "label": "L",
                    "description": "",
                    "patterns": [
                        {"field": "a.b", "match": "x", "type": "contains"},
                    ],
                },
            }
        )
        clf = IPClassifier(rules)
        # a 是字符串而非 dict，无法提取 a.b
        result = clf.classify({"a": "not_a_dict"})
        assert result["category"] == "other"


# ---------------------------------------------------------------------------
# Test: 默认 type 为 contains
# ---------------------------------------------------------------------------


class TestClassifyDefaultType:
    def test_missing_type_defaults_to_contains(self):
        rules = OrderedDict(
            {
                "default_type": {
                    "label": "默认类型",
                    "description": "",
                    "patterns": [
                        {"field": "data.v", "match": "hello"},
                    ],
                },
            }
        )
        clf = IPClassifier(rules)
        result = clf.classify({"data": {"v": "say hello world"}})
        assert result["category"] == "default_type"
        assert result["matched_by"][0]["type"] == "contains"


# ---------------------------------------------------------------------------
# Test: 返回值格式
# ---------------------------------------------------------------------------


class TestClassifyReturnFormat:
    def test_return_keys(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "ec2.amazonaws.com"}}
        result = classifier.classify(ip_data)
        expected_keys = {"category", "label", "description", "matched_by", "need_deep_query", "classify_time"}
        assert set(result.keys()) == expected_keys

    def test_matched_by_entry_keys(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "ec2.amazonaws.com"}}
        result = classifier.classify(ip_data)
        entry = result["matched_by"][0]
        expected_keys = {"rule_source", "field", "pattern", "type", "value", "note"}
        assert set(entry.keys()) == expected_keys

    def test_matched_by_rule_source_from_cat_def(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "ec2.amazonaws.com"}}
        result = classifier.classify(ip_data)
        assert result["matched_by"][0]["rule_source"] == "builtin"

    def test_matched_by_value_is_string(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "ec2.amazonaws.com"}}
        result = classifier.classify(ip_data)
        assert isinstance(result["matched_by"][0]["value"], str)
        assert result["matched_by"][0]["value"] == "ec2.amazonaws.com"

    def test_matched_by_pattern_field(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "ec2.amazonaws.com"}}
        result = classifier.classify(ip_data)
        entry = result["matched_by"][0]
        assert entry["field"] == "rdns_ptr.hostname"
        assert entry["pattern"] == ".amazonaws.com"

    def test_no_match_return_format(self, classifier):
        result = classifier.classify({})
        assert result["category"] == "other"
        assert result["label"] == "其他"
        assert result["description"] == "未匹配任何已知规则"
        assert result["matched_by"] == []
        assert result["need_deep_query"] is False
        assert "classify_time" in result

    def test_classify_time_is_iso_format(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "ec2.amazonaws.com"}}
        result = classifier.classify(ip_data)
        # 验证 classify_time 可以被 isoformat 解析
        from datetime import datetime

        datetime.fromisoformat(result["classify_time"])

    def test_need_deep_query_from_cat_def(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "cdn.cloudflare.com"}}
        result = classifier.classify(ip_data)
        assert result["need_deep_query"] is False

    def test_default_rule_source_is_builtin(self):
        """规则定义中没有 _source 时，默认为 builtin。"""
        rules = OrderedDict(
            {
                "cat": {
                    "label": "L",
                    "description": "",
                    "patterns": [
                        {"field": "x", "match": "val", "type": "contains"},
                    ],
                },
            }
        )
        clf = IPClassifier(rules)
        result = clf.classify({"x": "val"})
        assert result["matched_by"][0]["rule_source"] == "builtin"


# ---------------------------------------------------------------------------
# Test: categories / rule_count 属性
# ---------------------------------------------------------------------------


class TestIPClassifierProperties:
    def test_categories(self, classifier):
        assert classifier.categories == ["cloud_provider", "cdn"]

    def test_rule_count(self, classifier):
        # cloud_provider: 2 patterns, cdn: 1 pattern
        assert classifier.rule_count == 3

    def test_empty_rules(self):
        clf = IPClassifier(OrderedDict())
        assert clf.categories == []
        assert clf.rule_count == 0


# ---------------------------------------------------------------------------
# Test: _extract_field / _match_pattern 通过 classify() 公开接口间接覆盖
# ---------------------------------------------------------------------------


class TestExtractFieldViaClassify:
    def _make_classifier(self, field, match_str, match_type="contains"):
        rules = OrderedDict(
            {
                "test_cat": {
                    "label": "Test",
                    "patterns": [{"field": field, "match": match_str, "type": match_type}],
                }
            }
        )
        return IPClassifier(rules)

    def test_simple_field(self):
        clf = self._make_classifier("a", "1")
        result = clf.classify({"a": 1})
        assert result["category"] == "test_cat"

    def test_nested_field(self):
        clf = self._make_classifier("a.b", "2")
        result = clf.classify({"a": {"b": 2}})
        assert result["category"] == "test_cat"

    def test_missing_field(self):
        clf = self._make_classifier("b", "1")
        result = clf.classify({"a": 1})
        assert result["category"] == "other"

    def test_missing_nested_field(self):
        clf = self._make_classifier("a.c", "1")
        result = clf.classify({"a": {"b": 1}})
        assert result["category"] == "other"

    def test_non_dict_intermediate(self):
        clf = self._make_classifier("a.b", "x")
        result = clf.classify({"a": "str"})
        assert result["category"] == "other"

    def test_none_value(self):
        clf = self._make_classifier("a.b", "x")
        result = clf.classify({"a": None})
        assert result["category"] == "other"

    def test_deeply_nested(self):
        clf = self._make_classifier("a.b.c.d", "deep")
        result = clf.classify({"a": {"b": {"c": {"d": "deep"}}}})
        assert result["category"] == "test_cat"


class TestMatchPatternViaClassify:
    def _make_classifier(self, match_str, match_type="contains"):
        rules = OrderedDict(
            {
                "matched": {
                    "label": "Matched",
                    "patterns": [{"field": "ptr", "match": match_str, "type": match_type}],
                }
            }
        )
        return IPClassifier(rules)

    def test_suffix_match(self):
        clf = self._make_classifier(".com", "suffix")
        result = clf.classify({"ptr": "example.com"})
        assert result["category"] == "matched"

    def test_suffix_no_match(self):
        clf = self._make_classifier(".com", "suffix")
        result = clf.classify({"ptr": "example.org"})
        assert result["category"] == "other"

    def test_contains_match(self):
        clf = self._make_classifier("world")
        result = clf.classify({"ptr": "hello world"})
        assert result["category"] == "matched"

    def test_contains_no_match(self):
        clf = self._make_classifier("world")
        result = clf.classify({"ptr": "hello"})
        assert result["category"] == "other"

    def test_prefix_match(self):
        clf = self._make_classifier("hello", "prefix")
        result = clf.classify({"ptr": "hello_world"})
        assert result["category"] == "matched"

    def test_prefix_no_match(self):
        clf = self._make_classifier("hello", "prefix")
        result = clf.classify({"ptr": "world_hello"})
        assert result["category"] == "other"

    def test_exact_match(self):
        clf = self._make_classifier("exact_match", "exact")
        result = clf.classify({"ptr": "exact_match"})
        assert result["category"] == "matched"

    def test_exact_no_match(self):
        clf = self._make_classifier("exact_match", "exact")
        result = clf.classify({"ptr": "exact_match_extra"})
        assert result["category"] == "other"

    def test_regex_match(self):
        clf = self._make_classifier(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", "regex")
        result = clf.classify({"ptr": "192.168.1.1"})
        assert result["category"] == "matched"

    def test_regex_no_match(self):
        clf = self._make_classifier(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", "regex")
        result = clf.classify({"ptr": "not_an_ip"})
        assert result["category"] == "other"

    def test_case_insensitive(self):
        clf = self._make_classifier("hello")
        result = clf.classify({"ptr": "HELLO"})
        assert result["category"] == "matched"

    def test_none_field_value(self):
        clf = self._make_classifier("hello")
        result = clf.classify({"ptr": None})
        assert result["category"] == "other"

    def test_default_type_is_contains(self):
        clf = self._make_classifier("world")
        result = clf.classify({"ptr": "hello world"})
        assert result["category"] == "matched"

    def test_unknown_type_returns_false(self):
        clf = self._make_classifier("hello", "unknown")
        result = clf.classify({"ptr": "hello"})
        assert result["category"] == "other"
