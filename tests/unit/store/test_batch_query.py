import pytest

from ip_info.store.in_memory import InMemoryIPReader, InMemoryIPWriter


@pytest.fixture
def populated_store():
    """构造一个包含多条数据的 Reader，用于批量查询测试"""
    writer = InMemoryIPWriter()
    writer.add_or_update_ip("1.2.3.4", "rdns_ptr", {"hostname": "host1.com", "has_ptr": True})
    writer.add_or_update_ip("1.2.3.4", "ipinfo_api", {"country": "CN", "org": "ISP-A"})
    writer.add_or_update_ip("5.6.7.8", "rdns_ptr", {"hostname": "host2.com", "has_ptr": True})
    return InMemoryIPReader(writer.get_all())


class TestGetIPsData:
    def test_get_ips_data_returns_matching_records(self, populated_store):
        """批量获取多个 IP，不存在的 IP 不在结果中"""
        result = populated_store.get_ips_data(["1.2.3.4", "5.6.7.8", "99.99.99.99"])
        assert "1.2.3.4" in result
        assert "5.6.7.8" in result
        assert "99.99.99.99" not in result
        assert len(result) == 2

    def test_get_ips_data_empty_list(self, populated_store):
        """空列表返回空 dict"""
        result = populated_store.get_ips_data([])
        assert result == {}


class TestListAllIPsData:
    def test_list_all_ips_data_no_exclude(self, populated_store):
        """不排除时返回全部"""
        result = populated_store.list_all_ips_data()
        assert len(result) == 2
        assert "1.2.3.4" in result
        assert "5.6.7.8" in result

    def test_list_all_ips_data_excludes_specified(self, populated_store):
        """排除指定 IP"""
        result = populated_store.list_all_ips_data(exclude_ips=["1.2.3.4"])
        assert "1.2.3.4" not in result
        assert "5.6.7.8" in result
        assert len(result) == 1

    def test_list_all_ips_data_ignore_nonexistent_exclude(self, populated_store):
        """排除不存在的 IP 无副作用"""
        result = populated_store.list_all_ips_data(exclude_ips=["99.99.99.99"])
        assert len(result) == 2
        assert "1.2.3.4" in result
        assert "5.6.7.8" in result
