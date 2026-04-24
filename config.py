import os
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(CONFIG_DIR, '.env')

FORBIDDEN_STORAGE_DIRS = {'ip_domain_lookup', 'trace_ip'}


def _validate_path_no_traversal(v: str, field_name: str) -> str:
    v = v.strip()
    if not v:
        return v
    if os.path.isabs(v):
        raise ValueError(f'{field_name} 不允许使用绝对路径: {v}')
    normalized = os.path.normpath(v)
    parts = normalized.replace('\\', '/').split('/')
    if '..' in parts:
        raise ValueError(f'{field_name} 不允许包含 ".." 路径遍历: {v}')
    return v


def _validate_simple_name(v: str, field_name: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError(f'{field_name} 不能为空')
    if os.path.isabs(v):
        raise ValueError(f'{field_name} 不允许使用绝对路径: {v}')
    if '\\' in v or '/' in v:
        raise ValueError(f'{field_name} 不允许包含路径分隔符: {v}')
    if '..' in v:
        raise ValueError(f'{field_name} 不允许包含 "..": {v}')
    return v


class BaseIPSettings(BaseSettings):
    storage_dir: str = Field(default='', description='channel数据存储子目录（相对于data/，可为空）')
    storage_name: str = Field(default='ip_data', description='存储名称（用于数据文件命名前缀）')
    ip_domain_lookup_project_name: str = Field(default='temp', description='ip_domain_lookup场景项目名称')
    trace_ip_project_name: str = Field(default='temp', description='trace_ip场景项目名称')

    @field_validator('storage_dir')
    @classmethod
    def validate_storage_dir(cls, v: str) -> str:
        v = _validate_path_no_traversal(v, 'storage_dir')
        if v and v in FORBIDDEN_STORAGE_DIRS:
            raise ValueError(f'storage_dir 不允许使用场景保留名称: {v}')
        return v

    @field_validator('storage_name')
    @classmethod
    def validate_storage_name(cls, v: str) -> str:
        return _validate_simple_name(v, 'storage_name')

    @field_validator('ip_domain_lookup_project_name', 'trace_ip_project_name')
    @classmethod
    def validate_project_name(cls, v: str) -> str:
        return _validate_simple_name(v, '项目名称')

    class Config:
        env_prefix = 'IP_'
        env_file = ENV_FILE
        extra = 'ignore'


class Settings(BaseIPSettings):
    pass


class FofaSettings(BaseIPSettings):
    fofa_api_key: str = Field(..., description='Fofa API Key（必填）')
    fofa_query_delay: float = Field(default=2.0, description='Fofa API 查询间隔（秒）')


class IpinfoSettings(BaseIPSettings):
    ipinfo_access_token: str = Field(..., description='Ipinfo Access Token（必填）')
    ipinfo_query_delay: float = Field(default=1.2, description='Ipinfo API 查询间隔（秒）')


class AizhanSettings(BaseIPSettings):
    aizhan_cookie: str = Field(..., description='爱站网 Cookie（必填）')
    aizhan_query_delay: float = Field(default=2.0, description='爱站查询间隔（秒）')


class ChinazSettings(BaseIPSettings):
    chinaz_cookie: str = Field(default='', description='站长之家 Cookie（可选）')
    chinaz_query_delay: float = Field(default=2.0, description='站长之家查询间隔（秒）')


class WhoisSettings(BaseIPSettings):
    whois_query_timeout: float = Field(default=2.0, description='Whois 查询超时时间（秒）')
    whois_query_delay: float = Field(default=0.5, description='Whois 批量查询间隔（秒）')


class RdnsSettings(BaseIPSettings):
    rdns_query_timeout: float = Field(default=1.5, description='RDNS 查询超时时间（秒）')
    rdns_query_delay: float = Field(default=0.1, description='RDNS 批量查询间隔（秒）')


class ZoomeyeSettings(BaseIPSettings):
    zoomeye_api_key: str = Field(default='', description='ZoomEye API Key')
    zoomeye_query_delay: float = Field(default=1.0, description='ZoomEye 查询间隔（秒）')


class SslCertSettings(BaseIPSettings):
    ssl_cert_port: int = Field(default=443, description='SSL 证书获取端口')
    ssl_cert_timeout: float = Field(default=5.0, description='SSL 连接超时时间（秒）')
    ssl_cert_query_delay: float = Field(default=0.5, description='SSL 证书查询间隔（秒）')


class IPDomainLookupSettings(BaseIPSettings):
    rdns_ptr_enabled: bool = Field(default=True, description='启用 RDNS PTR 反向解析')
    aizhan_enabled: bool = Field(default=True, description='启用爱站网 IP 反查域名')
    chinaz_enabled: bool = Field(default=True, description='启用站长之家 IP 反查域名')
    zoomeye_enabled: bool = Field(default=True, description='启用 ZoomEye 网络空间测绘')
    fofa_search_enabled: bool = Field(default=True, description='启用 Fofa 搜索查询')
    ssl_cert_enabled: bool = Field(default=True, description='启用 SSL 证书域名提取')


class TraceIPSettings(BaseIPSettings):
    phase1_ipinfo_enabled: bool = Field(default=True, description='溯源IP流水线阶段1：启用 IPInfo 查询')
    phase1_rdns_ptr_enabled: bool = Field(default=True, description='溯源IP流水线阶段1：启用 RDNS PTR 反向解析')
    phase3_aizhan_enabled: bool = Field(default=True, description='溯源IP流水线阶段3：启用爱站网 IP 反查域名')
    phase3_chinaz_enabled: bool = Field(default=True, description='溯源IP流水线阶段3：启用站长之家 IP 反查域名')
    phase3_fofa_host_enabled: bool = Field(default=True, description='溯源IP流水线阶段3：启用 Fofa Host 聚合查询')
