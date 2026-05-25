from ip_info.pipeline.filter_ips import filter_ips_by_classification
from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter


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
