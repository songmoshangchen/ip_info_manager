import ipinfo
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
    token = settings.ipinfo_access_token

    if not token or not token.strip():
        print("错误: IPINFO_ACCESS_TOKEN 未配置，请在 .env 文件中设置")
        sys.exit(1)

    try:
        handler = ipinfo.getHandlerLite(access_token=token)
        handler.getDetails("8.8.8.8")
        print("✅ IPInfo Access Token 验证通过")
    except Exception as e:
        print(f"错误: IPInfo Access Token 无效 - {e}")
        sys.exit(1)


def request_channel(ip: str, key: str = '', **kwargs):
    try:
        handler = ipinfo.getHandlerLite(access_token=key)
        details = handler.getDetails(ip)
        return details.all
    except Exception as e:
        return {
            "raw_error": True,
            "error_message": str(e),
        }


def fetch_channel(ip: str, key: str = '', delay: float = 0, **kwargs) -> dict:
    apply_delay(delay)

    result = request_channel(ip, key=key, **kwargs)

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
    ip_writer = IPWriter()

    data = fetch_channel(
        ip=ip,
        key=settings.ipinfo_access_token,
        delay=settings.ipinfo_query_delay,
    )
    ip_writer.add_or_update_ip(ip=ip, channel="ipinfo_api", data=data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python ipinfo_api.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
