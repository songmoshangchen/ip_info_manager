import pytest

from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter


@pytest.fixture
def writer_and_reader():
    """构造一个写入多条数据的 Writer 和共享同一存储的 Reader 实例"""
    w = InMemoryIPWriter()
    w.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "host1.com", "has_ptr": True})
    w.add_or_update_ip("1.2.3.4", "ipinfo_api", {"country": "CN", "org": "ISP-A"})
    w.add_or_update_ip("5.6.7.8", "rdns_ptr", {"hostname": "host2.com", "has_ptr": True})
    r = InMemoryIPReader(data=w._store)
    return w, r


class TestWriterReaderConsistency:
    def test_write_then_read_ip_data(self, writer_and_reader):
        """写入后 get_ip_data 读回"""
        writer, reader = writer_and_reader
        record = reader.get_ip_data("1.2.3.4")
        assert record is not None
        assert record["ip"] == "1.2.3.4"
        assert record["rdns_ptr"] == {"hostname": "host1.com", "has_ptr": True}
        assert record["ipinfo_api"] == {"country": "CN", "org": "ISP-A"}

    def test_write_then_read_channel_data(self, writer_and_reader):
        """写入后 get_channel_data 读回"""
        writer, reader = writer_and_reader
        data = reader.get_channel_data("1.2.3.4", "ipinfo_api")
        assert data == {"country": "CN", "org": "ISP-A"}

    def test_write_then_list_all_ips(self, writer_and_reader):
        """写入后 list_all_ips 正确"""
        writer, reader = writer_and_reader
        ips = reader.list_all_ips()
        assert set(ips) == {"1.2.3.4", "5.6.7.8"}

    def test_write_then_list_ip_channels(self, writer_and_reader):
        """写入后 list_ip_channels 排除 ip 字段"""
        writer, reader = writer_and_reader
        channels = reader.list_ip_channels("1.2.3.4")
        assert set(channels) == {"rdns_ptr", "ipinfo_api"}
        assert "ip" not in channels

    def test_write_then_search(self, writer_and_reader):
        """写入后 search_ips_by_channel 正确"""
        writer, reader = writer_and_reader
        results = reader.search_ips_by_channel("rdns_ptr", key="has_ptr", value=True)
        assert set(results) == {"1.2.3.4", "5.6.7.8"}

    def test_write_then_get_ips_data(self, writer_and_reader):
        """写入后 get_ips_data 批量查询"""
        writer, reader = writer_and_reader
        result = reader.get_ips_data(["1.2.3.4", "5.6.7.8", "99.99.99.99"])
        assert "1.2.3.4" in result
        assert "5.6.7.8" in result
        assert "99.99.99.99" not in result
        assert len(result) == 2

    def test_write_then_list_all_ips_data_with_exclude(self, writer_and_reader):
        """写入后 list_all_ips_data 排除"""
        writer, reader = writer_and_reader
        result = reader.list_all_ips_data(exclude_ips=["5.6.7.8"])
        assert "1.2.3.4" in result
        assert "5.6.7.8" not in result
        assert len(result) == 1
