import re
import time
import requests
import os
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, Any
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import ChinazSettings as Settings
from writer import IPWriter
from scripts.logger_utils import get_channel_logger

_logger = get_channel_logger('chinaz')


def validate_channel_key():
    settings = Settings()
    cookie = settings.chinaz_cookie

    if not cookie or not cookie.strip():
        print("错误: CHINAZ_COOKIE 未配置，请在 .env 文件中设置")
        sys.exit(1)

    required_keys = ["toolUserGrade", "chinaz_zxuser"]
    missing = [k for k in required_keys if k not in cookie]
    if missing:
        print(f"错误: Cookie 缺少必要字段: {', '.join(missing)}，请重新获取完整 Cookie")
        sys.exit(1)

    try:
        url = "https://ipchaxun.com/8.8.8.8/"
        headers = {
            "Host": "ipchaxun.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.95 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Cookie": cookie,
        }
        response = requests.get(url, headers=headers, timeout=settings.chinaz_validate_timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        info_div = soup.find("div", class_="info", attrs={"data-result": "true"})

        if info_div:
            print("✅ 站长之家 Cookie 验证通过（查询接口正常）")
        else:
            print("警告: 站长之家查询页面结构异常，Cookie 可能无效")
            print("✅ Cookie 格式验证通过，继续执行...")
    except requests.exceptions.RequestException as e:
        print(f"警告: 无法连接站长之家验证 Cookie - {e}")
        print("✅ Cookie 格式验证通过，继续执行...")


def request_channel(ip: str, cookie: str = '', timeout: float = 15.0, **kwargs):
    _logger.debug(f"请求站长之家: ip={ip}")
    try:
        url = f"https://ipchaxun.com/{ip}/"
        headers = {
            "Host": "ipchaxun.com",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": f"https://ipchaxun.com/{ip}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.95 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "identity",
        }

        session = requests.Session()
        if cookie:
            session.headers.update({"Cookie": cookie})

        response = session.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        return response.text

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            error_type = "网络超时"
        elif "403" in error_msg or "429" in error_msg or "forbidden" in error_msg.lower():
            error_type = "站长之家禁止请求"
        elif "网络" in error_msg or "连接" in error_msg:
            error_type = "网络中断"
        else:
            error_type = "查询失败"

        return {
            "raw_error": True,
            "error_message": f"{error_type}: {error_msg}",
        }


def parse_response(raw_content: str, ip: str) -> dict:
    if isinstance(raw_content, dict) and raw_content.get('raw_error'):
        return raw_content

    _logger.debug(f"解析站长之家响应: ip={ip}")

    soup = BeautifulSoup(raw_content, "html.parser")

    info_div = soup.find("div", class_="info", attrs={"data-result": "true"})
    domain_div = soup.find("div", id="J_domain")

    if not info_div or not domain_div:
        missing = []
        if not info_div:
            missing.append("info section")
        if not domain_div:
            missing.append("domain section")
        return {
            "success": False,
            "error": f"页面缺少关键部分: {', '.join(missing)}",
        }

    result = {
        "success": True,
        "location": None,
        "isp": None,
        "domains": [],
    }

    labels = info_div.find_all("label")
    for label in labels:
        name_span = label.find("span", class_="name")
        value_span = label.find("span", class_="value")
        if name_span and value_span:
            name = name_span.get_text(strip=True)
            value = value_span.get_text(strip=True)
            if "归属地" in name:
                result["location"] = value
            elif "运营商" in name:
                result["isp"] = value

    domain_ps = domain_div.find_all("p")

    has_no_result = any(
        p.get_text(strip=True) == "暂无结果" for p in domain_ps
    )

    if not has_no_result:
        domain_list = []
        for p in domain_ps:
            a_tag = p.find("a")
            date_span = p.find("span", class_="date")
            if not a_tag:
                continue

            domain = a_tag.get_text(strip=True)

            start_time = ""
            end_time = ""
            if date_span:
                date_text = date_span.get_text(strip=True)
                if "-----" in date_text:
                    start_time, end_time = date_text.split("-----", 1)

            if len(domain) > 3 and "." in domain:
                domain_list.append({
                    "domain": domain,
                    "start_time": start_time,
                    "end_time": end_time,
                })

        seen = set()
        unique = []
        for d in domain_list:
            if d["domain"] not in seen:
                seen.add(d["domain"])
                unique.append(d)
        result["domains"] = unique[:20]

    return result


def fetch_channel(ip: str, key: str = '', cookie: str = '', delay: float = 2, timeout: float = 15.0, **kwargs) -> dict:
    apply_delay(delay)

    raw = request_channel(ip, cookie=cookie, timeout=timeout, **kwargs)

    if isinstance(raw, dict) and raw.get('raw_error'):
        return format_output(raw)

    result = parse_response(raw, ip)
    return format_output(result)


def apply_delay(delay: float):
    if delay > 0:
        time.sleep(delay)


def format_output(data: dict) -> dict:
    data.setdefault('query_time', datetime.now().isoformat())
    return data


def main(ip: str):
    ipv4_pattern = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    if not re.match(ipv4_pattern, ip):
        print(f"错误: 无效的 IPv4 地址: {ip}")
        return

    settings = Settings()
    ip_writer = IPWriter(settings=settings)

    data = fetch_channel(
        ip=ip,
        cookie=settings.chinaz_cookie,
        delay=settings.chinaz_query_delay,
        timeout=settings.chinaz_query_timeout,
    )
    ip_writer.add_or_update_ip(ip=ip, channel="chinaz", data=data)

    if data.get("success"):
        domain_count = len(data.get("domains", []))
        location = data.get("location", "N/A")
        print(f"✅ {ip} - {location} - {domain_count} 个域名")
    else:
        print(f"❌ {ip} - {data.get('error', 'Unknown error')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python chinaz.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
