import time

import pytest

from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.errors import ChannelError, ChannelPermanentError
from ip_info.channel.protocols import ChannelProtocol


class SimpleAdapter(BaseChannelAdapter):
    channel_name = "simple"

    def _request(self, ip, **kwargs):
        return {"ip": ip, **kwargs}


class FailingValidateAdapter(BaseChannelAdapter):
    channel_name = "failing_validate"

    def _request(self, ip, **kwargs):
        return {}

    def _validate_key(self):
        raise ValueError("Key not found")


class HtmlParseAdapter(BaseChannelAdapter):
    channel_name = "html_parser"

    def __init__(self):
        super().__init__()
        self._request_called_with = None

    def _request(self, ip, **kwargs):
        self._request_called_with = (ip, kwargs)
        return "<html>data</html>"

    def _parse(self, raw, ip):
        return {"parsed": raw, "ip": ip}


class NetworkErrorAdapter(BaseChannelAdapter):
    channel_name = "network_error"

    def _request(self, ip, **kwargs):
        raise ChannelError(f"连接超时: {ip}")


class PermanentErrorAdapter(BaseChannelAdapter):
    channel_name = "permanent_error"

    def _request(self, ip, **kwargs):
        raise ChannelPermanentError("API Key 无效")


class TestBaseChannelAdapterValidate:
    def test_validate成功返回True_disabled为False(self):
        adapter = SimpleAdapter()
        assert adapter.validate() is True
        assert adapter.disabled is False

    def test_validate失败返回False_disabled为True(self):
        adapter = FailingValidateAdapter()
        assert adapter.validate() is False
        assert adapter.disabled is True

    def test_validate是无状态调用(self):
        adapter = SimpleAdapter()
        assert adapter.validate() is True
        assert adapter.disabled is False


class TestBaseChannelAdapterFetch:
    def test_fetch标准调用链包含query_time(self):
        adapter = SimpleAdapter()
        result = adapter.fetch("1.2.3.4")
        assert result["ip"] == "1.2.3.4"
        assert "query_time" in result

    def test_fetch透传kwargs给_request(self):
        adapter = SimpleAdapter()
        result = adapter.fetch("1.2.3.4", timeout=5, key="abc")
        assert result["timeout"] == 5
        assert result["key"] == "abc"

    def test_fetch消费delay不传给_request(self):
        adapter = SimpleAdapter()
        result = adapter.fetch("1.2.3.4", delay=0)
        assert "delay" not in result

    def test_fetch_delay触发延迟(self):
        adapter = SimpleAdapter()
        start = time.monotonic()
        adapter.fetch("1.2.3.4", delay=0.15)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.1

    def test_fetch_调用_parse覆盖(self):
        adapter = HtmlParseAdapter()
        result = adapter.fetch("1.2.3.4")
        assert result["parsed"] == "<html>data</html>"
        assert result["ip"] == "1.2.3.4"
        assert "query_time" in result

    def test_fetch__parse默认透传dict(self):
        adapter = SimpleAdapter()
        result = adapter.fetch("1.2.3.4")
        assert "ip" in result
        assert "query_time" in result


class TestBaseChannelAdapterErrors:
    def test_ChannelError透传不改变disabled(self):
        adapter = NetworkErrorAdapter()
        assert adapter.disabled is False
        with pytest.raises(ChannelError, match="连接超时"):
            adapter.fetch("1.2.3.4")
        assert adapter.disabled is False

    def test_ChannelPermanentError设disabled为True(self):
        adapter = PermanentErrorAdapter()
        assert adapter.disabled is False
        with pytest.raises(ChannelPermanentError, match="API Key 无效"):
            adapter.fetch("1.2.3.4")
        assert adapter.disabled is True


class TestBaseChannelAdapterProtocol:
    def test_满足ChannelProtocol(self):
        adapter = SimpleAdapter()
        assert isinstance(adapter, ChannelProtocol)

    def test_未实现_request的子类无法实例化(self):
        with pytest.raises(TypeError):

            class IncompleteAdapter(BaseChannelAdapter):
                channel_name = "incomplete"

            IncompleteAdapter()
