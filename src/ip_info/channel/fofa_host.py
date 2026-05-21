import requests

from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.errors import ChannelError, ChannelPermanentError


class FofaHostChannel(BaseChannelAdapter):
    channel_name = "fofa_host"

    def __init__(self, key: str, timeout: float = 30.0):
        self.key = key
        self.timeout = timeout

    def _validate_key(self) -> None:
        if not self.key or not self.key.strip():
            raise ChannelPermanentError("FOFA API Key 未配置")
        response = requests.get(
            "https://fofa.info/api/v1/info/my",
            params={"key": self.key},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("error") and data.get("errmsg"):
            raise ChannelPermanentError(f"FOFA API Key 无效: {data['errmsg']}")

    def _request(self, ip: str, **kwargs) -> dict:
        timeout = kwargs.get("timeout", self.timeout)
        url = f"https://fofa.info/api/v1/host/{ip}"
        params = {"key": self.key, "detail": "true"}
        try:
            response = requests.get(url, params=params, timeout=timeout)
        except requests.exceptions.Timeout as e:
            raise ChannelError(f"FOFA Host 查询超时: {ip} - {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise ChannelError(f"FOFA Host 连接失败: {ip} - {e}") from e
        except Exception as e:
            raise ChannelError(f"FOFA Host 查询错误: {ip} - {e}") from e

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise ChannelError(f"FOFA Host 查询失败: {ip} - HTTP {response.status_code}")

        data = response.json()
        if data.get("error"):
            errmsg = data.get("errmsg", "")
            if "-700" in errmsg:
                raise ChannelPermanentError(f"FOFA API Key 无效: {errmsg}")
            raise ChannelError(f"FOFA Host 查询业务错误: {ip} - {errmsg}")

        return data
