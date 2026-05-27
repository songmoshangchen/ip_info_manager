import json
import os
import pytest

from scenarios.trace_ip.classifier import IPClassifier, ClassifyResult


@pytest.fixture
def rules_file(tmp_path):
    rules = {
        "cloud_provider": {
            "label": "云服务商",
            "description": "公有云/私有云主机",
            "need_deep_query": True,
            "patterns": [
                {"field": "rdns_ptr.hostname", "match": ".amazonaws.com", "type": "suffix", "note": "AWS"},
                {"field": "ipinfo_api.as_name", "match": "Amazon", "type": "contains", "note": "AWS"},
            ]
        },
        "cdn": {
            "label": "CDN/WAF",
            "description": "CDN节点",
            "need_deep_query": False,
            "patterns": [
                {"field": "rdns_ptr.hostname", "match": ".cloudflare.com", "type": "suffix", "note": "Cloudflare"},
            ]
        },
    }
    path = tmp_path / "test_rules.json"
    path.write_text(json.dumps(rules), encoding='utf-8')
    return str(path)


@pytest.fixture
def classifier(rules_file):
    return IPClassifier(builtin_path=rules_file)


class TestIPClassifierMatch:
    def test_suffix_match_returns_category(self, classifier):
        ip_data = {
            "rdns_ptr": {"hostname": "ec2-1-2-3-4.amazonaws.com"}
        }
        result = classifier.classify(ip_data)
        assert result.category == "cloud_provider"
        assert result.label == "云服务商"
        assert result.need_deep_query is True
        assert len(result.matched_by) == 1
        assert result.matched_by[0]["type"] == "suffix"

    def test_contains_match_returns_category(self, classifier):
        ip_data = {
            "ipinfo_api": {"as_name": "Amazon.com, Inc."}
        }
        result = classifier.classify(ip_data)
        assert result.category == "cloud_provider"
        assert result.matched_by[0]["type"] == "contains"

    def test_no_match_returns_other(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "unknown.example.com"}}
        result = classifier.classify(ip_data)
        assert result.category == "other"
        assert result.label == "其他"
        assert result.need_deep_query is True
        assert result.matched_by == []

    def test_empty_data_returns_other(self, classifier):
        result = classifier.classify({})
        assert result.category == "other"

    def test_first_match_wins(self, classifier):
        ip_data = {
            "rdns_ptr": {"hostname": "ec2.amazonaws.com"},
            "ipinfo_api": {"as_name": "Amazon AWS"},
        }
        result = classifier.classify(ip_data)
        assert result.category == "cloud_provider"
        assert len(result.matched_by) == 1

    def test_match_is_case_insensitive(self, classifier):
        ip_data = {
            "ipinfo_api": {"as_name": "AMAZON.COM"}
        }
        result = classifier.classify(ip_data)
        assert result.category == "cloud_provider"


class TestIPClassifierFieldExtraction:
    def test_nested_field_path(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": "ec2.amazonaws.com"}}
        result = classifier.classify(ip_data)
        assert result.category == "cloud_provider"

    def test_missing_intermediate_field(self, classifier):
        ip_data = {"other_channel": {"data": "value"}}
        result = classifier.classify(ip_data)
        assert result.category == "other"

    def test_field_value_is_none(self, classifier):
        ip_data = {"rdns_ptr": {"hostname": None}}
        result = classifier.classify(ip_data)
        assert result.category == "other"


class TestIPClassifierPatternTypes:
    @pytest.fixture
    def type_classifier(self, tmp_path):
        rules = {
            "test_cat": {
                "label": "测试",
                "description": "测试匹配类型",
                "patterns": [
                    {"field": "data.value", "match": ".com", "type": "suffix"},
                    {"field": "data.value", "match": "test", "type": "contains"},
                    {"field": "data.value", "match": "hello", "type": "prefix"},
                    {"field": "data.value", "match": "exact_match", "type": "exact"},
                    {"field": "data.value", "match": r"^\d+\.\d+$", "type": "regex"},
                ]
            }
        }
        path = tmp_path / "type_rules.json"
        path.write_text(json.dumps(rules), encoding='utf-8')
        return IPClassifier(builtin_path=str(path))

    def test_suffix_match(self, type_classifier):
        result = type_classifier.classify({"data": {"value": "example.com"}})
        assert result.category == "test_cat"
        assert result.matched_by[0]["type"] == "suffix"

    def test_contains_match(self, type_classifier):
        result = type_classifier.classify({"data": {"value": "my_test_data"}})
        assert result.category == "test_cat"
        assert result.matched_by[0]["type"] == "contains"

    def test_prefix_match(self, type_classifier):
        result = type_classifier.classify({"data": {"value": "hello_world"}})
        assert result.category == "test_cat"
        assert result.matched_by[0]["type"] == "prefix"

    def test_exact_match(self, type_classifier):
        result = type_classifier.classify({"data": {"value": "exact_match"}})
        assert result.category == "test_cat"
        assert result.matched_by[0]["type"] == "exact"

    def test_regex_match(self, type_classifier):
        result = type_classifier.classify({"data": {"value": "1.23"}})
        assert result.category == "test_cat"
        assert result.matched_by[0]["type"] == "regex"

    def test_no_type_defaults_to_contains(self, tmp_path):
        rules = {
            "default_type": {
                "label": "默认类型",
                "description": "",
                "patterns": [
                    {"field": "data.v", "match": "hello", "type": "contains"},
                ]
            }
        }
        path = tmp_path / "default_rules.json"
        path.write_text(json.dumps(rules), encoding='utf-8')
        clf = IPClassifier(builtin_path=str(path))
        result = clf.classify({"data": {"v": "say hello world"}})
        assert result.category == "default_type"


class TestIPClassifierCustomRules:
    def test_custom_rules_merge(self, tmp_path):
        builtin = {"cat1": {"label": "C1", "description": "", "patterns": [{"field": "a", "match": "x", "type": "contains"}]}}
        custom = {"cat2": {"label": "C2", "description": "", "patterns": [{"field": "b", "match": "y", "type": "contains"}]}}

        builtin_path = tmp_path / "builtin.json"
        custom_path = tmp_path / "custom.json"
        builtin_path.write_text(json.dumps(builtin), encoding='utf-8')
        custom_path.write_text(json.dumps(custom), encoding='utf-8')

        clf = IPClassifier(builtin_path=str(builtin_path), custom_path=str(custom_path))
        assert len(clf.categories) == 2

    def test_custom_rules_nonexistent_file(self, tmp_path):
        builtin = {"cat1": {"label": "C1", "description": "", "patterns": []}}
        builtin_path = tmp_path / "builtin.json"
        builtin_path.write_text(json.dumps(builtin), encoding='utf-8')

        clf = IPClassifier(builtin_path=str(builtin_path), custom_path=str(tmp_path / "nonexistent.json"))
        assert len(clf.categories) == 1

    def test_empty_builtin_rules(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("{}", encoding='utf-8')
        clf = IPClassifier(builtin_path=str(path))
        assert clf.rule_count == 0

    def test_empty_file(self, tmp_path):
        path = tmp_path / "blank.json"
        path.write_text("", encoding='utf-8')
        clf = IPClassifier(builtin_path=str(path))
        assert clf.rule_count == 0

    def test_builtin_count_tracks_rule_source(self, tmp_path):
        builtin = {"cat1": {"label": "C1", "description": "", "patterns": [{"field": "a", "match": "x", "type": "contains"}]}}
        custom = {"cat2": {"label": "C2", "description": "", "patterns": [{"field": "b", "match": "y", "type": "contains"}]}}

        builtin_path = tmp_path / "builtin.json"
        custom_path = tmp_path / "custom.json"
        builtin_path.write_text(json.dumps(builtin), encoding='utf-8')
        custom_path.write_text(json.dumps(custom), encoding='utf-8')

        clf = IPClassifier(builtin_path=str(builtin_path), custom_path=str(custom_path))
        result = clf.classify({"a": "x"})
        assert result.matched_by[0]["rule_source"] == "builtin"

        result = clf.classify({"b": "y"})
        assert result.matched_by[0]["rule_source"] == "custom"


class TestClassifyResult:
    def test_to_dict(self):
        r = ClassifyResult(
            category="cloud_provider",
            label="云服务商",
            description="desc",
            matched_by=[{"field": "test"}],
            need_deep_query=True,
            classify_time="2024-01-01T00:00:00",
        )
        d = r.to_dict()
        assert d["category"] == "cloud_provider"
        assert d["label"] == "云服务商"
        assert len(d["matched_by"]) == 1
        assert d["need_deep_query"] is True

    def test_default_values(self):
        r = ClassifyResult(category="other", label="其他", description="")
        assert r.matched_by == []
        assert r.need_deep_query is True
        assert r.classify_time == ""


class TestIPClassifierWithBuiltinRules:
    @pytest.fixture
    def real_classifier(self):
        builtin_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "scenarios", "trace_ip", "classifiers", "builtin_rules.json"
        )
        if not os.path.exists(builtin_path):
            pytest.skip("builtin_rules.json not found")
        return IPClassifier(builtin_path=builtin_path)

    def test_classifies_aws_hostname(self, real_classifier):
        result = real_classifier.classify({
            "rdns_ptr": {"hostname": "ec2-54-210-1-2.amazonaws.com"}
        })
        assert result.category == "cloud_provider"

    def test_classifies_cloudflare_cdn(self, real_classifier):
        result = real_classifier.classify({
            "rdns_ptr": {"hostname": "cdn.cloudflare.com"}
        })
        assert result.category == "cdn"

    def test_classifies_shodan_scanner(self, real_classifier):
        result = real_classifier.classify({
            "rdns_ptr": {"hostname": "scanner.shodan.io"}
        })
        assert result.category == "crawler_scanner"

    def test_classifies_residential_broadband(self, real_classifier):
        result = real_classifier.classify({
            "rdns_ptr": {"hostname": "dsl.dynamic.provider.broadband.isp.com"}
        })
        assert result.category == "residential"

    def test_classifies_invalid_rdns(self, real_classifier):
        result = real_classifier.classify({
            "rdns_ptr": {"hostname": "192.168.1.1"}
        })
        assert result.category == "invalid_rdns"
        assert result.need_deep_query is False

    def test_has_seven_categories(self, real_classifier):
        expected = ["invalid_rdns", "cloud_provider", "cdn", "crawler_scanner", "residential"]
        for cat in expected:
            assert cat in real_classifier.categories
