import os
import sys
import subprocess

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from channel.port_scan import (
    request_channel,
    parse_nmap_xml,
    fetch_channel,
    validate_engine,
    PortScanChannel,
)


SAMPLE_NMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nmaprun>
  <host>
    <status state="up"/>
    <ports>
      <port protocol="tcp" portid="80">
        <state state="open"/>
        <service name="http" product="nginx" version="1.18"/>
      </port>
      <port protocol="tcp" portid="443">
        <state state="open"/>
        <service name="https" product="nginx" version="1.18"/>
      </port>
      <port protocol="tcp" portid="22">
        <state state="closed"/>
        <service name="ssh"/>
      </port>
    </ports>
  </host>
</nmaprun>"""

SAMPLE_NMAP_XML_NO_HOST = '<?xml version="1.0"?><nmaprun></nmaprun>'

INVALID_XML = "this is not xml"


class TestRequestChannel:

    def test_normal_scan(self):
        mock_result = MagicMock()
        mock_result.stdout = SAMPLE_NMAP_XML
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch('channel.port_scan.subprocess.run', return_value=mock_result) as mock_run:
            result = request_channel("1.2.3.4", nmap_path="nmap", port_string="80,443", timeout=30)

        assert "xml_output" in result
        assert result["returncode"] == 0
        cmd = mock_run.call_args[0][0]
        assert "nmap" in cmd
        assert "-p" in cmd
        assert "80,443" in cmd

    def test_nmap_not_found(self):
        with patch('channel.port_scan.subprocess.run', side_effect=FileNotFoundError("nmap not found")):
            result = request_channel("1.2.3.4", nmap_path="nmap")

        assert result["raw_error"] is True
        assert "not found" in result["error_message"]

    def test_nmap_timeout(self):
        with patch('channel.port_scan.subprocess.run', side_effect=subprocess.TimeoutExpired("nmap", 30)):
            result = request_channel("1.2.3.4", nmap_path="nmap", timeout=30)

        assert result["raw_error"] is True
        assert "timeout" in result["error_message"].lower()

    def test_nmap_exception(self):
        with patch('channel.port_scan.subprocess.run', side_effect=OSError("permission denied")):
            result = request_channel("1.2.3.4", nmap_path="nmap")

        assert result["raw_error"] is True

    def test_empty_port_string(self):
        mock_result = MagicMock()
        mock_result.stdout = "<xml/>"
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch('channel.port_scan.subprocess.run', return_value=mock_result) as mock_run:
            request_channel("1.2.3.4", nmap_path="nmap", port_string="")

        cmd = mock_run.call_args[0][0]
        assert "-p" not in cmd


class TestParseNmapXml:

    def test_normal_parse(self):
        result = parse_nmap_xml(SAMPLE_NMAP_XML, historical_ports=[80, 443])

        assert result["host_alive"] is True
        assert result["open_count"] == 2
        assert result["total_scanned"] == 3
        assert 80 in result["historical_ports_verified"]
        assert 443 in result["historical_ports_verified"]
        assert result["open_ports"][0]["service"] == "http"
        assert result["open_ports"][0]["product"] == "nginx"

    def test_no_host_element(self):
        result = parse_nmap_xml(SAMPLE_NMAP_XML_NO_HOST, [])
        assert result["host_alive"] is False
        assert result["open_ports"] == []

    def test_invalid_xml(self):
        result = parse_nmap_xml(INVALID_XML, [])
        assert result["host_alive"] is False
        assert result["open_count"] == 0

    def test_historical_ports_closed(self):
        result = parse_nmap_xml(SAMPLE_NMAP_XML, historical_ports=[80, 22, 8080])
        assert 80 in result["historical_ports_verified"]
        assert 22 in result["historical_ports_closed"]
        assert 8080 in result["historical_ports_closed"]

    def test_empty_xml(self):
        result = parse_nmap_xml("", [])
        assert result["open_count"] == 0

    def test_no_open_ports(self):
        xml = """<?xml version="1.0"?>
        <nmaprun><host><status state="up"/><ports>
            <port protocol="tcp" portid="80"><state state="closed"/></port>
        </ports></host></nmaprun>"""
        result = parse_nmap_xml(xml, [])
        assert result["host_alive"] is True
        assert result["open_count"] == 0
        assert result["total_scanned"] == 1

    @pytest.mark.xfail(reason="BUG: nmap XML 解析异常时未返回 raw_error, 可能导致上层误判")
    def test_malformed_port_id(self):
        xml = """<?xml version="1.0"?>
        <nmaprun><host><status state="up"/><ports>
            <port protocol="tcp" portid="abc"><state state="open"/></port>
        </ports></host></nmaprun>"""
        result = parse_nmap_xml(xml, [])
        assert result["raw_error"] is True


class TestFetchChannel:

    def test_normal_flow(self):
        mock_raw = {
            "xml_output": SAMPLE_NMAP_XML,
            "returncode": 0,
            "stderr": "",
        }
        with patch('channel.port_scan.request_channel', return_value=mock_raw):
            with patch('channel.port_scan.apply_delay'):
                result = fetch_channel("1.2.3.4", nmap_path="nmap", port_string="80,443", delay=0)

        assert result["host_alive"] is True
        assert result["open_count"] == 2
        assert "scan_time" in result
        assert result["engine"] == "nmap"

    def test_error_flow(self):
        with patch('channel.port_scan.request_channel', return_value={"raw_error": True, "error_message": "nmap not found"}):
            with patch('channel.port_scan.apply_delay'):
                result = fetch_channel("1.2.3.4", nmap_path="nmap", delay=0)

        assert "error" in result
        assert result["host_alive"] is False

    def test_nonzero_returncode_included(self):
        mock_raw = {
            "xml_output": SAMPLE_NMAP_XML_NO_HOST,
            "returncode": 1,
            "stderr": "error",
        }
        with patch('channel.port_scan.request_channel', return_value=mock_raw):
            with patch('channel.port_scan.apply_delay'):
                result = fetch_channel("1.2.3.4", delay=0)

        assert result.get("nmap_returncode") == 1


class TestValidateEngine:

    def test_nmap_in_path(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Nmap 7.94"

        with patch('channel.port_scan.subprocess.run', return_value=mock_result):
            resolved = validate_engine()

        assert resolved is not None

    def test_nmap_not_found(self):
        with patch('channel.port_scan.subprocess.run', side_effect=FileNotFoundError()):
            resolved = validate_engine()

        assert resolved is None

    def test_nmap_absolute_path_exists(self):
        with patch('channel.port_scan._try_nmap') as mock_try:
            mock_try.side_effect = [None, "/usr/local/bin/nmap"]
            resolved = validate_engine(nmap_path="/usr/local/bin/nmap")

        assert resolved == "/usr/local/bin/nmap"

    def test_nmap_timeout(self):
        with patch('channel.port_scan.subprocess.run', side_effect=subprocess.TimeoutExpired("nmap", 10)):
            resolved = validate_engine()

        assert resolved is None


class TestPortScanChannelExtra:

    def test_fetch_delegates(self):
        ch = PortScanChannel()
        expected = {"ip": "1.2.3.4", "open_ports": [], "open_count": 0}
        with patch('channel.port_scan.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch("1.2.3.4", nmap_path="nmap", port_string="80,443")

        mock_fetch.assert_called_once_with("1.2.3.4", nmap_path="nmap", port_string="80,443")
        assert result == expected
