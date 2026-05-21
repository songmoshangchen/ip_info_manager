from typing import Protocol, runtime_checkable


@runtime_checkable
class ChannelProtocol(Protocol):
    """渠道协议：所有查询渠道必须实现的接口"""

    channel_name: str

    def validate(self) -> bool: ...

    def fetch(self, ip: str, **kwargs) -> dict: ...


@runtime_checkable
class ChannelFetcher(Protocol):
    """渠道获取器协议：可调用的 IP 查询函数"""

    def __call__(self, ip: str, **kwargs) -> dict: ...
