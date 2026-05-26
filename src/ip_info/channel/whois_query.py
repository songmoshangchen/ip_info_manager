import socket

from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.config import WhoisConfig
from ip_info.channel.errors import ChannelError

try:
    from whois import whois as whois_query
except ImportError:
    whois_query = None


def _first_or_none(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)) and len(value) > 0:
        return value[0]
    return None


def _format_date(date_val):
    if date_val is None:
        return None
    dt = date_val[0] if isinstance(date_val, list) and len(date_val) > 0 else date_val
    return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)


def _ensure_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class WhoisQueryChannel(BaseChannelAdapter):
    channel_name = "whois_query"
    default_delay = 0.5

    def __init__(self, timeout: float | None = None, config: WhoisConfig | None = None):
        _config = config or WhoisConfig()
        self.timeout = timeout if timeout is not None else _config.whois_query_timeout
        self.default_delay = _config.whois_query_delay

    def _request(self, ip: str, **kwargs):
        timeout = kwargs.get("timeout", self.timeout)
        socket.setdefaulttimeout(timeout)
        try:
            return whois_query(ip)
        except socket.timeout:
            raise ChannelError(f"Whois 查询超时（超过 {timeout} 秒）: {ip}")
        except Exception as e:
            raise ChannelError(f"Whois 查询错误: {ip} - {e}") from e

    def _parse(self, raw, ip: str) -> dict:
        if raw is None:
            return {
                "query_target": ip,
                "has_whois": False,
                "error_type": "not_found",
                "error_message": "未找到 Whois 信息",
            }

        w = raw
        whois_data = {}

        for attr, key in [
            ("domain_name", "domain_name"),
            ("registrar", "registrar"),
            ("org", "organization"),
            ("country", "country"),
            ("state", "state"),
            ("city", "city"),
            ("address", "address"),
            ("name", "registrant_name"),
        ]:
            val = getattr(w, attr, None)
            if val:
                whois_data[key] = _first_or_none(val)

        emails = getattr(w, "emails", None)
        if emails:
            whois_data["emails"] = _first_or_none(emails)

        for attr, key in [
            ("creation_date", "creation_date"),
            ("expiration_date", "expiration_date"),
            ("updated_date", "updated_date"),
        ]:
            val = getattr(w, attr, None)
            if val:
                whois_data[key] = _format_date(val)

        name_servers = getattr(w, "name_servers", None)
        if name_servers:
            whois_data["name_servers"] = _ensure_list(name_servers)

        status = getattr(w, "status", None)
        if status:
            whois_data["status"] = _ensure_list(status)

        dnssec = getattr(w, "dnssec", None)
        if dnssec:
            whois_data["dnssec"] = dnssec

        return {
            "query_target": ip,
            "has_whois": True,
            "whois_data": whois_data,
        }
