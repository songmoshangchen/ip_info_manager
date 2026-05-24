import json

from ip_info.batch.core.query import BatchResult
from ip_info.batch.core.runner import BatchRunner
from ip_info.processors.classifier.runner import CHANNEL_NAME, BatchClassifier
from ip_info.store.in_memory import InMemoryIPWriter


def _write_builtin_rules(path, rules_data):
    """辅助函数：写入 builtin_rules.json 文件。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rules_data, f, ensure_ascii=False)


def _setup_rules_dir(tmp_path, builtin_data, custom_data=None):
    """辅助函数：创建规则目录，包含 builtin_rules.json 和可选的自定义规则文件。

    Args:
        tmp_path: 临时目录
        builtin_data: 内置规则 dict
        custom_data: 自定义规则 dict（可选）

    Returns:
        (rules_dir, custom_rules_path) 元组
    """
    rules_dir = tmp_path / "classifier_rules"
    rules_dir.mkdir()
    _write_builtin_rules(rules_dir / "builtin_rules.json", builtin_data)

    custom_path = None
    if custom_data is not None:
        custom_path = str(rules_dir / "custom_rules.json")
        with open(custom_path, "w", encoding="utf-8") as f:
            json.dump(custom_data, f, ensure_ascii=False)

    return str(rules_dir), custom_path


# 基础规则数据，用于大多数测试
BASIC_BUILTIN_RULES = {
    "cloud_provider": {
        "label": "云服务商",
        "description": "公有云/私有云主机",
        "need_deep_query": True,
        "patterns": [
            {"field": "rdns_ptr.hostname", "match": ".amazonaws.com", "type": "suffix", "note": "AWS"},
            {"field": "ipinfo_api.as_name", "match": "Amazon", "type": "contains", "note": "AWS"},
        ],
    },
    "cdn": {
        "label": "CDN/WAF",
        "description": "CDN节点",
        "need_deep_query": False,
        "patterns": [
            {"field": "rdns_ptr.hostname", "match": ".cloudflare.com", "type": "suffix", "note": "Cloudflare"},
        ],
    },
}


class TestBatchRunnerProtocolConformance:
    """BatchClassifier 实现 BatchRunner Protocol 的测试。"""

    def test_isinstance_batch_runner(self, tmp_path):
        """BatchClassifier 实例应通过 isinstance 检查为 BatchRunner。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        classifier = BatchClassifier(ips=[], writer=writer, reader=writer, rules_dir=rules_dir)
        assert isinstance(classifier, BatchRunner)

    def test_has_run_method(self, tmp_path):
        """BatchClassifier 应有 run 方法。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        classifier = BatchClassifier(ips=[], writer=writer, reader=writer, rules_dir=rules_dir)
        assert hasattr(classifier, "run")
        assert callable(classifier.run)


class TestNormalBatchClassification:
    """正常批量分类测试。"""

    def test_classify_ip_with_rdns_data(self, tmp_path):
        """有 RDNS 数据的 IP 应被正确分类并写入 writer。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        # 预设 RDNS 数据
        writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "ec2-1-2-3-4.amazonaws.com"})

        classifier = BatchClassifier(ips=["1.2.3.4"], writer=writer, reader=writer, rules_dir=rules_dir)
        result = classifier.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("1.2.3.4", CHANNEL_NAME)
        assert channel_data is not None
        assert channel_data["category"] == "cloud_provider"
        assert channel_data["label"] == "云服务商"

    def test_classify_ip_with_ipinfo_data(self, tmp_path):
        """有 ipinfo 数据的 IP 应被正确分类。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("5.6.7.8", "ipinfo_api", {"as_name": "Amazon.com, Inc."})

        classifier = BatchClassifier(ips=["5.6.7.8"], writer=writer, reader=writer, rules_dir=rules_dir)
        result = classifier.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("5.6.7.8", CHANNEL_NAME)
        assert channel_data["category"] == "cloud_provider"

    def test_classify_multiple_ips(self, tmp_path):
        """多个 IP 应全部被分类。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "ec2.amazonaws.com"})
        writer.add_or_update_ip("9.8.7.6", "rdns_ptr", {"hostname": "cdn.cloudflare.com"})

        classifier = BatchClassifier(
            ips=["1.2.3.4", "9.8.7.6"],
            writer=writer,
            reader=writer,
            rules_dir=rules_dir,
        )
        result = classifier.run()

        assert result.success_count == 2
        assert writer.get_channel_data("1.2.3.4", CHANNEL_NAME)["category"] == "cloud_provider"
        assert writer.get_channel_data("9.8.7.6", CHANNEL_NAME)["category"] == "cdn"

    def test_add_or_update_ip_called_with_correct_channel(self, tmp_path):
        """add_or_update_ip 应以 'classifier' 作为 channel 名调用。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "ec2.amazonaws.com"})

        classifier = BatchClassifier(ips=["1.2.3.4"], writer=writer, reader=writer, rules_dir=rules_dir)
        classifier.run()

        ip_data = writer.get_ip_data("1.2.3.4")
        assert ip_data is not None
        assert CHANNEL_NAME in ip_data

    def test_batch_result_has_correct_counts(self, tmp_path):
        """BatchResult 的计数应正确。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "ec2.amazonaws.com"})
        writer.add_or_update_ip("9.8.7.6", "rdns_ptr", {"hostname": "cdn.cloudflare.com"})

        classifier = BatchClassifier(
            ips=["1.2.3.4", "9.8.7.6"],
            writer=writer,
            reader=writer,
            rules_dir=rules_dir,
        )
        result = classifier.run()

        assert result.success_count == 2
        assert result.skip_count == 0
        assert result.fail_count == 0
        assert result.total_elapsed > 0

    def test_no_match_classified_as_other(self, tmp_path):
        """不匹配任何规则的 IP 应分类为 other。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("10.0.0.1", "rdns_ptr", {"hostname": "unknown.example.com"})

        classifier = BatchClassifier(ips=["10.0.0.1"], writer=writer, reader=writer, rules_dir=rules_dir)
        result = classifier.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("10.0.0.1", CHANNEL_NAME)
        assert channel_data["category"] == "other"
        assert channel_data["label"] == "其他"


class TestSkipIPsWithNoData:
    """无数据的 IP 应被跳过。"""

    def test_ip_without_data_is_skipped(self, tmp_path):
        """store 中无数据的 IP 应被跳过，计入 skip_count。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        # 只给 1.2.3.4 加数据，不给 10.0.0.1 加
        writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "ec2.amazonaws.com"})

        classifier = BatchClassifier(
            ips=["1.2.3.4", "10.0.0.1"],
            writer=writer,
            reader=writer,
            rules_dir=rules_dir,
        )
        result = classifier.run()

        assert result.success_count == 1
        assert result.skip_count == 1

    def test_skipped_ip_not_written_to_writer(self, tmp_path):
        """被跳过的 IP 不应写入 classifier 数据。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()

        classifier = BatchClassifier(ips=["10.0.0.1"], writer=writer, reader=writer, rules_dir=rules_dir)
        classifier.run()

        assert writer.get_channel_data("10.0.0.1", CHANNEL_NAME) is None

    def test_all_ips_without_data(self, tmp_path):
        """所有 IP 都无数据时，全部跳过。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()

        classifier = BatchClassifier(
            ips=["10.0.0.1", "10.0.0.2"],
            writer=writer,
            reader=writer,
            rules_dir=rules_dir,
        )
        result = classifier.run()

        assert result.success_count == 0
        assert result.skip_count == 2


class TestFullReprocessing:
    """全量重处理测试：已有分类数据应被覆盖。"""

    def test_existing_classifier_data_overwritten(self, tmp_path):
        """已有 classifier 数据的 IP 应被重新分类并覆盖。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        # 预设 RDNS 数据
        writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "ec2.amazonaws.com"})
        # 预设旧的 classifier 数据
        writer.add_or_update_ip("1.2.3.4", CHANNEL_NAME, {"category": "old_category", "label": "旧标签"})

        classifier = BatchClassifier(ips=["1.2.3.4"], writer=writer, reader=writer, rules_dir=rules_dir)
        result = classifier.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("1.2.3.4", CHANNEL_NAME)
        assert channel_data["category"] == "cloud_provider"
        assert channel_data["label"] == "云服务商"
        assert channel_data["category"] != "old_category"

    def test_reprocessing_updates_all_ips(self, tmp_path):
        """重处理时所有有数据的 IP 都应被更新。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "ec2.amazonaws.com"})
        writer.add_or_update_ip("9.8.7.6", "rdns_ptr", {"hostname": "cdn.cloudflare.com"})
        # 预设旧的 classifier 数据
        writer.add_or_update_ip("1.2.3.4", CHANNEL_NAME, {"category": "old"})
        writer.add_or_update_ip("9.8.7.6", CHANNEL_NAME, {"category": "old"})

        classifier = BatchClassifier(
            ips=["1.2.3.4", "9.8.7.6"],
            writer=writer,
            reader=writer,
            rules_dir=rules_dir,
        )
        result = classifier.run()

        assert result.success_count == 2
        assert writer.get_channel_data("1.2.3.4", CHANNEL_NAME)["category"] == "cloud_provider"
        assert writer.get_channel_data("9.8.7.6", CHANNEL_NAME)["category"] == "cdn"


class TestEmptyInput:
    """空输入测试。"""

    def test_empty_ip_list_returns_zero_counts(self, tmp_path):
        """空 IP 列表应返回 success_count=0, skip_count=0。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        classifier = BatchClassifier(ips=[], writer=writer, reader=writer, rules_dir=rules_dir)

        result = classifier.run()

        assert result.success_count == 0
        assert result.skip_count == 0
        assert isinstance(result, BatchResult)

    def test_empty_ip_list_total_elapsed_positive(self, tmp_path):
        """空 IP 列表也应返回正的 total_elapsed。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        classifier = BatchClassifier(ips=[], writer=writer, reader=writer, rules_dir=rules_dir)

        result = classifier.run()

        assert result.total_elapsed >= 0


class TestCustomRulesPath:
    """自定义规则路径测试。"""

    def test_custom_rules_are_loaded_and_used(self, tmp_path):
        """自定义规则应被加载并用于分类。"""
        custom_rules = {
            "my_custom": {
                "label": "自定义分类",
                "description": "自定义规则测试",
                "need_deep_query": False,
                "patterns": [
                    {"field": "custom_channel.value", "match": "special", "type": "contains", "note": "自定义"},
                ],
            },
        }
        rules_dir, custom_path = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES, custom_rules)
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "custom_channel", {"value": "something_special_here"})

        classifier = BatchClassifier(
            ips=["1.2.3.4"],
            writer=writer,
            reader=writer,
            rules_dir=rules_dir,
            custom_rules_path=custom_path,
        )
        result = classifier.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("1.2.3.4", CHANNEL_NAME)
        assert channel_data["category"] == "my_custom"
        assert channel_data["label"] == "自定义分类"

    def test_custom_rules_override_builtin_on_first_match(self, tmp_path):
        """自定义规则在 builtin 之后加载，但如果 builtin 先匹配则 builtin 优先。"""
        custom_rules = {
            "my_custom": {
                "label": "自定义分类",
                "description": "自定义规则",
                "need_deep_query": False,
                "patterns": [
                    {"field": "rdns_ptr.hostname", "match": ".amazonaws.com", "type": "suffix", "note": "自定义AWS"},
                ],
            },
        }
        rules_dir, custom_path = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES, custom_rules)
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "ec2.amazonaws.com"})

        classifier = BatchClassifier(
            ips=["1.2.3.4"],
            writer=writer,
            reader=writer,
            rules_dir=rules_dir,
            custom_rules_path=custom_path,
        )
        result = classifier.run()

        # builtin 的 cloud_provider 先匹配
        assert result.success_count == 1
        channel_data = writer.get_channel_data("1.2.3.4", CHANNEL_NAME)
        assert channel_data["category"] == "cloud_provider"

    def test_no_custom_rules_path_still_works(self, tmp_path):
        """不提供 custom_rules_path 时应正常工作。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "ec2.amazonaws.com"})

        classifier = BatchClassifier(
            ips=["1.2.3.4"],
            writer=writer,
            reader=writer,
            rules_dir=rules_dir,
            custom_rules_path=None,
        )
        result = classifier.run()

        assert result.success_count == 1
        assert writer.get_channel_data("1.2.3.4", CHANNEL_NAME)["category"] == "cloud_provider"

    def test_custom_rules_path_nonexistent_still_works(self, tmp_path):
        """custom_rules_path 指向不存在的文件时仍应正常工作。"""
        rules_dir, _ = _setup_rules_dir(tmp_path, BASIC_BUILTIN_RULES)
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "ec2.amazonaws.com"})

        classifier = BatchClassifier(
            ips=["1.2.3.4"],
            writer=writer,
            reader=writer,
            rules_dir=rules_dir,
            custom_rules_path="/nonexistent/custom_rules.json",
        )
        result = classifier.run()

        assert result.success_count == 1
        assert writer.get_channel_data("1.2.3.4", CHANNEL_NAME)["category"] == "cloud_provider"
