import pytest

from ip_info.store.in_memory import InMemoryIPWriter
from ip_info.store.protocols import IPDataReader


@pytest.fixture
def writer():
    """构造一个写入多条数据的 Writer 实例"""
    w = InMemoryIPWriter()
    w.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "host1.com", "has_ptr": True})
    w.add_or_update_ip("1.2.3.4", "ipinfo_api", {"country": "CN", "org": "ISP-A"})
    w.add_or_update_ip("5.6.7.8", "rdns_ptr", {"hostname": "host2.com", "has_ptr": True})
    return w


class TestWriterReaderConsistency:

    def test_writer_implements_reader_protocol(self):
        """InMemoryIPWriter 满足 IPDataReader 协议"""
        writer = InMemoryIPWriter()
        assert isinstance(writer, IPDataReader)

    def test_write_then_read_ip_data(self, writer):
        """写入后 get_ip_data 读回"""
        record = writer.get_ip_data("1.2.3.4")
        assert record is not None
        assert record["ip"] == "1.2.3.4"
        assert record["rdns_ptr"] == {"hostname": "host1.com", "has_ptr": True}
        assert record["ipinfo_api"] == {"country": "CN", "org": "ISP-A"}

    def test_write_then_read_channel_data(self, writer):
        """写入后 get_channel_data 读回"""
        data = writer.get_channel_data("1.2.3.4", "ipinfo_api")
        assert data == {"country": "CN", "org": "ISP-A"}

    def test_write_then_list_all_ips(self, writer):
        """写入后 list_all_ips 正确"""
        ips = writer.list_all_ips()
        assert set(ips) == {"1.2.3.4", "5.6.7.8"}

    def test_write_then_list_ip_channels(self, writer):
        """写入后 list_ip_channels 排除 ip 字段"""
        channels = writer.list_ip_channels("1.2.3.4")
        assert set(channels) == {"rdns_ptr", "ipinfo_api"}
        assert "ip" not in channels

    def test_write_then_search(self, writer):
        """写入后 search_ips_by_channel 正确"""
        results = writer.search_ips_by_channel("rdns_ptr", key="has_ptr", value=True)
        assert set(results) == {"1.2.3.4", "5.6.7.8"}

    def test_write_then_get_ips_data(self, writer):
        """写入后 get_ips_data 批量查询"""
        result = writer.get_ips_data(["1.2.3.4", "5.6.7.8", "99.99.99.99"])
        assert "1.2.3.4" in result
        assert "5.6.7.8" in result
        assert "99.99.99.99" not in result
        assert len(result) == 2

    def test_write_then_list_all_ips_data_with_exclude(self, writer):
        """写入后 list_all_ips_data 排除"""
        result = writer.list_all_ips_data(exclude_ips=["5.6.7.8"])
        assert "1.2.3.4" in result
        assert "5.6.7.8" not in result
        assert len(result) == 1
