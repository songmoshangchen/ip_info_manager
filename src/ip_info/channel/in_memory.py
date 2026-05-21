import copy

from ip_info.channel.errors import ChannelError


class InMemoryChannel:
    """内存渠道：用于测试的轻量级渠道替身"""

    def __init__(
        self,
        name: str = "test_channel",
        validate_result: bool = True,
        fetch_result: dict | None = None,
        fetch_error: ChannelError | None = None,
    ):
        self.channel_name = name
        self._validate_result = validate_result
        self._fetch_result = fetch_result if fetch_result is not None else {}
        self._fetch_error = fetch_error
        self.fetch_calls: list[tuple] = []

    def validate(self) -> bool:
        return self._validate_result

    def fetch(self, ip: str, **kwargs) -> dict:
        self.fetch_calls.append((ip, kwargs))
        if self._fetch_error is not None:
            raise self._fetch_error
        return copy.deepcopy(self._fetch_result)
