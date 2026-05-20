import pytest

from ip_info.store.in_memory import InMemoryIPWriter, InMemoryIPReader
from ip_info.store.protocols import IPDataReader


@pytest.fixture
def populated_reader():
    writer = InMemoryIPWriter()
    writer.add_or_update_ip("1.2.3.4", "ipinfo", {"country": "CN", "org": "ISP-A"})
    writer.add_or_update_ip("1.2.3.4", "rdns", {"ptr": "host.example.com"})
    writer.add_or_update_ip("5.6.7.8", "ipinfo", {"country": "US", "org": "ISP-B"})
    writer.add_or_update_ip("5.6.7.8", "fofa", {"title": "Web Server"})
    writer.add_or_update_ip("10.0.0.1", "rdns", {"ptr": "internal.local"})
    return InMemoryIPReader(writer.get_all())


@pytest.fixture
def empty_reader():
    return InMemoryIPReader()


class TestInMemoryIPReaderGetIPData:

    def test_returns_full_record(self, populated_reader):
        record = populated_reader.get_ip_data("1.2.3.4")
        assert record is not None
        assert record["ip"] == "1.2.3.4"
        assert record["ipinfo"] == {"country": "CN", "org": "ISP-A"}
        assert record["rdns"] == {"ptr": "host.example.com"}

    def test_returns_none_for_nonexistent(self, populated_reader):
        assert populated_reader.get_ip_data("99.99.99.99") is None

    def test_returns_none_when_empty(self, empty_reader):
        assert empty_reader.get_ip_data("1.2.3.4") is None


class TestInMemoryIPReaderGetChannelData:

    def test_returns_channel_dict(self, populated_reader):
        data = populated_reader.get_channel_data("1.2.3.4", "ipinfo")
        assert data == {"country": "CN", "org": "ISP-A"}

    def test_returns_none_for_nonexistent_ip(self, populated_reader):
        assert populated_reader.get_channel_data("99.99.99.99", "ipinfo") is None

    def test_returns_none_for_nonexistent_channel(self, populated_reader):
        assert populated_reader.get_channel_data("1.2.3.4", "nonexistent") is None


class TestInMemoryIPReaderListAllIPs:

    def test_returns_all_keys(self, populated_reader):
        ips = populated_reader.list_all_ips()
        assert set(ips) == {"1.2.3.4", "5.6.7.8", "10.0.0.1"}

    def test_returns_empty_when_no_data(self, empty_reader):
        assert empty_reader.list_all_ips() == []


class TestInMemoryIPReaderListIPChannels:

    def test_excludes_ip_key(self, populated_reader):
        channels = populated_reader.list_ip_channels("1.2.3.4")
        assert set(channels) == {"ipinfo", "rdns"}
        assert "ip" not in channels

    def test_returns_empty_for_nonexistent(self, populated_reader):
        assert populated_reader.list_ip_channels("99.99.99.99") == []

    def test_returns_empty_for_ip_with_no_channels(self):
        reader = InMemoryIPReader({"1.2.3.4": {"ip": "1.2.3.4"}})
        assert reader.list_ip_channels("1.2.3.4") == []


class TestInMemoryIPReaderSearchByChannel:

    def test_returns_matching_ips(self, populated_reader):
        results = populated_reader.search_ips_by_channel("ipinfo")
        assert set(results) == {"1.2.3.4", "5.6.7.8"}

    def test_returns_empty_for_no_match(self, populated_reader):
        results = populated_reader.search_ips_by_channel("nonexistent")
        assert results == []

    def test_with_key_filter(self, populated_reader):
        results = populated_reader.search_ips_by_channel("ipinfo", key="country")
        assert set(results) == {"1.2.3.4", "5.6.7.8"}

    def test_with_key_and_value(self, populated_reader):
        results = populated_reader.search_ips_by_channel("ipinfo", key="country", value="CN")
        assert results == ["1.2.3.4"]

    def test_key_not_present_excludes_ip(self, populated_reader):
        results = populated_reader.search_ips_by_channel("ipinfo", key="nonexistent_key")
        assert results == []

    def test_value_mismatch_excludes_ip(self, populated_reader):
        results = populated_reader.search_ips_by_channel("ipinfo", key="country", value="JP")
        assert results == []


class TestInMemoryIPReaderGetIPsData:

    def test_returns_data_for_existing_ips(self, populated_reader):
        result = populated_reader.get_ips_data(["1.2.3.4", "5.6.7.8"])
        assert "1.2.3.4" in result
        assert "5.6.7.8" in result
        assert result["1.2.3.4"]["ip"] == "1.2.3.4"

    def test_skips_nonexistent_ips(self, populated_reader):
        result = populated_reader.get_ips_data(["1.2.3.4", "99.99.99.99"])
        assert len(result) == 1
        assert "1.2.3.4" in result

    def test_returns_empty_for_empty_input(self, populated_reader):
        assert populated_reader.get_ips_data([]) == {}


class TestInMemoryIPReaderListAllIPsData:

    def test_returns_all_data(self, populated_reader):
        result = populated_reader.list_all_ips_data()
        assert len(result) == 3
        assert "1.2.3.4" in result
        assert "5.6.7.8" in result
        assert "10.0.0.1" in result

    def test_excludes_specified_ips(self, populated_reader):
        result = populated_reader.list_all_ips_data(exclude_ips=["1.2.3.4"])
        assert "1.2.3.4" not in result
        assert len(result) == 2

    def test_returns_empty_when_no_data(self, empty_reader):
        assert empty_reader.list_all_ips_data() == {}

    def test_满足_IPDataReader_协议(self, populated_reader):
        assert isinstance(populated_reader, IPDataReader)
