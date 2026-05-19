import os
import sys

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from channel.aizhan import (
    request_channel,
    parse_response,
    fetch_channel,
    format_output,
    validate_channel_key,
    AizhanChannel,
)


def _make_html(dns_infos_content="", dns_content_text="", tbody_rows=None):
    if tbody_rows is None:
        tbody_html = ""
    else:
        rows = ""
        for row in tbody_rows:
            cells = "".join(f"<td>{c}</td>" for c in row)
            rows += f"<tr>{cells}</tr>"
        tbody_html = f"<tbody>{rows}</tbody>"

    return f"""
    <html><body>
    <div class="dns-infos">{dns_infos_content}</div>
    <div class="dns-content">{dns_content_text}
        <table>{tbody_html}</table>
    </div>
    </body></html>
    """


class TestRequestChannel:

    def test_normal_returns_html_text(self):
        html = "<html><body>test</body></html>"
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status.return_value = None

        with patch('channel.aizhan.requests.get', return_value=mock_resp) as mock_get:
            result = request_channel("1.2.3.4", cookie="test_cookie", timeout=10.0)

        assert result == html
        call_args = mock_get.call_args
        assert "dns.aizhan.com/1.2.3.4/" in call_args[0][0]
        assert call_args[1]["headers"]["Cookie"] == "test_cookie"

    @pytest.mark.xfail(reason="BUG: ReadTimeout 错误消息 'Read timed out' 不含 'timeout' 连续子串, 被误分类为 '查询失败'")
    def test_read_timeout_classified_as_network_timeout(self):
        import requests as req
        with patch('channel.aizhan.requests.get', side_effect=req.exceptions.ReadTimeout("Read timed out.")):
            result = request_channel("1.2.3.4", cookie="test")

        assert result["raw_error"] is True
        assert "网络超时" in result["error_message"]

    def test_timeout_keyword_in_message(self):
        import requests as req
        with patch('channel.aizhan.requests.get', side_effect=req.exceptions.Timeout("Connection timeout")):
            result = request_channel("1.2.3.4", cookie="test")

        assert result["raw_error"] is True
        assert "网络超时" in result["error_message"]

    def test_403_returns_error_dict(self):
        import requests as req
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("403 Forbidden")

        with patch('channel.aizhan.requests.get', return_value=mock_resp):
            result = request_channel("1.2.3.4", cookie="test")

        assert result["raw_error"] is True
        assert "爱站网禁止请求" in result["error_message"]

    def test_connection_error_returns_error_dict(self):
        import requests as req
        with patch('channel.aizhan.requests.get', side_effect=req.exceptions.ConnectionError("连接被拒绝")):
            result = request_channel("1.2.3.4", cookie="test")

        assert result["raw_error"] is True
        assert "网络中断" in result["error_message"]

    def test_generic_error_returns_error_dict(self):
        import requests as req
        with patch('channel.aizhan.requests.get', side_effect=req.exceptions.RequestException("unknown")):
            result = request_channel("1.2.3.4", cookie="test")

        assert result["raw_error"] is True
        assert "查询失败" in result["error_message"]


class TestParseResponse:

    def test_error_dict_passed_through(self):
        error_dict = {"raw_error": True, "error_message": "timeout"}
        result = parse_response(error_dict, "1.2.3.4")
        assert result == error_dict

    def test_missing_dns_infos_returns_error(self):
        html = "<html><body><div class='dns-content'>content</div></body></html>"
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is False
        assert "dns-infos" in result["error"]

    def test_missing_dns_content_returns_error(self):
        html = "<html><body><div class='dns-infos'>info</div></body></html>"
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is False
        assert "dns-content" in result["error"]

    def test_both_missing_returns_both_names(self):
        html = "<html><body></body></html>"
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is False
        assert "dns-infos" in result["error"]
        assert "dns-content" in result["error"]

    def test_no_domains_message_returns_empty_list(self):
        html = _make_html(
            dns_infos_content='<strong>IP</strong><strong>北京 朝阳 联通</strong><span class="red">0</span>',
            dns_content_text="暂无域名解析到该IP",
        )
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is True
        assert result["domains"] == []
        assert result["domain_count"] == 0

    def test_china_location_parsed(self):
        html = _make_html(
            dns_infos_content='<strong>IP</strong><strong>北京 朝阳 联通</strong><span class="red">3</span>',
            dns_content_text="some content",
            tbody_rows=[
                ["1", '<a href="#">example.com</a>', '<span>测试站</span>', "类型", "其他"],
                ["2", '<a href="#">test.cn</a>', '<span>测试2</span>', "类型", "其他"],
                ["3", '<a href="#">demo.org</a>', '<span>演示</span>', "类型", "其他"],
            ],
        )
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is True
        assert result["location"] == "中国北京朝阳"
        assert result["isp"] == "联通"
        assert result["domain_count"] == 3
        assert len(result["domains"]) == 3
        assert result["domains"][0]["domain"] == "example.com"
        assert result["domains"][0]["title"] == "测试站"

    def test_foreign_location_parsed(self):
        html = _make_html(
            dns_infos_content='<strong>IP</strong><strong>United States California CloudFlare</strong><span class="red">1</span>',
            dns_content_text="some content",
            tbody_rows=[
                ["1", '<a href="#">cloudflare.com</a>', '<span>CF</span>', "类型", "其他"],
            ],
        )
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is True
        assert "United States" in result["location"]

    def test_domain_deduplication(self):
        rows = [
            ["1", '<a href="#">dup.com</a>', '<span>A</span>', "类型", "其他"],
            ["2", '<a href="#">dup.com</a>', '<span>B</span>', "类型", "其他"],
            ["3", '<a href="#">unique.com</a>', '<span>C</span>', "类型", "其他"],
        ]
        html = _make_html(
            dns_infos_content='<strong>IP</strong><strong>广东 深圳 电信</strong><span class="red">3</span>',
            dns_content_text="content",
            tbody_rows=rows,
        )
        result = parse_response(html, "1.2.3.4")
        domains = [d["domain"] for d in result["domains"]]
        assert domains.count("dup.com") == 1
        assert "unique.com" in domains

    def test_domain_max_20(self):
        rows = [[str(i), f'<a href="#">domain{i}.com</a>', '<span>T</span>', "类型", "其他"] for i in range(30)]
        html = _make_html(
            dns_infos_content='<strong>IP</strong><strong>上海 浦东 电信</strong><span class="red">30</span>',
            dns_content_text="content",
            tbody_rows=rows,
        )
        result = parse_response(html, "1.2.3.4")
        assert len(result["domains"]) == 20

    def test_short_domain_filtered_out(self):
        rows = [
            ["1", '<a href="#">ab.com</a>', '<span>OK</span>', "类型", "其他"],
            ["2", '<a href="#">a.b</a>', '<span>Short</span>', "类型", "其他"],
        ]
        html = _make_html(
            dns_infos_content='<strong>IP</strong><strong>浙江 杭州 电信</strong><span class="red">2</span>',
            dns_content_text="content",
            tbody_rows=rows,
        )
        result = parse_response(html, "1.2.3.4")
        domain_names = [d["domain"] for d in result["domains"]]
        assert "ab.com" in domain_names
        assert "a.b" not in domain_names

    def test_no_strong_tags_still_succeeds(self):
        html = _make_html(
            dns_infos_content='<span class="red">0</span>',
            dns_content_text="暂无域名解析到该IP",
        )
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is True
        assert result["location"] is None
        assert result["isp"] is None

    def test_domain_count_span_non_numeric(self):
        html = _make_html(
            dns_infos_content='<strong>IP</strong><strong>广东 广州 电信</strong><span class="red">N/A</span>',
            dns_content_text="暂无域名解析到该IP",
        )
        result = parse_response(html, "1.2.3.4")
        assert result["domain_count"] == 0

    def test_missing_tbody_returns_error(self):
        html = """
        <html><body>
        <div class="dns-infos"><strong>IP</strong><strong>北京 海淀 联通</strong><span class="red">5</span></div>
        <div class="dns-content">有内容但没有表格
            <table></table>
        </div>
        </body></html>
        """
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is False
        assert "表格" in result["error"]

    def test_row_with_less_than_5_cols_skipped(self):
        rows = [
            ["1", '<a href="#">ok.com</a>', '<span>T</span>'],
        ]
        html = _make_html(
            dns_infos_content='<strong>IP</strong><strong>北京 朝阳 联通</strong><span class="red">1</span>',
            dns_content_text="content",
            tbody_rows=rows,
        )
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is True
        assert result["domains"] == []

    def test_domain_from_text_when_no_anchor(self):
        rows = [
            ["1", "fallback.com", '<span>Title</span>', "类型", "其他"],
        ]
        html = _make_html(
            dns_infos_content='<strong>IP</strong><strong>江苏 南京 电信</strong><span class="red">1</span>',
            dns_content_text="content",
            tbody_rows=rows,
        )
        result = parse_response(html, "1.2.3.4")
        assert len(result["domains"]) == 1
        assert result["domains"][0]["domain"] == "fallback.com"


class TestFetchChannel:

    def test_normal_flow(self):
        html = _make_html(
            dns_infos_content='<strong>IP</strong><strong>北京 朝阳 联通</strong><span class="red">1</span>',
            dns_content_text="content",
            tbody_rows=[
                ["1", '<a href="#">example.com</a>', '<span>测试</span>', "类型", "其他"],
            ],
        )
        with patch('channel.aizhan.request_channel', return_value=html):
            with patch('channel.aizhan.apply_delay'):
                result = fetch_channel("1.2.3.4", cookie="c", delay=0)

        assert result["success"] is True
        assert "query_time" in result

    def test_error_flow_still_adds_query_time(self):
        error_data = {"raw_error": True, "error_message": "网络超时: timeout"}
        with patch('channel.aizhan.request_channel', return_value=error_data):
            with patch('channel.aizhan.apply_delay'):
                result = fetch_channel("1.2.3.4", cookie="c", delay=0)

        assert result["raw_error"] is True
        assert "query_time" in result

    def test_delay_is_applied(self):
        with patch('channel.aizhan.request_channel', return_value="<html></html>"):
            with patch('channel.aizhan.apply_delay') as mock_delay:
                fetch_channel("1.2.3.4", cookie="c", delay=3.0)

        mock_delay.assert_called_once_with(3.0)


class TestValidateChannelKey:

    def test_empty_cookie_exits(self):
        with patch('channel.aizhan.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.aizhan_cookie = ""
            MockSettings.return_value = mock_settings
            with pytest.raises(SystemExit):
                validate_channel_key()

    def test_whitespace_cookie_exits(self):
        with patch('channel.aizhan.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.aizhan_cookie = "   "
            MockSettings.return_value = mock_settings
            with pytest.raises(SystemExit):
                validate_channel_key()

    def test_redirect_cookie_exits(self):
        with patch('channel.aizhan.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.aizhan_cookie = "expired_cookie"
            mock_settings.aizhan_validate_timeout = 10
            MockSettings.return_value = mock_settings

            mock_resp = MagicMock()
            mock_resp.status_code = 302
            with patch('channel.aizhan.requests.get', return_value=mock_resp):
                with pytest.raises(SystemExit):
                    validate_channel_key()

    def test_404_cookie_exits(self):
        with patch('channel.aizhan.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.aizhan_cookie = "bad_cookie"
            mock_settings.aizhan_validate_timeout = 10
            MockSettings.return_value = mock_settings

            mock_resp = MagicMock()
            mock_resp.status_code = 404
            with patch('channel.aizhan.requests.get', return_value=mock_resp):
                with pytest.raises(SystemExit):
                    validate_channel_key()

    def test_network_error_exits(self):
        import requests as req
        with patch('channel.aizhan.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.aizhan_cookie = "test_cookie"
            mock_settings.aizhan_validate_timeout = 10
            MockSettings.return_value = mock_settings

            with patch('channel.aizhan.requests.get', side_effect=req.exceptions.ConnectionError("网络错误")):
                with pytest.raises(SystemExit):
                    validate_channel_key()

    def test_valid_cookie_succeeds(self):
        with patch('channel.aizhan.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.aizhan_cookie = "valid_cookie"
            mock_settings.aizhan_validate_timeout = 10
            MockSettings.return_value = mock_settings

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            with patch('channel.aizhan.requests.get', return_value=mock_resp):
                validate_channel_key()


class TestAizhanChannelExtra:

    def test_fetch_with_kwargs(self):
        ch = AizhanChannel()
        expected = {"success": True, "query_time": "2024-01-01"}
        with patch('channel.aizhan.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch("1.2.3.4", cookie="c", timeout=20, delay=0)

        mock_fetch.assert_called_once_with("1.2.3.4", cookie="c", timeout=20, delay=0)
        assert result == expected
