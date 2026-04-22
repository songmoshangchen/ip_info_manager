import re
import time
import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, Any
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import AizhanSettings as Settings
from scripts.logger_utils import get_channel_logger

_logger = get_channel_logger('aizhan')


class IPWriter:
    def __init__(self):
        self.settings = Settings()
        script_dir = os.path.dirname(os.path.abspath(__file__))

        storage_dir = self.settings.storage_dir
        if not os.path.isabs(storage_dir):
            storage_dir = os.path.join(script_dir, storage_dir)

        self.storage_file = os.path.join(storage_dir, self.settings.storage_name + '.json')

        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)

        self._init_storage()

    def _init_storage(self):
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def _load_data(self):
        with open(self.storage_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)

    def _save_data(self, data):
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_or_update_ip(self, ip, channel, data):
        all_data = self._load_data()

        if ip not in all_data:
            all_data[ip] = {"ip": ip}

        all_data[ip][channel] = data
        self._save_data(all_data)
        return True


def validate_channel_key():
    settings = Settings()
    cookie = settings.aizhan_cookie

    if not cookie or not cookie.strip():
        print("错误: AIZHAN_COOKIE 未配置，请在 .env 文件中设置")
        sys.exit(1)

    try:
        url = "https://member.aizhan.com/user.php"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36 SE 2.X MetaSr 1.0",
            "Cookie": cookie,
        }
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=False)

        if response.status_code in (301, 302):
            print("错误: 爱站网 Cookie 已失效（被重定向到登录页）")
            sys.exit(1)

        if response.status_code == 404:
            print("错误: 爱站网 Cookie 验证失败（404）")
            sys.exit(1)

        print("✅ 爱站网 Cookie 验证通过")
    except requests.exceptions.RequestException as e:
        print(f"错误: 无法连接爱站网进行 Cookie 验证 - {e}")
        sys.exit(1)


def request_channel(ip: str, cookie: str = '', **kwargs):
    _logger.debug(f"请求爱站网: ip={ip}")
    try:
        url = f"https://dns.aizhan.com/{ip}/"
        headers = {
            "Host": "dns.aizhan.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "identity",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36 SE 2.X MetaSr 1.0",
            "Cookie": cookie,
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        return response.text

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            error_type = "网络超时"
        elif "403" in error_msg or "429" in error_msg or "forbidden" in error_msg.lower():
            error_type = "爱站网禁止请求"
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

    _logger.debug(f"解析爱站网响应: ip={ip}")

    soup = BeautifulSoup(raw_content, "html.parser")

    dns_infos = soup.find("div", class_="dns-infos")
    dns_content = soup.find("div", class_="dns-content")

    if not dns_infos or not dns_content:
        missing = []
        if not dns_infos:
            missing.append("dns-infos")
        if not dns_content:
            missing.append("dns-content")
        return {
            "success": False,
            "error": f"页面缺少关键部分: {', '.join(missing)}",
        }

    result = {
        "success": True,
        "location": None,
        "isp": None,
        "domain_count": 0,
        "domains": [],
    }

    strong_tags = dns_infos.find_all("strong")
    if len(strong_tags) >= 2:
        location_info = strong_tags[1].get_text(strip=True)
        parts = location_info.split()
        if len(parts) >= 3:
            china_provinces = [
                "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
                "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
                "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
                "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆",
                "香港", "澳门", "台湾",
            ]
            is_china = any(p in parts[0] for p in china_provinces)

            if is_china:
                result["location"] = f"中国{parts[0]}{parts[1]}"
                result["isp"] = " ".join(parts[2:]) if len(parts) > 3 else parts[2]
            else:
                result["location"] = location_info
                result["isp"] = parts[-1] if parts else None
        elif len(parts) >= 2:
            result["location"] = location_info

    domain_count_span = dns_infos.find("span", class_="red")
    if domain_count_span:
        try:
            result["domain_count"] = int(domain_count_span.get_text(strip=True))
        except ValueError:
            result["domain_count"] = 0

    if "暂无域名解析到该IP" in dns_content.get_text():
        result["domains"] = []
    else:
        tbody = dns_content.find("tbody")
        if not tbody:
            return {
                "success": False,
                "error": "页面结构异常: 未找到表格数据",
            }

        domain_list = []
        for row in tbody.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            domain_col = cols[1]
            domain_a = domain_col.find("a")
            domain = domain_a.get_text(strip=True) if domain_a else domain_col.get_text(strip=True)

            title_col = cols[2]
            title_span = title_col.find("span")
            title = title_span.get_text(strip=True) if title_span else title_col.get_text(strip=True)

            if len(domain) > 3 and "." in domain:
                domain_list.append({"domain": domain, "title": title})

        seen = set()
        unique = []
        for d in domain_list:
            if d["domain"] not in seen:
                seen.add(d["domain"])
                unique.append(d)
        result["domains"] = unique[:20]

    result["domain_count"] = max(result["domain_count"], len(result["domains"]))

    return result


def fetch_channel(ip: str, key: str = '', cookie: str = '', delay: float = 2, **kwargs) -> dict:
    apply_delay(delay)

    raw = request_channel(ip, cookie=cookie, **kwargs)

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
    ip_writer = IPWriter()

    data = fetch_channel(
        ip=ip,
        cookie=settings.aizhan_cookie,
        delay=settings.aizhan_query_delay,
    )
    ip_writer.add_or_update_ip(ip=ip, channel="aizhan", data=data)

    if data.get("success"):
        domain_count = data.get("domain_count", 0)
        location = data.get("location", "N/A")
        print(f"✅ {ip} - {location} - {domain_count} 个域名")
    else:
        print(f"❌ {ip} - {data.get('error', 'Unknown error')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python aizhan.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
