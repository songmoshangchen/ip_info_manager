import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestPydanticV2Migration:

    def test_no_deprecation_warning_on_import(self):
        from config import BaseIPSettings
        import inspect
        source = inspect.getsource(BaseIPSettings)
        assert 'class Config' not in source, "BaseIPSettings still uses deprecated 'class Config'"

    def test_base_settings_uses_model_config(self):
        from config import BaseIPSettings
        assert hasattr(BaseIPSettings, 'model_config')
        assert 'env_prefix' in BaseIPSettings.model_config
        assert BaseIPSettings.model_config['env_prefix'] == 'IP_'

    def test_base_settings_env_file_configured(self):
        from config import BaseIPSettings
        assert BaseIPSettings.model_config.get('env_file') is not None

    def test_base_settings_extra_ignore(self):
        from config import BaseIPSettings
        assert BaseIPSettings.model_config.get('extra') == 'ignore'

    def test_settings_inherits_base(self):
        from config import Settings, BaseIPSettings
        assert issubclass(Settings, BaseIPSettings)

    def test_fofa_settings_inherits_base(self):
        from config import FofaSettings, BaseIPSettings
        assert issubclass(FofaSettings, BaseIPSettings)

    def test_fofa_settings_has_required_field(self):
        from config import FofaSettings
        assert 'fofa_api_key' in FofaSettings.model_fields

    def test_ipinfo_settings_inherits_base(self):
        from config import IpinfoSettings, BaseIPSettings
        assert issubclass(IpinfoSettings, BaseIPSettings)

    def test_aizhan_settings_inherits_base(self):
        from config import AizhanSettings, BaseIPSettings
        assert issubclass(AizhanSettings, BaseIPSettings)

    def test_chinaz_settings_inherits_base(self):
        from config import ChinazSettings, BaseIPSettings
        assert issubclass(ChinazSettings, BaseIPSettings)

    def test_whois_settings_inherits_base(self):
        from config import WhoisSettings, BaseIPSettings
        assert issubclass(WhoisSettings, BaseIPSettings)

    def test_rdns_settings_inherits_base(self):
        from config import RdnsSettings, BaseIPSettings
        assert issubclass(RdnsSettings, BaseIPSettings)

    def test_zoomeye_settings_inherits_base(self):
        from config import ZoomeyeSettings, BaseIPSettings
        assert issubclass(ZoomeyeSettings, BaseIPSettings)

    def test_ssl_cert_settings_inherits_base(self):
        from config import SslCertSettings, BaseIPSettings
        assert issubclass(SslCertSettings, BaseIPSettings)

    def test_ip_domain_lookup_settings_inherits_base(self):
        from config import IPDomainLookupSettings, BaseIPSettings
        assert issubclass(IPDomainLookupSettings, BaseIPSettings)

    def test_trace_ip_settings_inherits_base(self):
        from config import TraceIPSettings, BaseIPSettings
        assert issubclass(TraceIPSettings, BaseIPSettings)

    def test_ip_tagger_settings_inherits_base(self):
        from config import IpTaggerSettings, BaseIPSettings
        assert issubclass(IpTaggerSettings, BaseIPSettings)


class TestSettingsValidation:

    def test_storage_dir_validator_works(self):
        from config import BaseIPSettings
        with pytest.raises(ValueError):
            BaseIPSettings(storage_dir='../traversal')

    def test_storage_dir_absolute_path_rejected(self):
        from config import BaseIPSettings
        with pytest.raises(ValueError):
            BaseIPSettings(storage_dir='/absolute/path')

    def test_storage_name_empty_rejected(self):
        from config import BaseIPSettings
        with pytest.raises(ValueError):
            BaseIPSettings(storage_name='')

    def test_storage_name_with_slash_rejected(self):
        from config import BaseIPSettings
        with pytest.raises(ValueError):
            BaseIPSettings(storage_name='bad/name')

    def test_storage_dir_forbidden_name_rejected(self):
        from config import BaseIPSettings
        with pytest.raises(ValueError):
            BaseIPSettings(storage_dir='trace_ip')

    def test_valid_storage_dir(self):
        from config import BaseIPSettings
        s = BaseIPSettings(storage_dir='my_data')
        assert s.storage_dir == 'my_data'

    def test_default_values(self):
        from config import BaseIPSettings
        s = BaseIPSettings(_env_file=None)
        assert s.storage_dir == ''
        assert s.storage_name == 'ip_data'

    def test_env_prefix_override(self, monkeypatch):
        monkeypatch.setenv('IP_STORAGE_DIR', 'from_env')
        from config import BaseIPSettings
        s = BaseIPSettings()
        assert s.storage_dir == 'from_env'
