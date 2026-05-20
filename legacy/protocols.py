from typing import Protocol, runtime_checkable


@runtime_checkable
class IPDataWriter(Protocol):

    def add_or_update_ip(self, ip: str, channel: str, data: dict) -> bool: ...

    def delete_ip(self, ip: str) -> bool: ...

    def delete_channel(self, ip: str, channel: str) -> bool: ...


@runtime_checkable
class IPDataReader(Protocol):

    def get_ip_data(self, ip: str) -> dict | None: ...

    def get_channel_data(self, ip: str, channel: str) -> dict | None: ...

    def list_all_ips(self) -> list[str]: ...

    def list_ip_channels(self, ip: str) -> list[str]: ...

    def search_ips_by_channel(self, channel: str, key: str = None, value: str = None) -> list[str]: ...


@runtime_checkable
class ChannelFetcher(Protocol):

    def __call__(self, ip: str, **kwargs) -> dict: ...


@runtime_checkable
class ChannelProtocol(Protocol):

    channel_name: str

    def validate(self) -> bool: ...

    def fetch(self, ip: str, **kwargs) -> dict: ...


class InMemoryIPReader:

    def __init__(self, data: dict = None):
        self._store: dict = data if data is not None else {}

    def get_ip_data(self, ip: str) -> dict | None:
        return self._store.get(ip, None)

    def get_channel_data(self, ip: str, channel: str) -> dict | None:
        ip_data = self.get_ip_data(ip)
        if ip_data and channel in ip_data:
            return ip_data[channel]
        return None

    def list_all_ips(self) -> list[str]:
        return list(self._store.keys())

    def list_ip_channels(self, ip: str) -> list[str]:
        ip_data = self.get_ip_data(ip)
        if ip_data:
            return [key for key in ip_data.keys() if key != 'ip']
        return []

    def search_ips_by_channel(self, channel: str, key: str = None, value: str = None) -> list[str]:
        result = []
        for ip, data in self._store.items():
            if channel in data:
                if key is None and value is None:
                    result.append(ip)
                elif key in data[channel]:
                    if value is None or data[channel][key] == value:
                        result.append(ip)
        return result


class InMemoryIPWriter:

    def __init__(self):
        self._store: dict = {}

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

    def get_ip_data(self, ip: str) -> dict | None:
        return self._store.get(ip, None)

    def get_channel_data(self, ip: str, channel: str) -> dict | None:
        ip_data = self.get_ip_data(ip)
        if ip_data and channel in ip_data:
            return ip_data[channel]
        return None

    def list_all_ips(self) -> list[str]:
        return list(self._store.keys())

    def list_ip_channels(self, ip: str) -> list[str]:
        ip_data = self.get_ip_data(ip)
        if ip_data:
            return [key for key in ip_data.keys() if key != 'ip']
        return []

    def search_ips_by_channel(self, channel: str, key: str = None, value: str = None) -> list[str]:
        result = []
        for ip, data in self._store.items():
            if channel in data:
                if key is None and value is None:
                    result.append(ip)
                elif key in data[channel]:
                    if value is None or data[channel][key] == value:
                        result.append(ip)
        return result

    def get_all(self) -> dict:
        return self._store


class InMemoryChannel:

    def __init__(self, name: str = 'test_channel', validate_result: bool = True, fetch_result: dict = None):
        self.channel_name = name
        self._validate_result = validate_result
        self._fetch_result = fetch_result if fetch_result is not None else {}
        self.fetch_calls: list[tuple[str, dict]] = []

    def validate(self) -> bool:
        return self._validate_result

    def fetch(self, ip: str, **kwargs) -> dict:
        self.fetch_calls.append((ip, kwargs))
        return dict(self._fetch_result)


class ChannelRegistry:

    def __init__(self):
        self._channels: dict[str, ChannelProtocol] = {}

    def register(self, channel: ChannelProtocol) -> None:
        if not isinstance(channel, ChannelProtocol):
            raise TypeError(f"Expected ChannelProtocol, got {type(channel).__name__}")
        self._channels[channel.channel_name] = channel

    def get(self, name: str) -> ChannelProtocol | None:
        return self._channels.get(name, None)

    def list_names(self) -> list[str]:
        return list(self._channels.keys())

    def list_channels(self) -> list[ChannelProtocol]:
        return list(self._channels.values())

    def validate_all(self) -> dict[str, bool]:
        return {name: ch.validate() for name, ch in self._channels.items()}

    def validate(self, name: str) -> bool:
        ch = self._channels.get(name)
        if ch is None:
            return False
        return ch.validate()

    def fetch(self, name: str, ip: str, **kwargs) -> dict:
        ch = self._channels.get(name)
        if ch is None:
            raise KeyError(f"Channel '{name}' not registered")
        return ch.fetch(ip, **kwargs)


def create_default_registry() -> ChannelRegistry:
    from channel.fofa_host import FofaHostChannel
    from channel.fofa_search import FofaSearchChannel
    from channel.aizhan import AizhanChannel
    from channel.chinaz import ChinazChannel
    from channel.zoomeye import ZoomeyeChannel
    from channel.rdns_ptr import RdnsPtrChannel
    from channel.whois_query import WhoisChannel
    from channel.ssl_cert import SslCertChannel
    from channel.ipinfo_api import IpinfoApiChannel
    from channel.ipinfo_free import IpinfoFreeChannel
    from channel.port_scan import PortScanChannel

    reg = ChannelRegistry()
    reg.register(FofaHostChannel())
    reg.register(FofaSearchChannel())
    reg.register(AizhanChannel())
    reg.register(ChinazChannel())
    reg.register(ZoomeyeChannel())
    reg.register(RdnsPtrChannel())
    reg.register(WhoisChannel())
    reg.register(SslCertChannel())
    reg.register(IpinfoApiChannel())
    reg.register(IpinfoFreeChannel())
    reg.register(PortScanChannel())
    return reg
