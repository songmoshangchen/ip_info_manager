import requests
from bs4 import BeautifulSoup

from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.errors import ChannelError, ChannelPermanentError


class ChinazChannel(BaseChannelAdapter):
    channel_name = "chinaz"
    REQUIRED_COOKIE_KEYS = ["toolUserGrade", "chinaz_zxuser"]

    def __init__(self, cookie: str, timeout: float = 15.0):
        self.cookie = cookie
        self.timeout = timeout

    def _validate_key(self) -> None:
        if not self.cookie or not self.cookie.strip():
            raise ChannelPermanentError("站长之家 Cookie 未配置")
        missing = [k for k in self.REQUIRED_COOKIE_KEYS if k not in self.cookie]
        if missing:
            raise ChannelPermanentError(f"站长之家 Cookie 缺少必要字段: {', '.join(missing)}")
        url = "https://ipchaxun.com/8.8.8.8/"
        headers = {
            "Host": "ipchaxun.com",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.95 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Cookie": self.cookie,
        }
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

    def _request(self, ip: str, **kwargs) -> str:
        timeout = kwargs.get("timeout", self.timeout)
        url = f"https://ipchaxun.com/{ip}/"
        headers = {
            "Host": "ipchaxun.com",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": f"https://ipchaxun.com/{ip}/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.95 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "identity",
            "Cookie": self.cookie,
        }
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout as e:
            raise ChannelError(f"站长之家查询超时: {ip} - {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise ChannelError(f"站长之家连接失败: {ip} - {e}") from e
        except Exception as e:
            raise ChannelError(f"站长之家查询错误: {ip} - {e}") from e

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise ChannelError(f"站长之家查询失败: {ip} - HTTP {response.status_code}")

        return response.text

    def _parse(self, raw: str, ip: str) -> dict:
        soup = BeautifulSoup(raw, "html.parser")

        info_div = soup.find("div", class_="info", attrs={"data-result": "true"})
        domain_div = soup.find("div", id="J_domain")

        if not info_div or not domain_div:
            missing = []
            if not info_div:
                missing.append("地域信息")
            if not domain_div:
                missing.append("域名区域")
            raise ChannelError(f"站长之家页面结构异常: 缺少 {', '.join(missing)}")

        result = {
            "query_ip": ip,
            "location": None,
            "isp": None,
            "domains": [],
            "domain_count": 0,
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
        has_no_result = any(p.get_text(strip=True) == "暂无结果" for p in domain_ps)

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
                        parts = date_text.split("-----", 1)
                        start_time = parts[0]
                        end_time = parts[1]

                if len(domain) > 3 and "." in domain:
                    domain_list.append(
                        {
                            "domain": domain,
                            "start_time": start_time,
                            "end_time": end_time,
                        }
                    )

            seen = set()
            unique = []
            for d in domain_list:
                if d["domain"] not in seen:
                    seen.add(d["domain"])
                    unique.append(d)
            result["domains"] = unique[:20]

        result["domain_count"] = len(result["domains"])

        return result
