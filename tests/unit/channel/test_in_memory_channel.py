import pytest

from ip_info.channel.errors import ChannelError
from ip_info.channel.in_memory import InMemoryChannel
from ip_info.channel.protocols import ChannelProtocol


class TestInMemoryChannelDefault:
    def test_默认名称为test_channel(self):
        ch = InMemoryChannel()
        assert ch.channel_name == "test_channel"

    def test_默认validate返回True(self):
        ch = InMemoryChannel()
        assert ch.validate() is True

    def test_默认fetch返回空dict(self):
        ch = InMemoryChannel()
        result = ch.fetch("1.2.3.4")
        assert result == {}


class TestInMemoryChannelCustom:
    def test_自定义名称(self):
        ch = InMemoryChannel(name="my_channel")
        assert ch.channel_name == "my_channel"

    def test_自定义validate返回False(self):
        ch = InMemoryChannel(validate_result=False)
        assert ch.validate() is False

    def test_自定义fetch返回指定数据(self):
        ch = InMemoryChannel(fetch_result={"country": "CN"})
        result = ch.fetch("1.2.3.4")
        assert result == {"country": "CN"}

    def test_fetch_error配置抛出ChannelError(self):
        ch = InMemoryChannel(fetch_error=ChannelError("模拟超时"))
        with pytest.raises(ChannelError, match="模拟超时"):
            ch.fetch("1.2.3.4")


class TestInMemoryChannelFetchCalls:
    def test_记录fetch调用参数(self):
        ch = InMemoryChannel(fetch_result={"data": 1})
        ch.fetch("1.2.3.4", timeout=5)
        ch.fetch("5.6.7.8", key="abc")
        assert len(ch.fetch_calls) == 2
        assert ch.fetch_calls[0] == ("1.2.3.4", {"timeout": 5})
        assert ch.fetch_calls[1] == ("5.6.7.8", {"key": "abc"})

    def test_fetch返回副本非引用(self):
        original = {"country": "CN"}
        ch = InMemoryChannel(fetch_result=original)
        r1 = ch.fetch("1.2.3.4")
        r2 = ch.fetch("1.2.3.4")
        r1["extra"] = "modified"
        assert "extra" not in r2
        assert "extra" not in original


class TestInMemoryChannelProtocol:
    def test_满足ChannelProtocol(self):
        ch = InMemoryChannel()
        assert isinstance(ch, ChannelProtocol)
