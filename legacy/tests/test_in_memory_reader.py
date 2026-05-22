import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from protocols import InMemoryIPWriter, InMemoryIPReader


@pytest.fixture
def populated_reader():
    writer = InMemoryIPWriter()
    writer.add_or_update_ip('1.2.3.4', 'rdns_ptr', {'hostname': 'host1.com', 'has_ptr': True})
    writer.add_or_update_ip('1.2.3.4', 'ipinfo_api', {'country': 'CN', 'org': 'ISP-A'})
    writer.add_or_update_ip('5.6.7.8', 'rdns_ptr', {'hostname': 'host2.com', 'has_ptr': True})
    return InMemoryIPReader(writer.get_all())


@pytest.fixture
def empty_reader():
    return InMemoryIPReader()


class TestInMemoryIPReaderGetIPData:

    def test_get_ip_data_returns_full_record(self, populated_reader):
        data = populated_reader.get_ip_data('1.2.3.4')
        assert data is not None
        assert data['ip'] == '1.2.3.4'
        assert 'rdns_ptr' in data
        assert 'ipinfo_api' in data

    def test_get_ip_data_returns_none_for_nonexistent(self, populated_reader):
        assert populated_reader.get_ip_data('9.9.9.9') is None

    def test_get_ip_data_returns_none_when_empty(self, empty_reader):
        assert empty_reader.get_ip_data('1.2.3.4') is None


class TestInMemoryIPReaderGetChannelData:

    def test_get_channel_data_returns_channel_dict(self, populated_reader):
        data = populated_reader.get_channel_data('1.2.3.4', 'rdns_ptr')
        assert data == {'hostname': 'host1.com', 'has_ptr': True}

    def test_get_channel_data_returns_none_for_nonexistent_ip(self, populated_reader):
        assert populated_reader.get_channel_data('9.9.9.9', 'rdns_ptr') is None

    def test_get_channel_data_returns_none_for_nonexistent_channel(self, populated_reader):
        assert populated_reader.get_channel_data('1.2.3.4', 'fofa_host') is None


class TestInMemoryIPReaderListAllIPs:

    def test_list_all_ips_returns_all_keys(self, populated_reader):
        ips = populated_reader.list_all_ips()
        assert sorted(ips) == ['1.2.3.4', '5.6.7.8']

    def test_list_all_ips_returns_empty_when_no_data(self, empty_reader):
        assert empty_reader.list_all_ips() == []


class TestInMemoryIPReaderListIPChannels:

    def test_list_ip_channels_excludes_ip_key(self, populated_reader):
        channels = populated_reader.list_ip_channels('1.2.3.4')
        assert sorted(channels) == ['ipinfo_api', 'rdns_ptr']
        assert 'ip' not in channels

    def test_list_ip_channels_returns_empty_for_nonexistent(self, populated_reader):
        assert populated_reader.list_ip_channels('9.9.9.9') == []

    def test_list_ip_channels_returns_empty_for_ip_with_no_channels(self):
        reader = InMemoryIPReader({'1.2.3.4': {'ip': '1.2.3.4'}})
        assert reader.list_ip_channels('1.2.3.4') == []


class TestInMemoryIPReaderSearchByChannel:

    def test_search_by_channel_returns_matching_ips(self, populated_reader):
        result = populated_reader.search_ips_by_channel('rdns_ptr')
        assert sorted(result) == ['1.2.3.4', '5.6.7.8']

    def test_search_by_channel_returns_empty_for_no_match(self, populated_reader):
        assert populated_reader.search_ips_by_channel('fofa_host') == []

    def test_search_by_channel_with_key_filter(self, populated_reader):
        result = populated_reader.search_ips_by_channel('rdns_ptr', key='hostname')
        assert sorted(result) == ['1.2.3.4', '5.6.7.8']

    def test_search_by_channel_with_key_and_value(self, populated_reader):
        result = populated_reader.search_ips_by_channel('rdns_ptr', key='hostname', value='host1.com')
        assert result == ['1.2.3.4']

    def test_search_by_channel_key_not_present_excludes_ip(self, populated_reader):
        result = populated_reader.search_ips_by_channel('rdns_ptr', key='nonexistent_key')
        assert result == []

    def test_search_by_channel_value_mismatch_excludes_ip(self, populated_reader):
        result = populated_reader.search_ips_by_channel('rdns_ptr', key='hostname', value='no-such-host.com')
        assert result == []
