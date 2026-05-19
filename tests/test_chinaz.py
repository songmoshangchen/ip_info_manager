import os
import sys

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from channel.chinaz import (
    request_channel,
    parse_response,
    fetch_channel,
    validate_channel_key,
    ChinazChannel,
)


def _make_html(info_labels=None, domain_ps=None):
    info_div = '<div class="info" data-result="true">'
    if info_labels:
        for name, value in info_labels:
            info_div += f'<label><span class="name">{name}</span><span class="value">{value}</span></label>'
    info_div += '</div>'

    domain_div = '<div id="J_domain">'
    if domain_ps is not None:
        for item in domain_ps:
            if item.get("no_result"):
                domain_div += '<p>暂无结果</p>'
            else:
                domain = item.get("domain", "")
                date = item.get("date", "")
                domain_div += f'<p><a href="#">{domain}</a><span class="date">{date}</span></p>'
    domain_div += '</div>'

    return f'<html><body>{info_div}{domain_div}</body></html>'


class TestRequestChannel:

    def test_normal_returns_html(self):
        html = "<html>test</html>"
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status.return_value = None
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_session.headers = {}

        with patch('channel.chinaz.requests.Session', return_value=mock_session):
            result = request_channel("1.2.3.4", cookie="test_cookie", timeout=10.0)

        assert result == html

    @pytest.mark.xfail(reason="BUG: ReadTimeout 'Read timed out' 不含 'timeout' 连续子串, 被误分类为 '查询失败'")
    def test_read_timeout_classified_as_network_timeout(self):
        import requests as req
        with patch('channel.chinaz.requests.Session') as MockSession:
            mock_session = MagicMock()
            mock_session.get.side_effect = req.exceptions.ReadTimeout("Read timed out.")
            MockSession.return_value = mock_session
            result = request_channel("1.2.3.4", cookie="test")

        assert result["raw_error"] is True
        assert "网络超时" in result["error_message"]

    def test_timeout_keyword_in_message(self):
        import requests as req
        with patch('channel.chinaz.requests.Session') as MockSession:
            mock_session = MagicMock()
            mock_session.get.side_effect = req.exceptions.Timeout("Connection timeout")
            MockSession.return_value = mock_session
            result = request_channel("1.2.3.4", cookie="test")

        assert result["raw_error"] is True
        assert "网络超时" in result["error_message"]

    def test_403_returns_error_dict(self):
        import requests as req
        with patch('channel.chinaz.requests.Session') as MockSession:
            mock_session = MagicMock()
            mock_session.get.side_effect = req.exceptions.HTTPError("403 Forbidden")
            MockSession.return_value = mock_session
            result = request_channel("1.2.3.4", cookie="test")

        assert result["raw_error"] is True
        assert "站长之家禁止请求" in result["error_message"]

    def test_connection_error_returns_error_dict(self):
        import requests as req
        with patch('channel.chinaz.requests.Session') as MockSession:
            mock_session = MagicMock()
            mock_session.get.side_effect = req.exceptions.ConnectionError("连接被拒绝")
            MockSession.return_value = mock_session
            result = request_channel("1.2.3.4", cookie="test")

        assert result["raw_error"] is True
        assert "网络中断" in result["error_message"]


class TestParseResponse:

    def test_error_dict_passed_through(self):
        error_dict = {"raw_error": True, "error_message": "timeout"}
        result = parse_response(error_dict, "1.2.3.4")
        assert result == error_dict

    def test_missing_info_div_returns_error(self):
        html = '<html><body><div id="J_domain"></div></body></html>'
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is False
        assert "info section" in result["error"]

    def test_missing_domain_div_returns_error(self):
        html = '<html><body><div class="info" data-result="true"></div></body></html>'
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is False
        assert "domain section" in result["error"]

    def test_normal_parse_with_location_and_isp(self):
        html = _make_html(
            info_labels=[("归属地", "广东省深圳市"), ("运营商", "中国电信")],
            domain_ps=[{"no_result": True}],
        )
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is True
        assert result["location"] == "广东省深圳市"
        assert result["isp"] == "中国电信"

    def test_domains_parsed_with_dates(self):
        html = _make_html(
            info_labels=[("归属地", "北京")],
            domain_ps=[
                {"domain": "example.com", "date": "2024-01-01-----2025-01-01"},
                {"domain": "test.cn", "date": "2023-06-01-----2024-06-01"},
            ],
        )
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is True
        assert len(result["domains"]) == 2
        assert result["domains"][0]["domain"] == "example.com"
        assert result["domains"][0]["start_time"] == "2024-01-01"
        assert result["domains"][0]["end_time"] == "2025-01-01"

    def test_domain_deduplication(self):
        html = _make_html(
            info_labels=[("归属地", "上海")],
            domain_ps=[
                {"domain": "dup.com", "date": "-----"},
                {"domain": "dup.com", "date": "-----"},
                {"domain": "unique.com", "date": "-----"},
            ],
        )
        result = parse_response(html, "1.2.3.4")
        domains = [d["domain"] for d in result["domains"]]
        assert domains.count("dup.com") == 1
        assert "unique.com" in domains

    def test_domain_max_20(self):
        domain_ps = [{"domain": f"domain{i}.com", "date": "-----"} for i in range(30)]
        html = _make_html(
            info_labels=[("归属地", "广州")],
            domain_ps=domain_ps,
        )
        result = parse_response(html, "1.2.3.4")
        assert len(result["domains"]) == 20

    def test_short_domain_filtered(self):
        html = _make_html(
            info_labels=[("归属地", "杭州")],
            domain_ps=[
                {"domain": "ab.com", "date": "-----"},
                {"domain": "a.b", "date": "-----"},
            ],
        )
        result = parse_response(html, "1.2.3.4")
        domain_names = [d["domain"] for d in result["domains"]]
        assert "ab.com" in domain_names
        assert "a.b" not in domain_names

    def test_no_result_message_returns_empty_domains(self):
        html = _make_html(
            info_labels=[("归属地", "成都")],
            domain_ps=[{"no_result": True}],
        )
        result = parse_response(html, "1.2.3.4")
        assert result["success"] is True
        assert result["domains"] == []

    def test_no_anchor_tag_in_p_skipped(self):
        html = _make_html(
            info_labels=[("归属地", "武汉")],
            domain_ps=[{"domain": "", "date": ""}],
        )
        result = parse_response(html, "1.2.3.4")
        assert result["domains"] == []


class TestFetchChannel:

    def test_normal_flow(self):
        html = _make_html(
            info_labels=[("归属地", "北京"), ("运营商", "联通")],
            domain_ps=[{"no_result": True}],
        )
        with patch('channel.chinaz.request_channel', return_value=html):
            with patch('channel.chinaz.apply_delay'):
                result = fetch_channel("1.2.3.4", cookie="c", delay=0)

        assert result["success"] is True
        assert "query_time" in result

    def test_error_flow_still_adds_query_time(self):
        error_data = {"raw_error": True, "error_message": "网络超时: timeout"}
        with patch('channel.chinaz.request_channel', return_value=error_data):
            with patch('channel.chinaz.apply_delay'):
                result = fetch_channel("1.2.3.4", cookie="c", delay=0)

        assert result["raw_error"] is True
        assert "query_time" in result


class TestValidateChannelKey:

    def test_empty_cookie_exits(self):
        with patch('channel.chinaz.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.chinaz_cookie = ""
            MockSettings.return_value = mock_settings
            with pytest.raises(SystemExit):
                validate_channel_key()

    def test_whitespace_cookie_exits(self):
        with patch('channel.chinaz.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.chinaz_cookie = "   "
            MockSettings.return_value = mock_settings
            with pytest.raises(SystemExit):
                validate_channel_key()

    def test_missing_required_cookie_fields_exits(self):
        with patch('channel.chinaz.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.chinaz_cookie = "some_other_field=value"
            mock_settings.chinaz_validate_timeout = 10
            MockSettings.return_value = mock_settings
            with pytest.raises(SystemExit):
                validate_channel_key()

    def test_network_error_does_not_exit(self):
        import requests as req
        with patch('channel.chinaz.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.chinaz_cookie = "toolUserGrade=1; chinaz_zxuser=test"
            mock_settings.chinaz_validate_timeout = 10
            MockSettings.return_value = mock_settings

            with patch('channel.chinaz.requests.get', side_effect=req.exceptions.ConnectionError("网络错误")):
                validate_channel_key()

    def test_valid_cookie_succeeds(self):
        with patch('channel.chinaz.Settings') as MockSettings:
            mock_settings = MagicMock()
            mock_settings.chinaz_cookie = "toolUserGrade=1; chinaz_zxuser=test"
            mock_settings.chinaz_validate_timeout = 10
            MockSettings.return_value = mock_settings

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status.return_value = None
            mock_resp.text = '<html><div class="info" data-result="true"></div></html>'

            with patch('channel.chinaz.requests.get', return_value=mock_resp):
                validate_channel_key()


class TestChinazChannelExtra:

    def test_fetch_with_kwargs(self):
        ch = ChinazChannel()
        expected = {"success": True, "query_time": "2024-01-01"}
        with patch('channel.chinaz.fetch_channel', return_value=expected) as mock_fetch:
            result = ch.fetch("1.2.3.4", cookie="c", timeout=20, delay=0)

        mock_fetch.assert_called_once_with("1.2.3.4", cookie="c", timeout=20, delay=0)
        assert result == expected
