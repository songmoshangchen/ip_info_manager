import requests

from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.errors import ChannelError


class IpinfoFreeChannel(BaseChannelAdapter):
    channel_name = "ipinfo_free"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def _request(self, ip: str, **kwargs) -> dict:
        timeout = kwargs.get("timeout", self.timeout)
        url = f"https://ipinfo.io/{ip}/json"
        try:
            response = requests.get(url, timeout=timeout)
        except requests.exceptions.Timeout as e:
            raise ChannelError(f"IPInfo 免费查询超时: {ip} - {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise ChannelError(f"IPInfo 免费连接失败: {ip} - {e}") from e
        except Exception as e:
            raise ChannelError(f"IPInfo 免费查询错误: {ip} - {e}") from e

        if response.status_code == 429:
            raise ChannelError(f"IPInfo 免费请求限流: {ip}")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise ChannelError(f"IPInfo 免费查询失败: {ip} - HTTP {response.status_code}")

        return response.json()
