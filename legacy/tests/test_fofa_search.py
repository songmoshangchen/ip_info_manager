import base64
import os
import sys

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from channel.fofa_search import (
    request_channel,
    fetch_channel,
    format_output,
    validate_channel_key,
    FofaSearchChannel,
)


class TestRequestChannel:

    def test_normal_response(self):
        api_data = {
            "results": [["1.2.3.4", "80", "example.com", "http"]],
            "size": 1,
            "page": 1,
            "message": "ok",
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_data
        mock_resp.raise_for_status.return_value = None

        with patch('channel.fofa_search.requests.get', return_value=mock_resp) as mock_get:
            result = request_channel("1.2.3.4", key="test_key", timeout=10.0)

        assert result["size"] == 1
        call_args = mock_get.call_args
        assert "fofa.info/api/v1/search/all" in call_args[0][0]
        assert call_args[1]["params"]["key"] == "test_key"

    def test_timeout_returns_error(self):
        import requests as req
        with patch('channel.fofa_search.requests.get', side_effect=req.exceptions.Timeout("Read timed out")):
            result = request_channel("1.2.3.4", key="test")

        assert result["raw_error"] is True

    def test_http_error_returns_error(self):
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("401")

        with patch('channel.fofa_search.requests.get', return_value=mock_resp):
            result = request_channel("1.2.3.4", key="bad")

        assert result["raw_error"] is True

    def test_invalid_json_returns_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("No JSON")

        with patch('channel.fofa_search.requests.get', return_value=mock_resp):
            result = request_channel("1.2.3.4", key="test")

        assert result["raw_error"] is True

    def test_query_suffix_encoded(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [], "size": 0}
        mock_resp.raise_for_status.return_value = None

        with patch('channel.fofa_search.requests.get', return_value=mock_resp) as mock_get:
            request_channel("1.2.3.4", key="k", query_suffix=" and port=80")

        params = mock_get.call_args[1]["params"]
        decoded = base64.b64decode(params["qbase64"]).decode()
        assert 'port=80' in decoded

    def test_empty_results(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [], "size": 0, "page": 1}
        mock_resp.raise_for_status.return_value = None

        with patch('channel.fofa_search.requests.get', return_value=mock_resp):
            result = request_channel("1.2.3.4", key="test")

        assert result["size"] == 0


class TestFetchChannel:

    def test_normal_flow(self):
        api_data = {"results": [], "size": 0}
        with patch('channel.fofa_search.request_channel', return_value=api_data):
            with patch('channel.fofa_search.apply_delay'):
                result = fetch_channel("1.2.3.4", key="k", delay=0, timeout=10)

        assert "query_time" in result

    def test_error_flow(self):
        error_data = {"raw_error": True, "error_message": "timeout"}
        with patch('channel.fofa_search.request_channel', return_value=error_data):
            with patch('channel.fofa_search.apply_delay'):
                result = fetch_channel("1.2.3.4", key="k", delay=0)

        assert result["raw_error"] is True
        assert "query_time" in result

    def test_delay_applied(self):
        with patch('channel.fofa_search.request_channel', return_value={"size": 0}):
            with patch('channel.fofa_search.apply_delay') as mock_delay:
                fetch_channel("1.2.3.4", key="k", delay=3.0)

        mock_delay.assert_called_once_with(3.0)


class TestFormatOutput:

    def test_adds_query_time_and_fields(self):
        data = {"results": [], "size": 0}
        result = format_output(data)
        assert "query_time" in result
        assert "fields" in result

    def test_preserves_existing_query_time(self):
        data = {"query_time": "2024-01-01"}
        result = format_output(data)
        assert result["query_time"] == "2024-01-01"


class TestValidateChannelKey:

    def test_empty_key_exits(self):
        with patch('channel.fofa_search.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.fofa_api_key = ""
            MockSettings.return_value = mock_settings
            with pytest.raises(SystemExit):
                validate_channel_key()

    def test_invalid_key_exits(self):
        with patch('channel.fofa_search.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.fofa_api_key = "bad_key"
            mock_settings.fofa_validate_timeout = 10
            MockSettings.return_value = mock_settings

            mock_resp = MagicMock()
            mock_resp.json.return_value = {"error": True, "errmsg": "invalid key"}
            mock_resp.raise_for_status.return_value = None

            with patch('channel.fofa_search.requests.get', return_value=mock_resp):
                with pytest.raises(SystemExit):
                    validate_channel_key()

    def test_valid_key_succeeds(self):
        with patch('channel.fofa_search.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.fofa_api_key = "valid_key"
            mock_settings.fofa_validate_timeout = 10
            MockSettings.return_value = mock_settings

            mock_resp = MagicMock()
            mock_resp.json.return_value = {"error": False, "data": {"user_name": "test"}}
            mock_resp.raise_for_status.return_value = None

            with patch('channel.fofa_search.requests.get', return_value=mock_resp):
                validate_channel_key()


class TestFofaSearchChannelExtra:

    def test_fetch_delegates(self):
        ch = FofaSearchChannel()
        expected = {"size": 0, "query_time": "2024-01-01"}
        with patch('channel.fofa_search.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch("1.2.3.4", key="k", timeout=20)

        mock_fetch.assert_called_once_with("1.2.3.4", key="k", timeout=20)
        assert result == expected
