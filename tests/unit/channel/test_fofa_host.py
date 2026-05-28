from unittest.mock import MagicMock, patch

import pytest
import requests

from ip_info.channel.config import FofaHostConfig
from ip_info.channel.errors import ChannelError, ChannelPermanentError
from ip_info.channel.fofa_host import FofaHostChannel
from ip_info.channel.protocols import ChannelProtocol


class TestFofaHostValidateKey:
    def test_Key有效_API返回error_false(self):
        channel = FofaHostChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": False, "data": {"user_name": "test"}}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_host.requests.get", return_value=mock_response):
            result = channel.validate()
        assert result is True
        assert channel.disabled is False

    def test_Key为空_validate返回False(self):
        channel = FofaHostChannel(key="", config=FofaHostConfig(fofa_api_key="", _env_file=None))
        result = channel.validate()
        assert result is False
        assert channel.disabled is True

    def test_Key无效_API返回error_true_validate返回False(self):
        channel = FofaHostChannel(key="bad_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": True, "errmsg": "[-700] Account Invalid"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_host.requests.get", return_value=mock_response):
            result = channel.validate()
        assert result is False
        assert channel.disabled is True

    def test_验证请求网络错误_validate返回False(self):
        channel = FofaHostChannel(key="valid_key")
        with patch(
            "ip_info.channel.fofa_host.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            result = channel.validate()
        assert result is False
        assert channel.disabled is True


class TestFofaHostRequest:
    def test_查询成功_HTTP200_error_false(self):
        channel = FofaHostChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": False, "host": "8.8.8.8", "ip": "8.8.8.8"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_host.requests.get", return_value=mock_response) as mock_get:
            result = channel.fetch("8.8.8.8")

        assert "query_time" in result
        assert result["host"] == "8.8.8.8"
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["params"]["key"] == "valid_key"
        assert call_kwargs[1]["params"]["detail"] == "true"

    def test_Key无效_error_true_700_抛ChannelPermanentError(self):
        channel = FofaHostChannel(key="bad_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": True, "errmsg": "[-700] Account Invalid"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_host.requests.get", return_value=mock_response):
            with pytest.raises(ChannelPermanentError, match="FOFA API Key 无效"):
                channel.fetch("8.8.8.8")

    def test_业务错误_error_true_其他_抛ChannelError(self):
        channel = FofaHostChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": True, "errmsg": "[-4] Params Error"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_host.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="FOFA Host 查询业务错误"):
                channel.fetch("8.8.8.8")

    def test_网络超时_抛ChannelError(self):
        channel = FofaHostChannel(key="valid_key")
        with patch(
            "ip_info.channel.fofa_host.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(ChannelError, match="FOFA Host 查询超时"):
                channel.fetch("8.8.8.8")

    def test_连接失败_抛ChannelError(self):
        channel = FofaHostChannel(key="valid_key")
        with patch(
            "ip_info.channel.fofa_host.requests.get",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with pytest.raises(ChannelError, match="FOFA Host 连接失败"):
                channel.fetch("8.8.8.8")

    def test_HTTP错误_HTTP500_抛ChannelError(self):
        channel = FofaHostChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        with patch("ip_info.channel.fofa_host.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="HTTP 500"):
                channel.fetch("8.8.8.8")

    def test_其他非预期异常_抛ChannelError(self):
        channel = FofaHostChannel(key="valid_key")
        with patch(
            "ip_info.channel.fofa_host.requests.get",
            side_effect=ValueError("bad"),
        ):
            with pytest.raises(ChannelError, match="FOFA Host 查询错误"):
                channel.fetch("8.8.8.8")


class TestFofaHostFetch:
    def test_fetch完整流程_包含query_time(self):
        channel = FofaHostChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": False, "host": "8.8.8.8"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_host.requests.get", return_value=mock_response):
            result = channel.fetch("8.8.8.8")

        assert "query_time" in result
        assert result["host"] == "8.8.8.8"

    def test_fetch_Key无效设disabled为True(self):
        channel = FofaHostChannel(key="bad_key")
        assert channel.disabled is False
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": True, "errmsg": "[-700] Account Invalid"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_host.requests.get", return_value=mock_response):
            with pytest.raises(ChannelPermanentError, match="FOFA API Key 无效"):
                channel.fetch("8.8.8.8")

        assert channel.disabled is True

    def test_fetch_网络错误不改变disabled(self):
        channel = FofaHostChannel(key="valid_key")
        assert channel.disabled is False
        with patch(
            "ip_info.channel.fofa_host.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(ChannelError, match="查询超时"):
                channel.fetch("8.8.8.8")

        assert channel.disabled is False


class TestFofaHostValidateAndProtocol:
    def test_validate成功_返回True_disabled为False(self):
        channel = FofaHostChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": False, "data": {"user_name": "test"}}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_host.requests.get", return_value=mock_response):
            result = channel.validate()

        assert result is True
        assert channel.disabled is False

    def test_validate失败_返回False_disabled为True(self):
        channel = FofaHostChannel(key="bad_key")
        with patch.object(channel, "_validate_key", side_effect=ChannelPermanentError("Key 无效")):
            result = channel.validate()

        assert result is False
        assert channel.disabled is True

    def test_满足ChannelProtocol(self):
        channel = FofaHostChannel(key="valid_key")
        assert isinstance(channel, ChannelProtocol) is True
