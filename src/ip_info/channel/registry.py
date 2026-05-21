from ip_info.channel.protocols import ChannelProtocol


class ChannelRegistry:
    """渠道注册表：管理所有可用渠道的注册、查询和调用"""

    def __init__(self):
        self._channels: dict[str, ChannelProtocol] = {}

    def register(self, channel) -> None:
        """注册渠道实例，必须满足 ChannelProtocol 协议"""
        if not isinstance(channel, ChannelProtocol):
            raise TypeError(f"Expected ChannelProtocol, got {type(channel).__name__}")
        self._channels[channel.channel_name] = channel

    def get(self, name: str):
        """根据名称获取渠道实例，不存在返回 None"""
        return self._channels.get(name, None)

    def list_names(self) -> list[str]:
        """返回所有已注册渠道的名称列表"""
        return list(self._channels.keys())

    def list_channels(self) -> list:
        """返回所有已注册渠道的实例列表"""
        return list(self._channels.values())

    def validate(self, name: str) -> bool:
        """验证指定名称的渠道是否可用，不存在返回 False"""
        channel = self._channels.get(name)
        if channel is None:
            return False
        return channel.validate()

    def validate_all(self) -> dict[str, bool]:
        """验证所有已注册渠道，返回 {名称: 验证结果} 字典"""
        return {name: ch.validate() for name, ch in self._channels.items()}

    def fetch(self, name: str, ip: str, **kwargs) -> dict:
        """通过注册表委托调用指定渠道的 fetch 方法"""
        channel = self._channels.get(name)
        if channel is None:
            raise KeyError(f"Channel not found: {name}")
        return channel.fetch(ip, **kwargs)
