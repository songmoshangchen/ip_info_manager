import pytest

from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter


@pytest.fixture
def writer_and_reader():
    """构造一个包含少量数据的 Writer 和共享同一存储的 Reader，用于异常边界测试"""
    w = InMemoryIPWriter()
    w.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "host1.com", "has_ptr": True})
    w.add_or_update_ip("1.2.3.4", "ipinfo_api", {"country": "CN", "org": "ISP-A"})
    r = InMemoryIPReader(data=w._store)
    return w, r


class TestEdgeCases:
    def test_delete_nonexistent_ip_returns_false(self, writer_and_reader):
        """删除不存在的 IP 返回 False"""
        writer, reader = writer_and_reader
        assert writer.delete_ip("99.99.99.99") is False

    def test_delete_nonexistent_channel_returns_false(self, writer_and_reader):
        """删除不存在的 channel 返回 False"""
        writer, reader = writer_and_reader
        assert writer.delete_channel("1.2.3.4", "nonexistent") is False

    def test_get_ip_data_nonexistent_returns_none(self, writer_and_reader):
        """查询不存在的 IP 返回 None"""
        writer, reader = writer_and_reader
        assert reader.get_ip_data("99.99.99.99") is None

    def test_get_channel_data_nonexistent_ip_returns_none(self, writer_and_reader):
        """查询不存在的 IP 的 channel 返回 None"""
        writer, reader = writer_and_reader
        assert reader.get_channel_data("99.99.99.99", "rdns_ptr") is None

    def test_get_channel_data_nonexistent_channel_returns_none(self, writer_and_reader):
        """查询存在的 IP 的不存在 channel 返回 None"""
        writer, reader = writer_and_reader
        assert reader.get_channel_data("1.2.3.4", "nonexistent") is None

    def test_list_ip_channels_nonexistent_returns_empty(self, writer_and_reader):
        """查询不存在的 IP 的 channel 列表返回空列表"""
        writer, reader = writer_and_reader
        assert reader.list_ip_channels("99.99.99.99") == []

    def test_search_no_match_returns_empty(self, writer_and_reader):
        """搜索不匹配的 channel 返回空列表"""
        writer, reader = writer_and_reader
        assert reader.search_ips_by_channel("nonexistent") == []

    def test_get_ips_data_all_nonexistent_returns_empty_dict(self, writer_and_reader):
        """批量查询全部不存在的 IP 返回空 dict"""
        writer, reader = writer_and_reader
        result = reader.get_ips_data(["99.99.99.99", "88.88.88.88"])
        assert result == {}

    def test_list_all_ips_data_empty_store_returns_empty_dict(self):
        """空存储的 list_all_ips_data 返回空 dict"""
        reader = InMemoryIPReader()
        assert reader.list_all_ips_data() == {}
