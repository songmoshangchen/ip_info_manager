import pytest

from ip_info.channel.errors import ChannelError
from ip_info.channel.registry import ChannelRegistry


class FakeChannel:
    """用于测试的渠道替身，模拟 ChannelProtocol 行为"""

    def __init__(self, name="fake", validate_result=True, fetch_result=None, fetch_error=None):
        self.channel_name = name
        self._validate_result = validate_result
        self._fetch_result = fetch_result or {"data": "test"}
        self._fetch_error = fetch_error

    def validate(self) -> bool:
        return self._validate_result

    def fetch(self, ip: str, **kwargs) -> dict:
        if self._fetch_error:
            raise self._fetch_error
        return dict(self._fetch_result)


class TestChannelRegistryRegister:
    def test_注册渠道后可通过名称获取(self):
        registry = ChannelRegistry()
        ch = FakeChannel(name="test_ch")
        registry.register(ch)
        assert registry.get("test_ch") is ch

    def test_注册非协议对象抛出TypeError(self):
        registry = ChannelRegistry()
        with pytest.raises(TypeError, match="ChannelProtocol"):
            registry.register("not_a_channel")

    def test_重复注册同名渠道覆盖旧的(self):
        registry = ChannelRegistry()
        ch1 = FakeChannel(name="test")
        ch2 = FakeChannel(name="test")
        registry.register(ch1)
        registry.register(ch2)
        assert registry.get("test") is ch2


class TestChannelRegistryGet:
    def test_获取不存在的渠道返回None(self):
        registry = ChannelRegistry()
        assert registry.get("nonexistent") is None


class TestChannelRegistryList:
    def test_list_names返回所有渠道名(self):
        registry = ChannelRegistry()
        registry.register(FakeChannel(name="ch1"))
        registry.register(FakeChannel(name="ch2"))
        registry.register(FakeChannel(name="ch3"))
        assert sorted(registry.list_names()) == ["ch1", "ch2", "ch3"]

    def test_list_channels返回所有渠道实例(self):
        registry = ChannelRegistry()
        ch1 = FakeChannel(name="ch1")
        ch2 = FakeChannel(name="ch2")
        registry.register(ch1)
        registry.register(ch2)
        assert len(registry.list_channels()) == 2

    def test_空注册表返回空列表(self):
        registry = ChannelRegistry()
        assert registry.list_names() == []
        assert registry.list_channels() == []


class TestChannelRegistryValidate:
    def test_validate存在的渠道返回结果(self):
        registry = ChannelRegistry()
        registry.register(FakeChannel(name="ok", validate_result=True))
        assert registry.validate("ok") is True

    def test_validate失败的渠道返回False(self):
        registry = ChannelRegistry()
        registry.register(FakeChannel(name="bad", validate_result=False))
        assert registry.validate("bad") is False

    def test_validate不存在的渠道返回False(self):
        registry = ChannelRegistry()
        assert registry.validate("nonexistent") is False

    def test_validate_all返回所有渠道的验证结果(self):
        registry = ChannelRegistry()
        registry.register(FakeChannel(name="ok", validate_result=True))
        registry.register(FakeChannel(name="bad", validate_result=False))
        results = registry.validate_all()
        assert results == {"ok": True, "bad": False}


class TestChannelRegistryFetch:
    def test_fetch委托调用成功(self):
        registry = ChannelRegistry()
        registry.register(FakeChannel(name="test", fetch_result={"ip": "1.2.3.4"}))
        result = registry.fetch("test", "1.2.3.4")
        assert result == {"ip": "1.2.3.4"}

    def test_fetch透传ChannelError(self):
        registry = ChannelRegistry()
        registry.register(FakeChannel(name="test", fetch_error=ChannelError("超时")))
        with pytest.raises(ChannelError, match="超时"):
            registry.fetch("test", "1.2.3.4")

    def test_fetch不存在的渠道抛出KeyError(self):
        registry = ChannelRegistry()
        with pytest.raises(KeyError, match="nonexistent"):
            registry.fetch("nonexistent", "1.2.3.4")
