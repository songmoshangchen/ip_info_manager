from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChannelConfig(BaseSettings):
    storage_dir: str = Field(default="", description="channel数据存储子目录（相对于data/，可为空）")
    storage_name: str = Field(default="ip_data", description="存储名称（用于数据文件命名前缀）")

    model_config = SettingsConfigDict(
        env_prefix="IP_",
        env_file=".env",
        extra="ignore",
    )


class RdnsConfig(ChannelConfig):
    rdns_query_timeout: float = Field(default=1.5, description="RDNS 查询超时时间（秒）")
    rdns_query_delay: float = Field(default=0.1, description="RDNS 批量查询间隔（秒）")


class IpInfoApiConfig(ChannelConfig):
    ipinfo_access_token: str = Field(..., description="IPInfo Access Token（必填）")
    ipinfo_query_timeout: float = Field(default=30.0, description="IPInfo API 查询超时时间（秒）")
    ipinfo_query_delay: float = Field(default=1.2, description="IPInfo API 查询间隔（秒）")


class IpInfoFreeConfig(ChannelConfig):
    ipinfo_query_timeout: float = Field(default=30.0, description="IPInfo 免费查询超时时间（秒）")
    ipinfo_query_delay: float = Field(default=1.2, description="IPInfo 免费查询间隔（秒）")


class FofaHostConfig(ChannelConfig):
    fofa_api_key: str = Field(..., description="FOFA API Key（必填）")
    fofa_query_timeout: float = Field(default=30.0, description="FOFA 查询超时时间（秒）")
    fofa_query_delay: float = Field(default=2.0, description="FOFA 查询间隔（秒）")


class FofaSearchConfig(ChannelConfig):
    fofa_api_key: str = Field(..., description="FOFA API Key（必填）")
    fofa_query_timeout: float = Field(default=30.0, description="FOFA 查询超时时间（秒）")
    fofa_query_delay: float = Field(default=2.0, description="FOFA 查询间隔（秒）")


class AizhanConfig(ChannelConfig):
    aizhan_cookie: str = Field(..., description="爱站网 Cookie（必填）")
    aizhan_query_timeout: float = Field(default=15.0, description="爱站网查询超时时间（秒）")
    aizhan_query_delay: float = Field(default=2.0, description="爱站网查询间隔（秒）")


class ChinazConfig(ChannelConfig):
    chinaz_cookie: str = Field(default="", description="站长之家 Cookie（可选）")
    chinaz_query_timeout: float = Field(default=15.0, description="站长之家查询超时时间（秒）")
    chinaz_query_delay: float = Field(default=2.0, description="站长之家查询间隔（秒）")


class WhoisConfig(ChannelConfig):
    whois_query_timeout: float = Field(default=2.0, description="Whois 查询超时时间（秒）")
    whois_query_delay: float = Field(default=0.5, description="Whois 批量查询间隔（秒）")


class SslCertConfig(ChannelConfig):
    ssl_cert_port: int = Field(default=443, description="SSL 证书获取端口")
    ssl_cert_timeout: float = Field(default=5.0, description="SSL 连接超时时间（秒）")
    ssl_cert_openssl_timeout: float = Field(default=10.0, description="OpenSSL 子进程超时时间（秒）")
    ssl_cert_query_delay: float = Field(default=0.5, description="SSL 证书查询间隔（秒）")


class ZoomEyeConfig(ChannelConfig):
    zoomeye_api_key: str = Field(default="", description="ZoomEye API Key")
    zoomeye_query_timeout: float = Field(default=30.0, description="ZoomEye 查询超时时间（秒）")
    zoomeye_query_delay: float = Field(default=2.0, description="ZoomEye 查询间隔（秒）")


class PortScanConfig(ChannelConfig):
    port_scan_nmap_path: str = Field(default="nmap", description="nmap 可执行文件路径")
    port_scan_timeout: int = Field(default=90, description="单 IP 端口扫描超时秒数")
    port_scan_port_list: str = Field(default="config/port_scan/top1000.txt", description="端口列表文件路径")
