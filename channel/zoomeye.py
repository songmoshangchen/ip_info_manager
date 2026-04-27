import base64
import time
import requests
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import ZoomeyeSettings as Settings
from writer import IPWriter
from utils.logger_utils import get_channel_logger

_logger = get_channel_logger('zoomeye')


def validate_channel_key():
    settings = Settings()
    key = settings.zoomeye_api_key

    if not key or not key.strip():
        print("错误: ZOOMEYE_API_KEY 未配置，请在 .env 文件中设置 IP_ZOOMEYE_API_KEY")
        sys.exit(1)

    print(f"✅ ZoomEye API Key 已配置（不进行在线校验，避免消耗额度）")


def request_channel(ip: str, key: str = '', sub_type: str = '', timeout: float = 30, **kwargs):
    query_str = f"ip:{ip}"
    qbase64 = base64.b64encode(query_str.encode()).decode()

    url = "https://api.zoomeye.org/v2/search"
    headers = {"API-KEY": key, "Content-Type": "application/json"}
    data = {
        "qbase64": qbase64,
        "page": 1,
        "pagesize": 20,
        "fields": "ip,port,domain",
    }
    if sub_type:
        data["sub_type"] = sub_type

    _logger.debug(f"请求 ZoomEye API: ip={ip}, query={query_str}")

    try:
        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        result = response.json()

        if result.get("message") != "success":
            return {
                "raw_error": True,
                "error_message": result.get("message", "ZoomEye API error"),
            }

        return result
    except Exception as e:
        _logger.debug(f"请求 ZoomEye API 失败: ip={ip}, error={e}")
        return {
            "raw_error": True,
            "error_message": str(e),
        }


def fetch_channel(ip: str, key: str = '', delay: float = 0, timeout: float = 30, **kwargs) -> dict:
    apply_delay(delay)

    _logger.debug(f"fetch_channel 开始: ip={ip}")

    result = request_channel(ip, key=key, timeout=timeout, **kwargs)

    if isinstance(result, dict) and result.get('raw_error'):
        _logger.debug(f"fetch_channel 请求失败: {result.get('error_message', 'Unknown')}")
        return format_output(result)

    _logger.debug(f"fetch_channel 完成: ip={ip}, total={result.get('total', 0)}")
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
        key=settings.zoomeye_api_key,
        delay=settings.zoomeye_query_delay,
        timeout=settings.zoomeye_query_timeout,
    )
    ip_writer.add_or_update_ip(ip=ip, channel="zoomeye", data=data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python zoomeye.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
