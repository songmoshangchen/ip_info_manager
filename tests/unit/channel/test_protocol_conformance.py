from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.in_memory import InMemoryChannel
from ip_info.channel.protocols import ChannelProtocol


class _MinimalAdapter(BaseChannelAdapter):
    channel_name = "minimal"

    def _request(self, ip, **kwargs):
        return {"ip": ip}


class TestProtocolConformance:
    def test_InMemoryChannel满足ChannelProtocol(self):
        ch = InMemoryChannel()
        assert isinstance(ch, ChannelProtocol)

    def test_BaseChannelAdapter子类满足ChannelProtocol(self):
        adapter = _MinimalAdapter()
        assert isinstance(adapter, ChannelProtocol)

    def test_从包级别导入所有类(self):
        from ip_info.channel import (
            ChannelError,
            ChannelProtocol,
        )

        assert ChannelProtocol is not None
        assert ChannelError is not None
