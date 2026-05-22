import base64

import requests

from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.config import FofaSearchConfig
from ip_info.channel.errors import ChannelError, ChannelPermanentError


class FofaSearchChannel(BaseChannelAdapter):
    channel_name = "fofa_search"
    default_delay = 2.0

    FIELDS = "host,ip,port,domain,protocol,title,server,os,country,country_name,region,city,asn,org,link,lastupdatetime"

    def __init__(self, key: str | None = None, timeout: float | None = None, config: FofaSearchConfig | None = None):
        _config = config or FofaSearchConfig()
        self.key = key or _config.fofa_api_key
        self.timeout = timeout if timeout is not None else _config.fofa_query_timeout

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
        query_suffix = kwargs.get("query_suffix", "")
        query_str = f'ip="{ip}"{query_suffix}'
        qbase64 = base64.b64encode(query_str.encode()).decode()
        url = "https://fofa.info/api/v1/search/all"
        params = {
            "key": self.key,
            "qbase64": qbase64,
            "fields": self.FIELDS,
            "page": 1,
            "size": 20,
        }
        try:
            response = requests.get(url, params=params, timeout=timeout)
        except requests.exceptions.Timeout as e:
            raise ChannelError(f"FOFA Search 查询超时: {ip} - {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise ChannelError(f"FOFA Search 连接失败: {ip} - {e}") from e
        except Exception as e:
            raise ChannelError(f"FOFA Search 查询错误: {ip} - {e}") from e

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise ChannelError(f"FOFA Search 查询失败: {ip} - HTTP {response.status_code}")

        try:
            data = response.json()
        except ValueError as e:
            raise ChannelError(f"FOFA Search 响应非JSON: {ip} - {e}") from e

        if data.get("error"):
            errmsg = data.get("errmsg", "")
            if "-700" in errmsg:
                raise ChannelPermanentError(f"FOFA API Key 无效: {errmsg}")
            raise ChannelError(f"FOFA Search 查询业务错误: {ip} - {errmsg}")

        return data
