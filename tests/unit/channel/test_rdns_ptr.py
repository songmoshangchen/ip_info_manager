import socket
from unittest.mock import patch

import pytest

from ip_info.channel.errors import ChannelError
from ip_info.channel.protocols import ChannelProtocol
from ip_info.channel.rdns_ptr import RdnsPtrChannel


class TestRdnsPtrRequest:
    def test_查询成功_有PTR记录(self):
        channel = RdnsPtrChannel()
        with patch("ip_info.channel.rdns_ptr.socket") as mock_socket:
            mock_socket.gethostbyaddr.return_value = (
                "dns.google",
                ["dns.google"],
                ["8.8.8.8"],
            )
            mock_socket.herror = socket.herror
            mock_socket.gaierror = socket.gaierror
            mock_socket.timeout = socket.timeout
            result = channel._request("8.8.8.8")

        assert result["query_ip"] == "8.8.8.8"
        assert result["hostname"] == "dns.google"
        assert result["aliases"] == ["dns.google"]
        assert result["ip_addresses"] == ["8.8.8.8"]
        assert result["ptr_count"] == 2
        assert result["has_ptr"] is True

    def test_无PTR记录_herror(self):
        channel = RdnsPtrChannel()
        with patch("ip_info.channel.rdns_ptr.socket") as mock_socket:
            mock_socket.gethostbyaddr.side_effect = socket.herror("Unknown host")
            mock_socket.herror = socket.herror
            mock_socket.gaierror = socket.gaierror
            mock_socket.timeout = socket.timeout
            result = channel._request("1.2.3.4")

        assert result["query_ip"] == "1.2.3.4"
        assert result["has_ptr"] is False
        assert result["error_type"] == "herror"
        assert "Unknown host" in result["error_message"]

    def test_地址查询失败_gaierror(self):
        channel = RdnsPtrChannel()
        with patch("ip_info.channel.rdns_ptr.socket") as mock_socket:
            mock_socket.gethostbyaddr.side_effect = socket.gaierror("Name or service not known")
            mock_socket.herror = socket.herror
            mock_socket.gaierror = socket.gaierror
            mock_socket.timeout = socket.timeout
            result = channel._request("1.2.3.4")

        assert result["query_ip"] == "1.2.3.4"
        assert result["has_ptr"] is False
        assert result["error_type"] == "gaierror"

    def test_DNS查询超时_timeout(self):
        channel = RdnsPtrChannel(timeout=3.0)
        with patch("ip_info.channel.rdns_ptr.socket") as mock_socket:
            mock_socket.gethostbyaddr.side_effect = socket.timeout()
            mock_socket.herror = socket.herror
            mock_socket.gaierror = socket.gaierror
            mock_socket.timeout = socket.timeout
            result = channel._request("1.2.3.4")

        assert result["query_ip"] == "1.2.3.4"
        assert result["has_ptr"] is False
        assert result["error_type"] == "timeout"
        assert "3.0" in result["error_message"]

    def test_网络不可用_其他异常_抛ChannelError(self):
        channel = RdnsPtrChannel()
        with patch("ip_info.channel.rdns_ptr.socket") as mock_socket:
            mock_socket.gethostbyaddr.side_effect = OSError("Network unreachable")
            mock_socket.herror = socket.herror
            mock_socket.gaierror = socket.gaierror
            mock_socket.timeout = socket.timeout
            with pytest.raises(ChannelError, match="8.8.8.8.*Network unreachable"):
                channel._request("8.8.8.8")


class TestRdnsPtrFetch:
    def test_fetch完整流程_包含query_time(self):
        channel = RdnsPtrChannel()
        with patch(
            "ip_info.channel.rdns_ptr.socket.gethostbyaddr",
            return_value=("dns.google", ["dns.google"], ["8.8.8.8"]),
        ):
            result = channel.fetch("8.8.8.8")

        assert "query_time" in result
        assert result["query_ip"] == "8.8.8.8"
        assert result["has_ptr"] is True

    def test_fetch网络错误透传ChannelError(self):
        channel = RdnsPtrChannel()
        assert channel.disabled is False
        with patch(
            "ip_info.channel.rdns_ptr.socket.gethostbyaddr",
            side_effect=OSError("Network unreachable"),
        ):
            with pytest.raises(ChannelError, match="Network unreachable"):
                channel.fetch("1.2.3.4")

        assert channel.disabled is False


class TestRdnsPtrProtocol:
    def test_满足ChannelProtocol(self):
        channel = RdnsPtrChannel()
        assert isinstance(channel, ChannelProtocol) is True

    def test_validate永远返回True(self):
        channel = RdnsPtrChannel()
        assert channel.validate() is True
        assert channel.disabled is False

    def test_channel_name(self):
        channel = RdnsPtrChannel()
        assert channel.channel_name == "rdns_ptr"
