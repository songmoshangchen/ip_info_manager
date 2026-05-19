import base64
import os
import sys

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from channel.zoomeye import (
    request_channel,
    fetch_channel,
    format_output,
    validate_channel_key,
    ZoomeyeChannel,
)


class TestRequestChannel:

    def test_normal_response(self):
        api_data = {
            "message": "success",
            "total": 5,
            "data": [
                {"ip": "1.2.3.4", "port": 80, "domain": "example.com"},
            ],
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_data
        mock_resp.raise_for_status.return_value = None

        with patch('channel.zoomeye.requests.post', return_value=mock_resp) as mock_post:
            result = request_channel("1.2.3.4", key="test_key", timeout=10.0)

        assert result["total"] == 5
        call_args = mock_post.call_args
        assert "zoomeye.org/v2/search" in call_args[0][0]
        assert call_args[1]["headers"]["API-KEY"] == "test_key"

    def test_api_error_message(self):
        api_data = {"message": "invalid api key"}
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_data
        mock_resp.raise_for_status.return_value = None

        with patch('channel.zoomeye.requests.post', return_value=mock_resp):
            result = request_channel("1.2.3.4", key="bad_key")

        assert result["raw_error"] is True
        assert "invalid api key" in result["error_message"]

    def test_timeout_returns_error(self):
        import requests as req
        with patch('channel.zoomeye.requests.post', side_effect=req.exceptions.Timeout("Read timed out")):
            result = request_channel("1.2.3.4", key="test")

        assert result["raw_error"] is True

    def test_http_error_returns_error(self):
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("401")

        with patch('channel.zoomeye.requests.post', return_value=mock_resp):
            result = request_channel("1.2.3.4", key="bad")

        assert result["raw_error"] is True

    def test_connection_error_returns_error(self):
        import requests as req
        with patch('channel.zoomeye.requests.post', side_effect=req.exceptions.ConnectionError("DNS failed")):
            result = request_channel("1.2.3.4", key="test")

        assert result["raw_error"] is True

    def test_query_encoded_in_body(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": "success", "total": 0, "data": []}
        mock_resp.raise_for_status.return_value = None

        with patch('channel.zoomeye.requests.post', return_value=mock_resp) as mock_post:
            request_channel("1.2.3.4", key="k")

        body = mock_post.call_args[1]["json"]
        decoded = base64.b64decode(body["qbase64"]).decode()
        assert "1.2.3.4" in decoded

    def test_sub_type_passed(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": "success", "total": 0, "data": []}
        mock_resp.raise_for_status.return_value = None

        with patch('channel.zoomeye.requests.post', return_value=mock_resp) as mock_post:
            request_channel("1.2.3.4", key="k", sub_type="web")

        body = mock_post.call_args[1]["json"]
        assert body["sub_type"] == "web"

    def test_empty_results(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": "success", "total": 0, "data": []}
        mock_resp.raise_for_status.return_value = None

        with patch('channel.zoomeye.requests.post', return_value=mock_resp):
            result = request_channel("1.2.3.4", key="test")

        assert result["total"] == 0
        assert "raw_error" not in result


class TestFetchChannel:

    def test_normal_flow(self):
        api_data = {"message": "success", "total": 1, "data": []}
        with patch('channel.zoomeye.request_channel', return_value=api_data):
            with patch('channel.zoomeye.apply_delay'):
                result = fetch_channel("1.2.3.4", key="k", delay=0, timeout=10)

        assert "query_time" in result
        assert result["total"] == 1

    def test_error_flow(self):
        error_data = {"raw_error": True, "error_message": "timeout"}
        with patch('channel.zoomeye.request_channel', return_value=error_data):
            with patch('channel.zoomeye.apply_delay'):
                result = fetch_channel("1.2.3.4", key="k", delay=0)

        assert result["raw_error"] is True
        assert "query_time" in result

    def test_delay_applied(self):
        with patch('channel.zoomeye.request_channel', return_value={"message": "success", "total": 0, "data": []}):
            with patch('channel.zoomeye.apply_delay') as mock_delay:
                fetch_channel("1.2.3.4", key="k", delay=2.5)

        mock_delay.assert_called_once_with(2.5)


class TestFormatOutput:

    def test_adds_query_time(self):
        data = {"total": 0}
        result = format_output(data)
        assert "query_time" in result

    def test_preserves_existing(self):
        data = {"query_time": "2024-01-01"}
        result = format_output(data)
        assert result["query_time"] == "2024-01-01"


class TestValidateChannelKey:

    def test_empty_key_exits(self):
        with patch('channel.zoomeye.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.zoomeye_api_key = ""
            MockSettings.return_value = mock_settings
            with pytest.raises(SystemExit):
                validate_channel_key()

    def test_valid_key_succeeds(self):
        with patch('channel.zoomeye.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.zoomeye_api_key = "valid_key"
            MockSettings.return_value = mock_settings
            validate_channel_key()

    def test_whitespace_key_exits(self):
        with patch('channel.zoomeye.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.zoomeye_api_key = "   "
            MockSettings.return_value = mock_settings
            with pytest.raises(SystemExit):
                validate_channel_key()


class TestZoomeyeChannelExtra:

    def test_fetch_delegates(self):
        ch = ZoomeyeChannel()
        expected = {"total": 0, "query_time": "2024-01-01"}
        with patch('channel.zoomeye.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch("1.2.3.4", key="k", timeout=20)

        mock_fetch.assert_called_once_with("1.2.3.4", key="k", timeout=20)
        assert result == expected
