from unittest.mock import MagicMock, patch

import pytest
import requests

from ip_info.channel.chinaz import ChinazChannel
from ip_info.channel.config import ChinazConfig
from ip_info.channel.errors import ChannelError
from ip_info.channel.protocols import ChannelProtocol


def _make_html(info_html="", domain_html="", no_result=False):
    no_result_text = "<p>暂无结果</p>" if no_result else ""
    return f"""
    <html><body>
        <div class="info" data-result="true">{info_html}</div>
        <div id="J_domain">{no_result_text}{domain_html}</div>
    </body></html>
    """


class TestChinazValidateKey:
    def test_Cookie有效(self):
        channel = ChinazChannel(cookie="toolUserGrade=1;chinaz_zxuser=test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.chinaz.requests.get", return_value=mock_response):
            result = channel.validate()
        assert result is True
        assert channel.disabled is False

    def test_Cookie为空_validate返回False(self):
        channel = ChinazChannel(cookie="", config=ChinazConfig(_env_file=None))
        result = channel.validate()
        assert result is False
        assert channel.disabled is True

    def test_Cookie缺少必需字段_validate返回False(self):
        channel = ChinazChannel(cookie="some_other_key=value")
        result = channel.validate()
        assert result is False
        assert channel.disabled is True

    def test_验证请求网络错误_validate返回False(self):
        channel = ChinazChannel(cookie="toolUserGrade=1;chinaz_zxuser=test")
        with patch(
            "ip_info.channel.chinaz.requests.get",
            side_effect=requests.exceptions.Timeout("timeout"),
        ):
            result = channel.validate()
        assert result is False
        assert channel.disabled is True


class TestChinazRequest:
    def test_请求成功_返回解析结果(self):
        channel = ChinazChannel(cookie="toolUserGrade=1;chinaz_zxuser=test")
        info_html = '<label><span class="name">IP归属地</span><span class="value">北京</span></label>'
        html = _make_html(info_html=info_html, no_result=True)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.chinaz.requests.get", return_value=mock_response):
            result = channel.fetch("1.2.3.4")

        assert "query_time" in result
        assert result["query_ip"] == "1.2.3.4"
        assert result["location"] == "北京"

    def test_网络超时_抛ChannelError(self):
        channel = ChinazChannel(cookie="toolUserGrade=1;chinaz_zxuser=test")
        with patch(
            "ip_info.channel.chinaz.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(ChannelError, match="查询超时"):
                channel.fetch("1.2.3.4")

    def test_连接失败_抛ChannelError(self):
        channel = ChinazChannel(cookie="toolUserGrade=1;chinaz_zxuser=test")
        with patch(
            "ip_info.channel.chinaz.requests.get",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with pytest.raises(ChannelError, match="连接失败"):
                channel.fetch("1.2.3.4")

    def test_其他HTTP错误_抛ChannelError(self):
        channel = ChinazChannel(cookie="toolUserGrade=1;chinaz_zxuser=test")
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        with patch("ip_info.channel.chinaz.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="HTTP 500"):
                channel.fetch("1.2.3.4")


class TestChinazParse:
    def test_完整解析成功(self):
        info_html = (
            '<label><span class="name">IP归属地</span>'
            '<span class="value">美国加利福尼亚</span></label>'
            '<label><span class="name">运营商</span>'
            '<span class="value">Google</span></label>'
        )
        domain_html = (
            "<p><a>example.com</a>"
            '<span class="date">2020-01-01-----2025-12-31</span></p>'
            "<p><a>test.org</a>"
            '<span class="date">2021-06-15-----2024-06-15</span></p>'
        )
        html = _make_html(info_html=info_html, domain_html=domain_html)
        channel = ChinazChannel(cookie="test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.chinaz.requests.get", return_value=mock_response):
            result = channel.fetch("8.8.8.8")

        assert result["query_ip"] == "8.8.8.8"
        assert result["location"] == "美国加利福尼亚"
        assert result["isp"] == "Google"
        assert len(result["domains"]) == 2
        assert result["domains"][0]["domain"] == "example.com"
        assert result["domains"][0]["start_time"] == "2020-01-01"
        assert result["domains"][0]["end_time"] == "2025-12-31"
        assert result["domains"][1]["domain"] == "test.org"
        assert result["domains"][1]["start_time"] == "2021-06-15"
        assert result["domains"][1]["end_time"] == "2024-06-15"
        assert result["domain_count"] == 2

    def test_无关联域名(self):
        info_html = '<label><span class="name">IP归属地</span><span class="value">北京</span></label>'
        html = _make_html(info_html=info_html, no_result=True)
        channel = ChinazChannel(cookie="test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.chinaz.requests.get", return_value=mock_response):
            result = channel.fetch("1.2.3.4")

        assert result["domains"] == []
        assert result["domain_count"] == 0

    def test_域名去重_上限20_过滤无点号(self):
        info_html = ""
        domain_parts = []
        domains = []
        for i in range(1, 26):
            domains.append(f"site{i}.com")
        domains.append("site1.com")
        domains.append("nodots")
        for d in domains:
            domain_parts.append(f'<p><a>{d}</a><span class="date">2020-01-01-----2025-12-31</span></p>')
        domain_html = "".join(domain_parts)
        html = _make_html(info_html=info_html, domain_html=domain_html)
        channel = ChinazChannel(cookie="test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.chinaz.requests.get", return_value=mock_response):
            result = channel.fetch("1.2.3.4")

        assert len(result["domains"]) <= 20
        domain_names = [d["domain"] for d in result["domains"]]
        seen = set()
        for name in domain_names:
            assert name not in seen
            seen.add(name)
        assert "nodots" not in domain_names

    def test_页面结构异常_抛ChannelError(self):
        channel = ChinazChannel(cookie="test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.chinaz.requests.get", return_value=mock_response):
            with pytest.raises(ChannelError, match="页面结构异常"):
                channel.fetch("1.2.3.4")


class TestChinazFetchValidateProtocol:
    def test_fetch完整流程_包含query_time(self):
        channel = ChinazChannel(cookie="test")
        info_html = '<label><span class="name">IP归属地</span><span class="value">北京</span></label>'
        html = _make_html(info_html=info_html, no_result=True)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.chinaz.requests.get", return_value=mock_response):
            result = channel.fetch("1.2.3.4")

        assert "query_time" in result
        assert result["query_ip"] == "1.2.3.4"
        assert result["location"] == "北京"

    def test_fetch_网络错误不改变disabled(self):
        channel = ChinazChannel(cookie="test")
        assert channel.disabled is False
        with patch(
            "ip_info.channel.chinaz.requests.get",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(ChannelError, match="查询超时"):
                channel.fetch("1.2.3.4")

        assert channel.disabled is False

    def test_validate成功_返回True(self):
        channel = ChinazChannel(cookie="toolUserGrade=1;chinaz_zxuser=test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        with patch("ip_info.channel.chinaz.requests.get", return_value=mock_response):
            assert channel.validate() is True
        assert channel.disabled is False

    def test_validate失败_返回False(self):
        channel = ChinazChannel(cookie="", config=ChinazConfig(_env_file=None))
        assert channel.validate() is False
        assert channel.disabled is True

    def test_满足ChannelProtocol(self):
        channel = ChinazChannel(cookie="test")
        assert isinstance(channel, ChannelProtocol) is True
