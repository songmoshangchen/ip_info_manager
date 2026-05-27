from ip_info.pipeline.filter_ips import filter_dynamic_ips, filter_ips_by_classification
from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter


class TestFilterDynamicIps:
    def _make_classifier_data(self, category, matched_pattern="", matched_note=""):
        data = {
            "category": category,
            "label": category,
            "need_deep_query": True,
            "matched_by": [],
        }
        if matched_pattern:
            data["matched_by"] = [
                {
                    "field": "rdns_ptr.hostname",
                    "pattern": matched_pattern,
                    "type": "contains",
                    "note": matched_note,
                }
            ]
        return data

    def test_dynamic_ip_detected_by_hostname(self):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip(
            "1.1.1.1",
            "classifier",
            self._make_classifier_data("residential", ".dynamic", "动态 IP"),
        )
        writer.add_or_update_ip(
            "1.1.1.1",
            "rdns_ptr",
            {"hostname": "dynamic-ip-1.example.com"},
        )
        writer.add_or_update_ip(
            "2.2.2.2",
            "classifier",
            self._make_classifier_data("cloud_provider", ".amazonaws.com", "AWS"),
        )
        writer.add_or_update_ip(
            "3.3.3.3",
            "classifier",
            self._make_classifier_data("residential", ".fiber", "光纤接入"),
        )

        reader = InMemoryIPReader(writer.get_all())
        dynamic, non_dynamic = filter_dynamic_ips(["1.1.1.1", "2.2.2.2", "3.3.3.3"], reader)

        assert dynamic == ["1.1.1.1"]
        assert non_dynamic == ["2.2.2.2", "3.3.3.3"]

    def test_dhcp_ip_detected(self):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip(
            "10.0.0.1",
            "classifier",
            self._make_classifier_data("residential", ".dhcp", "DHCP"),
        )

        reader = InMemoryIPReader(writer.get_all())
        dynamic, non_dynamic = filter_dynamic_ips(["10.0.0.1"], reader)

        assert dynamic == ["10.0.0.1"]
        assert non_dynamic == []

    def test_pppoe_ip_detected(self):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip(
            "10.0.0.2",
            "classifier",
            self._make_classifier_data("residential", ".pppoe", "PPPoE"),
        )

        reader = InMemoryIPReader(writer.get_all())
        dynamic, non_dynamic = filter_dynamic_ips(["10.0.0.2"], reader)

        assert dynamic == ["10.0.0.2"]
        assert non_dynamic == []

    def test_broadband_ip_detected(self):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip(
            "10.0.0.3",
            "classifier",
            self._make_classifier_data("residential", ".broadband", "宽带"),
        )

        reader = InMemoryIPReader(writer.get_all())
        dynamic, non_dynamic = filter_dynamic_ips(["10.0.0.3"], reader)

        assert dynamic == ["10.0.0.3"]
        assert non_dynamic == []

    def test_adsl_ip_detected(self):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip(
            "10.0.0.4",
            "classifier",
            self._make_classifier_data("residential", ".adsl", "ADSL"),
        )

        reader = InMemoryIPReader(writer.get_all())
        dynamic, non_dynamic = filter_dynamic_ips(["10.0.0.4"], reader)

        assert dynamic == ["10.0.0.4"]
        assert non_dynamic == []

    def test_cloud_provider_not_dynamic(self):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip(
            "1.2.3.4",
            "classifier",
            self._make_classifier_data("cloud_provider", ".amazonaws.com", "AWS"),
        )

        reader = InMemoryIPReader(writer.get_all())
        dynamic, non_dynamic = filter_dynamic_ips(["1.2.3.4"], reader)

        assert dynamic == []
        assert non_dynamic == ["1.2.3.4"]

    def test_residential_fiber_not_dynamic(self):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip(
            "5.5.5.5",
            "classifier",
            self._make_classifier_data("residential", ".fiber", "光纤接入"),
        )

        reader = InMemoryIPReader(writer.get_all())
        dynamic, non_dynamic = filter_dynamic_ips(["5.5.5.5"], reader)

        assert dynamic == []
        assert non_dynamic == ["5.5.5.5"]

    def test_no_classifier_data_not_dynamic(self):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip("6.6.6.6", "rdns_ptr", {"hostname": "host.example.com"})

        reader = InMemoryIPReader(writer.get_all())
        dynamic, non_dynamic = filter_dynamic_ips(["6.6.6.6"], reader)

        assert dynamic == []
        assert non_dynamic == ["6.6.6.6"]

    def test_mixed_ips(self):
        writer = InMemoryIPWriter()
        writer.add_or_update_ip(
            "1.1.1.1",
            "classifier",
            self._make_classifier_data("residential", ".dhcp", "DHCP"),
        )
        writer.add_or_update_ip(
            "2.2.2.2",
            "classifier",
            self._make_classifier_data("cloud_provider", ".amazonaws.com", "AWS"),
        )
        writer.add_or_update_ip(
            "3.3.3.3",
            "classifier",
            self._make_classifier_data("residential", ".dynamic", "动态IP"),
        )
        writer.add_or_update_ip(
            "4.4.4.4",
            "classifier",
            self._make_classifier_data("residential", ".fiber", "光纤"),
        )

        reader = InMemoryIPReader(writer.get_all())
        dynamic, non_dynamic = filter_dynamic_ips(["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"], reader)

        assert dynamic == ["1.1.1.1", "3.3.3.3"]
        assert non_dynamic == ["2.2.2.2", "4.4.4.4"]

    def test_empty_ips(self):
        reader = InMemoryIPReader({})
        dynamic, non_dynamic = filter_dynamic_ips([], reader)

        assert dynamic == []
        assert non_dynamic == []


class TestFilterIpsByClassification:
    """filter_ips_by_classification 函数测试"""

    def test_normal_filter_keeps_deep_query_ips(self):
        """正常过滤：cdn 被过滤，cloud_provider 和 other 保留"""
        writer = InMemoryIPWriter()
        writer.add_or_update_ip(
            "1.1.1.1",
            "classifier",
            {
                "category": "cdn",
                "label": "CDN/WAF",
                "need_deep_query": False,
            },
        )
        writer.add_or_update_ip(
            "2.2.2.2",
            "classifier",
            {
                "category": "cloud_provider",
                "label": "云服务商",
                "need_deep_query": True,
            },
        )
        writer.add_or_update_ip(
            "3.3.3.3",
            "classifier",
            {
                "category": "other",
                "label": "其他",
                "need_deep_query": True,
            },
        )

        reader = InMemoryIPReader(writer.get_all())
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        result = filter_ips_by_classification(ips, reader)

        assert result == ["2.2.2.2", "3.3.3.3"]

    def test_all_filtered_returns_empty(self):
        """全部被过滤：invalid_rdns/cdn/crawler_scanner 全部 need_deep_query=False"""
        writer = InMemoryIPWriter()
        writer.add_or_update_ip(
            "1.1.1.1",
            "classifier",
            {
                "category": "invalid_rdns",
                "label": "无效RDNS",
                "need_deep_query": False,
            },
        )
        writer.add_or_update_ip(
            "2.2.2.2",
            "classifier",
            {
                "category": "cdn",
                "label": "CDN/WAF",
                "need_deep_query": False,
            },
        )
        writer.add_or_update_ip(
            "3.3.3.3",
            "classifier",
            {
                "category": "crawler_scanner",
                "label": "爬虫/扫描器",
                "need_deep_query": False,
            },
        )

        reader = InMemoryIPReader(writer.get_all())
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
        result = filter_ips_by_classification(ips, reader)

        assert result == []

    def test_no_classifier_data_keeps_ip(self):
        """无分类数据的 IP 默认保留"""
        writer = InMemoryIPWriter()
        writer.add_or_update_ip(
            "1.1.1.1",
            "classifier",
            {
                "category": "cdn",
                "label": "CDN/WAF",
                "need_deep_query": False,
            },
        )
        # 2.2.2.2 不写入任何 classifier 数据

        reader = InMemoryIPReader(writer.get_all())
        ips = ["1.1.1.1", "2.2.2.2"]
        result = filter_ips_by_classification(ips, reader)

        assert result == ["2.2.2.2"]
