import requests

from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.config import IpInfoApiConfig
from ip_info.channel.errors import ChannelError, ChannelPermanentError


class IpinfoApiChannel(BaseChannelAdapter):
    channel_name = "ipinfo_api"
    default_delay = 1.2

    def __init__(self, token: str | None = None, timeout: float | None = None, config: IpInfoApiConfig | None = None):
        _config = config or IpInfoApiConfig()
        self.token = token or _config.ipinfo_access_token
        self.timeout = timeout if timeout is not None else _config.ipinfo_query_timeout
        self.default_delay = _config.ipinfo_query_delay

    def _validate_key(self) -> None:
        if not self.token or not self.token.strip():
            raise ChannelPermanentError("IPInfo API Token 未配置")
        try:
            response = requests.get(
                "https://api.ipinfo.io/lite/8.8.8.8",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.timeout,
            )
        except Exception:
            raise
        if response.status_code in (401, 403):
            raise ChannelPermanentError("IPInfo API Token 无效")
        response.raise_for_status()

    def _request(self, ip: str, **kwargs) -> dict:
        timeout = kwargs.get("timeout", self.timeout)
        url = f"https://api.ipinfo.io/lite/{ip}"
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout as e:
            raise ChannelError(f"IPInfo API 查询超时: {ip} - {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise ChannelError(f"IPInfo API 连接失败: {ip} - {e}") from e
        except Exception as e:
            raise ChannelError(f"IPInfo API 查询错误: {ip} - {e}") from e

        if response.status_code in (401, 403):
            raise ChannelPermanentError(f"IPInfo API Token 无效: {ip}")
        if response.status_code == 429:
            raise ChannelError(f"IPInfo API 请求限流: {ip}")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise ChannelError(f"IPInfo API 查询失败: {ip} - HTTP {response.status_code}")

        data = response.json()
        data.pop("readme", None)
        return data
