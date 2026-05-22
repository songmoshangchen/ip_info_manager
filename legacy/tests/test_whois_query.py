import os
import sys
import socket
from datetime import datetime

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from channel.whois_query import (
    request_channel,
    parse_response,
    fetch_channel,
    validate_channel_key,
    WhoisChannel,
)


def _make_whois_result(**overrides):
    result = MagicMock()
    result.domain_name = overrides.get("domain_name", "example.com")
    result.registrar = overrides.get("registrar", "Test Registrar")
    result.org = overrides.get("org", "Test Org")
    result.country = overrides.get("country", "US")
    result.state = overrides.get("state", "California")
    result.city = overrides.get("city", "Los Angeles")
    result.address = overrides.get("address", "123 Main St")
    result.name = overrides.get("name", "John Doe")
    result.emails = overrides.get("emails", "admin@example.com")
    result.creation_date = overrides.get("creation_date", datetime(2020, 1, 1))
    result.expiration_date = overrides.get("expiration_date", datetime(2025, 1, 1))
    result.updated_date = overrides.get("updated_date", datetime(2023, 6, 1))
    result.name_servers = overrides.get("name_servers", ["ns1.example.com", "ns2.example.com"])
    result.status = overrides.get("status", ["clientTransferProhibited"])
    result.dnssec = overrides.get("dnssec", "unsigned")
    return result


class TestRequestChannel:

    def test_normal_query(self):
        mock_result = _make_whois_result()
        with patch('channel.whois_query.whois_query', return_value=mock_result):
            result = request_channel("example.com", timeout=10)

        assert result is mock_result

    def test_none_result_returns_error(self):
        with patch('channel.whois_query.whois_query', return_value=None):
            result = request_channel("0.0.0.0", timeout=10)

        assert result["raw_error"] is True
        assert "未找到" in result["error_message"]

    def test_timeout_returns_error(self):
        with patch('channel.whois_query.whois_query', side_effect=socket.timeout("timed out")):
            result = request_channel("1.2.3.4", timeout=5)

        assert result["raw_error"] is True
        assert "超时" in result["error_message"]

    def test_exception_returns_error(self):
        with patch('channel.whois_query.whois_query', side_effect=Exception("query failed")):
            result = request_channel("1.2.3.4")

        assert result["raw_error"] is True
        assert "query failed" in result["error_message"]

    def test_whois_not_installed(self):
        with patch('channel.whois_query.whois_query', None):
            result = request_channel("1.2.3.4")

        assert result["raw_error"] is True
        assert "未安装" in result["error_message"]


class TestParseResponse:

    def test_error_dict_passed_through(self):
        error = {"raw_error": True, "error_message": "timeout"}
        result = parse_response(error, "1.2.3.4")
        assert result["has_whois"] is False
        assert result["raw_error"] is True

    def test_normal_parse(self):
        mock_w = _make_whois_result()
        result = parse_response(mock_w, "example.com")

        assert result["has_whois"] is True
        assert result["whois_data"]["domain_name"] == "example.com"
        assert result["whois_data"]["registrar"] == "Test Registrar"
        assert result["whois_data"]["country"] == "US"

    def test_list_fields_take_first(self):
        mock_w = _make_whois_result(
            domain_name=["example.com", "example.org"],
            registrar=["Reg1", "Reg2"],
        )
        result = parse_response(mock_w, "example.com")

        assert result["whois_data"]["domain_name"] == "example.com"
        assert result["whois_data"]["registrar"] == "Reg1"

    @pytest.mark.xfail(reason="BUG: whois parse_response 对空列表 [] 的 truthy 检查会跳过字段而非设为 None")
    def test_empty_list_field_returns_none(self):
        mock_w = _make_whois_result(domain_name=[])
        result = parse_response(mock_w, "example.com")

        assert result["whois_data"]["domain_name"] is None

    def test_datetime_fields_isoformat(self):
        mock_w = _make_whois_result(
            creation_date=datetime(2020, 6, 15, 12, 0, 0),
        )
        result = parse_response(mock_w, "example.com")

        assert "2020-06-15" in result["whois_data"]["creation_date"]

    def test_date_list_takes_first(self):
        mock_w = _make_whois_result(
            creation_date=[datetime(2020, 1, 1), datetime(2019, 1, 1)],
        )
        result = parse_response(mock_w, "example.com")

        assert "2020-01-01" in result["whois_data"]["creation_date"]

    def test_name_servers_as_list(self):
        mock_w = _make_whois_result(name_servers=["ns1.test.com", "ns2.test.com"])
        result = parse_response(mock_w, "example.com")

        assert result["whois_data"]["name_servers"] == ["ns1.test.com", "ns2.test.com"]

    def test_name_servers_string_wrapped(self):
        mock_w = _make_whois_result(name_servers="ns.single.com")
        result = parse_response(mock_w, "example.com")

        assert result["whois_data"]["name_servers"] == ["ns.single.com"]

    def test_none_fields_excluded(self):
        mock_w = _make_whois_result(org=None, city=None)
        result = parse_response(mock_w, "example.com")

        assert "organization" not in result["whois_data"]
        assert "city" not in result["whois_data"]


class TestFetchChannel:

    def test_normal_flow(self):
        mock_w = _make_whois_result()
        with patch('channel.whois_query.request_channel', return_value=mock_w):
            with patch('channel.whois_query.apply_delay'):
                result = fetch_channel("example.com", delay=0)

        assert result["has_whois"] is True
        assert "query_time" in result

    def test_error_flow(self):
        error = {"raw_error": True, "error_message": "timeout"}
        with patch('channel.whois_query.request_channel', return_value=error):
            with patch('channel.whois_query.apply_delay'):
                result = fetch_channel("1.2.3.4", delay=0)

        assert result["raw_error"] is True
        assert result["has_whois"] is False


class TestValidateChannelKey:

    def test_whois_not_installed_exits(self):
        with patch('channel.whois_query.whois_query', None):
            with pytest.raises(SystemExit):
                validate_channel_key()

    def test_successful_validation(self):
        with patch('channel.whois_query.whois_query', return_value=MagicMock()):
            validate_channel_key()

    def test_timeout_still_passes(self):
        with patch('channel.whois_query.whois_query', side_effect=socket.timeout()):
            validate_channel_key()


class TestWhoisChannelExtra:

    def test_fetch_delegates(self):
        ch = WhoisChannel()
        expected = {"has_whois": True}
        with patch('channel.whois_query.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch("example.com", timeout=15)

        mock_fetch.assert_called_once_with("example.com", timeout=15)
        assert result == expected
