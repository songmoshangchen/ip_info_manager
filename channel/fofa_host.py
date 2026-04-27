import time
import requests
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import FofaSettings as Settings
from writer import IPWriter
from scripts.logger_utils import get_channel_logger

_logger = get_channel_logger('fofa_host')


def validate_channel_key():
    settings = Settings()
    key = settings.fofa_api_key

    if not key or not key.strip():
        print("错误: FOFA_API_KEY 未配置，请在 .env 文件中设置")
        sys.exit(1)

    try:
        url = "https://fofa.info/api/v1/info/my"
        params = {"key": key}
        response = requests.get(url, params=params, timeout=settings.fofa_validate_timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("error") and data.get("errmsg"):
            print(f"错误: Fofa API Key 无效 - {data.get('errmsg')}")
            sys.exit(1)

        username = data.get("data", {}).get("user_name", "N/A") if isinstance(data.get("data"), dict) else "N/A"
        print(f"✅ Fofa API Key 验证通过（Host 聚合渠道），用户: {username}")
    except requests.exceptions.RequestException as e:
        print(f"错误: 无法连接 Fofa API 进行 Key 验证 - {e}")
        sys.exit(1)


def request_channel(ip: str, key: str = '', timeout: float = 30.0, **kwargs):
    url = f"https://fofa.info/api/v1/host/{ip}"
    params = {"key": key, "detail": "true"}

    _logger.debug(f"请求 Fofa Host 聚合 API: ip={ip}")

    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        _logger.debug(f"请求 Fofa Host 聚合 API 失败: ip={ip}, error={e}")
        return {
            "raw_error": True,
            "error_message": str(e),
        }


def fetch_channel(ip: str, key: str = '', delay: float = 2, timeout: float = 30.0, **kwargs) -> dict:
    apply_delay(delay)

    result = request_channel(ip, key=key, timeout=timeout, **kwargs)

    if isinstance(result, dict) and result.get('raw_error'):
        return format_output(result)

    return format_output(result)


def apply_delay(delay: float):
    if delay > 0:
        time.sleep(delay)


def format_output(data: dict) -> dict:
    data.setdefault('query_time', datetime.now().isoformat())
    return data


def main(ip: str):
    settings = Settings()
    ip_writer = IPWriter(settings=settings)

    data = fetch_channel(
        ip=ip,
        key=settings.fofa_api_key,
        delay=settings.fofa_query_delay,
        timeout=settings.fofa_query_timeout,
    )
    ip_writer.add_or_update_ip(ip=ip, channel="fofa_host", data=data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python fofa_host.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
