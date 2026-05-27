class ChannelError(Exception):
    """渠道基础异常：所有渠道运行时错误的基类"""

    pass


class ChannelPermanentError(ChannelError):
    """渠道永久性错误：如 API Key 无效、账户被封等不可恢复的错误"""

    pass
