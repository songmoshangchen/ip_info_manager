import os
import sys

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestIpinfoFreeRequestChannel:

    def test_normal_response(self):
        from channel.ipinfo_free import request_channel
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'ip': '8.8.8.8', 'hostname': 'dns.google',
            'city': 'Mountain View', 'country': 'US', 'loc': '37.4056,-122.0775',
        }
        mock_resp.raise_for_status.return_value = None
        with patch('channel.ipinfo_free.requests.get', return_value=mock_resp):
            result = request_channel('8.8.8.8')
        assert result['ip'] == '8.8.8.8'
        assert result['hostname'] == 'dns.google'

    def test_timeout_returns_error(self):
        from channel.ipinfo_free import request_channel
        with patch('channel.ipinfo_free.requests.get', side_effect=Exception('timed out')):
            result = request_channel('8.8.8.8')
        assert result['raw_error'] is True
        assert 'timed out' in result['error_message']

    def test_rate_limit_returns_error(self):
        from channel.ipinfo_free import request_channel
        with patch('channel.ipinfo_free.requests.get', side_effect=Exception('rate limit exceeded')):
            result = request_channel('8.8.8.8')
        assert result['raw_error'] is True


class TestIpinfoFreeFetchChannel:

    def test_normal_flow_adds_query_time(self):
        from channel.ipinfo_free import fetch_channel
        with patch('channel.ipinfo_free.request_channel', return_value={'ip': '8.8.8.8', 'hostname': 'dns.google'}):
            result = fetch_channel('8.8.8.8', delay=0)
        assert 'query_time' in result
        assert result['hostname'] == 'dns.google'

    def test_error_flow_adds_query_time(self):
        from channel.ipinfo_free import fetch_channel
        with patch('channel.ipinfo_free.request_channel', return_value={'raw_error': True, 'error_message': 'timeout'}):
            result = fetch_channel('8.8.8.8', delay=0)
        assert 'query_time' in result
        assert result['raw_error'] is True

    def test_returns_hostname_and_loc(self):
        from channel.ipinfo_free import fetch_channel
        with patch('channel.ipinfo_free.request_channel', return_value={
            'ip': '8.8.8.8', 'hostname': 'dns.google', 'country': 'US', 'loc': '37.4056,-122.0775',
        }):
            result = fetch_channel('8.8.8.8', delay=0)
        assert result['hostname'] == 'dns.google'
        assert result['loc'] == '37.4056,-122.0775'


class TestIpinfoFreeChannel:

    def test_satisfies_channel_protocol(self):
        from protocols import ChannelProtocol
        from channel.ipinfo_free import IpinfoFreeChannel
        ch = IpinfoFreeChannel()
        assert isinstance(ch, ChannelProtocol)

    def test_channel_name(self):
        from channel.ipinfo_free import IpinfoFreeChannel
        ch = IpinfoFreeChannel()
        assert ch.channel_name == 'ipinfo_free'

    def test_validate_success(self):
        from channel.ipinfo_free import IpinfoFreeChannel
        ch = IpinfoFreeChannel()
        with patch('channel.ipinfo_free.requests.get'):
            assert ch.validate() is True
        assert ch.disabled is False

    def test_validate_failure_sets_disabled(self):
        from channel.ipinfo_free import IpinfoFreeChannel
        ch = IpinfoFreeChannel()
        with patch('channel.ipinfo_free.requests.get', side_effect=Exception('unreachable')):
            assert ch.validate() is False
        assert ch.disabled is True

    def test_fetch_delegates(self):
        from channel.ipinfo_free import IpinfoFreeChannel
        ch = IpinfoFreeChannel()
        expected = {'ip': '1.2.3.4', 'query_time': '2024-01-01'}
        with patch('channel.ipinfo_free.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch('1.2.3.4')
            mock_fetch.assert_called_once_with('1.2.3.4')
            assert result == expected

    def test_disabled_default_is_false(self):
        from channel.ipinfo_free import IpinfoFreeChannel
        ch = IpinfoFreeChannel()
        assert ch.disabled is False


class TestIpinfoFreeRegistry:

    def test_registered_in_default_registry(self):
        from protocols import create_default_registry
        reg = create_default_registry()
        ch = reg.get('ipinfo_free')
        assert ch is not None
        assert ch.channel_name == 'ipinfo_free'
