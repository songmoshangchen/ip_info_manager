import socket

from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.config import RdnsConfig
from ip_info.channel.errors import ChannelError


class RdnsPtrChannel(BaseChannelAdapter):
    channel_name = "rdns_ptr"
    default_delay = 0.1

    def __init__(self, timeout: float | None = None, config: RdnsConfig | None = None):
        _config = config or RdnsConfig()
        self.timeout = timeout if timeout is not None else _config.rdns_query_timeout

    def _request(self, ip: str, **kwargs) -> dict:
        timeout = kwargs.get("timeout", self.timeout)
        socket.setdefaulttimeout(timeout)
        try:
            ptr_records = socket.gethostbyaddr(ip)
            return {
                "query_ip": ip,
                "hostname": ptr_records[0],
                "has_ptr": True,
            }
        except socket.herror as e:
            return {
                "query_ip": ip,
                "has_ptr": False,
                "error_type": "herror",
                "error_message": str(e),
            }
        except socket.gaierror as e:
            return {
                "query_ip": ip,
                "has_ptr": False,
                "error_type": "gaierror",
                "error_message": str(e),
            }
        except socket.timeout:
            return {
                "query_ip": ip,
                "has_ptr": False,
                "error_type": "timeout",
                "error_message": f"查询超时（超过 {timeout} 秒）",
            }
        except Exception as e:
            raise ChannelError(f"RDNS 查询网络错误: {ip} - {e}") from e
