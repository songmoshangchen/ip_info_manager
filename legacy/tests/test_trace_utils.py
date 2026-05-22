import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def cn_ip_with_domains():
    return {
        'ipinfo_api': {'country_code': 'CN', 'country': 'China'},
        'aizhan': {
            'success': True,
            'domains': [
                {'domain': 'example.cn', 'title': '示例'},
                {'domain': 'test.cn', 'start_time': '2024-01-01'},
            ],
        },
        'chinaz': {'success': False},
        'fofa_host': {
            'ports': [
                {'port': 80, 'protocol': 'http', 'products': [{'product': 'nginx'}]},
                {'port': 443, 'protocol': 'https', 'products': []},
            ],
        },
        'trace_classify': {
            'category': 'residential',
            'matched_by': [{'note': '住宅宽带'}],
        },
    }


@pytest.fixture
def foreign_ip_no_domains():
    return {
        'ipinfo_api': {'country_code': 'US', 'country': 'United States'},
        'aizhan': {'success': False},
        'chinaz': {'success': False},
        'fofa_host': {'error': True},
        'trace_classify': {'category': 'other'},
    }


@pytest.fixture
def cn_ip_no_channels():
    return {
        'ipinfo_api': {'country_code': 'CN', 'country': 'China'},
        'trace_classify': {'category': 'cdn', 'matched_by': [{'note': 'CDN节点'}]},
    }


class TestIsChinaIP:

    def test_china_by_country_code(self):
        from scenarios.trace_ip.trace_utils import is_china_ip

        assert is_china_ip({'ipinfo_api': {'country_code': 'CN', 'country': ''}}) is True

    def test_china_by_country_name(self):
        from scenarios.trace_ip.trace_utils import is_china_ip

        assert is_china_ip({'ipinfo_api': {'country_code': '', 'country': 'China'}}) is True

    def test_not_china(self):
        from scenarios.trace_ip.trace_utils import is_china_ip

        assert is_china_ip({'ipinfo_api': {'country_code': 'US', 'country': 'United States'}}) is False

    def test_no_ipinfo(self):
        from scenarios.trace_ip.trace_utils import is_china_ip

        assert is_china_ip({}) is False


class TestExtractAllDomains:

    def test_extracts_from_aizhan(self, cn_ip_with_domains):
        from scenarios.trace_ip.trace_utils import extract_all_domains

        domains = extract_all_domains(cn_ip_with_domains)
        assert len(domains) == 2
        assert domains[0]['domain'] == 'example.cn'
        assert domains[0]['source'] == 'aizhan'
        assert domains[0]['title'] == '示例'
        assert domains[1]['domain'] == 'test.cn'
        assert domains[1]['start_time'] == '2024-01-01'

    def test_deduplicates_across_sources(self):
        from scenarios.trace_ip.trace_utils import extract_all_domains

        info = {
            'aizhan': {'success': True, 'domains': [{'domain': 'dup.com'}]},
            'chinaz': {'success': True, 'domains': [{'domain': 'dup.com'}]},
        }
        domains = extract_all_domains(info)
        assert len(domains) == 1

    def test_returns_empty_when_no_success(self, foreign_ip_no_domains):
        from scenarios.trace_ip.trace_utils import extract_all_domains

        assert extract_all_domains(foreign_ip_no_domains) == []

    def test_skips_empty_domain_strings(self):
        from scenarios.trace_ip.trace_utils import extract_all_domains

        info = {
            'aizhan': {'success': True, 'domains': [{'domain': ''}, {'domain': 'valid.com'}]},
        }
        domains = extract_all_domains(info)
        assert len(domains) == 1
        assert domains[0]['domain'] == 'valid.com'


class TestExtractFofaPorts:

    def test_extracts_port_dicts(self, cn_ip_with_domains):
        from scenarios.trace_ip.trace_utils import extract_fofa_ports

        ports = extract_fofa_ports(cn_ip_with_domains)
        assert len(ports) == 2
        assert ports[0]['port'] == 80
        assert ports[0]['protocol'] == 'http'
        assert ports[0]['products'] == 'nginx'
        assert ports[1]['port'] == 443
        assert ports[1]['products'] == ''

    def test_returns_empty_on_error(self, foreign_ip_no_domains):
        from scenarios.trace_ip.trace_utils import extract_fofa_ports

        assert extract_fofa_ports(foreign_ip_no_domains) == []

    def test_returns_empty_when_no_fofa(self):
        from scenarios.trace_ip.trace_utils import extract_fofa_ports

        assert extract_fofa_ports({}) == []


class TestHasDomains:

    def test_has_domains_true(self, cn_ip_with_domains):
        from scenarios.trace_ip.trace_utils import has_domains

        assert has_domains(cn_ip_with_domains) is True

    def test_has_domains_false(self, foreign_ip_no_domains):
        from scenarios.trace_ip.trace_utils import has_domains

        assert has_domains(foreign_ip_no_domains) is False


class TestHasPorts:

    def test_has_ports_true(self, cn_ip_with_domains):
        from scenarios.trace_ip.trace_utils import has_ports

        assert has_ports(cn_ip_with_domains) is True

    def test_has_ports_false(self, foreign_ip_no_domains):
        from scenarios.trace_ip.trace_utils import has_ports

        assert has_ports(foreign_ip_no_domains) is False


class TestTracePriority:

    def test_p1_cn_with_domains(self, cn_ip_with_domains):
        from scenarios.trace_ip.trace_utils import trace_priority

        assert trace_priority(cn_ip_with_domains) == 1

    def test_p2_foreign_with_domains(self):
        from scenarios.trace_ip.trace_utils import trace_priority

        info = {
            'ipinfo_api': {'country_code': 'US', 'country': 'US'},
            'aizhan': {'success': True, 'domains': [{'domain': 'x.com'}]},
            'fofa_host': {},
        }
        assert trace_priority(info) == 2

    def test_p2_cn_no_domains_with_ports(self):
        from scenarios.trace_ip.trace_utils import trace_priority

        info = {
            'ipinfo_api': {'country_code': 'CN', 'country': 'China'},
            'aizhan': {'success': False},
            'chinaz': {'success': False},
            'fofa_host': {'ports': [{'port': 80}]},
        }
        assert trace_priority(info) == 2

    def test_p4_foreign_nothing(self, foreign_ip_no_domains):
        from scenarios.trace_ip.trace_utils import trace_priority

        assert trace_priority(foreign_ip_no_domains) == 4

    def test_p3_foreign_with_ports(self):
        from scenarios.trace_ip.trace_utils import trace_priority

        info = {
            'ipinfo_api': {'country_code': 'US', 'country': 'US'},
            'aizhan': {'success': False},
            'chinaz': {'success': False},
            'fofa_host': {'ports': [{'port': 80}]},
        }
        assert trace_priority(info) == 3

    def test_p3_cn_only(self):
        from scenarios.trace_ip.trace_utils import trace_priority

        info = {
            'ipinfo_api': {'country_code': 'CN', 'country': 'China'},
            'aizhan': {'success': False},
            'chinaz': {'success': False},
        }
        assert trace_priority(info) == 3


class TestCatDisplay:

    def test_category_with_note(self, cn_ip_with_domains):
        from scenarios.trace_ip.trace_utils import cat_display

        result = cat_display(cn_ip_with_domains)
        assert '住宅宽带' in result

    def test_other_category(self, foreign_ip_no_domains):
        from scenarios.trace_ip.trace_utils import cat_display

        result = cat_display(foreign_ip_no_domains)
        assert '其他' in result

    def test_category_without_note(self, cn_ip_no_channels):
        from scenarios.trace_ip.trace_utils import cat_display

        result = cat_display(cn_ip_no_channels)
        assert 'CDN' in result


class TestTraceAction:

    def test_cn_with_domains(self, cn_ip_with_domains):
        from scenarios.trace_ip.trace_utils import trace_action

        result = trace_action(cn_ip_with_domains)
        assert 'ICP备案' in result

    def test_foreign_with_domains(self):
        from scenarios.trace_ip.trace_utils import trace_action

        info = {
            'ipinfo_api': {'country_code': 'US', 'country': 'US'},
            'aizhan': {'success': True, 'domains': [{'domain': 'x.com'}]},
        }
        result = trace_action(info)
        assert 'WHOIS' in result
        assert 'ICP' not in result

    def test_nothing_fallback(self, foreign_ip_no_domains):
        from scenarios.trace_ip.trace_utils import trace_action

        result = trace_action(foreign_ip_no_domains)
        assert '公开信息检索' in result


class TestSortKey:

    def test_sort_key_ordering(self, cn_ip_with_domains):
        from scenarios.trace_ip.trace_utils import sort_key

        key = sort_key(cn_ip_with_domains)
        assert key[0] == -2
        assert key[1] == -2
        assert key[2] == -1


class TestRobustnessFieldMissing:

    def test_is_china_ip_country_code_none(self):
        from scenarios.trace_ip.trace_utils import is_china_ip

        assert is_china_ip({'ipinfo_api': {'country_code': None, 'country': ''}}) is False

    @pytest.mark.xfail(reason="生产代码 bug: country=None 时 'China' in None 会 TypeError")
    def test_is_china_ip_country_none(self):
        from scenarios.trace_ip.trace_utils import is_china_ip

        assert is_china_ip({'ipinfo_api': {'country_code': '', 'country': None}}) is False

    @pytest.mark.xfail(reason="生产代码 bug: country=None 时 'China' in None 会 TypeError")
    def test_is_china_ip_both_none(self):
        from scenarios.trace_ip.trace_utils import is_china_ip

        assert is_china_ip({'ipinfo_api': {'country_code': None, 'country': None}}) is False

    def test_extract_domains_domain_key_missing(self):
        from scenarios.trace_ip.trace_utils import extract_all_domains

        info = {
            'aizhan': {'success': True, 'domains': [{'title': 'no domain key'}]},
        }
        domains = extract_all_domains(info)
        assert domains == []

    @pytest.mark.xfail(reason="生产代码 bug: domains 列表中含 None 时 d.get() 会 AttributeError")
    def test_extract_domains_none_in_list(self):
        from scenarios.trace_ip.trace_utils import extract_all_domains

        info = {
            'aizhan': {'success': True, 'domains': [None, {'domain': 'valid.com'}]},
        }
        domains = extract_all_domains(info)
        assert len(domains) == 1

    def test_extract_fofa_ports_missing_port_key(self):
        from scenarios.trace_ip.trace_utils import extract_fofa_ports

        info = {
            'fofa_host': {'ports': [{'protocol': 'http'}]},
        }
        ports = extract_fofa_ports(info)
        assert len(ports) == 1
        assert ports[0]['port'] == ''

    def test_extract_fofa_ports_missing_products_key(self):
        from scenarios.trace_ip.trace_utils import extract_fofa_ports

        info = {
            'fofa_host': {'ports': [{'port': 80, 'protocol': 'http'}]},
        }
        ports = extract_fofa_ports(info)
        assert len(ports) == 1
        assert ports[0]['products'] == ''

    def test_sort_key_no_trace_classify(self):
        from scenarios.trace_ip.trace_utils import sort_key

        key = sort_key({})
        assert key == (0, 0, 0)

    def test_sort_key_unknown_category(self):
        from scenarios.trace_ip.trace_utils import sort_key

        key = sort_key({'trace_classify': {'category': 'new_unknown_cat'}})
        assert key[2] == 0

    def test_cat_display_unknown_category_uses_category_as_label(self):
        from scenarios.trace_ip.trace_utils import cat_display

        info = {'trace_classify': {'category': 'future_category'}}
        result = cat_display(info)
        assert 'future_category' in result

    def test_cat_display_empty_matched_by(self):
        from scenarios.trace_ip.trace_utils import cat_display

        info = {'trace_classify': {'category': 'cloud_provider', 'matched_by': []}}
        result = cat_display(info)
        assert '云服务商' in result
        assert '（' not in result

    def test_trace_action_domains_and_ports(self):
        from scenarios.trace_ip.trace_utils import trace_action

        info = {
            'ipinfo_api': {'country_code': 'CN', 'country': 'China'},
            'aizhan': {'success': True, 'domains': [{'domain': 'x.cn'}]},
            'fofa_host': {'ports': [{'port': 80}]},
        }
        result = trace_action(info)
        assert 'ICP备案' in result
        assert '端口' in result
