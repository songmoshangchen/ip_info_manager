import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from ip_info.channel.config import (
    AizhanConfig,
    ChannelConfig,
    ChinazConfig,
    FofaHostConfig,
    FofaSearchConfig,
    IpInfoApiConfig,
    IpInfoFreeConfig,
    PortScanConfig,
    RdnsConfig,
    SslCertConfig,
    WhoisConfig,
    ZoomEyeConfig,
)


@pytest.fixture(autouse=True)
def clean_ip_env(monkeypatch):
    for key in list(os.environ.keys()):
        if key.startswith("IP_"):
            monkeypatch.delenv(key, raising=False)


def _no_env_file(**kwargs):
    kwargs["_env_file"] = None
    return kwargs


class TestChannelConfigBase:
    def test_default_values(self):
        config = ChannelConfig(**_no_env_file())
        assert config.storage_dir == ""
        assert config.storage_name == "ip_data"

    def test_custom_values(self):
        config = ChannelConfig(**_no_env_file(storage_dir="custom_dir", storage_name="custom_name"))
        assert config.storage_dir == "custom_dir"
        assert config.storage_name == "custom_name"

    def test_env_prefix_is_ip(self):
        with patch.dict(os.environ, {"IP_STORAGE_DIR": "from_env"}, clear=False):
            config = ChannelConfig(_env_file=None)
            assert config.storage_dir == "from_env"


class TestRdnsConfig:
    def test_default_values(self):
        config = RdnsConfig(**_no_env_file())
        assert config.rdns_query_timeout == 1.5
        assert config.rdns_query_delay == 0.1
        assert config.storage_dir == ""

    def test_custom_timeout(self):
        config = RdnsConfig(**_no_env_file(rdns_query_timeout=5.0))
        assert config.rdns_query_timeout == 5.0


class TestIpInfoApiConfig:
    def test_required_field_missing(self):
        with pytest.raises(ValidationError, match="ipinfo_access_token"):
            IpInfoApiConfig(_env_file=None)

    def test_with_token(self):
        config = IpInfoApiConfig(**_no_env_file(ipinfo_access_token="test_token"))
        assert config.ipinfo_access_token == "test_token"
        assert config.ipinfo_query_timeout == 30.0
        assert config.ipinfo_query_delay == 1.2

    def test_all_custom_values(self):
        config = IpInfoApiConfig(
            _env_file=None,
            ipinfo_access_token="tok",
            ipinfo_query_timeout=10.0,
            ipinfo_query_delay=0.5,
        )
        assert config.ipinfo_access_token == "tok"
        assert config.ipinfo_query_timeout == 10.0
        assert config.ipinfo_query_delay == 0.5


class TestIpInfoFreeConfig:
    def test_default_values(self):
        config = IpInfoFreeConfig(**_no_env_file())
        assert config.ipinfo_query_timeout == 30.0
        assert config.ipinfo_query_delay == 1.2

    def test_inherits_channel_config(self):
        config = IpInfoFreeConfig(**_no_env_file(storage_name="my_data"))
        assert config.storage_name == "my_data"


class TestFofaHostConfig:
    def test_required_field_missing(self):
        with pytest.raises(ValidationError, match="fofa_api_key"):
            FofaHostConfig(_env_file=None)

    def test_with_key(self):
        config = FofaHostConfig(**_no_env_file(fofa_api_key="my_key"))
        assert config.fofa_api_key == "my_key"
        assert config.fofa_query_timeout == 30.0
        assert config.fofa_query_delay == 2.0


class TestFofaSearchConfig:
    def test_required_field_missing(self):
        with pytest.raises(ValidationError, match="fofa_api_key"):
            FofaSearchConfig(_env_file=None)

    def test_with_key(self):
        config = FofaSearchConfig(**_no_env_file(fofa_api_key="my_key"))
        assert config.fofa_api_key == "my_key"


class TestAizhanConfig:
    def test_required_field_missing(self):
        with pytest.raises(ValidationError, match="aizhan_cookie"):
            AizhanConfig(_env_file=None)

    def test_with_cookie(self):
        config = AizhanConfig(**_no_env_file(aizhan_cookie="session=abc"))
        assert config.aizhan_cookie == "session=abc"
        assert config.aizhan_query_timeout == 15.0
        assert config.aizhan_query_delay == 2.0


class TestChinazConfig:
    def test_default_cookie_is_empty(self):
        config = ChinazConfig(**_no_env_file())
        assert config.chinaz_cookie == ""
        assert config.chinaz_query_timeout == 15.0
        assert config.chinaz_query_delay == 2.0

    def test_with_cookie(self):
        config = ChinazConfig(**_no_env_file(chinaz_cookie="toolUserGrade=1; chinaz_zxuser=x"))
        assert config.chinaz_cookie == "toolUserGrade=1; chinaz_zxuser=x"


class TestWhoisConfig:
    def test_default_values(self):
        config = WhoisConfig(**_no_env_file())
        assert config.whois_query_timeout == 2.0
        assert config.whois_query_delay == 0.5


class TestSslCertConfig:
    def test_default_values(self):
        config = SslCertConfig(**_no_env_file())
        assert config.ssl_cert_port == 443
        assert config.ssl_cert_timeout == 5.0
        assert config.ssl_cert_openssl_timeout == 10.0
        assert config.ssl_cert_query_delay == 0.5


class TestZoomEyeConfig:
    def test_default_values(self):
        config = ZoomEyeConfig(**_no_env_file())
        assert config.zoomeye_api_key == ""
        assert config.zoomeye_query_timeout == 30.0
        assert config.zoomeye_query_delay == 2.0


class TestPortScanConfig:
    def test_default_values(self):
        config = PortScanConfig(**_no_env_file())
        assert config.port_scan_nmap_path == "nmap"
        assert config.port_scan_timeout == 90
        assert config.port_scan_port_list == "config/port_scan/top1000.txt"
        assert config.port_scan_arguments == "-sV -T4 -Pn --open"

    def test_custom_arguments(self):
        config = PortScanConfig(**_no_env_file(port_scan_arguments="-sT -T4 -Pn --open"))
        assert config.port_scan_arguments == "-sT -T4 -Pn --open"


class TestEnvOverride:
    def test_env_var_overrides_default(self):
        with patch.dict(os.environ, {"IP_RDNS_QUERY_TIMEOUT": "5.0"}, clear=False):
            config = RdnsConfig(_env_file=None)
            assert config.rdns_query_timeout == 5.0

    def test_explicit_value_overrides_env(self):
        with patch.dict(os.environ, {"IP_RDNS_QUERY_TIMEOUT": "5.0"}, clear=False):
            config = RdnsConfig(_env_file=None, rdns_query_timeout=8.0)
            assert config.rdns_query_timeout == 8.0

    def test_env_var_fills_required_field(self):
        with patch.dict(os.environ, {"IP_FOFA_API_KEY": "env_key"}, clear=False):
            config = FofaHostConfig(_env_file=None)
            assert config.fofa_api_key == "env_key"
