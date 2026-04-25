# 异常处理与故障排除

当渠道采集过程中出现报错、凭证失效、限频等异常时读取此文件。

## 异常分流

```
采集报错
  ├─ 报 "cookie 无效" / "登录过期" / HTTP 403 → 凭证失效 → 见下方"凭证失效"
  ├─ 报 "key 无效" / "unauthorized" / HTTP 401 → API Key 失效 → 见下方"凭证失效"
  ├─ 报 "rate limit" / "too many requests" / HTTP 429 → 频率限制 → 见下方"频率限制"
  ├─ 报 "timeout" / "连接超时" → 网络超时 → 见下方"网络超时"
  ├─ 报 "connection refused" / "无法连接" → 目标不可达 → 见下方"目标不可达"
  ├─ 大量 IP 查询失败 → 批量异常 → 见下方"批量异常"
  └─ 其他错误 → 查看日志详细排查 → 见下方"查看日志"
```

## 凭证失效

**症状**：爱站/站长之家报 cookie 相关错误，Fofa/ZoomEye 报 key 无效，IPInfo 报 token 无效

**处理步骤**：

1. 确认哪个渠道的凭证失效
2. 引导用户获取新凭证（浏览器登录对应网站获取 cookie，或到对应平台获取新 key）
3. 使用 config_tool.py 更新凭证（不要直接编辑 .env 文件）：

```bash
python tools/config_tool.py set IP_AIZHAN_COOKIE "新cookie值"
python tools/config_tool.py set IP_FOFA_API_KEY "新key值"
python tools/config_tool.py set IP_ZOOMEYE_API_KEY "新key值"
python tools/config_tool.py set IP_IPINFO_ACCESS_TOKEN "新token值"
python tools/config_tool.py set IP_CHINAZ_COOKIE "新cookie值"
```

4. 验证凭证是否生效：

```bash
python channel/fofa_host.py "8.8.8.8"  # 用一个公共 IP 测试
```

5. 重新运行采集命令

更多凭证配置详见 references/config.md。

## 频率限制

**症状**：报 rate limit / too many requests / HTTP 429，或部分 IP 查询返回空结果

**处理步骤**：

1. 增大查询间隔时间：

```bash
python tools/config_tool.py set IP_FOFA_QUERY_DELAY 5.0
python tools/config_tool.py set IP_AIZHAN_QUERY_DELAY 5.0
python tools/config_tool.py set IP_CHINAZ_QUERY_DELAY 5.0
```

2. 等待一段时间后重新运行（批量脚本支持断点续查，已处理的 IP 会自动跳过）
3. 对于批量脚本，可考虑分批处理（拆分 IP 文件为多个小文件）

## 网络超时

**症状**：报 timeout / 连接超时

**处理步骤**：

1. 增大超时时间：

```bash
python tools/config_tool.py set IP_RDNS_QUERY_TIMEOUT 5.0
python tools/config_tool.py set IP_WHOIS_QUERY_TIMEOUT 5.0
python tools/config_tool.py set IP_SSL_CERT_TIMEOUT 10
```

2. 检查网络连接是否正常
3. 部分超时可能是目标服务器问题，可跳过失败 IP 后续重查

## 目标不可达

**症状**：报 connection refused / 无法连接

**处理步骤**：

1. 确认目标 IP 是否存活（ping 或 curl 测试）
2. SSL 证书查询需要目标开放 443 端口，不开放则无法获取
3. 属于正常情况（不是所有 IP 都开放端口），可跳过

## 批量异常

**症状**：大量 IP 查询失败，日志中出现大量错误

**处理步骤**：

1. 查看日志确认错误类型（见下方"查看日志"）
2. 根据错误类型对应处理（凭证失效 / 频率限制 / 网络问题）
3. 批量脚本支持断点续查，修复问题后直接重新运行即可
4. 可用 progress_tool.py 管理进度文件

## 查看日志

日志文件存储在 `data/logs/` 目录，按渠道分文件：

| 日志文件 | 对应渠道 |
|---------|---------|
| data/logs/fofa_host.log | Fofa Host 聚合 |
| data/logs/fofa_search.log | Fofa 搜索 |
| data/logs/ipinfo_api.log | IPInfo |
| data/logs/rdns_ptr.log | RDNS PTR |
| data/logs/whois.log | Whois |
| data/logs/aizhan.log | 爱站 |
| data/logs/chinaz.log | 站长之家 |
| data/logs/zoomeye.log | ZoomEye |
| data/logs/ssl_cert.log | SSL 证书 |

日志自动轮转：单文件最大 10MB，保留 3 份备份。日志级别为 DEBUG，包含详细的请求和响应信息。

查看日志命令：

```bash
Get-Content data/logs/aizhan.log -Tail 50
Get-Content data/logs/fofa_host.log -Tail 100
```

## 重新查询特定 IP

如果某些 IP 因异常导致数据不正确，可以：

1. 删除错误数据：`python writer.py delete-channel "<IP>" "<渠道名>"`
2. 删除进度记录：`python tools/progress_tool.py remove <progress_file> "<IP>"`
3. 重新查询：`python channel/<channel>.py "<IP>"` 或重新运行批量命令
