import nmap

from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.config import PortScanConfig
from ip_info.channel.errors import ChannelError, ChannelPermanentError


class PortScanChannel(BaseChannelAdapter):
    channel_name = "port_scan"
    default_delay = 0

    def __init__(
        self, nmap_path: str | None = None, timeout: float | None = None, config: PortScanConfig | None = None
    ):
        _config = config or PortScanConfig()
        self.nmap_path = nmap_path or _config.port_scan_nmap_path
        self.timeout = timeout if timeout is not None else float(_config.port_scan_timeout)
        self._arguments = _config.port_scan_arguments
        self._port_list = _config.port_scan_port_list
        self._historical_ports = []

    def _validate_key(self) -> None:
        try:
            nmap.PortScanner()
        except nmap.PortScannerError:
            raise ChannelPermanentError(f"nmap 不可用: {self.nmap_path}") from None

    def _request(self, ip: str, **kwargs) -> nmap.PortScanner:
        self._historical_ports = kwargs.get("historical_ports", [])
        port_string = kwargs.get("port_string", "")

        try:
            nm = nmap.PortScanner()
        except nmap.PortScannerError as e:
            raise ChannelError(f"nmap 扫描错误: {ip} - {e}") from e

        arguments = f"{self._arguments} --host-timeout {int(self.timeout)}s"
        scan_kwargs = {"arguments": arguments}
        if port_string:
            scan_kwargs["ports"] = port_string
        elif self._port_list:
            scan_kwargs["ports"] = self._port_list

        try:
            nm.scan(ip, **scan_kwargs)
        except nmap.PortScannerError as e:
            raise ChannelError(f"nmap 扫描错误: {ip} - {e}") from e

        return nm

    def _parse(self, raw, ip: str) -> dict:
        result = {
            "query_target": ip,
            "engine": "nmap",
            "host_alive": False,
            "open_ports": [],
            "total_scanned": 0,
            "open_count": 0,
            "historical_ports_verified": [],
            "historical_ports_closed": [],
        }

        scaninfo = raw.scaninfo()
        if isinstance(scaninfo, dict) and "error" in scaninfo:
            result["nmap_error"] = scaninfo["error"]

        if ip not in raw.all_hosts():
            return result

        result["host_alive"] = raw[ip].state() == "up"

        tcp_ports = raw[ip].all_tcp()
        result["total_scanned"] = len(tcp_ports)

        open_ports = []
        open_port_numbers = []
        for port in tcp_ports:
            port_info = raw[ip]["tcp"][port]
            if port_info.get("state") == "open":
                open_ports.append(
                    {
                        "port": port,
                        "protocol": "tcp",
                        "state": "open",
                        "service": port_info.get("name", ""),
                        "product": port_info.get("product", ""),
                        "version": port_info.get("version", ""),
                    }
                )
                open_port_numbers.append(port)

        result["open_ports"] = open_ports
        result["open_count"] = len(open_ports)

        if self._historical_ports:
            open_set = set(open_port_numbers)
            result["historical_ports_verified"] = [p for p in self._historical_ports if p in open_set]
            result["historical_ports_closed"] = [p for p in self._historical_ports if p not in open_set]

        return result
