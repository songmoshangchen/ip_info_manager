from ip_info.channel.errors import ChannelError, ChannelPermanentError


class TestChannelError:
    def test_创建异常_消息正确(self):
        err = ChannelError("连接超时: 1.2.3.4")
        assert str(err) == "连接超时: 1.2.3.4"

    def test_是Exception子类(self):
        assert issubclass(ChannelError, Exception)


class TestChannelPermanentError:
    def test_是ChannelError子类(self):
        assert issubclass(ChannelPermanentError, ChannelError)

    def test_创建异常_消息正确(self):
        err = ChannelPermanentError("API Key 无效")
        assert str(err) == "API Key 无效"

    def test_捕获ChannelError也能捕获PermanentError(self):
        try:
            raise ChannelPermanentError("test")
        except ChannelError:
            pass
