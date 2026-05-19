import os
import sys

import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from protocols import ChannelProtocol


class TestChannelProtocolStructure:

    def test_protocol_has_channel_name_attribute(self):
        assert 'channel_name' in ChannelProtocol.__annotations__

    def test_protocol_has_validate_method(self):
        assert hasattr(ChannelProtocol, 'validate')

    def test_protocol_has_fetch_method(self):
        assert hasattr(ChannelProtocol, 'fetch')

    def test_protocol_is_runtime_checkable(self):
        class FakeChannel:
            channel_name = 'fake'

            def validate(self) -> bool:
                return True

            def fetch(self, ip: str, **kwargs) -> dict:
                return {}

        assert isinstance(FakeChannel(), ChannelProtocol)

    def test_non_conforming_class_fails_isinstance(self):
        class NotAChannel:
            pass

        assert not isinstance(NotAChannel(), ChannelProtocol)


class TestInMemoryChannel:

    def test_satisfies_channel_protocol(self):
        from protocols import InMemoryChannel
        ch = InMemoryChannel()
        assert isinstance(ch, ChannelProtocol)

    def test_default_channel_name(self):
        from protocols import InMemoryChannel
        ch = InMemoryChannel()
        assert ch.channel_name == 'test_channel'

    def test_custom_channel_name(self):
        from protocols import InMemoryChannel
        ch = InMemoryChannel(name='custom')
        assert ch.channel_name == 'custom'

    def test_validate_returns_true_by_default(self):
        from protocols import InMemoryChannel
        ch = InMemoryChannel()
        assert ch.validate() is True

    def test_validate_returns_configured_result(self):
        from protocols import InMemoryChannel
        ch = InMemoryChannel(validate_result=False)
        assert ch.validate() is False

    def test_fetch_returns_configured_result(self):
        from protocols import InMemoryChannel
        ch = InMemoryChannel(fetch_result={'country': 'CN'})
        result = ch.fetch('1.2.3.4')
        assert result == {'country': 'CN'}

    def test_fetch_records_calls(self):
        from protocols import InMemoryChannel
        ch = InMemoryChannel()
        ch.fetch('1.2.3.4', key='test')
        ch.fetch('5.6.7.8')
        assert len(ch.fetch_calls) == 2
        assert ch.fetch_calls[0] == ('1.2.3.4', {'key': 'test'})
        assert ch.fetch_calls[1] == ('5.6.7.8', {})

    def test_fetch_does_not_mutate_configured_result(self):
        from protocols import InMemoryChannel
        original = {'country': 'CN'}
        ch = InMemoryChannel(fetch_result=original)
        result = ch.fetch('1.2.3.4')
        result['extra'] = 'added'
        assert 'extra' not in original

    def test_fetch_returns_copy_each_time(self):
        from protocols import InMemoryChannel
        ch = InMemoryChannel(fetch_result={'a': 1})
        r1 = ch.fetch('1.2.3.4')
        r2 = ch.fetch('5.6.7.8')
        r1['b'] = 2
        assert 'b' not in r2


class TestFofaHostAdapter:

    def test_satisfies_channel_protocol(self):
        from channel.fofa_host import FofaHostChannel
        ch = FofaHostChannel()
        assert isinstance(ch, ChannelProtocol)

    def test_channel_name(self):
        from channel.fofa_host import FofaHostChannel
        ch = FofaHostChannel()
        assert ch.channel_name == 'fofa_host'

    def test_validate_returns_true_on_success(self):
        from channel.fofa_host import FofaHostChannel
        ch = FofaHostChannel()
        with patch('channel.fofa_host.validate_channel_key'):
            assert ch.validate() is True

    def test_validate_returns_false_on_exit(self):
        from channel.fofa_host import FofaHostChannel
        ch = FofaHostChannel()
        with patch('channel.fofa_host.validate_channel_key', side_effect=SystemExit(1)):
            assert ch.validate() is False

    def test_validate_returns_false_on_exception(self):
        from channel.fofa_host import FofaHostChannel
        ch = FofaHostChannel()
        with patch('channel.fofa_host.validate_channel_key', side_effect=ConnectionError('network')):
            assert ch.validate() is False

    def test_fetch_delegates_to_fetch_channel(self):
        from channel.fofa_host import FofaHostChannel
        ch = FofaHostChannel()
        expected = {'ip': '1.2.3.4', 'query_time': '2024-01-01'}
        with patch('channel.fofa_host.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch('1.2.3.4', key='test_key')
            mock_fetch.assert_called_once_with('1.2.3.4', key='test_key')
            assert result == expected


class TestAizhanAdapter:

    def test_satisfies_channel_protocol(self):
        from channel.aizhan import AizhanChannel
        ch = AizhanChannel()
        assert isinstance(ch, ChannelProtocol)

    def test_channel_name(self):
        from channel.aizhan import AizhanChannel
        ch = AizhanChannel()
        assert ch.channel_name == 'aizhan'

    def test_validate_returns_true_on_success(self):
        from channel.aizhan import AizhanChannel
        ch = AizhanChannel()
        with patch('channel.aizhan.validate_channel_key'):
            assert ch.validate() is True

    def test_validate_returns_false_on_exit(self):
        from channel.aizhan import AizhanChannel
        ch = AizhanChannel()
        with patch('channel.aizhan.validate_channel_key', side_effect=SystemExit(1)):
            assert ch.validate() is False

    def test_validate_returns_false_on_exception(self):
        from channel.aizhan import AizhanChannel
        ch = AizhanChannel()
        with patch('channel.aizhan.validate_channel_key', side_effect=ConnectionError('network')):
            assert ch.validate() is False

    def test_fetch_delegates_to_fetch_channel(self):
        from channel.aizhan import AizhanChannel
        ch = AizhanChannel()
        expected = {'success': True, 'domains': []}
        with patch('channel.aizhan.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch('1.2.3.4', cookie='test_cookie')
            mock_fetch.assert_called_once_with('1.2.3.4', cookie='test_cookie')
            assert result == expected


class TestPortScanAdapter:

    def test_satisfies_channel_protocol(self):
        from channel.port_scan import PortScanChannel
        ch = PortScanChannel()
        assert isinstance(ch, ChannelProtocol)

    def test_channel_name(self):
        from channel.port_scan import PortScanChannel
        ch = PortScanChannel()
        assert ch.channel_name == 'port_scan'

    def test_validate_returns_true_when_engine_available(self):
        from channel.port_scan import PortScanChannel
        ch = PortScanChannel()
        with patch('channel.port_scan.validate_engine', return_value='/usr/bin/nmap'):
            assert ch.validate() is True

    def test_validate_returns_false_when_engine_unavailable(self):
        from channel.port_scan import PortScanChannel
        ch = PortScanChannel()
        with patch('channel.port_scan.validate_engine', return_value=None):
            assert ch.validate() is False

    def test_validate_returns_false_on_exception(self):
        from channel.port_scan import PortScanChannel
        ch = PortScanChannel()
        with patch('channel.port_scan.validate_engine', side_effect=OSError('fail')):
            assert ch.validate() is False

    def test_fetch_delegates_to_fetch_channel(self):
        from channel.port_scan import PortScanChannel
        ch = PortScanChannel()
        expected = {'ip': '1.2.3.4', 'open_ports': []}
        with patch('channel.port_scan.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch('1.2.3.4', nmap_path='nmap', port_string='80,443')
            mock_fetch.assert_called_once_with('1.2.3.4', nmap_path='nmap', port_string='80,443')
            assert result == expected


class TestChannelProtocolIntegration:

    def test_use_channels_through_protocol_interface(self):
        from protocols import InMemoryChannel
        channels = [
            InMemoryChannel(name='rdns', fetch_result={'has_ptr': True}),
            InMemoryChannel(name='fofa_host', fetch_result={'ports': []}),
        ]
        for ch in channels:
            assert isinstance(ch, ChannelProtocol)
            result = ch.fetch('1.2.3.4')
            assert isinstance(result, dict)

    def test_validate_and_fetch_workflow(self):
        from protocols import InMemoryChannel
        ch = InMemoryChannel(name='test', validate_result=True, fetch_result={'ok': True})
        assert ch.validate() is True
        result = ch.fetch('1.2.3.4')
        assert result == {'ok': True}

    def test_invalid_channel_fails_validation(self):
        from protocols import InMemoryChannel
        ch = InMemoryChannel(name='bad', validate_result=False)
        assert ch.validate() is False

    def test_protocol_type_annotation_usage(self):
        from protocols import InMemoryChannel

        def query_channel(ch: ChannelProtocol, ip: str) -> dict:
            if not ch.validate():
                return {'raw_error': True, 'error_message': f'{ch.channel_name} unavailable'}
            return ch.fetch(ip)

        ch = InMemoryChannel(name='mock', validate_result=True, fetch_result={'data': 1})
        result = query_channel(ch, '1.2.3.4')
        assert result == {'data': 1}

        ch_bad = InMemoryChannel(name='bad', validate_result=False)
        result = query_channel(ch_bad, '1.2.3.4')
        assert result['raw_error'] is True
