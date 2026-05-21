from unittest.mock import MagicMock, patch

import pytest
import requests

from ip_info.channel.errors import ChannelError, ChannelPermanentError
from ip_info.channel.ipinfo_api import IpinfoApiChannel
from ip_info.channel.protocols import ChannelProtocol


class TestIpinfoApiValidateKey:
    def test_Token有效_HTTP200(self):
        channel = IpinfoApiChannel(token="valid_token")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.ipinfo_api.requests.get", return_value=mock_response):
            channel._validate_key()

    def test_Token为空_抛ChannelPermanentError(self):
        channel = IpinfoApiChannel(token="")
        with pytest.raises(ChannelPermanentError, match="IPInfo API Token 未配置"):
            channel._validate_key()

    def test_Token无效_HTTP401_抛ChannelPermanentError(self):
        channel = IpinfoApiChannel(token="bad_token")
        mock_response = MagicMock()
        mock_response.status_code = 401
        with patch("ip_info.channel.ipinfo_api.requests.get", return_value=mock_response):
            with pytest.raises(ChannelPermanentError, match="IPInfo API Token 无效"):
                channel._validate_key()

    def test_验证请求网络错误_异常向上抛出(self):
        channel = IpinfoApiChannel(token="valid_token")
        with patch(
            "ip_info.channel.ipinfo_api.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(requests.exceptions.Timeout):
                channel._validate_key()


class TestIpinfoApiRequest:
    def test_查询成功_HTTP200(self):
        channel = IpinfoApiChannel(token="valid_token")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ip": "8.8.8.8", "country": "US"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.ipinfo_api.requests.get", return_value=mock_response) as mock_get:
            result = channel._request("8.8.8.8")

        assert result == {"ip": "8.8.8.8", "country": "US"}
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["headers"]["Authorization"] == "Bearer valid_token"

    def test_Token无效_HTTP401_抛ChannelPermanentError(self):
        channel = IpinfoApiChannel(token="bad_token")
        mock_response = MagicMock()
        mock_response.status_code = 401
        with patch("ip_info.channel.ipinfo_api.requests.get", return_value=mock_response):
            with pytest.raises(ChannelPermanentError, match="IPInfo API Token 无效"):
                channel._request("8.8.8.8")

    def test_请求限流_HTTP429_抛ChannelError(self):
        channel = IpinfoApiChannel(token="valid_token")
        mock_response = MagicMock()
        mock_response.status_code = 429
        with patch("ip_info.channel.ipinfo_api.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="IPInfo API 请求限流"):
                channel._request("8.8.8.8")

    def test_网络超时_抛ChannelError(self):
        channel = IpinfoApiChannel(token="valid_token")
        with patch(
            "ip_info.channel.ipinfo_api.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(ChannelError, match="IPInfo API 查询超时"):
                channel._request("8.8.8.8")

    def test_连接失败_抛ChannelError(self):
        channel = IpinfoApiChannel(token="valid_token")
        with patch(
            "ip_info.channel.ipinfo_api.requests.get",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with pytest.raises(ChannelError, match="IPInfo API 连接失败"):
                channel._request("8.8.8.8")

    def test_其他HTTP错误_HTTP500_抛ChannelError(self):
        channel = IpinfoApiChannel(token="valid_token")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        with patch("ip_info.channel.ipinfo_api.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="HTTP 500"):
                channel._request("8.8.8.8")

    def test_其他非预期异常_抛ChannelError(self):
        channel = IpinfoApiChannel(token="valid_token")
        with patch(
            "ip_info.channel.ipinfo_api.requests.get",
            side_effect=ValueError("bad"),
        ):
            with pytest.raises(ChannelError, match="IPInfo API 查询错误"):
                channel._request("8.8.8.8")


class TestIpinfoApiFetch:
    def test_fetch完整流程_包含query_time(self):
        channel = IpinfoApiChannel(token="valid_token")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ip": "8.8.8.8", "country": "US"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.ipinfo_api.requests.get", return_value=mock_response):
            result = channel.fetch("8.8.8.8")

        assert "query_time" in result
        assert result["ip"] == "8.8.8.8"
        assert result["country"] == "US"

    def test_fetch_Token无效设disabled为True(self):
        channel = IpinfoApiChannel(token="bad_token")
        assert channel.disabled is False
        mock_response = MagicMock()
        mock_response.status_code = 401
        with patch("ip_info.channel.ipinfo_api.requests.get", return_value=mock_response):
            with pytest.raises(ChannelPermanentError, match="Token 无效"):
                channel.fetch("8.8.8.8")

        assert channel.disabled is True

    def test_fetch_网络错误不改变disabled(self):
        channel = IpinfoApiChannel(token="valid_token")
        assert channel.disabled is False
        with patch(
            "ip_info.channel.ipinfo_api.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(ChannelError, match="查询超时"):
                channel.fetch("8.8.8.8")

        assert channel.disabled is False


class TestIpinfoApiValidate:
    def test_validate成功_返回True_disabled为False(self):
        channel = IpinfoApiChannel(token="valid_token")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.ipinfo_api.requests.get", return_value=mock_response):
            result = channel.validate()

        assert result is True
        assert channel.disabled is False

    def test_validate失败_返回False_disabled为True(self):
        channel = IpinfoApiChannel(token="bad_token")
        with patch.object(channel, "_validate_key", side_effect=ChannelPermanentError("Token 无效")):
            result = channel.validate()

        assert result is False
        assert channel.disabled is True


class TestIpinfoApiProtocol:
    def test_满足ChannelProtocol(self):
        channel = IpinfoApiChannel(token="valid_token")
        assert isinstance(channel, ChannelProtocol) is True
