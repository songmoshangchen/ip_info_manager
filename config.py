import os
from pydantic_settings import BaseSettings
from pydantic import Field


CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(CONFIG_DIR, '.env')


class BaseIPSettings(BaseSettings):
    storage_dir: str = Field(default='data', description='存储目录')
    storage_name: str = Field(default='ip_data', description='存储名称（用于数据文件命名前缀）')
    
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
