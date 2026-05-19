import os
import sys

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from channel.fofa_host import (
    request_channel,
    fetch_channel,
    format_output,
    validate_channel_key,
    FofaHostChannel,
)


class TestRequestChannel:

    def test_normal_response_returns_json(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ip": "1.2.3.4",
            "detail": [
                {"port": 80, "protocol": "http"},
                {"port": 443, "protocol": "https"},
            ],
        }
        mock_resp.raise_for_status.return_value = None

        with patch('channel.fofa_host.requests.get', return_value=mock_resp) as mock_get:
            result = request_channel("1.2.3.4", key="test_key", timeout=10.0)

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "fofa.info/api/v1/host/1.2.3.4" in call_args[0][0]
        assert call_args[1]["params"]["key"] == "test_key"
        assert call_args[1]["params"]["detail"] == "true"
        assert call_args[1]["timeout"] == 10.0
        assert result["ip"] == "1.2.3.4"
        assert len(result["detail"]) == 2

    def test_timeout_returns_error_dict(self):
        import requests as req
        with patch('channel.fofa_host.requests.get', side_effect=req.exceptions.Timeout("连接超时")):
            result = request_channel("1.2.3.4", key="test_key", timeout=5.0)

        assert result["raw_error"] is True
        assert "连接超时" in result["error_message"]

    def test_http_error_returns_error_dict(self):
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("401 Unauthorized")

        with patch('channel.fofa_host.requests.get', return_value=mock_resp):
            result = request_channel("1.2.3.4", key="bad_key")

        assert result["raw_error"] is True
        assert "401" in result["error_message"]

    def test_invalid_json_returns_error_dict(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("No JSON")

        with patch('channel.fofa_host.requests.get', return_value=mock_resp):
            result = request_channel("1.2.3.4", key="test_key")

        assert result["raw_error"] is True
        assert "No JSON" in result["error_message"]

    def test_connection_error_returns_error_dict(self):
        import requests as req
        with patch('channel.fofa_host.requests.get', side_effect=req.exceptions.ConnectionError("DNS 解析失败")):
            result = request_channel("1.2.3.4", key="test_key")

        assert result["raw_error"] is True
        assert "DNS" in result["error_message"]

    def test_api_error_response_not_wrapped(self):
        api_response = {"error": True, "errmsg": "invalid key", "size": 0}
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_response
        mock_resp.raise_for_status.return_value = None

        with patch('channel.fofa_host.requests.get', return_value=mock_resp):
            result = request_channel("1.2.3.4", key="bad_key")

        assert "raw_error" not in result
        assert result["error"] is True
        assert result["errmsg"] == "invalid key"

    def test_empty_result(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ip": "10.0.0.1", "detail": []}
        mock_resp.raise_for_status.return_value = None

        with patch('channel.fofa_host.requests.get', return_value=mock_resp):
            result = request_channel("10.0.0.1", key="test_key")

        assert result["ip"] == "10.0.0.1"
        assert result["detail"] == []


class TestFetchChannel:

    def test_normal_flow_adds_query_time(self):
        api_data = {"ip": "1.2.3.4", "detail": [{"port": 80}]}
        with patch('channel.fofa_host.request_channel', return_value=api_data):
            with patch('channel.fofa_host.apply_delay'):
                result = fetch_channel("1.2.3.4", key="k", delay=0, timeout=10)

        assert "query_time" in result
        assert result["ip"] == "1.2.3.4"

    def test_error_flow_still_adds_query_time(self):
        error_data = {"raw_error": True, "error_message": "timeout"}
        with patch('channel.fofa_host.request_channel', return_value=error_data):
            with patch('channel.fofa_host.apply_delay'):
                result = fetch_channel("1.2.3.4", key="k", delay=0, timeout=10)

        assert "query_time" in result
        assert result["raw_error"] is True

    def test_delay_is_applied(self):
        with patch('channel.fofa_host.request_channel', return_value={"ip": "1.2.3.4"}):
            with patch('channel.fofa_host.apply_delay') as mock_delay:
                fetch_channel("1.2.3.4", key="k", delay=2.5, timeout=10)

        mock_delay.assert_called_once_with(2.5)

    def test_passes_kwargs_to_request_channel(self):
        with patch('channel.fofa_host.request_channel', return_value={"ip": "1.2.3.4"}) as mock_req:
            with patch('channel.fofa_host.apply_delay'):
                fetch_channel("1.2.3.4", key="mykey", delay=0, timeout=15.0)

        mock_req.assert_called_once_with("1.2.3.4", key="mykey", timeout=15.0)


class TestFormatOutput:

    def test_adds_query_time_if_missing(self):
        data = {"ip": "1.2.3.4"}
        result = format_output(data)
        assert "query_time" in result
        assert result["ip"] == "1.2.3.4"

    def test_preserves_existing_query_time(self):
        data = {"ip": "1.2.3.4", "query_time": "2024-01-01T00:00:00"}
        result = format_output(data)
        assert result["query_time"] == "2024-01-01T00:00:00"

    def test_mutates_input_dict(self):
        data = {"ip": "1.2.3.4"}
        result = format_output(data)
        assert result is data


class TestValidateChannelKey:

    def test_empty_key_exits(self):
        with patch('channel.fofa_host.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.fofa_api_key = ""
            MockSettings.return_value = mock_settings
            with pytest.raises(SystemExit):
                validate_channel_key()

    def test_whitespace_key_exits(self):
        with patch('channel.fofa_host.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.fofa_api_key = "   "
            MockSettings.return_value = mock_settings
            with pytest.raises(SystemExit):
                validate_channel_key()

    def test_invalid_key_exits(self):
        with patch('channel.fofa_host.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.fofa_api_key = "bad_key"
            mock_settings.fofa_validate_timeout = 10
            MockSettings.return_value = mock_settings

            mock_resp = MagicMock()
            mock_resp.json.return_value = {"error": True, "errmsg": "invalid key"}
            mock_resp.raise_for_status.return_value = None

            with patch('channel.fofa_host.requests.get', return_value=mock_resp):
                with pytest.raises(SystemExit):
                    validate_channel_key()

    def test_network_error_exits(self):
        import requests as req
        with patch('channel.fofa_host.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.fofa_api_key = "test_key"
            mock_settings.fofa_validate_timeout = 10
            MockSettings.return_value = mock_settings

            with patch('channel.fofa_host.requests.get', side_effect=req.exceptions.ConnectionError("网络错误")):
                with pytest.raises(SystemExit):
                    validate_channel_key()

    def test_valid_key_succeeds(self):
        with patch('channel.fofa_host.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.fofa_api_key = "valid_key"
            mock_settings.fofa_validate_timeout = 10
            MockSettings.return_value = mock_settings

            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "error": False,
                "data": {"user_name": "test_user"},
            }
            mock_resp.raise_for_status.return_value = None

            with patch('channel.fofa_host.requests.get', return_value=mock_resp):
                validate_channel_key()


class TestFofaHostChannelExtra:

    def test_fetch_with_extra_kwargs(self):
        ch = FofaHostChannel()
        expected = {"ip": "1.2.3.4", "query_time": "2024-01-01"}
        with patch('channel.fofa_host.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch("1.2.3.4", key="k", timeout=20, delay=0)

        mock_fetch.assert_called_once_with("1.2.3.4", key="k", timeout=20, delay=0)
        assert result == expected
