import socket
import ssl
from unittest.mock import patch

import pytest

from ip_info.channel.errors import ChannelError
from ip_info.channel.protocols import ChannelProtocol
from ip_info.channel.ssl_cert import SslCertChannel

SAMPLE_CERT_TEXT = (
    "Certificate:\n"
    "    Data:\n"
    "        Version: 3 (0x2)\n"
    "        Serial Number: 1234567890\n"
    "        Signature Algorithm: sha256WithRSAEncryption\n"
    "        Issuer: C = US, O = DigiCert, CN = TestCA\n"
    "        Validity\n"
    "            Not Before: Jan  1 00:00:00 2024 GMT\n"
    "            Not After : Dec 31 23:59:59 2025 GMT\n"
    "        Subject: C = US, ST = California, O = Example, CN = example.com\n"
    "        X509v3 extensions:\n"
    "            X509v3 Subject Alternative Name: \n"
    "                DNS:example.com, DNS:www.example.com, DNS:mail.example.com\n"
)


class TestSslCertRequest:
    def test_成功获取证书文本(self):
        channel = SslCertChannel()
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", return_value=SAMPLE_CERT_TEXT):
            result = channel._request("example.com")

        assert result == SAMPLE_CERT_TEXT

    def test_无SSL证书返回None(self):
        channel = SslCertChannel()
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", return_value=None):
            result = channel._request("0.0.0.0")

        assert result is None

    def test_连接超时_抛ChannelError(self):
        channel = SslCertChannel()
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", side_effect=socket.timeout()):
            with pytest.raises(ChannelError, match="SSL 连接超时"):
                channel._request("1.2.3.4")

    def test_连接被拒绝_抛ChannelError(self):
        channel = SslCertChannel()
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", side_effect=ConnectionRefusedError()):
            with pytest.raises(ChannelError, match="SSL 连接被拒绝"):
                channel._request("1.2.3.4")

    def test_SSL错误_抛ChannelError(self):
        channel = SslCertChannel()
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", side_effect=ssl.SSLError("cert verify failed")):
            with pytest.raises(ChannelError, match="SSL 错误"):
                channel._request("1.2.3.4")

    def test_通用异常_抛ChannelError(self):
        channel = SslCertChannel()
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", side_effect=Exception("unexpected")):
            with pytest.raises(ChannelError, match="SSL 证书获取失败"):
                channel._request("1.2.3.4")


class TestSslCertFetch:
    def test_fetch完整流程_有证书(self):
        channel = SslCertChannel()
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", return_value=SAMPLE_CERT_TEXT):
            result = channel.fetch("example.com")

        assert result["query_target"] == "example.com"
        assert result["has_cert"] is True
        assert result["port"] == 443
        assert result["subject_cn"] == "example.com"
        assert result["issuer_cn"] == "TestCA"
        assert result["not_before"] == "Jan  1 00:00:00 2024 GMT"
        assert result["not_after"] == "Dec 31 23:59:59 2025 GMT"
        assert "example.com" in result["san_domains"]
        assert "www.example.com" in result["san_domains"]
        assert "mail.example.com" in result["san_domains"]
        assert "query_time" in result

    def test_fetch无证书返回has_certFalse(self):
        channel = SslCertChannel()
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", return_value=None):
            result = channel.fetch("0.0.0.0")

        assert result["query_target"] == "0.0.0.0"
        assert result["has_cert"] is False
        assert result["port"] == 443
        assert "query_time" in result

    def test_fetch_CN和SAN合并去重(self):
        cert_text = (
            "        Issuer: CN = TestCA\n"
            "        Subject: CN = example.com\n"
            "        X509v3 Subject Alternative Name: \n"
            "                DNS:example.com, DNS:www.example.com\n"
        )
        channel = SslCertChannel()
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", return_value=cert_text):
            result = channel.fetch("example.com")

        domains = result["domains"]
        assert domains.count("example.com") == 1
        assert "example.com" in domains
        assert "www.example.com" in domains

    def test_fetch_证书缺少字段时使用默认值(self):
        cert_text = "Certificate:\n    Data:\n        Version: 3 (0x2)\n"
        channel = SslCertChannel()
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", return_value=cert_text):
            result = channel.fetch("example.com")

        assert result["has_cert"] is True
        assert result["subject_cn"] == ""
        assert result["issuer_cn"] == ""
        assert result["not_before"] == ""
        assert result["not_after"] == ""
        assert result["san_domains"] == []

    def test_fetch_ChannelError透传(self):
        channel = SslCertChannel()
        assert channel.disabled is False
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", side_effect=socket.timeout()):
            with pytest.raises(ChannelError, match="SSL 连接超时"):
                channel.fetch("1.2.3.4")

        assert channel.disabled is False

    def test_fetch_port参数透传(self):
        channel = SslCertChannel()
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", return_value=SAMPLE_CERT_TEXT):
            result = channel.fetch("example.com", port=8443)

        assert result["port"] == 8443

    def test_fetch_使用默认port(self):
        channel = SslCertChannel()
        with patch("ip_info.channel.ssl_cert._get_ssl_cert_text", return_value=SAMPLE_CERT_TEXT):
            result = channel.fetch("example.com")

        assert result["port"] == 443


class TestSslCertProtocol:
    def test_满足ChannelProtocol(self):
        channel = SslCertChannel()
        assert isinstance(channel, ChannelProtocol) is True

    def test_validate返回True(self):
        channel = SslCertChannel()
        assert channel.validate() is True

    def test_channel_name(self):
        channel = SslCertChannel()
        assert channel.channel_name == "ssl_cert"

    def test_disabled默认False(self):
        channel = SslCertChannel()
        assert channel.disabled is False
