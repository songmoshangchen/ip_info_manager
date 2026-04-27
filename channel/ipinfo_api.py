import requests
import time
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import IpinfoSettings as Settings
from writer import IPWriter
from utils.logger_utils import get_channel_logger

_logger = get_channel_logger('ipinfo_api')


def validate_channel_key():
    settings = Settings()
    token = getattr(settings, 'ipinfo_access_token', '')

    if token and token.strip():
        try:
            resp = requests.get(
                "https://api.ipinfo.io/lite/8.8.8.8",
                headers={"Authorization": f"Bearer {token}"},
                timeout=settings.ipinfo_validate_timeout,
            )
            resp.raise_for_status()
            print("✅ IPInfo Access Token 验证通过（API 模式）")
        except Exception as e:
            print(f"错误: IPInfo Access Token 无效 - {e}")
            sys.exit(1)
    else:
        try:
            resp = requests.get("https://ipinfo.io/8.8.8.8/json", timeout=settings.ipinfo_validate_timeout)
            resp.raise_for_status()
            print("✅ IPInfo 免费 API 连通性验证通过（无 API 模式）")
        except Exception as e:
            print(f"错误: IPInfo 免费 API 不可达 - {e}")
            sys.exit(1)


def _request_channel_api(ip: str, key: str, timeout: float = 30.0):
    try:
        url = f"https://api.ipinfo.io/lite/{ip}"
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {key}"},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "raw_error": True,
            "error_message": str(e),
        }


def _request_channel_noapi(ip: str, timeout: float = 30.0):
    try:
        url = f"https://ipinfo.io/{ip}/json"
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "raw_error": True,
            "error_message": str(e),
        }


def request_channel(ip: str, key: str = '', use_api: bool = True, timeout: float = 30.0, **kwargs):
    _logger.debug(f"请求 IPInfo: ip={ip}, use_api={use_api}")
    if use_api:
        return _request_channel_api(ip, key, timeout=timeout)
    else:
        return _request_channel_noapi(ip, timeout=timeout)


def fetch_channel(ip: str, key: str = '', delay: float = 2, use_api: bool = True, timeout: float = 30.0, **kwargs) -> dict:
    apply_delay(delay)

    result = request_channel(ip, key=key, use_api=use_api, timeout=timeout, **kwargs)

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

    token = getattr(settings, 'ipinfo_access_token', '')
    use_api = bool(token and token.strip())

    data = fetch_channel(
        ip=ip,
        key=token,
        delay=settings.ipinfo_query_delay,
        use_api=use_api,
        timeout=settings.ipinfo_query_timeout,
    )

    channel = "ipinfo_api" if use_api else "ipinfo"
    ip_writer.add_or_update_ip(ip=ip, channel=channel, data=data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python ipinfo_api.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
