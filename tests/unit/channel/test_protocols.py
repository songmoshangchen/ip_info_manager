from ip_info.channel.protocols import ChannelFetcher, ChannelProtocol


class TestChannelProtocol:
    def test_满足协议的类_isinstance_返回_true(self):
        class FakeChannel:
            channel_name = "test"

            def validate(self) -> bool:
                return True

            def fetch(self, ip: str, **kwargs) -> dict:
                return {}

        ch = FakeChannel()
        assert isinstance(ch, ChannelProtocol)

    def test_缺少_channel_name_isinstance_返回_false(self):
        class FakeChannel:
            def validate(self) -> bool:
                return True

            def fetch(self, ip: str, **kwargs) -> dict:
                return {}

        ch = FakeChannel()
        assert not isinstance(ch, ChannelProtocol)

    def test_缺少_fetch_isinstance_返回_false(self):
        class FakeChannel:
            channel_name = "test"

            def validate(self) -> bool:
                return True

        ch = FakeChannel()
        assert not isinstance(ch, ChannelProtocol)


class TestChannelFetcher:
    def test_可调用对象_isinstance_返回_true(self):
        def fetcher(ip: str, **kwargs) -> dict:
            return {}

        assert isinstance(fetcher, ChannelFetcher)

    def test_不可调用对象_isinstance_返回_false(self):
        assert not isinstance("not_callable", ChannelFetcher)
