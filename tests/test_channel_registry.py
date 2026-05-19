import os
import sys

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from protocols import ChannelProtocol, InMemoryChannel


class TestChannelRegistryRegister:

    def test_register_channel(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        ch = InMemoryChannel(name='test_ch')
        reg.register(ch)
        assert reg.get('test_ch') is ch

    def test_register_multiple_channels(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        ch1 = InMemoryChannel(name='a')
        ch2 = InMemoryChannel(name='b')
        reg.register(ch1)
        reg.register(ch2)
        assert len(reg.list_names()) == 2

    def test_register_replaces_existing(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        ch1 = InMemoryChannel(name='x', fetch_result={'v': 1})
        ch2 = InMemoryChannel(name='x', fetch_result={'v': 2})
        reg.register(ch1)
        reg.register(ch2)
        assert reg.get('x') is ch2

    def test_register_requires_channel_protocol(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        with pytest.raises(TypeError):
            reg.register("not a channel")

    def test_register_none_raises(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        with pytest.raises(TypeError):
            reg.register(None)


class TestChannelRegistryGet:

    def test_get_returns_registered_channel(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        ch = InMemoryChannel(name='rdns')
        reg.register(ch)
        assert reg.get('rdns') is ch

    def test_get_returns_none_for_unknown(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        assert reg.get('nonexistent') is None

    def test_get_returns_none_for_empty_registry(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        assert reg.get('anything') is None


class TestChannelRegistryList:

    def test_list_names_returns_all_registered(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        reg.register(InMemoryChannel(name='a'))
        reg.register(InMemoryChannel(name='b'))
        reg.register(InMemoryChannel(name='c'))
        assert sorted(reg.list_names()) == ['a', 'b', 'c']

    def test_list_names_empty_registry(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        assert reg.list_names() == []

    def test_list_channels_returns_all_instances(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        ch1 = InMemoryChannel(name='a')
        ch2 = InMemoryChannel(name='b')
        reg.register(ch1)
        reg.register(ch2)
        channels = reg.list_channels()
        assert len(channels) == 2
        assert ch1 in channels
        assert ch2 in channels


class TestChannelRegistryValidate:

    def test_validate_all_returns_dict(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        reg.register(InMemoryChannel(name='ok', validate_result=True))
        reg.register(InMemoryChannel(name='bad', validate_result=False))
        results = reg.validate_all()
        assert results == {'ok': True, 'bad': False}

    def test_validate_all_empty_registry(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        assert reg.validate_all() == {}

    def test_validate_single_channel(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        reg.register(InMemoryChannel(name='test', validate_result=True))
        assert reg.validate('test') is True

    def test_validate_single_nonexistent_returns_false(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        assert reg.validate('nope') is False


class TestChannelRegistryFetch:

    def test_fetch_delegates_to_channel(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        reg.register(InMemoryChannel(name='mock', fetch_result={'country': 'CN'}))
        result = reg.fetch('mock', '1.2.3.4')
        assert result == {'country': 'CN'}

    def test_fetch_unknown_channel_raises(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        with pytest.raises(KeyError):
            reg.fetch('nonexistent', '1.2.3.4')

    def test_fetch_passes_kwargs(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        ch = InMemoryChannel(name='mock')
        reg.register(ch)
        reg.fetch('mock', '1.2.3.4', key='test', timeout=30)
        assert ch.fetch_calls[0] == ('1.2.3.4', {'key': 'test', 'timeout': 30})


class TestChannelRegistryIntegration:

    def test_register_inmemory_and_use(self):
        from protocols import ChannelRegistry
        reg = ChannelRegistry()
        reg.register(InMemoryChannel(name='ch1', fetch_result={'a': 1}))
        reg.register(InMemoryChannel(name='ch2', fetch_result={'b': 2}))
        assert sorted(reg.list_names()) == ['ch1', 'ch2']
        assert reg.fetch('ch1', '1.2.3.4') == {'a': 1}
        assert reg.fetch('ch2', '5.6.7.8') == {'b': 2}

    def test_registry_with_type_annotation(self):
        from protocols import ChannelRegistry

        def process_channels(registry: ChannelRegistry, ip: str) -> dict:
            results = {}
            for name in registry.list_names():
                ch = registry.get(name)
                if ch and ch.validate():
                    results[name] = ch.fetch(ip)
            return results

        reg = ChannelRegistry()
        reg.register(InMemoryChannel(name='ok', validate_result=True, fetch_result={'data': 1}))
        reg.register(InMemoryChannel(name='bad', validate_result=False))
        results = process_channels(reg, '1.2.3.4')
        assert 'ok' in results
        assert 'bad' not in results


class TestCreateDefaultRegistry:

    def test_returns_channel_registry(self):
        from protocols import ChannelRegistry, create_default_registry
        reg = create_default_registry()
        assert isinstance(reg, ChannelRegistry)

    def test_contains_all_builtin_channels(self):
        from protocols import create_default_registry
        reg = create_default_registry()
        names = reg.list_names()
        expected = [
            'fofa_host', 'fofa_search', 'aizhan', 'chinaz',
            'zoomeye', 'rdns_ptr', 'whois', 'ssl_cert',
            'ipinfo_api', 'port_scan',
        ]
        for name in expected:
            assert name in names, f"missing channel: {name}"

    def test_all_registered_are_channel_protocol(self):
        from protocols import ChannelProtocol, create_default_registry
        reg = create_default_registry()
        for ch in reg.list_channels():
            assert isinstance(ch, ChannelProtocol), f"{ch.channel_name} not ChannelProtocol"

    def test_each_channel_has_correct_name(self):
        from protocols import create_default_registry
        reg = create_default_registry()
        for ch in reg.list_channels():
            got = reg.get(ch.channel_name)
            assert got is ch

    def test_registry_has_ten_channels(self):
        from protocols import create_default_registry
        reg = create_default_registry()
        assert len(reg.list_names()) == 10


class TestRemainingAdapters:

    def test_chinaz_adapter_satisfies_protocol(self):
        from channel.chinaz import ChinazChannel
        ch = ChinazChannel()
        assert isinstance(ch, ChannelProtocol)
        assert ch.channel_name == 'chinaz'

    def test_fofa_search_adapter_satisfies_protocol(self):
        from channel.fofa_search import FofaSearchChannel
        ch = FofaSearchChannel()
        assert isinstance(ch, ChannelProtocol)
        assert ch.channel_name == 'fofa_search'

    def test_zoomeye_adapter_satisfies_protocol(self):
        from channel.zoomeye import ZoomeyeChannel
        ch = ZoomeyeChannel()
        assert isinstance(ch, ChannelProtocol)
        assert ch.channel_name == 'zoomeye'

    def test_rdns_ptr_adapter_satisfies_protocol(self):
        from channel.rdns_ptr import RdnsPtrChannel
        ch = RdnsPtrChannel()
        assert isinstance(ch, ChannelProtocol)
        assert ch.channel_name == 'rdns_ptr'

    def test_whois_adapter_satisfies_protocol(self):
        from channel.whois_query import WhoisChannel
        ch = WhoisChannel()
        assert isinstance(ch, ChannelProtocol)
        assert ch.channel_name == 'whois'

    def test_ssl_cert_adapter_satisfies_protocol(self):
        from channel.ssl_cert import SslCertChannel
        ch = SslCertChannel()
        assert isinstance(ch, ChannelProtocol)
        assert ch.channel_name == 'ssl_cert'

    def test_ipinfo_api_adapter_satisfies_protocol(self):
        from channel.ipinfo_api import IpinfoApiChannel
        ch = IpinfoApiChannel()
        assert isinstance(ch, ChannelProtocol)
        assert ch.channel_name == 'ipinfo_api'

    def test_chinaz_validate_returns_false_on_exit(self):
        from channel.chinaz import ChinazChannel
        ch = ChinazChannel()
        with patch('channel.chinaz.validate_channel_key', side_effect=SystemExit(1)):
            assert ch.validate() is False

    def test_chinaz_fetch_delegates(self):
        from channel.chinaz import ChinazChannel
        ch = ChinazChannel()
        expected = {'success': True, 'domains': []}
        with patch('channel.chinaz.fetch_channel', return_value=expected) as m:
            result = ch.fetch('1.2.3.4', cookie='test')
            m.assert_called_once_with('1.2.3.4', cookie='test')
            assert result == expected

    def test_fofa_search_fetch_delegates(self):
        from channel.fofa_search import FofaSearchChannel
        ch = FofaSearchChannel()
        expected = {'results': [], 'size': 0}
        with patch('channel.fofa_search.fetch_channel', return_value=expected) as m:
            result = ch.fetch('1.2.3.4', key='k')
            m.assert_called_once_with('1.2.3.4', key='k')
            assert result == expected

    def test_zoomeye_fetch_delegates(self):
        from channel.zoomeye import ZoomeyeChannel
        ch = ZoomeyeChannel()
        expected = {'total': 0, 'data': []}
        with patch('channel.zoomeye.fetch_channel', return_value=expected) as m:
            result = ch.fetch('1.2.3.4', key='k')
            m.assert_called_once_with('1.2.3.4', key='k')
            assert result == expected

    def test_rdns_ptr_fetch_delegates(self):
        from channel.rdns_ptr import RdnsPtrChannel
        ch = RdnsPtrChannel()
        expected = {'has_ptr': True, 'hostname': 'test.com'}
        with patch('channel.rdns_ptr.fetch_channel', return_value=expected) as m:
            result = ch.fetch('1.2.3.4', timeout=5.0)
            m.assert_called_once_with('1.2.3.4', timeout=5.0)
            assert result == expected

    def test_whois_fetch_delegates(self):
        from channel.whois_query import WhoisChannel
        ch = WhoisChannel()
        expected = {'has_whois': True, 'whois_data': {}}
        with patch('channel.whois_query.fetch_channel', return_value=expected) as m:
            result = ch.fetch('1.2.3.4', timeout=10.0)
            m.assert_called_once_with('1.2.3.4', timeout=10.0)
            assert result == expected

    def test_ssl_cert_fetch_delegates(self):
        from channel.ssl_cert import SslCertChannel
        ch = SslCertChannel()
        expected = {'domains': ['test.com'], 'subject_cn': 'test.com'}
        with patch('channel.ssl_cert.fetch_channel', return_value=expected) as m:
            result = ch.fetch('1.2.3.4', port=443)
            m.assert_called_once_with('1.2.3.4', port=443)
            assert result == expected

    def test_ipinfo_api_fetch_delegates(self):
        from channel.ipinfo_api import IpinfoApiChannel
        ch = IpinfoApiChannel()
        expected = {'country': 'CN', 'ip': '1.2.3.4'}
        with patch('channel.ipinfo_api.fetch_channel', return_value=expected) as m:
            result = ch.fetch('1.2.3.4', key='token')
            m.assert_called_once_with('1.2.3.4', key='token')
            assert result == expected

    def test_whois_validate_returns_false_on_exit(self):
        from channel.whois_query import WhoisChannel
        ch = WhoisChannel()
        with patch('channel.whois_query.validate_channel_key', side_effect=SystemExit(1)):
            assert ch.validate() is False

    def test_ssl_cert_validate_returns_true(self):
        from channel.ssl_cert import SslCertChannel
        ch = SslCertChannel()
        with patch('channel.ssl_cert.validate_channel_key'):
            assert ch.validate() is True

    def test_rdns_ptr_validate_returns_true(self):
        from channel.rdns_ptr import RdnsPtrChannel
        ch = RdnsPtrChannel()
        with patch('channel.rdns_ptr.validate_channel_key'):
            assert ch.validate() is True

    def test_ipinfo_api_validate_returns_false_on_exit(self):
        from channel.ipinfo_api import IpinfoApiChannel
        ch = IpinfoApiChannel()
        with patch('channel.ipinfo_api.validate_channel_key', side_effect=SystemExit(1)):
            assert ch.validate() is False

    def test_zoomeye_validate_returns_false_on_exit(self):
        from channel.zoomeye import ZoomeyeChannel
        ch = ZoomeyeChannel()
        with patch('channel.zoomeye.validate_channel_key', side_effect=SystemExit(1)):
            assert ch.validate() is False

    def test_fofa_search_validate_returns_false_on_exit(self):
        from channel.fofa_search import FofaSearchChannel
        ch = FofaSearchChannel()
        with patch('channel.fofa_search.validate_channel_key', side_effect=SystemExit(1)):
            assert ch.validate() is False
