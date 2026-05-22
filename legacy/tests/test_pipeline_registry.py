import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from protocols import ChannelRegistry, InMemoryChannel, ChannelProtocol


class TestPipelineChannelRegistryIntegration:

    def test_registry_provides_channels_for_trace_ip(self):
        from protocols import create_default_registry
        reg = create_default_registry()
        trace_ip_channels = ['ipinfo_api', 'rdns_ptr', 'aizhan', 'chinaz', 'fofa_host', 'port_scan']
        for name in trace_ip_channels:
            ch = reg.get(name)
            assert ch is not None, f"Missing channel: {name}"
            assert isinstance(ch, ChannelProtocol)

    def test_registry_provides_channels_for_ip_domain_lookup(self):
        from protocols import create_default_registry
        reg = create_default_registry()
        idl_channels = ['rdns_ptr', 'aizhan', 'chinaz', 'zoomeye', 'fofa_search', 'ssl_cert']
        for name in idl_channels:
            ch = reg.get(name)
            assert ch is not None, f"Missing channel: {name}"
            assert isinstance(ch, ChannelProtocol)

    def test_fetch_via_registry_matches_direct_call(self):
        from protocols import create_default_registry
        from unittest.mock import patch
        reg = create_default_registry()
        expected = {'ip': '1.2.3.4', 'country': 'CN'}
        with patch('channel.fofa_host.fetch_channel', return_value=expected) as m:
            result = reg.fetch('fofa_host', '1.2.3.4', key='test')
            m.assert_called_once_with('1.2.3.4', key='test')
            assert result == expected

    def test_validate_via_registry(self):
        from protocols import create_default_registry
        from unittest.mock import patch
        reg = create_default_registry()
        with patch('channel.fofa_host.validate_channel_key'):
            assert reg.validate('fofa_host') is True
        with patch('channel.fofa_host.validate_channel_key', side_effect=SystemExit(1)):
            assert reg.validate('fofa_host') is False

    def test_custom_registry_for_testing(self):
        reg = ChannelRegistry()
        reg.register(InMemoryChannel(name='fofa_host', fetch_result={'ports': [80]}))
        reg.register(InMemoryChannel(name='aizhan', fetch_result={'domains': []}))
        result = reg.fetch('fofa_host', '1.2.3.4')
        assert result == {'ports': [80]}
        assert reg.validate('fofa_host') is True

    def test_pipeline_phase1_pattern_with_registry(self):
        reg = ChannelRegistry()
        reg.register(InMemoryChannel(name='ipinfo_api', fetch_result={'country': 'CN'}))
        reg.register(InMemoryChannel(name='rdns_ptr', fetch_result={'has_ptr': True}))

        phase1_channels = ['ipinfo_api', 'rdns_ptr']
        ip = '1.2.3.4'
        results = {}
        for name in phase1_channels:
            ch = reg.get(name)
            if ch and ch.validate():
                results[name] = ch.fetch(ip)

        assert 'ipinfo_api' in results
        assert 'rdns_ptr' in results
        assert results['ipinfo_api']['country'] == 'CN'

    def test_pipeline_phase3_pattern_with_registry(self):
        reg = ChannelRegistry()
        reg.register(InMemoryChannel(name='aizhan', fetch_result={'domain_count': 5}))
        reg.register(InMemoryChannel(name='chinaz', fetch_result={'domains': []}))
        reg.register(InMemoryChannel(name='fofa_host', fetch_result={'ports': [443]}))

        phase3_channels = ['aizhan', 'chinaz', 'fofa_host']
        ip = '1.2.3.4'
        results = {}
        for name in phase3_channels:
            ch = reg.get(name)
            if ch and ch.validate():
                results[name] = ch.fetch(ip)

        assert len(results) == 3

    def test_pipeline_skips_invalid_channels(self):
        reg = ChannelRegistry()
        reg.register(InMemoryChannel(name='ok', validate_result=True, fetch_result={'data': 1}))
        reg.register(InMemoryChannel(name='bad', validate_result=False, fetch_result={'data': 2}))

        channels = ['ok', 'bad']
        results = {}
        for name in channels:
            ch = reg.get(name)
            if ch and ch.validate():
                results[name] = ch.fetch('1.2.3.4')

        assert 'ok' in results
        assert 'bad' not in results
