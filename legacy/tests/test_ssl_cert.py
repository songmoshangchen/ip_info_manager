import os
import sys
import socket
import ssl

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from channel.ssl_cert import (
    request_channel,
    fetch_channel,
    format_output,
    _parse_domains,
    SslCertChannel,
)


SAMPLE_CERT_TEXT = """
Certificate:
    Data:
        Version: 3 (0x2)
        Subject: C=US, ST=California, O=Test Org, CN=example.com
        Issuer: C=US, O=Test CA, CN=Test CA Root
        Validity
            Not Before: Jan  1 00:00:00 2024 GMT
            Not After : Dec 31 23:59:59 2025 GMT
        X509v3 extensions:
            X509v3 Subject Alternative Name:
                DNS:example.com, DNS:*.example.com, DNS:www.example.org
"""


class TestRequestChannel:

    def test_normal_cert(self):
        with patch('channel.ssl_cert._get_ssl_cert_text', return_value=SAMPLE_CERT_TEXT):
            result = request_channel("1.2.3.4", port=443, timeout=5.0)

        assert "cert_text" in result
        assert "raw_error" not in result

    def test_no_cert(self):
        with patch('channel.ssl_cert._get_ssl_cert_text', return_value=None):
            result = request_channel("1.2.3.4", port=443)

        assert result["raw_error"] is True
        assert result["error_message"] == "no_cert"

    def test_connection_timeout(self):
        with patch('channel.ssl_cert._get_ssl_cert_text', side_effect=socket.timeout("timed out")):
            result = request_channel("1.2.3.4", port=443, timeout=5.0)

        assert result["raw_error"] is True
        assert result["error_message"] == "connection_timeout"

    def test_connection_refused(self):
        with patch('channel.ssl_cert._get_ssl_cert_text', side_effect=ConnectionRefusedError("refused")):
            result = request_channel("1.2.3.4", port=443)

        assert result["raw_error"] is True
        assert result["error_message"] == "connection_refused"

    def test_ssl_error(self):
        with patch('channel.ssl_cert._get_ssl_cert_text', side_effect=ssl.SSLError("cert verify failed")):
            result = request_channel("1.2.3.4", port=443)

        assert result["raw_error"] is True
        assert "ssl_error" in result["error_message"]

    def test_generic_exception(self):
        with patch('channel.ssl_cert._get_ssl_cert_text', side_effect=OSError("unknown")):
            result = request_channel("1.2.3.4", port=443)

        assert result["raw_error"] is True


class TestParseDomains:

    def test_cn_and_san_extracted(self):
        domains = _parse_domains(SAMPLE_CERT_TEXT)
        assert "example.com" in domains
        assert "*.example.com" in domains
        assert "www.example.org" in domains

    def test_cn_only(self):
        cert_text = "Subject: C=US, CN=only-cn.com\n"
        domains = _parse_domains(cert_text)
        assert domains == ["only-cn.com"]

    def test_san_only(self):
        cert_text = "Subject Alternative Name:\n    DNS:san1.com, DNS:san2.com\n"
        domains = _parse_domains(cert_text)
        assert "san1.com" in domains
        assert "san2.com" in domains

    def test_no_domains(self):
        cert_text = "Certificate:\n    Data:\n        Version: 3\n"
        domains = _parse_domains(cert_text)
        assert domains == []

    def test_deduplication(self):
        cert_text = "Subject: CN=dup.com\n\nSubject Alternative Name:\n    DNS:dup.com, DNS:other.com\n"
        domains = _parse_domains(cert_text)
        assert domains.count("dup.com") == 1
        assert "other.com" in domains


class TestFormatOutput:

    def test_error_result(self):
        result = format_output({"raw_error": True, "error_message": "timeout"}, ip="1.2.3.4", port=443)
        assert result["error"] == "timeout"
        assert result["ip"] == "1.2.3.4"
        assert result["port"] == 443
        assert "query_time" in result

    @pytest.mark.xfail(reason="BUG: ssl_cert format_output 的 issuer_cn 正则 [^/\\n,\\s]+ 会在空格处截断, 如 'Test CA Root' -> 'Test'")
    def test_success_result_issuer_cn_preserved(self):
        cert_result = {"cert_text": SAMPLE_CERT_TEXT}
        result = format_output(cert_result, ip="1.2.3.4", port=443)
        assert result["subject_cn"] == "example.com"
        assert "CA" in result["issuer_cn"]
        assert len(result["san_domains"]) == 3
        assert "query_time" in result

    def test_success_result_basic_fields(self):
        cert_result = {"cert_text": SAMPLE_CERT_TEXT}
        result = format_output(cert_result, ip="1.2.3.4", port=443)
        assert result["subject_cn"] == "example.com"
        assert len(result["san_domains"]) == 3
        assert "query_time" in result
        assert result["ip"] == "1.2.3.4"
        assert result["port"] == 443


class TestFetchChannel:

    def test_normal_flow(self):
        with patch('channel.ssl_cert.request_channel', return_value={"cert_text": SAMPLE_CERT_TEXT}):
            with patch('channel.ssl_cert.apply_delay'):
                result = fetch_channel("1.2.3.4", port=443, delay=0)

        assert result["subject_cn"] == "example.com"
        assert "query_time" in result

    def test_error_flow(self):
        with patch('channel.ssl_cert.request_channel', return_value={"raw_error": True, "error_message": "connection_timeout"}):
            with patch('channel.ssl_cert.apply_delay'):
                result = fetch_channel("1.2.3.4", port=443, delay=0)

        assert result["error"] == "connection_timeout"

    def test_delay_applied(self):
        with patch('channel.ssl_cert.request_channel', return_value={"cert_text": "cert"}):
            with patch('channel.ssl_cert.apply_delay') as mock_delay:
                fetch_channel("1.2.3.4", delay=2.0)

        mock_delay.assert_called_once_with(2.0)


class TestSslCertChannelExtra:

    def test_fetch_delegates(self):
        ch = SslCertChannel()
        expected = {"subject_cn": "test.com", "query_time": "2024-01-01"}
        with patch('channel.ssl_cert.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch("1.2.3.4", port=8443, timeout=10)

        mock_fetch.assert_called_once_with("1.2.3.4", port=8443, timeout=10)
        assert result == expected
