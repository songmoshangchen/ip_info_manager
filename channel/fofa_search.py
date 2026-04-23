import base64
import time
import requests
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import FofaSettings as Settings
from writer import IPWriter
from scripts.logger_utils import get_channel_logger

_logger = get_channel_logger('fofa_search')

FIELDS = 'host,ip,port,domain,protocol,title,server,os,country,country_name,region,city,asn,org,link,lastupdatetime'


def validate_channel_key():
    settings = Settings()
    key = settings.fofa_api_key

    if not key or not key.strip():
        print("错误: FOFA_API_KEY 未配置，请在 .env 文件中设置 IP_FOFA_API_KEY")
        sys.exit(1)

    try:
        url = "https://fofa.info/api/v1/info/my"
        params = {"key": key}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("error") and data.get("errmsg"):
            print(f"错误: Fofa API Key 无效 - {data.get('errmsg')}")
            sys.exit(1)

        username = data.get("data", {}).get("user_name", "N/A") if isinstance(data.get("data"), dict) else "N/A"
        print(f"✅ Fofa API Key 验证通过（查询渠道），用户: {username}")
    except requests.exceptions.RequestException as e:
        print(f"错误: 无法连接 Fofa API 进行 Key 验证 - {e}")
        sys.exit(1)


def request_channel(ip: str, key: str = '', query_suffix: str = '', **kwargs):
    query_str = f'ip="{ip}"'
    if query_suffix:
        query_str += query_suffix
    qbase64 = base64.b64encode(query_str.encode()).decode()
    url = "https://fofa.info/api/v1/search/all"
    params = {
        "key": key,
        "qbase64": qbase64,
        "fields": FIELDS,
        "page": 1,
        "size": 20,
    }

    _logger.debug(f"请求 Fofa Search API: ip={ip}, query={query_str}")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        _logger.debug(f"请求 Fofa Search API 失败: ip={ip}, error={e}")
        return {
            "raw_error": True,
            "error_message": str(e),
        }


def fetch_channel(ip: str, key: str = '', delay: float = 2, **kwargs) -> dict:
    apply_delay(delay)

    _logger.debug(f"fetch_channel 开始: ip={ip}")

    result = request_channel(ip, key=key, **kwargs)

    if isinstance(result, dict) and result.get('raw_error'):
        _logger.debug(f"fetch_channel 请求失败: {result.get('error_message', 'Unknown')}")
        return format_output(result)

    _logger.debug(f"fetch_channel 完成: ip={ip}, size={result.get('size', 0)}")
    return format_output(result)


def apply_delay(delay: float):
    if delay > 0:
        time.sleep(delay)


def format_output(data: dict) -> dict:
    data.setdefault('query_time', datetime.now().isoformat())
    data.setdefault('fields', FIELDS)
    return data


def main(ip: str):
    settings = Settings()
    ip_writer = IPWriter(settings=settings)

    data = fetch_channel(
        ip=ip,
        key=settings.fofa_api_key,
        delay=settings.fofa_query_delay,
    )
    ip_writer.add_or_update_ip(ip=ip, channel="fofa_search", data=data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python fofa_search.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
