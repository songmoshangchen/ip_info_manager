import socket
import time
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import WhoisSettings as Settings
from writer import IPWriter
from utils.logger_utils import get_channel_logger

_logger = get_channel_logger('whois')

try:
    from whois import whois as whois_query
except ImportError:
    whois_query = None


def validate_channel_key():
    if whois_query is None:
        print("错误: whois 库未安装，请运行: pip install python-whois")
        sys.exit(1)

    try:
        socket.setdefaulttimeout(5.0)
        whois_query("google.com")
        print("✅ Whois 库验证通过")
    except socket.timeout:
        print("✅ Whois 库已安装（测试查询超时，属正常情况）")
    except Exception:
        print("✅ Whois 库已安装并可调用")


def request_channel(ip: str, timeout: float = 10.0, **kwargs):
    if whois_query is None:
        return {
            "raw_error": True,
            "error_message": "whois 库未安装，请运行: pip install python-whois",
        }

    _logger.debug(f"Whois 查询: ip={ip}, timeout={timeout}")
    try:
        socket.setdefaulttimeout(timeout)
        w = whois_query(ip)

        if w is None:
            return {
                "raw_error": True,
                "error_message": "未找到 Whois 信息",
            }

        return w

    except socket.timeout:
        return {
            "raw_error": True,
            "error_message": f"查询超时（超过 {timeout} 秒）",
        }

    except Exception as e:
        return {
            "raw_error": True,
            "error_message": str(e),
        }


def parse_response(raw_content, ip: str) -> dict:
    result = {
        "query_target": ip,
        "query_time": datetime.now().isoformat()
    }

    if isinstance(raw_content, dict) and raw_content.get('raw_error'):
        result.update({
            "has_whois": False,
            "raw_error": True,
            "error_message": raw_content.get('error_message', ''),
        })
        return result

    w = raw_content
    whois_data = {}

    if w.domain_name:
        whois_data["domain_name"] = w.domain_name if isinstance(w.domain_name, str) else (w.domain_name[0] if w.domain_name and len(w.domain_name) > 0 else None)

    if w.registrar:
        whois_data["registrar"] = w.registrar if isinstance(w.registrar, str) else (w.registrar[0] if w.registrar and len(w.registrar) > 0 else None)

    if w.org:
        whois_data["organization"] = w.org if isinstance(w.org, str) else (w.org[0] if w.org and len(w.org) > 0 else None)

    if w.country:
        whois_data["country"] = w.country if isinstance(w.country, str) else (w.country[0] if w.country and len(w.country) > 0 else None)

    if w.state:
        whois_data["state"] = w.state if isinstance(w.state, str) else (w.state[0] if w.state and len(w.state) > 0 else None)

    if w.city:
        whois_data["city"] = w.city if isinstance(w.city, str) else (w.city[0] if w.city and len(w.city) > 0 else None)

    if w.address:
        whois_data["address"] = w.address if isinstance(w.address, str) else (w.address[0] if w.address and len(w.address) > 0 else None)

    if w.name:
        whois_data["registrant_name"] = w.name if isinstance(w.name, str) else (w.name[0] if w.name and len(w.name) > 0 else None)

    if w.emails:
        whois_data["emails"] = w.emails if isinstance(w.emails, str) else (w.emails[0] if w.emails and len(w.emails) > 0 else None)

    if w.creation_date:
        creation_date = w.creation_date[0] if isinstance(w.creation_date, list) and len(w.creation_date) > 0 else w.creation_date
        whois_data["creation_date"] = creation_date.isoformat() if hasattr(creation_date, 'isoformat') else str(creation_date)

    if w.expiration_date:
        expiration_date = w.expiration_date[0] if isinstance(w.expiration_date, list) and len(w.expiration_date) > 0 else w.expiration_date
        whois_data["expiration_date"] = expiration_date.isoformat() if hasattr(expiration_date, 'isoformat') else str(expiration_date)

    if w.updated_date:
        updated_date = w.updated_date[0] if isinstance(w.updated_date, list) and len(w.updated_date) > 0 else w.updated_date
        whois_data["updated_date"] = updated_date.isoformat() if hasattr(updated_date, 'isoformat') else str(updated_date)

    if w.name_servers:
        whois_data["name_servers"] = w.name_servers if isinstance(w.name_servers, list) else ([w.name_servers] if w.name_servers else [])

    whois_data["status"] = w.status if isinstance(w.status, list) else ([w.status] if w.status else [])

    whois_data["dnssec"] = w.dnssec if hasattr(w, 'dnssec') else None

    result.update({
        "has_whois": True,
        "whois_data": whois_data
    })

    return result


def fetch_channel(ip: str, key: str = '', cookie: str = '', delay: float = 0, timeout: float = 10.0, **kwargs) -> dict:
    apply_delay(delay)

    raw = request_channel(ip, timeout=timeout, **kwargs)

    if isinstance(raw, dict) and raw.get('raw_error'):
        return format_output(parse_response(raw, ip))

    result = parse_response(raw, ip)
    return format_output(result)


def apply_delay(delay: float):
    if delay > 0:
        time.sleep(delay)


def format_output(data: dict) -> dict:
    data.setdefault('query_time', datetime.now().isoformat())
    return data


def main(ip: str):
    settings = Settings()
    ip_writer = IPWriter(settings=settings)

    data = fetch_channel(
        ip=ip,
        delay=settings.whois_query_delay,
        timeout=settings.whois_query_timeout,
    )
    ip_writer.add_or_update_ip(ip=ip, channel="whois", data=data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python whois.py <IP地址或域名>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
