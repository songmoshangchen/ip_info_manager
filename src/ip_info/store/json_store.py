import json
import os
import threading

from ip_info.batch.progress import FileProgressTracker
from ip_info.batch.protocols import ProgressTracker


class IPWriter:
    """基于 JSON 文件的 IP 数据写入器，线程安全"""

    def __init__(self, storage_file: str):
        self._storage_file = storage_file
        self._lock = threading.Lock()
        parent_dir = os.path.dirname(storage_file)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        if not os.path.isfile(storage_file):
            with open(storage_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def _load_data(self) -> dict:
        """从文件加载数据，空文件返回 {}"""
        with open(self._storage_file, encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                return {}
            return json.loads(content)

    def _save_data(self, data: dict):
        """将数据写入文件"""
        with open(self._storage_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_or_update_ip(self, ip: str, channel: str, data: dict) -> bool:
        """添加或更新 IP 渠道数据，整体替换渠道"""
        with self._lock:
            store = self._load_data()
            if ip not in store:
                store[ip] = {"ip": ip}
            store[ip][channel] = data
            self._save_data(store)
        return True

    def delete_ip(self, ip: str) -> bool:
        """删除 IP 记录，不存在返回 False"""
        with self._lock:
            store = self._load_data()
            if ip not in store:
                return False
            del store[ip]
            self._save_data(store)
        return True

    def delete_channel(self, ip: str, channel: str) -> bool:
        """删除指定渠道，不存在返回 False"""
        with self._lock:
            store = self._load_data()
            if ip not in store or channel not in store[ip]:
                return False
            del store[ip][channel]
            self._save_data(store)
        return True

    def progress_tracker(self, channel_name: str) -> ProgressTracker:
        """为指定渠道返回进度跟踪器"""
        base = self._storage_file
        if base.endswith(".json"):
            base = base[:-5]
        progress_path = f"{base}.{channel_name}.progress"
        return FileProgressTracker(progress_path)


class IPReader:
    """基于 JSON 文件的 IP 数据读取器"""

    def __init__(self, storage_file: str):
        self._storage_file = storage_file

    def _load_data(self) -> dict:
        """从文件加载数据，文件不存在返回 {}（不抛异常）"""
        if not os.path.isfile(self._storage_file):
            return {}
        with open(self._storage_file, encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                return {}
            return json.loads(content)

    def get_ip_data(self, ip: str) -> dict | None:
        """获取 IP 完整记录，不存在返回 None"""
        store = self._load_data()
        return store.get(ip, None)

    def get_channel_data(self, ip: str, channel: str) -> dict | None:
        """获取 IP 指定渠道数据，不存在返回 None"""
        ip_data = self.get_ip_data(ip)
        if ip_data is None:
            return None
        return ip_data.get(channel, None)

    def list_all_ips(self) -> list[str]:
        """列出所有 IP 地址"""
        store = self._load_data()
        return list(store.keys())

    def list_ip_channels(self, ip: str) -> list[str]:
        """列出 IP 的所有渠道名称（排除 'ip' 字段）"""
        ip_data = self.get_ip_data(ip)
        if ip_data is None:
            return []
        return [key for key in ip_data.keys() if key != "ip"]

    def search_ips_by_channel(self, channel: str, key: str = None, value: str = None) -> list[str]:
        """按渠道名称和键值对搜索 IP"""
        store = self._load_data()
        matched = []
        for ip, ip_data in store.items():
            if channel not in ip_data:
                continue
            channel_data = ip_data[channel]
            if key is not None:
                if key not in channel_data:
                    continue
                if value is not None and channel_data[key] != value:
                    continue
            matched.append(ip)
        return matched

    def get_ips_data(self, ips: list[str]) -> dict[str, dict]:
        """批量获取多个 IP 的数据"""
        store = self._load_data()
        return {ip: store[ip] for ip in ips if ip in store}

    def list_all_ips_data(self, exclude_ips: list[str] | None = None) -> dict[str, dict]:
        """列出所有 IP 数据，可排除指定 IP"""
        store = self._load_data()
        exclude = set(exclude_ips) if exclude_ips else set()
        return {ip: data for ip, data in store.items() if ip not in exclude}
