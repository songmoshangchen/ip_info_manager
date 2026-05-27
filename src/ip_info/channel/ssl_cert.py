import os
import re
import socket
import ssl
import subprocess
import tempfile

from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.config import SslCertConfig
from ip_info.channel.errors import ChannelError


def _get_ssl_cert_text(ip, port, timeout, openssl_timeout):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with socket.create_connection((ip, port), timeout=timeout) as sock:
        with context.wrap_socket(sock, server_hostname=ip) as ssock:
            der_cert = ssock.getpeercert(binary_form=True)
            if not der_cert:
                return None
            pem_text = ssl.DER_cert_to_PEM_cert(der_cert)
            return _cert_to_text(pem_text, openssl_timeout=openssl_timeout)


def _cert_to_text(pem_text, openssl_timeout):
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False, encoding="utf-8")
    try:
        tmp.write(pem_text)
        tmp.close()
        result = subprocess.run(
            ["openssl", "x509", "-text", "-noout", "-in", tmp.name],
            capture_output=True,
            text=True,
            timeout=openssl_timeout,
        )
        return result.stdout
    except FileNotFoundError:
        return pem_text
    except Exception:
        return pem_text
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def _parse_domains(cert_text):
    seen = set()
    domains = []

    cn_match = re.search(r"Subject:.*?CN\s*=\s*([^/\n,\s]+)", cert_text)
    if cn_match:
        cn = cn_match.group(1).strip()
        if cn and cn not in seen:
            seen.add(cn)
            domains.append(cn)

    san_match = re.search(r"Subject Alternative Name[^:]*:\s*(.+)", cert_text, re.IGNORECASE)
    if san_match:
        san_text = san_match.group(1)
        for dns_match in re.finditer(r"DNS:([^,\s]+)", san_text):
            domain = dns_match.group(1).strip()
            if domain and domain not in seen:
                seen.add(domain)
                domains.append(domain)

    return domains


class SslCertChannel(BaseChannelAdapter):
    channel_name = "ssl_cert"
    default_delay = 0.5

    def __init__(
        self,
        port: int | None = None,
        timeout: float | None = None,
        openssl_timeout: float | None = None,
        config: SslCertConfig | None = None,
    ):
        _config = config or SslCertConfig()
        self.port = port if port is not None else _config.ssl_cert_port
        self.timeout = timeout if timeout is not None else _config.ssl_cert_timeout
        self.openssl_timeout = openssl_timeout if openssl_timeout is not None else _config.ssl_cert_openssl_timeout
        self.default_delay = _config.ssl_cert_query_delay
        self._last_port = self.port

    def _request(self, ip: str, **kwargs):
        port = kwargs.get("port", self.port)
        self._last_port = port

        try:
            return _get_ssl_cert_text(ip, port, self.timeout, self.openssl_timeout)
        except socket.timeout:
            raise ChannelError(f"SSL 连接超时: {ip}:{port}")
        except ConnectionRefusedError:
            raise ChannelError(f"SSL 连接被拒绝: {ip}:{port}")
        except ssl.SSLError as e:
            raise ChannelError(f"SSL 错误: {ip}:{port} - {e}")
        except Exception as e:
            raise ChannelError(f"SSL 证书获取失败: {ip}:{port} - {e}")

    def _parse(self, raw, ip: str) -> dict:
        if raw is None:
            return {
                "query_target": ip,
                "port": self._last_port,
                "has_cert": False,
            }

        subject_cn = ""
        cn_match = re.search(r"Subject:.*?CN\s*=\s*([^/\n,\s]+)", raw)
        if cn_match:
            subject_cn = cn_match.group(1).strip()

        issuer_cn = ""
        issuer_match = re.search(r"Issuer:.*?CN\s*=\s*([^/\n,\s]+)", raw)
        if issuer_match:
            issuer_cn = issuer_match.group(1).strip()

        not_before = ""
        nb_match = re.search(r"Not Before\s*:\s*(.+)", raw)
        if nb_match:
            not_before = nb_match.group(1).strip()

        not_after = ""
        na_match = re.search(r"Not After\s*:\s*(.+)", raw)
        if na_match:
            not_after = na_match.group(1).strip()

        san_domains = []
        san_match = re.search(r"Subject Alternative Name[^:]*:\s*(.+)", raw, re.IGNORECASE)
        if san_match:
            san_text = san_match.group(1)
            for dns_match in re.finditer(r"DNS:([^,\s]+)", san_text):
                san_domains.append(dns_match.group(1).strip())

        domains = _parse_domains(raw)

        return {
            "query_target": ip,
            "port": self._last_port,
            "has_cert": True,
            "subject_cn": subject_cn,
            "issuer_cn": issuer_cn,
            "not_before": not_before,
            "not_after": not_after,
            "san_domains": san_domains,
            "domains": domains,
        }
