from ip_info.utils.progress import InMemoryProgressTracker, ProgressTracker


class InMemoryIPWriter:
    """基于内存的 IP 数据写入器"""

    def __init__(self):
        self._store: dict[str, dict] = {}

    def add_or_update_ip(self, ip: str, channel: str, data: dict) -> bool:
        if ip not in self._store:
            self._store[ip] = {"ip": ip}
        self._store[ip][channel] = data
        return True

    def delete_ip(self, ip: str) -> bool:
        if ip in self._store:
            del self._store[ip]
            return True
        return False

    def delete_channel(self, ip: str, channel: str) -> bool:
        if ip in self._store and channel in self._store[ip]:
            del self._store[ip][channel]
            return True
        return False

    def progress_tracker(self, channel_name: str) -> ProgressTracker:
        """为指定渠道返回进度跟踪器"""
        return InMemoryProgressTracker()

    def get_all(self) -> dict[str, dict]:
        return self._store

    def get_ip_data(self, ip: str) -> dict | None:
        return self._store.get(ip, None)

    def get_channel_data(self, ip: str, channel: str) -> dict | None:
        ip_data = self.get_ip_data(ip)
        if ip_data is None:
            return None
        return ip_data.get(channel, None)

    def list_all_ips(self) -> list[str]:
        return list(self._store.keys())

    def list_ip_channels(self, ip: str) -> list[str]:
        ip_data = self.get_ip_data(ip)
        if ip_data is None:
            return []
        return [key for key in ip_data.keys() if key != "ip"]

    def search_ips_by_channel(self, channel: str, key: str = None, value: str = None) -> list[str]:
        matched = []
        for ip, ip_data in self._store.items():
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
        return {ip: self._store[ip] for ip in ips if ip in self._store}

    def list_all_ips_data(self, exclude_ips: list[str] | None = None) -> dict[str, dict]:
        exclude = set(exclude_ips) if exclude_ips else set()
        return {ip: data for ip, data in self._store.items() if ip not in exclude}


class InMemoryIPReader:
    """基于内存的 IP 数据读取器"""

    def __init__(self, data: dict[str, dict] | None = None):
        self._store: dict[str, dict] = data if data is not None else {}

    def get_ip_data(self, ip: str) -> dict | None:
        return self._store.get(ip, None)

    def get_channel_data(self, ip: str, channel: str) -> dict | None:
        ip_data = self.get_ip_data(ip)
        if ip_data is None:
            return None
        return ip_data.get(channel, None)

    def list_all_ips(self) -> list[str]:
        return list(self._store.keys())

    def list_ip_channels(self, ip: str) -> list[str]:
        ip_data = self.get_ip_data(ip)
        if ip_data is None:
            return []
        return [key for key in ip_data.keys() if key != "ip"]

    def search_ips_by_channel(self, channel: str, key: str = None, value: str = None) -> list[str]:
        matched = []
        for ip, ip_data in self._store.items():
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
        return {ip: self._store[ip] for ip in ips if ip in self._store}

    def list_all_ips_data(self, exclude_ips: list[str] | None = None) -> dict[str, dict]:
        exclude = set(exclude_ips) if exclude_ips else set()
        return {ip: data for ip, data in self._store.items() if ip not in exclude}
