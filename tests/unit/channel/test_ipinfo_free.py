from unittest.mock import MagicMock, patch

import pytest
import requests

from ip_info.channel.errors import ChannelError
from ip_info.channel.ipinfo_free import IpinfoFreeChannel
from ip_info.channel.protocols import ChannelProtocol


class TestIpinfoFreeRequest:
    def test_查询成功_HTTP200(self):
        channel = IpinfoFreeChannel()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ip": "8.8.8.8",
            "city": "Mountain View",
            "country": "US",
        }
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.ipinfo_free.requests.get", return_value=mock_response):
            result = channel._request("8.8.8.8")

        assert result == {"ip": "8.8.8.8", "city": "Mountain View", "country": "US"}

    def test_网络超时_抛ChannelError(self):
        channel = IpinfoFreeChannel()
        with patch(
            "ip_info.channel.ipinfo_free.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(ChannelError, match="查询超时.*8.8.8.8"):
                channel._request("8.8.8.8")

    def test_连接失败_抛ChannelError(self):
        channel = IpinfoFreeChannel()
        with patch(
            "ip_info.channel.ipinfo_free.requests.get",
            side_effect=requests.exceptions.ConnectionError("connection refused"),
        ):
            with pytest.raises(ChannelError, match="连接失败.*8.8.8.8"):
                channel._request("8.8.8.8")

    def test_请求限流_HTTP429_抛ChannelError(self):
        channel = IpinfoFreeChannel()
        mock_response = MagicMock()
        mock_response.status_code = 429
        with patch("ip_info.channel.ipinfo_free.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="限流.*8.8.8.8"):
                channel._request("8.8.8.8")

    def test_其他HTTP错误_HTTP500_抛ChannelError(self):
        channel = IpinfoFreeChannel()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        with patch("ip_info.channel.ipinfo_free.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="8.8.8.8.*HTTP 500"):
                channel._request("8.8.8.8")

    def test_其他非预期异常_抛ChannelError(self):
        channel = IpinfoFreeChannel()
        with patch(
            "ip_info.channel.ipinfo_free.requests.get",
            side_effect=ValueError("bad value"),
        ):
            with pytest.raises(ChannelError, match="查询错误.*8.8.8.8"):
                channel._request("8.8.8.8")


class TestIpinfoFreeFetch:
    def test_fetch完整流程_包含query_time(self):
        channel = IpinfoFreeChannel()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ip": "8.8.8.8", "city": "Mountain View"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.ipinfo_free.requests.get", return_value=mock_response):
            result = channel.fetch("8.8.8.8")

        assert "query_time" in result
        assert result["ip"] == "8.8.8.8"
        assert result["city"] == "Mountain View"

    def test_fetch网络错误透传ChannelError(self):
        channel = IpinfoFreeChannel()
        assert channel.disabled is False
        with patch(
            "ip_info.channel.ipinfo_free.requests.get",
            side_effect=requests.exceptions.Timeout("timeout"),
        ):
            with pytest.raises(ChannelError, match="查询超时"):
                channel.fetch("8.8.8.8")

        assert channel.disabled is False

    def test_fetch限流时不改变disabled(self):
        channel = IpinfoFreeChannel()
        assert channel.disabled is False
        mock_response = MagicMock()
        mock_response.status_code = 429
        with patch("ip_info.channel.ipinfo_free.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="限流"):
                channel.fetch("8.8.8.8")

        assert channel.disabled is False


class TestIpinfoFreeProtocol:
    def test_满足ChannelProtocol(self):
        channel = IpinfoFreeChannel()
        assert isinstance(channel, ChannelProtocol) is True

    def test_validate永远返回True(self):
        channel = IpinfoFreeChannel()
        assert channel.validate() is True
        assert channel.disabled is False

    def test_channel_name(self):
        channel = IpinfoFreeChannel()
        assert channel.channel_name == "ipinfo_free"
