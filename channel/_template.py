import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import Settings


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
    """
    【第3部分】Key/Cookie 有效性校验

    需要校验的渠道：
      - 检查 key/cookie 是否非空
      - 检查长度是否合理
      - 调用测试接口验证连通性（如有）
      - 失败时抛出异常或 sys.exit(1)

    不需要校验的渠道（如 rdns、whois）：
      - 此函数可以为空，直接 return True
    """
    pass


def fetch_channel(ip: str) -> dict:
    """
    【第4部分】数据采集函数

    参数:
        ip: 目标 IP 地址

    返回:
        dict: 采集结果，结构由各渠道自行定义

    建议包含:
        - 成功时: 渠道特定的字段
        - 失败时: raw_error=True + error_message 字段
    """
    pass


def main(ip: str):
    """
    【第5部分】CLI 入口

    组合逻辑:
      1. 读取 Settings 获取 key/cookie/delay 等配置
      2. 调用 fetch_channel() 采集数据
      3. 调用 IPWriter.add_or_update_ip() 写入数据
    """
    settings = Settings()
    ip_writer = IPWriter()

    data = fetch_channel(ip)
    ip_writer.add_or_update_ip(ip=ip, channel="channel_name", data=data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python _template.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
