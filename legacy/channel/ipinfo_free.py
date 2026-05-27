import requests
import time
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import IpinfoSettings as Settings
from writer import IPWriter
from utils.logger_utils import get_channel_logger
from channel.base import is_network_error

_logger = get_channel_logger('ipinfo_free')


def validate_channel_key():
    settings = Settings()
    try:
        resp = requests.get("https://ipinfo.io/8.8.8.8/json", timeout=settings.ipinfo_validate_timeout)
        resp.raise_for_status()
        print("✅ IPInfo 免费 API 连通性验证通过")
    except Exception as e:
        print(f"错误: IPInfo 免费 API 不可达 - {e}")
        sys.exit(1)


def request_channel(ip: str, timeout: float = 30.0):
    _logger.debug(f"请求 IPInfo 免费: ip={ip}")
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


def fetch_channel(ip: str, delay: float = 2, timeout: float = 30.0, **kwargs) -> dict:
    if delay > 0:
        time.sleep(delay)

    result = request_channel(ip, timeout=timeout)
    result.setdefault('query_time', datetime.now().isoformat())
    return result


def main(ip: str):
    settings = Settings()
    ip_writer = IPWriter(settings=settings)

    data = fetch_channel(
        ip=ip,
        delay=settings.ipinfo_query_delay,
        timeout=settings.ipinfo_query_timeout,
    )

    if not is_network_error(data):
        ip_writer.add_or_update_ip(ip=ip, channel="ipinfo_free", data=data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python ipinfo_free.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)


class IpinfoFreeChannel:

    channel_name = 'ipinfo_free'
    disabled = False

    def validate(self) -> bool:
        try:
            validate_channel_key()
            self.disabled = False
            return True
        except (SystemExit, Exception):
            self.disabled = True
            return False

    def fetch(self, ip: str, **kwargs) -> dict:
        return fetch_channel(ip, **kwargs)
