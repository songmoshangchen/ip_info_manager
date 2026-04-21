import re
import time
import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, Optional, List, Any
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import ChinazSettings as Settings


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


def _parse_chinaz_html(html_content: str, ip: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html_content, "html.parser")

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
            "query_time": datetime.now().isoformat()
        }

    result = {
        "success": True,
        "location": None,
        "isp": None,
        "domains": [],
        "query_time": datetime.now().isoformat()
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


def fetch_chinaz(ip: str, cookie: str = "", delay: float = 2.0) -> dict:
    time.sleep(delay)

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

        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        return _parse_chinaz_html(response.text, ip)

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
            "success": False,
            "error": f"{error_type}: {error_msg}",
            "query_time": datetime.now().isoformat()
        }


def main(ip: str):
    ipv4_pattern = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    if not re.match(ipv4_pattern, ip):
        print(f"错误: 无效的 IPv4 地址: {ip}")
        return

    settings = Settings()
    ip_writer = IPWriter()

    chinaz_data = fetch_chinaz(
        ip=ip,
        cookie=settings.chinaz_cookie,
        delay=settings.chinaz_query_delay
    )
    ip_writer.add_or_update_ip(ip=ip, channel="chinaz", data=chinaz_data)

    if chinaz_data.get("success"):
        domain_count = len(chinaz_data.get("domains", []))
        location = chinaz_data.get("location", "N/A")
        print(f"✅ {ip} - {location} - {domain_count} 个域名")
    else:
        print(f"❌ {ip} - {chinaz_data.get('error', 'Unknown error')}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使用方法: python chinaz.py <IP地址>")
        sys.exit(1)

    target_ip = sys.argv[1]
    main(target_ip)
