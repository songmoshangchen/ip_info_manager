import os
import sys

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from channel.ipinfo_api import (
    _request_channel_api,
    _request_channel_noapi,
    request_channel,
    fetch_channel,
    validate_channel_key,
    IpinfoApiChannel,
)


class TestRequestChannelApiMode:

    def test_api_mode_normal_response(self):
        api_data = {
            "ip": "8.8.8.8",
            "country": "US",
            "city": "Mountain View",
            "org": "AS15169 Google LLC",
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_data
        mock_resp.raise_for_status.return_value = None

        with patch('channel.ipinfo_api.requests.get', return_value=mock_resp) as mock_get:
            result = _request_channel_api("8.8.8.8", "test_token", timeout=10.0)

        assert result["ip"] == "8.8.8.8"
        assert result["country"] == "US"
        call_args = mock_get.call_args
        assert "api.ipinfo.io/lite/8.8.8.8" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_token"

    def test_api_mode_timeout_returns_error(self):
        import requests as req
        with patch('channel.ipinfo_api.requests.get', side_effect=req.exceptions.Timeout("Read timed out")):
            result = _request_channel_api("8.8.8.8", "key", timeout=5.0)

        assert result["raw_error"] is True

    def test_api_mode_http_error_returns_error(self):
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("401 Unauthorized")

        with patch('channel.ipinfo_api.requests.get', return_value=mock_resp):
            result = _request_channel_api("8.8.8.8", "bad_token", timeout=10.0)

        assert result["raw_error"] is True

    def test_api_mode_invalid_json_returns_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("No JSON")

        with patch('channel.ipinfo_api.requests.get', return_value=mock_resp):
            result = _request_channel_api("8.8.8.8", "test", timeout=10.0)

        assert result["raw_error"] is True


class TestRequestChannelNoApiMode:

    def test_noapi_mode_normal_response(self):
        api_data = {
            "ip": "8.8.8.8",
            "hostname": "dns.google",
            "city": "Mountain View",
            "country": "US",
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_data
        mock_resp.raise_for_status.return_value = None

        with patch('channel.ipinfo_api.requests.get', return_value=mock_resp) as mock_get:
            result = _request_channel_noapi("8.8.8.8", timeout=10.0)

        assert result["ip"] == "8.8.8.8"
        assert result["hostname"] == "dns.google"
        call_args = mock_get.call_args
        assert "ipinfo.io/8.8.8.8/json" in call_args[0][0]

    def test_noapi_mode_timeout_returns_error(self):
        import requests as req
        with patch('channel.ipinfo_api.requests.get', side_effect=req.exceptions.Timeout("Read timed out")):
            result = _request_channel_noapi("8.8.8.8", timeout=10.0)

        assert result["raw_error"] is True

    def test_noapi_mode_rate_limit_returns_error(self):
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("429 Too Many Requests")

        with patch('channel.ipinfo_api.requests.get', return_value=mock_resp):
            result = _request_channel_noapi("8.8.8.8", timeout=10.0)

        assert result["raw_error"] is True

    def test_noapi_returns_different_fields_than_api(self):
        api_data = {"ip": "1.2.3.4", "hostname": "host.example.com", "loc": "37.38,-122.09"}
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_data
        mock_resp.raise_for_status.return_value = None

        with patch('channel.ipinfo_api.requests.get', return_value=mock_resp):
            result = _request_channel_noapi("1.2.3.4", timeout=10.0)

        assert "hostname" in result
        assert "loc" in result


class TestRequestChannelDispatch:

    def test_use_api_true_calls_api(self):
        with patch('channel.ipinfo_api._request_channel_api', return_value={"ip": "1.2.3.4"}) as mock_api:
            request_channel("1.2.3.4", key="k", use_api=True, timeout=10)

        mock_api.assert_called_once_with("1.2.3.4", "k", timeout=10)

    def test_use_api_false_calls_noapi(self):
        with patch('channel.ipinfo_api._request_channel_noapi', return_value={"ip": "1.2.3.4"}) as mock_noapi:
            request_channel("1.2.3.4", key="k", use_api=False, timeout=10)

        mock_noapi.assert_called_once_with("1.2.3.4", timeout=10)


class TestFetchChannel:

    def test_api_mode_adds_query_time(self):
        api_data = {"ip": "8.8.8.8", "country": "US"}
        with patch('channel.ipinfo_api.request_channel', return_value=api_data):
            with patch('channel.ipinfo_api.apply_delay'):
                result = fetch_channel("8.8.8.8", key="k", delay=0, use_api=True, timeout=10)

        assert "query_time" in result
        assert result["country"] == "US"

    def test_noapi_mode_adds_query_time(self):
        noapi_data = {"ip": "8.8.8.8", "hostname": "dns.google"}
        with patch('channel.ipinfo_api.request_channel', return_value=noapi_data):
            with patch('channel.ipinfo_api.apply_delay'):
                result = fetch_channel("8.8.8.8", key="", delay=0, use_api=False, timeout=10)

        assert "query_time" in result
        assert result["hostname"] == "dns.google"

    def test_error_flow_adds_query_time(self):
        error_data = {"raw_error": True, "error_message": "timeout"}
        with patch('channel.ipinfo_api.request_channel', return_value=error_data):
            with patch('channel.ipinfo_api.apply_delay'):
                result = fetch_channel("8.8.8.8", key="k", delay=0)

        assert result["raw_error"] is True
        assert "query_time" in result

    def test_delay_is_applied(self):
        with patch('channel.ipinfo_api.request_channel', return_value={"ip": "1.2.3.4"}):
            with patch('channel.ipinfo_api.apply_delay') as mock_delay:
                fetch_channel("1.2.3.4", delay=2.5)

        mock_delay.assert_called_once_with(2.5)


class TestValidateChannelKey:

    def test_with_valid_token(self):
        with patch('channel.ipinfo_api.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.ipinfo_access_token = "valid_token"
            mock_settings.ipinfo_validate_timeout = 10
            MockSettings.return_value = mock_settings

            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            with patch('channel.ipinfo_api.requests.get', return_value=mock_resp):
                validate_channel_key()

    def test_with_invalid_token_exits(self):
        with patch('channel.ipinfo_api.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.ipinfo_access_token = "bad_token"
            mock_settings.ipinfo_validate_timeout = 10
            MockSettings.return_value = mock_settings

            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = Exception("401")
            with patch('channel.ipinfo_api.requests.get', return_value=mock_resp):
                with pytest.raises(SystemExit):
                    validate_channel_key()

    def test_without_token_uses_free_api(self):
        with patch('channel.ipinfo_api.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.ipinfo_access_token = ""
            mock_settings.ipinfo_validate_timeout = 10
            MockSettings.return_value = mock_settings

            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            with patch('channel.ipinfo_api.requests.get', return_value=mock_resp) as mock_get:
                validate_channel_key()

            assert "ipinfo.io/8.8.8.8/json" in mock_get.call_args[0][0]

    def test_without_token_free_api_unreachable_exits(self):
        with patch('channel.ipinfo_api.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.ipinfo_access_token = ""
            mock_settings.ipinfo_validate_timeout = 10
            MockSettings.return_value = mock_settings

            with patch('channel.ipinfo_api.requests.get', side_effect=Exception("network error")):
                with pytest.raises(SystemExit):
                    validate_channel_key()


class TestIpinfoApiChannelExtra:

    def test_fetch_delegates(self):
        ch = IpinfoApiChannel()
        expected = {"ip": "1.2.3.4", "query_time": "2024-01-01"}
        with patch('channel.ipinfo_api.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch("1.2.3.4", key="k", use_api=True, timeout=20)

        mock_fetch.assert_called_once_with("1.2.3.4", key="k", use_api=True, timeout=20)
        assert result == expected
