import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime

from ip_info.channel.errors import ChannelPermanentError

logger = logging.getLogger(__name__)


class BaseChannelAdapter(ABC):
    """渠道适配器基类：所有查询渠道的抽象基类"""

    channel_name: str = ""
    disabled: bool = False
    default_delay: float = 0

    @abstractmethod
    def _request(self, ip: str, **kwargs) -> dict | str:
        """发送请求并返回原始数据，失败时抛出 ChannelError / ChannelPermanentError"""
        ...

    def _validate_key(self) -> None:
        """验证 API Key 等配置，子类可覆盖。失败时抛异常即可"""
        pass

    def _parse(self, raw, ip: str) -> dict:
        """解析原始数据为 dict。默认直接透传 dict，爬虫类需覆盖"""
        if isinstance(raw, dict):
            return raw
        msg = f"子类返回非dict类型({type(raw).__name__})，需覆盖 _parse()"
        raise NotImplementedError(msg)

    def validate(self) -> bool:
        """验证渠道配置是否有效，成功返回 True 并重置 disabled"""
        try:
            self._validate_key()
            self.disabled = False
            return True
        except Exception as e:
            self.disabled = True
            logger.warning("[%s] 渠道验证失败: %s", self.channel_name, e)
            return False

    def fetch(self, ip: str, **kwargs) -> dict:
        """完整查询流程：delay → _request → _parse → 补充 query_time"""
        delay = kwargs.pop("delay", 0)
        if delay > 0:
            time.sleep(delay)

        try:
            raw = self._request(ip, **kwargs)
        except ChannelPermanentError:
            self.disabled = True
            raise

        result = self._parse(raw, ip)
        result.setdefault("query_time", datetime.now().isoformat())
        return result
