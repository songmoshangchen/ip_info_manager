import requests
from bs4 import BeautifulSoup

from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.channel.errors import ChannelError, ChannelPermanentError

CHINA_PROVINCES = [
    "北京",
    "天津",
    "河北",
    "山西",
    "内蒙古",
    "辽宁",
    "吉林",
    "黑龙江",
    "上海",
    "江苏",
    "浙江",
    "安徽",
    "福建",
    "江西",
    "山东",
    "河南",
    "湖北",
    "湖南",
    "广东",
    "广西",
    "海南",
    "重庆",
    "四川",
    "贵州",
    "云南",
    "西藏",
    "陕西",
    "甘肃",
    "青海",
    "宁夏",
    "新疆",
    "香港",
    "澳门",
    "台湾",
]


class AizhanChannel(BaseChannelAdapter):
    channel_name = "aizhan"

    def __init__(self, cookie: str, timeout: float = 15.0):
        self.cookie = cookie
        self.timeout = timeout

    def _validate_key(self) -> None:
        if not self.cookie or not self.cookie.strip():
            raise ChannelPermanentError("爱站网 Cookie 未配置")
        response = requests.get(
            "https://member.aizhan.com/user.php",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36 "
                    "SE 2.X MetaSr 1.0"
                ),
                "Cookie": self.cookie,
            },
            timeout=self.timeout,
            allow_redirects=False,
        )
        if response.status_code in (301, 302):
            raise ChannelPermanentError("爱站网 Cookie 已失效")
        if response.status_code == 403:
            raise ChannelPermanentError("爱站网 Cookie 无效")
        response.raise_for_status()

    def _request(self, ip: str, **kwargs) -> str:
        timeout = kwargs.get("timeout", self.timeout)
        url = f"https://dns.aizhan.com/{ip}/"
        headers = {
            "Host": "dns.aizhan.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "identity",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36 "
                "SE 2.X MetaSr 1.0"
            ),
            "Cookie": self.cookie,
        }
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout as e:
            raise ChannelError(f"爱站网查询超时: {ip} - {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise ChannelError(f"爱站网连接失败: {ip} - {e}") from e
        except Exception as e:
            raise ChannelError(f"爱站网查询错误: {ip} - {e}") from e

        if response.status_code == 403:
            raise ChannelPermanentError(f"爱站网 Cookie 无效: {ip}")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            raise ChannelError(f"爱站网查询失败: {ip} - HTTP {response.status_code}")

        return response.text

    def _parse(self, raw: str, ip: str) -> dict:
        soup = BeautifulSoup(raw, "html.parser")

        dns_infos = soup.find("div", class_="dns-infos")
        dns_content = soup.find("div", class_="dns-content")

        if not dns_infos or not dns_content:
            missing = []
            if not dns_infos:
                missing.append("dns-infos")
            if not dns_content:
                missing.append("dns-content")
            raise ChannelError(f"爱站网页面结构异常: 缺少 {', '.join(missing)}")

        result = {
            "query_ip": ip,
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
                is_china = any(p in parts[0] for p in CHINA_PROVINCES)
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
                raise ChannelError("爱站网页面结构异常: 未找到表格数据")

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
