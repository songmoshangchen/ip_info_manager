import ssl
import socket
import subprocess
import tempfile
import re
import time
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import SslCertSettings as Settings
from writer import IPWriter
from utils.logger_utils import get_channel_logger

_logger = get_channel_logger('ssl_cert')


def validate_channel_key():
    print("✅ SSL 证书渠道无需 Key 校验（直连目标 IP 获取证书）")


def _get_ssl_cert_text(ip: str, port: int = 443, timeout: float = 5.0, openssl_timeout: float = 10.0):
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


def _cert_to_text(pem_text: str, openssl_timeout: float = 10.0) -> str:
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False, encoding='utf-8')
    try:
        tmp.write(pem_text)
        tmp.close()
        result = subprocess.run(
            ['openssl', 'x509', '-text', '-noout', '-in', tmp.name],
            capture_output=True, text=True, timeout=openssl_timeout,
        )
        return result.stdout
    except FileNotFoundError:
        _logger.debug("openssl 命令不可用，尝试直接解析 PEM")
        return pem_text
    except Exception as e:
        _logger.debug(f"openssl 解析证书失败: {e}")
        return pem_text
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def _parse_domains(cert_text: str) -> list:
    seen = set()
    domains = []

    cn_match = re.search(r'Subject:.*?CN\s*=\s*([^/\n,\s]+)', cert_text)
    if cn_match:
        cn = cn_match.group(1).strip()
        if cn and cn not in seen:
            seen.add(cn)
            domains.append(cn)

    san_match = re.search(r'Subject Alternative Name[^:]*:\s*(.+)', cert_text, re.IGNORECASE)
    if san_match:
        san_text = san_match.group(1)
        for dns_match in re.finditer(r'DNS:([^,\s]+)', san_text):
            domain = dns_match.group(1).strip()
            if domain and domain not in seen:
                seen.add(domain)
                domains.append(domain)

    return domains


def request_channel(ip: str, port: int = 443, timeout: float = 5.0, openssl_timeout: float = 10.0, **kwargs):
    _logger.debug(f"获取 SSL 证书: ip={ip}, port={port}")

    try:
        cert_text = _get_ssl_cert_text(ip, port=port, timeout=timeout, openssl_timeout=openssl_timeout)
        if not cert_text:
            return {
                'raw_error': True,
                'error_message': 'no_cert',
            }
        return {'cert_text': cert_text}
    except socket.timeout:
        _logger.debug(f"SSL 连接超时: ip={ip}")
        return {
            'raw_error': True,
            'error_message': 'connection_timeout',
        }
    except ConnectionRefusedError:
        _logger.debug(f"连接被拒绝: ip={ip}")
        return {
            'raw_error': True,
            'error_message': 'connection_refused',
        }
    except ssl.SSLError as e:
        _logger.debug(f"SSL 错误: ip={ip}, error={e}")
        return {
            'raw_error': True,
            'error_message': f'ssl_error: {e}',
        }
    except Exception as e:
        _logger.debug(f"获取 SSL 证书失败: ip={ip}, error={e}")
        return {
            'raw_error': True,
            'error_message': str(e),
        }


def fetch_channel(ip: str, port: int = 443, timeout: float = 5.0, openssl_timeout: float = 10.0, delay: float = 0, **kwargs) -> dict:
    apply_delay(delay)

    _logger.debug(f"fetch_channel 开始: ip={ip}")

    result = request_channel(ip, port=port, timeout=timeout, openssl_timeout=openssl_timeout, **kwargs)

    return format_output(result, ip=ip, port=port)


def apply_delay(delay: float):
    if delay > 0:
        time.sleep(delay)


def format_output(result: dict, ip: str = '', port: int = 443) -> dict:
    if result.get('raw_error'):
        return {
            'ip': ip,
            'port': port,
            'error': result.get('error_message', 'Unknown'),
            'query_time': datetime.now().isoformat(),
        }

    cert_text = result.get('cert_text', '')
    domains = _parse_domains(cert_text)

    subject_cn = ''
    cn_match = re.search(r'Subject:.*?CN\s*=\s*([^/\n,\s]+)', cert_text)
    if cn_match:
        subject_cn = cn_match.group(1).strip()

    issuer_cn = ''
    issuer_match = re.search(r'Issuer:.*?CN\s*=\s*([^/\n,\s]+)', cert_text)
    if issuer_match:
        issuer_cn = issuer_match.group(1).strip()

    not_before = ''
    nb_match = re.search(r'Not Before\s*:\s*(.+)', cert_text)
    if nb_match:
        not_before = nb_match.group(1).strip()

    not_after = ''
    na_match = re.search(r'Not After\s*:\s*(.+)', cert_text)
    if na_match:
        not_after = na_match.group(1).strip()

    san_entries = []
    san_match = re.search(r'Subject Alternative Name[^:]*:\s*(.+)', cert_text, re.IGNORECASE)
    if san_match:
        san_text = san_match.group(1)
        for dns_match in re.finditer(r'DNS:([^,\s]+)', san_text):
            san_entries.append(dns_match.group(1).strip())

    return {
        'ip': ip,
        'port': port,
        'subject_cn': subject_cn,
        'issuer_cn': issuer_cn,
        'not_before': not_before,
        'not_after': not_after,
        'san_domains': san_entries,
        'domains': domains,
        'query_time': datetime.now().isoformat(),
    }


def main(ip: str):
    settings = Settings()
    ip_writer = IPWriter(settings=settings)

    data = fetch_channel(
        ip=ip,
        port=settings.ssl_cert_port,
        timeout=settings.ssl_cert_timeout,
        openssl_timeout=settings.ssl_cert_openssl_timeout,
        delay=settings.ssl_cert_query_delay,
    )
    ip_writer.add_or_update_ip(ip=ip, channel="ssl_cert", data=data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python ssl_cert.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
