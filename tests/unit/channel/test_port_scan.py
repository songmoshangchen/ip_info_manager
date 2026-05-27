from unittest.mock import MagicMock, patch

import nmap
import pytest

from ip_info.channel.config import PortScanConfig
from ip_info.channel.errors import ChannelError
from ip_info.channel.port_scan import PortScanChannel
from ip_info.channel.protocols import ChannelProtocol


def _make_mock_nm(hosts_data=None, scaninfo=None):
    mock_nm = MagicMock()
    if hosts_data is None:
        mock_nm.all_hosts.return_value = []
    else:
        mock_nm.all_hosts.return_value = list(hosts_data.keys())
        host_mocks = {}
        for ip_addr, data in hosts_data.items():
            mock_host = MagicMock()
            mock_host.state.return_value = data.get("state", "up")
            mock_host.all_tcp.return_value = data.get("tcp_ports", [])
            tcp_data = {}
            for p in data.get("port_data", []):
                tcp_data[p["port"]] = {
                    "state": p.get("state", "open"),
                    "name": p.get("name", ""),
                    "product": p.get("product", ""),
                    "version": p.get("version", ""),
                }
            mock_host.__getitem__.return_value = tcp_data
            host_mocks[ip_addr] = mock_host
        mock_nm.__getitem__.side_effect = lambda ip: host_mocks[ip]
    mock_nm.scaninfo.return_value = scaninfo if scaninfo is not None else {}
    return mock_nm


class TestPortScanFetch:
    def test_有开放端口的完整返回(self):
        mock_nm = _make_mock_nm(
            hosts_data={
                "1.2.3.4": {
                    "state": "up",
                    "tcp_ports": [80, 443],
                    "port_data": [
                        {"port": 80, "name": "http", "product": "nginx", "version": "1.18.0"},
                        {"port": 443, "name": "https", "product": "", "version": ""},
                    ],
                }
            }
        )
        channel = PortScanChannel()
        with patch("ip_info.channel.port_scan.nmap.PortScanner", return_value=mock_nm):
            result = channel.fetch("1.2.3.4")

        assert result["query_target"] == "1.2.3.4"
        assert result["engine"] == "nmap"
        assert result["host_alive"] is True
        assert result["open_count"] == 2
        assert result["total_scanned"] == 2
        assert len(result["open_ports"]) == 2

        port80 = result["open_ports"][0]
        assert port80["port"] == 80
        assert port80["protocol"] == "tcp"
        assert port80["state"] == "open"
        assert port80["service"] == "http"
        assert port80["product"] == "nginx"
        assert port80["version"] == "1.18.0"

        port443 = result["open_ports"][1]
        assert port443["port"] == 443
        assert port443["service"] == "https"

        assert "query_time" in result

    def test_无开放端口_host存在但无open端口(self):
        mock_nm = _make_mock_nm(
            hosts_data={
                "1.2.3.4": {
                    "state": "up",
                    "tcp_ports": [],
                    "port_data": [],
                }
            }
        )
        channel = PortScanChannel()
        with patch("ip_info.channel.port_scan.nmap.PortScanner", return_value=mock_nm):
            result = channel.fetch("1.2.3.4")

        assert result["host_alive"] is True
        assert result["open_count"] == 0
        assert result["open_ports"] == []
        assert result["total_scanned"] == 0

    def test_主机不存在_all_hosts为空(self):
        mock_nm = _make_mock_nm()
        channel = PortScanChannel()
        with patch("ip_info.channel.port_scan.nmap.PortScanner", return_value=mock_nm):
            result = channel.fetch("1.2.3.4")

        assert result["host_alive"] is False
        assert result["open_count"] == 0
        assert result["open_ports"] == []

    def test_主机down_state不是up(self):
        mock_nm = _make_mock_nm(
            hosts_data={
                "1.2.3.4": {
                    "state": "down",
                    "tcp_ports": [],
                    "port_data": [],
                }
            }
        )
        channel = PortScanChannel()
        with patch("ip_info.channel.port_scan.nmap.PortScanner", return_value=mock_nm):
            result = channel.fetch("1.2.3.4")

        assert result["host_alive"] is False
        assert result["open_count"] == 0

    def test_scaninfo包含error(self):
        mock_nm = _make_mock_nm(
            hosts_data={
                "1.2.3.4": {
                    "state": "up",
                    "tcp_ports": [],
                    "port_data": [],
                }
            },
            scaninfo={"error": "Route to host failed"},
        )
        channel = PortScanChannel()
        with patch("ip_info.channel.port_scan.nmap.PortScanner", return_value=mock_nm):
            result = channel.fetch("1.2.3.4")

        assert "nmap_error" in result
        assert result["nmap_error"] == "Route to host failed"

    def test_nmap_PortScannerError_抛ChannelError(self):
        mock_nm = MagicMock()
        mock_nm.scan.side_effect = nmap.PortScannerError("nmap not found")
        channel = PortScanChannel()
        assert channel.disabled is False
        with patch("ip_info.channel.port_scan.nmap.PortScanner", return_value=mock_nm):
            with pytest.raises(ChannelError):
                channel.fetch("1.2.3.4")

        assert channel.disabled is False

    def test_port_string参数传递(self):
        mock_nm = _make_mock_nm(
            hosts_data={
                "1.2.3.4": {
                    "state": "up",
                    "tcp_ports": [80],
                    "port_data": [
                        {"port": 80, "name": "http", "product": "", "version": ""},
                    ],
                }
            }
        )
        channel = PortScanChannel()
        with patch("ip_info.channel.port_scan.nmap.PortScanner", return_value=mock_nm):
            result = channel.fetch("1.2.3.4", port_string="80,443,8080")

        assert result["query_target"] == "1.2.3.4"
        assert result["open_count"] == 1
        assert result["open_ports"][0]["port"] == 80
        assert "query_time" in result

    def test_historical_ports验证(self):
        mock_nm = _make_mock_nm(
            hosts_data={
                "1.2.3.4": {
                    "state": "up",
                    "tcp_ports": [80, 443],
                    "port_data": [
                        {"port": 80, "name": "http", "product": "", "version": ""},
                        {"port": 443, "name": "https", "product": "", "version": ""},
                    ],
                }
            }
        )
        channel = PortScanChannel()
        with patch("ip_info.channel.port_scan.nmap.PortScanner", return_value=mock_nm):
            result = channel.fetch("1.2.3.4", historical_ports=[80, 443, 8080])

        assert result["historical_ports_verified"] == [80, 443]
        assert result["historical_ports_closed"] == [8080]


class TestPortScanProtocol:
    def test_isinstance检查(self):
        channel = PortScanChannel()
        assert isinstance(channel, ChannelProtocol) is True

    def test_validate成功_disabled为False(self):
        mock_nm = MagicMock()
        channel = PortScanChannel()
        with patch("ip_info.channel.port_scan.nmap.PortScanner", return_value=mock_nm):
            assert channel.validate() is True
        assert channel.disabled is False

    def test_validate失败_disabled为True(self):
        channel = PortScanChannel()
        with patch("ip_info.channel.port_scan.nmap.PortScanner", side_effect=nmap.PortScannerError("not found")):
            assert channel.validate() is False
        assert channel.disabled is True

    def test_channel_name(self):
        channel = PortScanChannel()
        assert channel.channel_name == "port_scan"

    def test_disabled默认False(self):
        channel = PortScanChannel()
        assert channel.disabled is False


class TestPortScanConfigIntegration:
    """测试 PortScanChannel 从 PortScanConfig 读取配置"""

    def test_默认arguments来自配置(self):
        config = PortScanConfig(_env_file=None)
        channel = PortScanChannel(config=config)
        assert channel._arguments == "-sV -T4 -Pn --open"

    def test_自定义arguments来自配置(self):
        config = PortScanConfig(_env_file=None, port_scan_arguments="-sT -T4 -Pn --open")
        channel = PortScanChannel(config=config)
        assert channel._arguments == "-sT -T4 -Pn --open"

    def test_默认timeout来自配置(self):
        config = PortScanConfig(_env_file=None)
        channel = PortScanChannel(config=config)
        assert channel.timeout == 90.0

    def test_自定义timeout来自配置(self):
        config = PortScanConfig(_env_file=None, port_scan_timeout=120)
        channel = PortScanChannel(config=config)
        assert channel.timeout == 120.0

    def test_默认port_list来自配置(self):
        config = PortScanConfig(_env_file=None)
        channel = PortScanChannel(config=config)
        assert channel._port_list == "config/port_scan/top1000.txt"

    def test_自定义port_list来自配置(self):
        config = PortScanConfig(_env_file=None, port_scan_port_list="custom_ports.txt")
        channel = PortScanChannel(config=config)
        assert channel._port_list == "custom_ports.txt"

    def test_request使用配置中的arguments(self):
        mock_nm = _make_mock_nm(
            hosts_data={
                "1.2.3.4": {
                    "state": "up",
                    "tcp_ports": [80],
                    "port_data": [
                        {"port": 80, "name": "http", "product": "nginx", "version": "1.18.0"},
                    ],
                }
            }
        )
        config = PortScanConfig(_env_file=None, port_scan_arguments="-sV -T4 -Pn --open")
        channel = PortScanChannel(config=config)
        with patch("ip_info.channel.port_scan.nmap.PortScanner", return_value=mock_nm):
            channel.fetch("1.2.3.4")

        mock_nm.scan.assert_called_once()
        call_kwargs = mock_nm.scan.call_args
        assert "-sV" in call_kwargs.kwargs.get("arguments", call_kwargs[1].get("arguments", ""))

    def test_request使用配置中的timeout(self):
        mock_nm = _make_mock_nm(
            hosts_data={
                "1.2.3.4": {
                    "state": "up",
                    "tcp_ports": [],
                    "port_data": [],
                }
            }
        )
        config = PortScanConfig(_env_file=None, port_scan_timeout=60)
        channel = PortScanChannel(config=config)
        with patch("ip_info.channel.port_scan.nmap.PortScanner", return_value=mock_nm):
            channel.fetch("1.2.3.4")

        mock_nm.scan.assert_called_once()
        call_kwargs = mock_nm.scan.call_args
        assert "--host-timeout" in call_kwargs.kwargs.get("arguments", call_kwargs[1].get("arguments", ""))
