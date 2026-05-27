# 单条渠道查询

当用户需要查询单个 IP 的某个渠道情报时读取此文件。

## 决策树

```
用户说"查一下这个 IP 的 fofa 信息" → channel/fofa_host.py
用户说"查一下这个 IP 在爱站反查到哪些域名" → channel/aizhan.py
用户说"帮我查这个 IP 的 SSL 证书" → channel/ssl_cert.py
用户没有指定渠道 → 先用 reader.py get 查看已有数据，再询问需要补充哪些渠道
```

## 渠道速查表

所有命令在项目根目录 `ip_info_manager/` 下执行。查询结果自动写入数据库。

| 渠道 | 命令 | 凭证需求 | 默认间隔 |
|------|------|---------|---------|
| Fofa Host 聚合 | `python channel/fofa_host.py "<IP>"` | IP_FOFA_API_KEY | 2s |
| Fofa 搜索 | `python channel/fofa_search.py "<IP>"` | IP_FOFA_API_KEY | 2s |
| IPInfo | `python channel/ipinfo_api.py "<IP>"` | IP_IPINFO_ACCESS_TOKEN（可选） | 2s |
| RDNS PTR | `python channel/rdns_ptr.py "<IP>"` | 无 | 0s |
| Whois | `python channel/whois_query.py "<IP>"` | 需安装 python-whois | 0s |
| 爱站 IP 反查域名 | `python channel/aizhan.py "<IP>"` | IP_AIZHAN_COOKIE | 2s |
| 站长之家 IP 反查域名 | `python channel/chinaz.py "<IP>"` | IP_CHINAZ_COOKIE（可选） | 2s |
| ZoomEye | `python channel/zoomeye.py "<IP>"` | IP_ZOOMEYE_API_KEY | 1s |
| SSL 证书域名 | `python channel/ssl_cert.py "<IP>"` | 无（需系统 openssl） | 0.5s |

## 各渠道返回数据说明

**fofa_host**：主机详情（端口、服务、操作系统、国家、组织）
**fofa_search**：IP 关联的资产信息（完整 API 原始响应）
**ipinfo_api**：IP 地理位置、ASN、运营商（有 Token 返回更多信息）
**rdns_ptr**：反向域名解析结果（hostname、PTR 记录）
**whois**：IP/域名注册信息
**aizhan**：IP 反查域名列表 + 网站标题 + 归属地 + 运营商
**chinaz**：IP 反查域名列表 + 绑定时间段 + 归属地 + 运营商
**zoomeye**：网络空间资产信息（完整 API 原始响应）
**ssl_cert**：SSL 证书中的域名（Subject CN + SubjectAltName）
**port_scan**：nmap 端口扫描结果（开放端口、服务指纹、历史端口验证状态）

## 注意事项

- 爱站和站长之家通过爬虫抓取，Cookie 会过期，需定期更新
- 爱站和站长之家查询间隔建议不低于 2 秒
- Fofa 和 IPInfo API 有速率限制，不要将间隔设太短
- 查询结果自动写入数据库，无需手动操作
- 不确定参数时用 `python channel/<channel_name>.py --help`
