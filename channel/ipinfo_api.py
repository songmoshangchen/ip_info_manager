import ipinfo
import requests
import time
from datetime import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import IpinfoSettings as Settings


class IPWriter:
    def __init__(self):
        self.settings = Settings()
        script_dir = os.path.dirname(os.path.abspath(__file__))

        storage_dir = self.settings.storage_dir
        if not os.path.isabs(storage_dir):
            storage_dir = os.path.join(script_dir, storage_dir)

        self.storage_file = os.path.join(storage_dir, self.settings.storage_name + '.json')

        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)

        self._init_storage()

    def _init_storage(self):
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def _load_data(self):
        with open(self.storage_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)

    def _save_data(self, data):
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_or_update_ip(self, ip, channel, data):
        all_data = self._load_data()

        if ip not in all_data:
            all_data[ip] = {"ip": ip}

        all_data[ip][channel] = data
        self._save_data(all_data)
        return True


def validate_channel_key():
    settings = Settings()
    token = getattr(settings, 'ipinfo_access_token', '')

    if token and token.strip():
        try:
            handler = ipinfo.getHandlerLite(access_token=token)
            handler.getDetails("8.8.8.8")
            print("✅ IPInfo Access Token 验证通过（API 模式）")
        except Exception as e:
            print(f"错误: IPInfo Access Token 无效 - {e}")
            sys.exit(1)
    else:
        try:
            resp = requests.get("https://ipinfo.io/8.8.8.8/json", timeout=10)
            resp.raise_for_status()
            print("✅ IPInfo 免费 API 连通性验证通过（无 API 模式）")
        except Exception as e:
            print(f"错误: IPInfo 免费 API 不可达 - {e}")
            sys.exit(1)


def _request_channel_api(ip: str, key: str):
    try:
        handler = ipinfo.getHandlerLite(access_token=key)
        details = handler.getDetails(ip)
        return details.all
    except Exception as e:
        return {
            "raw_error": True,
            "error_message": str(e),
        }


def _request_channel_noapi(ip: str):
    try:
        url = f"https://ipinfo.io/{ip}/json"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "raw_error": True,
            "error_message": str(e),
        }


def request_channel(ip: str, key: str = '', use_api: bool = True, **kwargs):
    if use_api:
        return _request_channel_api(ip, key)
    else:
        return _request_channel_noapi(ip)


def fetch_channel(ip: str, key: str = '', delay: float = 2, use_api: bool = True, **kwargs) -> dict:
    apply_delay(delay)

    result = request_channel(ip, key=key, use_api=use_api, **kwargs)

    if isinstance(result, dict) and result.get('raw_error'):
        return format_output(result, use_api=use_api)

    return format_output(result, use_api=use_api)


def apply_delay(delay: float):
    if delay > 0:
        time.sleep(delay)


def _format_output_api(data: dict) -> dict:
    data.setdefault('query_time', datetime.now().isoformat())
    return data


def _format_output_noapi(data: dict) -> dict:
    data.setdefault('query_time', datetime.now().isoformat())
    return data


def format_output(data: dict, use_api: bool = True, **kwargs) -> dict:
    if use_api:
        return _format_output_api(data)
    else:
        return _format_output_noapi(data)


def main(ip: str):
    settings = Settings()
    ip_writer = IPWriter()

    token = getattr(settings, 'ipinfo_access_token', '')
    use_api = bool(token and token.strip())

    data = fetch_channel(
        ip=ip,
        key=token,
        delay=settings.ipinfo_query_delay,
        use_api=use_api,
    )

    channel = "ipinfo_api" if use_api else "ipinfo"
    ip_writer.add_or_update_ip(ip=ip, channel=channel, data=data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python ipinfo_api.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
