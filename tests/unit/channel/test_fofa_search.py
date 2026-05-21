import base64
from unittest.mock import MagicMock, patch

import pytest
import requests

from ip_info.channel.errors import ChannelError, ChannelPermanentError
from ip_info.channel.fofa_search import FofaSearchChannel
from ip_info.channel.protocols import ChannelProtocol


class TestFofaSearchValidateKey:
    def test_Key有效(self):
        channel = FofaSearchChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": False}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_search.requests.get", return_value=mock_response):
            channel._validate_key()

    def test_Key为空_抛ChannelPermanentError(self):
        channel = FofaSearchChannel(key="")
        with pytest.raises(ChannelPermanentError, match="FOFA API Key 未配置"):
            channel._validate_key()

    def test_Key无效_抛ChannelPermanentError(self):
        channel = FofaSearchChannel(key="bad_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": True, "errmsg": "[-700] Account Invalid"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_search.requests.get", return_value=mock_response):
            with pytest.raises(ChannelPermanentError, match=r"\[-700\] Account Invalid"):
                channel._validate_key()

    def test_验证请求网络错误_异常向上抛出(self):
        channel = FofaSearchChannel(key="valid_key")
        with patch(
            "ip_info.channel.fofa_search.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(requests.exceptions.Timeout):
                channel._validate_key()


class TestFofaSearchRequest:
    def test_查询成功有结果(self):
        channel = FofaSearchChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": False,
            "results": [["8.8.8.8", "8.8.8.8", "80"]],
            "size": 1,
        }
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_search.requests.get", return_value=mock_response):
            result = channel._request("8.8.8.8")

        assert result["results"] == [["8.8.8.8", "8.8.8.8", "80"]]
        assert result["size"] == 1

    def test_查询成功无结果(self):
        channel = FofaSearchChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": False, "results": [], "size": 0}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_search.requests.get", return_value=mock_response):
            result = channel._request("8.8.8.8")

        assert result["results"] == []
        assert result["size"] == 0

    def test_query_suffix追加条件(self):
        channel = FofaSearchChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": False, "results": [], "size": 0}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_search.requests.get", return_value=mock_response) as mock_get:
            channel._request("8.8.8.8", query_suffix=' && port="80"')

        call_kwargs = mock_get.call_args
        qbase64 = call_kwargs[1]["params"]["qbase64"]
        decoded = base64.b64decode(qbase64).decode()
        assert decoded == 'ip="8.8.8.8" && port="80"'

    def test_Key无效_700_抛ChannelPermanentError(self):
        channel = FofaSearchChannel(key="bad_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": True, "errmsg": "[-700] Account Invalid"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_search.requests.get", return_value=mock_response):
            with pytest.raises(ChannelPermanentError, match="FOFA API Key 无效"):
                channel._request("8.8.8.8")

    def test_业务错误_抛ChannelError(self):
        channel = FofaSearchChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": True, "errmsg": "[-4] Params Error"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_search.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="FOFA Search 查询业务错误"):
                channel._request("8.8.8.8")

    def test_网络超时_抛ChannelError(self):
        channel = FofaSearchChannel(key="valid_key")
        with patch(
            "ip_info.channel.fofa_search.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(ChannelError, match="FOFA Search 查询超时"):
                channel._request("8.8.8.8")

    def test_连接失败_抛ChannelError(self):
        channel = FofaSearchChannel(key="valid_key")
        with patch(
            "ip_info.channel.fofa_search.requests.get",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with pytest.raises(ChannelError, match="FOFA Search 连接失败"):
                channel._request("8.8.8.8")

    def test_HTTP错误_抛ChannelError(self):
        channel = FofaSearchChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        with patch("ip_info.channel.fofa_search.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="HTTP 500"):
                channel._request("8.8.8.8")

    def test_非JSON响应_抛ChannelError(self):
        channel = FofaSearchChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("bad json")
        with patch("ip_info.channel.fofa_search.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="非JSON"):
                channel._request("8.8.8.8")

    def test_其他异常_抛ChannelError(self):
        channel = FofaSearchChannel(key="valid_key")
        with patch(
            "ip_info.channel.fofa_search.requests.get",
            side_effect=ValueError("unexpected"),
        ):
            with pytest.raises(ChannelError, match="FOFA Search 查询错误"):
                channel._request("8.8.8.8")


class TestFofaSearchFetchAndValidate:
    def test_fetch完整流程_包含query_time(self):
        channel = FofaSearchChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": False, "results": [], "size": 0}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_search.requests.get", return_value=mock_response):
            result = channel.fetch("8.8.8.8")

        assert "query_time" in result
        assert result["results"] == []
        assert result["size"] == 0

    def test_fetch_Key无效设disabled为True(self):
        channel = FofaSearchChannel(key="bad_key")
        assert channel.disabled is False
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": True, "errmsg": "[-700] Account Invalid"}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_search.requests.get", return_value=mock_response):
            with pytest.raises(ChannelPermanentError, match="FOFA API Key 无效"):
                channel.fetch("8.8.8.8")

        assert channel.disabled is True

    def test_fetch_网络错误不改变disabled(self):
        channel = FofaSearchChannel(key="valid_key")
        assert channel.disabled is False
        with patch(
            "ip_info.channel.fofa_search.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(ChannelError, match="查询超时"):
                channel.fetch("8.8.8.8")

        assert channel.disabled is False

    def test_validate成功_返回True(self):
        channel = FofaSearchChannel(key="valid_key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": False}
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.fofa_search.requests.get", return_value=mock_response):
            result = channel.validate()

        assert result is True
        assert channel.disabled is False

    def test_validate失败_返回False(self):
        channel = FofaSearchChannel(key="bad_key")
        with patch.object(channel, "_validate_key", side_effect=ChannelPermanentError("Key 无效")):
            result = channel.validate()

        assert result is False
        assert channel.disabled is True

    def test_满足ChannelProtocol(self):
        channel = FofaSearchChannel(key="valid_key")
        assert isinstance(channel, ChannelProtocol) is True
