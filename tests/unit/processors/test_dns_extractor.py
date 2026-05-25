from ip_info.processors.dns_verify.extractor import extract_domain_mappings


class TestExtractDomainMappings:
    def test_extract_from_aizhan_string_domains(self):
        ip_data = {
            "ip": "1.2.3.4",
            "aizhan": {
                "domains": ["example.com", "test.com"],
            },
        }
        mappings = extract_domain_mappings(ip_data, channels=("aizhan",))
        assert len(mappings) == 2
        assert mappings[0]["domain"] == "example.com"
        assert mappings[0]["target_ip"] == "1.2.3.4"
        assert mappings[0]["sources"] == ["aizhan"]
        assert mappings[1]["domain"] == "test.com"

    def test_extract_from_chinaz_dict_domains(self):
        ip_data = {
            "ip": "1.2.3.4",
            "chinaz": {
                "domains": [
                    {"domain": "example.cn", "ip": "1.2.3.4"},
                    {"domain": "test.cn", "ip": "1.2.3.4"},
                ],
            },
        }
        mappings = extract_domain_mappings(ip_data, channels=("chinaz",))
        assert len(mappings) == 2
        assert mappings[0]["domain"] == "example.cn"
        assert mappings[0]["sources"] == ["chinaz"]
        assert mappings[1]["domain"] == "test.cn"

    def test_no_domains_returns_empty(self):
        ip_data = {
            "ip": "1.2.3.4",
            "aizhan": {"domains": []},
        }
        mappings = extract_domain_mappings(ip_data)
        assert mappings == []

    def test_no_channel_data_returns_empty(self):
        ip_data = {
            "ip": "1.2.3.4",
        }
        mappings = extract_domain_mappings(ip_data)
        assert mappings == []

    def test_channel_data_not_dict_returns_empty(self):
        ip_data = {
            "ip": "1.2.3.4",
            "aizhan": "not a dict",
        }
        mappings = extract_domain_mappings(ip_data)
        assert mappings == []

    def test_multiple_channels_merged(self):
        ip_data = {
            "ip": "1.2.3.4",
            "aizhan": {
                "domains": ["a.com"],
            },
            "chinaz": {
                "domains": [{"domain": "b.cn"}],
            },
        }
        mappings = extract_domain_mappings(ip_data)
        assert len(mappings) == 2
        aizhan_mappings = [m for m in mappings if "aizhan" in m["sources"]]
        chinaz_mappings = [m for m in mappings if "chinaz" in m["sources"]]
        assert len(aizhan_mappings) == 1
        assert len(chinaz_mappings) == 1
        assert aizhan_mappings[0]["domain"] == "a.com"
        assert chinaz_mappings[0]["domain"] == "b.cn"

    def test_empty_ip_data(self):
        ip_data = {}
        mappings = extract_domain_mappings(ip_data)
        assert mappings == []

    def test_dict_domain_without_domain_key_skipped(self):
        ip_data = {
            "ip": "1.2.3.4",
            "aizhan": {
                "domains": [{"name": "no-domain-key"}],
            },
        }
        mappings = extract_domain_mappings(ip_data, channels=("aizhan",))
        assert mappings == []

    def test_empty_string_domain_skipped(self):
        ip_data = {
            "ip": "1.2.3.4",
            "aizhan": {
                "domains": ["", "valid.com"],
            },
        }
        mappings = extract_domain_mappings(ip_data, channels=("aizhan",))
        assert len(mappings) == 1
        assert mappings[0]["domain"] == "valid.com"
