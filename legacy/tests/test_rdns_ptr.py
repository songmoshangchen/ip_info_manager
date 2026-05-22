import os
import sys
import socket

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from channel.rdns_ptr import (
    request_channel,
    fetch_channel,
    validate_channel_key,
    RdnsPtrChannel,
)


class TestRequestChannel:

    def test_single_ptr_record(self):
        with patch('channel.rdns_ptr.socket.gethostbyaddr', return_value=(
            "dns.google", [], ["8.8.8.8"]
        )):
            result = request_channel("8.8.8.8", timeout=3.0)

        assert result["has_ptr"] is True
        assert result["hostname"] == "dns.google"
        assert result["ptr_count"] == 1

    def test_multiple_ptr_records(self):
        with patch('channel.rdns_ptr.socket.gethostbyaddr', return_value=(
            "host.example.com", ["alias1.com", "alias2.com"], ["1.2.3.4"]
        )):
            result = request_channel("1.2.3.4", timeout=3.0)

        assert result["has_ptr"] is True
        assert result["hostname"] == "host.example.com"
        assert len(result["aliases"]) == 2
        assert result["ptr_count"] == 3

    def test_no_ptr_record_herror(self):
        with patch('channel.rdns_ptr.socket.gethostbyaddr', side_effect=socket.herror("Unknown host")):
            result = request_channel("10.0.0.1", timeout=3.0)

        assert result["has_ptr"] is False
        assert result["error_type"] == "herror"

    def test_gaierror(self):
        with patch('channel.rdns_ptr.socket.gethostbyaddr', side_effect=socket.gaierror("Name or service not known")):
            result = request_channel("invalid", timeout=3.0)

        assert result["has_ptr"] is False
        assert result["error_type"] == "gaierror"

    def test_network_timeout(self):
        with patch('channel.rdns_ptr.socket.gethostbyaddr', side_effect=socket.timeout("timed out")):
            result = request_channel("1.2.3.4", timeout=3.0)

        assert result["has_ptr"] is False
        assert result["error_type"] == "timeout"
        assert "3" in result["error_message"]

    def test_unexpected_exception(self):
        with patch('channel.rdns_ptr.socket.gethostbyaddr', side_effect=OSError("network unreachable")):
            result = request_channel("1.2.3.4", timeout=3.0)

        assert result["has_ptr"] is False
        assert result["raw_error"] is True
        assert result["error_type"] == "OSError"

    def test_result_contains_query_ip(self):
        with patch('channel.rdns_ptr.socket.gethostbyaddr', side_effect=socket.herror("no ptr")):
            result = request_channel("192.168.1.1")

        assert result["query_ip"] == "192.168.1.1"


class TestFetchChannel:

    def test_normal_flow(self):
        with patch('channel.rdns_ptr.request_channel', return_value={
            "query_ip": "8.8.8.8", "has_ptr": True, "hostname": "dns.google"
        }):
            with patch('channel.rdns_ptr.apply_delay'):
                result = fetch_channel("8.8.8.8", delay=0, timeout=3.0)

        assert result["has_ptr"] is True
        assert "query_time" in result

    def test_error_flow(self):
        with patch('channel.rdns_ptr.request_channel', return_value={
            "query_ip": "1.2.3.4", "has_ptr": False, "error_type": "timeout",
            "raw_error": True, "error_message": "查询超时"
        }):
            with patch('channel.rdns_ptr.apply_delay'):
                result = fetch_channel("1.2.3.4", delay=0)

        assert result["raw_error"] is True
        assert "query_time" in result

    def test_delay_applied(self):
        with patch('channel.rdns_ptr.request_channel', return_value={"query_ip": "1.2.3.4"}):
            with patch('channel.rdns_ptr.apply_delay') as mock_delay:
                fetch_channel("1.2.3.4", delay=1.5)

        mock_delay.assert_called_once_with(1.5)


class TestValidateChannelKey:

    def test_successful_validation(self):
        with patch('channel.rdns_ptr.socket.gethostbyaddr', return_value=("dns.google", [], ["8.8.8.8"])):
            validate_channel_key()

    def test_herror_still_passes(self):
        with patch('channel.rdns_ptr.socket.gethostbyaddr', side_effect=socket.herror("no ptr")):
            validate_channel_key()

    def test_other_error_exits(self):
        with patch('channel.rdns_ptr.socket.gethostbyaddr', side_effect=OSError("broken")):
            with pytest.raises(SystemExit):
                validate_channel_key()


class TestRdnsPtrChannelExtra:

    def test_fetch_delegates(self):
        ch = RdnsPtrChannel()
        expected = {"has_ptr": True, "hostname": "test.com"}
        with patch('channel.rdns_ptr.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch("1.2.3.4", timeout=5)

        mock_fetch.assert_called_once_with("1.2.3.4", timeout=5)
        assert result == expected
