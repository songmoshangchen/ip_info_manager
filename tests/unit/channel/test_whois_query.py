import socket
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ip_info.channel.errors import ChannelError
from ip_info.channel.protocols import ChannelProtocol
from ip_info.channel.whois_query import WhoisQueryChannel


def _make_whois_obj(**overrides):
    obj = SimpleNamespace()
    obj.domain_name = overrides.get("domain_name", "example.com")
    obj.registrar = overrides.get("registrar", "Test Registrar")
    obj.org = overrides.get("org", "Test Org")
    obj.country = overrides.get("country", "US")
    obj.state = overrides.get("state", "California")
    obj.city = overrides.get("city", "Los Angeles")
    obj.address = overrides.get("address", "123 Main St")
    obj.name = overrides.get("name", "John Doe")
    obj.emails = overrides.get("emails", "admin@example.com")
    obj.creation_date = overrides.get("creation_date", datetime(2020, 1, 1))
    obj.expiration_date = overrides.get("expiration_date", datetime(2025, 1, 1))
    obj.updated_date = overrides.get("updated_date", datetime(2023, 6, 1))
    obj.name_servers = overrides.get("name_servers", ["ns1.example.com", "ns2.example.com"])
    obj.status = overrides.get("status", ["clientTransferProhibited"])
    obj.dnssec = overrides.get("dnssec", "unsigned")
    return obj


class TestWhoisQueryRequest:
    def test_查询成功_返回whois对象(self):
        mock_obj = _make_whois_obj()
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel._request("google.com")

        assert result is mock_obj

    def test_设置socket超时(self):
        mock_obj = _make_whois_obj()
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            with patch("ip_info.channel.whois_query.socket.setdefaulttimeout") as mock_st:
                channel._request("google.com", timeout=15)

        mock_st.assert_called_once_with(15)

    def test_使用构造函数默认timeout(self):
        mock_obj = _make_whois_obj()
        channel = WhoisQueryChannel(timeout=5.0)
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            with patch("ip_info.channel.whois_query.socket.setdefaulttimeout") as mock_st:
                channel._request("google.com")

        mock_st.assert_called_once_with(5.0)

    def test_whois返回None_透传None(self):
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=None):
            result = channel._request("0.0.0.0")

        assert result is None

    def test_查询超时_抛ChannelError(self):
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", side_effect=socket.timeout()):
            with pytest.raises(ChannelError, match="超时"):
                channel._request("1.2.3.4")

    def test_通用异常_抛ChannelError(self):
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", side_effect=Exception("query failed")):
            with pytest.raises(ChannelError, match="query failed"):
                channel._request("1.2.3.4")


class TestWhoisQueryFetch:
    def test_fetch完整流程_有WHOIS数据(self):
        mock_obj = _make_whois_obj()
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel.fetch("google.com")

        assert result["query_target"] == "google.com"
        assert result["has_whois"] is True
        assert "whois_data" in result
        assert "query_time" in result
        assert result["whois_data"]["domain_name"] == "example.com"
        assert result["whois_data"]["registrar"] == "Test Registrar"
        assert result["whois_data"]["country"] == "US"

    def test_fetch无WHOIS记录(self):
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=None):
            result = channel.fetch("0.0.0.0")

        assert result["query_target"] == "0.0.0.0"
        assert result["has_whois"] is False
        assert "query_time" in result

    def test_fetch_多值字段取第一个(self):
        mock_obj = _make_whois_obj(
            domain_name=["example.com", "example.org"],
            registrar=["Reg1", "Reg2"],
            org=["Org1", "Org2"],
            country=["US", "UK"],
        )
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel.fetch("example.com")

        data = result["whois_data"]
        assert data["domain_name"] == "example.com"
        assert data["registrar"] == "Reg1"
        assert data["organization"] == "Org1"
        assert data["country"] == "US"

    def test_fetch_日期字段转ISO字符串(self):
        mock_obj = _make_whois_obj(
            creation_date=datetime(2020, 6, 15, 12, 30, 0),
            expiration_date=datetime(2025, 12, 31, 23, 59, 59),
            updated_date=datetime(2023, 3, 10, 8, 0, 0),
        )
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel.fetch("example.com")

        data = result["whois_data"]
        assert "2020-06-15" in data["creation_date"]
        assert "2025-12-31" in data["expiration_date"]
        assert "2023-03-10" in data["updated_date"]

    def test_fetch_日期列表取第一个再转ISO(self):
        mock_obj = _make_whois_obj(
            creation_date=[datetime(2020, 1, 1), datetime(2019, 1, 1)],
            expiration_date=[datetime(2025, 1, 1), datetime(2024, 1, 1)],
        )
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel.fetch("example.com")

        data = result["whois_data"]
        assert "2020-01-01" in data["creation_date"]
        assert "2025-01-01" in data["expiration_date"]

    def test_fetch_name_servers保持列表(self):
        mock_obj = _make_whois_obj(name_servers=["ns1.test.com", "ns2.test.com", "ns3.test.com"])
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel.fetch("example.com")

        assert result["whois_data"]["name_servers"] == ["ns1.test.com", "ns2.test.com", "ns3.test.com"]

    def test_fetch_name_servers字符串包装为列表(self):
        mock_obj = _make_whois_obj(name_servers="ns.single.com")
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel.fetch("example.com")

        assert result["whois_data"]["name_servers"] == ["ns.single.com"]

    def test_fetch_status保持列表(self):
        mock_obj = _make_whois_obj(status=["status1", "status2"])
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel.fetch("example.com")

        assert result["whois_data"]["status"] == ["status1", "status2"]

    def test_fetch_status字符串包装为列表(self):
        mock_obj = _make_whois_obj(status="active")
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel.fetch("example.com")

        assert result["whois_data"]["status"] == ["active"]

    def test_fetch_status为None_返回空列表(self):
        mock_obj = _make_whois_obj(status=None)
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel.fetch("example.com")

        assert result["whois_data"]["status"] == []

    def test_fetch_字段为None时不包含(self):
        mock_obj = _make_whois_obj(org=None, city=None, state=None, address=None)
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel.fetch("example.com")

        data = result["whois_data"]
        assert "organization" not in data
        assert "city" not in data
        assert "state" not in data
        assert "address" not in data

    def test_fetch_dnssec字段(self):
        mock_obj = _make_whois_obj(dnssec="signed")
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel.fetch("example.com")

        assert result["whois_data"]["dnssec"] == "signed"

    def test_fetch_dnssec不存在_返回None(self):
        mock_obj = _make_whois_obj()
        del mock_obj.dnssec
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            result = channel.fetch("example.com")

        assert result["whois_data"]["dnssec"] is None

    def test_fetch网络错误透传ChannelError(self):
        channel = WhoisQueryChannel()
        assert channel.disabled is False
        with patch("ip_info.channel.whois_query.whois_query", side_effect=socket.timeout()):
            with pytest.raises(ChannelError, match="超时"):
                channel.fetch("1.2.3.4")

        assert channel.disabled is False

    def test_fetch_透传timeout给_request(self):
        mock_obj = _make_whois_obj()
        channel = WhoisQueryChannel()
        with patch("ip_info.channel.whois_query.whois_query", return_value=mock_obj):
            with patch("ip_info.channel.whois_query.socket.setdefaulttimeout") as mock_st:
                channel.fetch("google.com", timeout=20.0)

        mock_st.assert_called_once_with(20.0)


class TestWhoisQueryProtocol:
    def test_满足ChannelProtocol(self):
        channel = WhoisQueryChannel()
        assert isinstance(channel, ChannelProtocol) is True

    def test_validate永远返回True(self):
        channel = WhoisQueryChannel()
        assert channel.validate() is True
        assert channel.disabled is False

    def test_channel_name(self):
        channel = WhoisQueryChannel()
        assert channel.channel_name == "whois_query"

    def test_disabled默认False(self):
        channel = WhoisQueryChannel()
        assert channel.disabled is False
