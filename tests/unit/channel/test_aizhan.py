from unittest.mock import MagicMock, patch

import pytest
import requests

from ip_info.channel.aizhan import AizhanChannel
from ip_info.channel.errors import ChannelError, ChannelPermanentError
from ip_info.channel.protocols import ChannelProtocol


def _make_html(dns_infos_html="", dns_content_html="", has_no_domain=False):
    no_domain_text = "暂无域名解析到该IP" if has_no_domain else ""
    return f"""
    <html><body>
        <div class="dns-infos">{dns_infos_html}</div>
        <div class="dns-content">{no_domain_text}{dns_content_html}</div>
    </body></html>
    """


class TestAizhanValidateKey:
    def test_Cookie有效_HTTP200(self):
        channel = AizhanChannel(cookie="valid_cookie")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.aizhan.requests.get", return_value=mock_response):
            channel._validate_key()

    def test_Cookie为空_抛ChannelPermanentError(self):
        channel = AizhanChannel(cookie="")
        with pytest.raises(ChannelPermanentError, match="Cookie 未配置"):
            channel._validate_key()

    def test_Cookie失效_HTTP302_抛ChannelPermanentError(self):
        channel = AizhanChannel(cookie="expired_cookie")
        mock_response = MagicMock()
        mock_response.status_code = 302
        with patch("ip_info.channel.aizhan.requests.get", return_value=mock_response):
            with pytest.raises(ChannelPermanentError, match="Cookie 已失效"):
                channel._validate_key()

    def test_Cookie无效_HTTP403_抛ChannelPermanentError(self):
        channel = AizhanChannel(cookie="bad_cookie")
        mock_response = MagicMock()
        mock_response.status_code = 403
        with patch("ip_info.channel.aizhan.requests.get", return_value=mock_response):
            with pytest.raises(ChannelPermanentError, match="Cookie 无效"):
                channel._validate_key()

    def test_验证请求网络错误_异常向上抛出(self):
        channel = AizhanChannel(cookie="valid_cookie")
        with patch(
            "ip_info.channel.aizhan.requests.get",
            side_effect=requests.exceptions.Timeout("timeout"),
        ):
            with pytest.raises(requests.exceptions.Timeout):
                channel._validate_key()


class TestAizhanRequest:
    def test_请求成功_返回HTML(self):
        channel = AizhanChannel(cookie="valid_cookie")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>test</html>"
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.aizhan.requests.get", return_value=mock_response):
            result = channel._request("1.2.3.4")

        assert result == "<html>test</html>"

    def test_HTTP403_抛ChannelPermanentError(self):
        channel = AizhanChannel(cookie="valid_cookie")
        mock_response = MagicMock()
        mock_response.status_code = 403
        with patch("ip_info.channel.aizhan.requests.get", return_value=mock_response):
            with pytest.raises(ChannelPermanentError, match="Cookie 无效"):
                channel._request("1.2.3.4")

    def test_网络超时_抛ChannelError(self):
        channel = AizhanChannel(cookie="valid_cookie")
        with patch(
            "ip_info.channel.aizhan.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(ChannelError, match="查询超时"):
                channel._request("1.2.3.4")

    def test_连接失败_抛ChannelError(self):
        channel = AizhanChannel(cookie="valid_cookie")
        with patch(
            "ip_info.channel.aizhan.requests.get",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with pytest.raises(ChannelError, match="连接失败"):
                channel._request("1.2.3.4")

    def test_其他HTTP错误_抛ChannelError(self):
        channel = AizhanChannel(cookie="valid_cookie")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        with patch("ip_info.channel.aizhan.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="HTTP 500"):
                channel._request("1.2.3.4")


class TestAizhanParse:
    def test_中国地域格式化(self):
        dns_infos = '<strong>IP信息</strong><strong>广东 深圳 电信</strong><span class="red">5</span>'
        html = _make_html(dns_infos_html=dns_infos, has_no_domain=True)
        channel = AizhanChannel(cookie="test")
        result = channel._parse(html, "1.2.3.4")

        assert result["location"] == "中国广东深圳"
        assert result["isp"] == "电信"

    def test_非中国地域保留原样(self):
        dns_infos = '<strong>IP信息</strong><strong>美国 加利福尼亚 Google</strong><span class="red">0</span>'
        html = _make_html(dns_infos_html=dns_infos, has_no_domain=True)
        channel = AizhanChannel(cookie="test")
        result = channel._parse(html, "8.8.8.8")

        assert result["location"] == "美国 加利福尼亚 Google"
        assert result["isp"] == "Google"

    def test_无关联域名(self):
        dns_infos = '<strong>IP信息</strong><strong>广东 深圳 电信</strong><span class="red">0</span>'
        html = _make_html(dns_infos_html=dns_infos, has_no_domain=True)
        channel = AizhanChannel(cookie="test")
        result = channel._parse(html, "1.2.3.4")

        assert result["domains"] == []

    def test_域名去重_上限20_过滤无点号(self):
        dns_infos = '<strong>IP信息</strong><strong>广东 深圳 电信</strong><span class="red">3</span>'
        rows = ""
        domains = []
        for i in range(1, 26):
            domains.append((f"site{i}.com", f"站点{i}"))
        domains.append(("site1.com", "重复"))
        domains.append(("nodots", "无点号"))
        for d in domains:
            rows += f"<tr><td>1</td><td><a>{d[0]}</a></td><td><span>{d[1]}</span></td><td>data</td><td>data</td></tr>"
        dns_content = f"<tbody>{rows}</tbody>"
        html = _make_html(dns_infos_html=dns_infos, dns_content_html=dns_content)
        channel = AizhanChannel(cookie="test")
        result = channel._parse(html, "1.2.3.4")

        assert len(result["domains"]) <= 20
        domain_names = [d["domain"] for d in result["domains"]]
        seen = set()
        for name in domain_names:
            assert name not in seen
            seen.add(name)
        assert "nodots" not in domain_names

    def test_页面缺少dns_infos_dns_content_抛ChannelError(self):
        channel = AizhanChannel(cookie="test")
        with pytest.raises(ChannelError, match="页面结构异常"):
            channel._parse("<html><body></body></html>", "1.2.3.4")

    def test_无tbody_抛ChannelError(self):
        dns_infos = '<strong>IP信息</strong><strong>广东 深圳 电信</strong><span class="red">3</span>'
        dns_content = "<table><thead><tr><th>1</th></tr></thead></table>"
        html = _make_html(dns_infos_html=dns_infos, dns_content_html=dns_content)
        channel = AizhanChannel(cookie="test")
        with pytest.raises(ChannelError, match="未找到表格数据"):
            channel._parse(html, "1.2.3.4")


class TestAizhanFetchValidateProtocol:
    def test_fetch完整流程_包含query_time(self):
        channel = AizhanChannel(cookie="test")
        dns_infos = '<strong>IP信息</strong><strong>广东 深圳 电信</strong><span class="red">0</span>'
        html = _make_html(dns_infos_html=dns_infos, has_no_domain=True)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.aizhan.requests.get", return_value=mock_response):
            result = channel.fetch("1.2.3.4")

        assert "query_time" in result
        assert result["query_ip"] == "1.2.3.4"
        assert result["location"] == "中国广东深圳"

    def test_fetch_Cookie无效设disabled为True(self):
        channel = AizhanChannel(cookie="bad")
        assert channel.disabled is False
        mock_response = MagicMock()
        mock_response.status_code = 403
        with patch("ip_info.channel.aizhan.requests.get", return_value=mock_response):
            with pytest.raises(ChannelPermanentError):
                channel.fetch("1.2.3.4")

        assert channel.disabled is True

    def test_fetch_网络错误不改变disabled(self):
        channel = AizhanChannel(cookie="test")
        assert channel.disabled is False
        with patch(
            "ip_info.channel.aizhan.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(ChannelError, match="查询超时"):
                channel.fetch("1.2.3.4")

        assert channel.disabled is False

    def test_validate成功_返回True(self):
        channel = AizhanChannel(cookie="valid")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.aizhan.requests.get", return_value=mock_response):
            assert channel.validate() is True
        assert channel.disabled is False

    def test_validate失败_返回False(self):
        channel = AizhanChannel(cookie="")
        assert channel.validate() is False
        assert channel.disabled is True

    def test_满足ChannelProtocol(self):
        channel = AizhanChannel(cookie="test")
        assert isinstance(channel, ChannelProtocol) is True
