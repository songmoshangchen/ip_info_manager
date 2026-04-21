import socket
import time
from datetime import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import RdnsSettings as Settings


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
    try:
        socket.setdefaulttimeout(3.0)
        socket.gethostbyaddr("8.8.8.8")
        print("✅ RDNS (socket.gethostbyaddr) 功能验证通过")
    except socket.herror:
        print("✅ RDNS 功能可用（8.8.8.8 无 PTR 记录，属正常情况）")
    except Exception as e:
        print(f"错误: RDNS socket 功能不可用 - {e}")
        sys.exit(1)


def request_channel(ip: str, timeout: float = 3.0, **kwargs):
    result = {
        "query_ip": ip,
        "query_time": datetime.now().isoformat()
    }

    try:
        socket.setdefaulttimeout(timeout)
        ptr_records = socket.gethostbyaddr(ip)

        result.update({
            "hostname": ptr_records[0],
            "aliases": ptr_records[1],
            "ip_addresses": ptr_records[2],
            "ptr_count": len(ptr_records[1]) + 1,
            "has_ptr": True
        })

    except socket.herror as e:
        result.update({
            "has_ptr": False,
            "error_type": "herror",
            "error_code": e.errno if hasattr(e, 'errno') else None,
            "error_message": str(e)
        })

    except socket.gaierror as e:
        result.update({
            "has_ptr": False,
            "error_type": "gaierror",
            "error_code": e.errno if hasattr(e, 'errno') else None,
            "error_message": str(e)
        })

    except socket.timeout:
        result.update({
            "has_ptr": False,
            "error_type": "timeout",
            "error_message": f"查询超时（超过 {timeout} 秒）"
        })

    except Exception as e:
        result.update({
            "raw_error": True,
            "has_ptr": False,
            "error_type": type(e).__name__,
            "error_message": str(e)
        })

    return result


def fetch_channel(ip: str, key: str = '', cookie: str = '', delay: float = 0, timeout: float = 3.0, **kwargs) -> dict:
    apply_delay(delay)

    result = request_channel(ip, timeout=timeout, **kwargs)

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
        delay=settings.rdns_query_delay,
        timeout=settings.rdns_query_timeout,
    )
    ip_writer.add_or_update_ip(ip=ip, channel="rdns_ptr", data=data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python rdns_ptr.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
