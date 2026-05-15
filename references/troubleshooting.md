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
  ├─ 报 "未安装" / "not found" / "ImportError" / "nmap 不可用" → 依赖缺失 → 见下方"依赖缺失"
  ├─ 报 "页面缺少关键部分" / "页面结构异常" → 页面结构变更 → 见下方"页面结构变更"
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

**各渠道凭证验证行为差异**：

| 渠道 | 验证方式 | 说明 |
|------|---------|------|
| Fofa | 在线校验 | 调用 `/api/v1/info/my` 验证 Key 有效性并返回用户名 |
| IPInfo（有 Token） | 在线校验 | 调用 `api.ipinfo.io/lite/8.8.8.8` 验证 Token |
| IPInfo（无 Token） | 连通性校验 | 调用 `ipinfo.io/8.8.8.8/json` 验证免费 API 可达 |
| 爱站 | 在线校验 | 访问 `member.aizhan.com` 检查 Cookie 是否被重定向 |
| 站长之家 | 格式+在线校验 | 检查 Cookie 必要字段 + 访问查询页验证 |
| ZoomEye | **仅本地检查** | 只检查 Key 是否已配置，**不进行在线校验**（避免消耗额度） |
| RDNS | 功能校验 | 测试 socket.gethostbyaddr 是否可用 |
| SSL 证书 | 无需校验 | 直连目标 IP 获取证书，无需凭证 |
| Whois | 依赖检查 | 检查 python-whois 库是否已安装 |
| port_scan | 依赖检查 | 检查 nmap 是否可用 |

**站长之家 Cookie 必要字段**：Cookie 中必须包含 `toolUserGrade` 和 `chinaz_zxuser` 字段，缺少任一字段会报错 `Cookie 缺少必要字段: xxx`，需重新获取完整 Cookie。

**ZoomEye Key 验证说明**：`validate_channel_key` 仅检查 Key 是否已配置（非空），不进行在线校验。即使验证通过，Key 可能已过期或无效，实际查询时才会暴露问题。

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

**RDNS / Whois / SSL 证书：**
```bash
python tools/config_tool.py set IP_RDNS_QUERY_TIMEOUT 5.0
python tools/config_tool.py set IP_WHOIS_QUERY_TIMEOUT 5.0
python tools/config_tool.py set IP_SSL_CERT_TIMEOUT 10
python tools/config_tool.py set IP_SSL_CERT_OPENSSL_TIMEOUT 15.0
```

**Fofa：**
```bash
python tools/config_tool.py set IP_FOFA_QUERY_TIMEOUT 60.0
python tools/config_tool.py set IP_FOFA_VALIDATE_TIMEOUT 30.0
```

**IPInfo：**
```bash
python tools/config_tool.py set IP_IPINFO_QUERY_TIMEOUT 60.0
python tools/config_tool.py set IP_IPINFO_VALIDATE_TIMEOUT 60.0
```

**爱站：**
```bash
python tools/config_tool.py set IP_AIZHAN_QUERY_TIMEOUT 30.0
python tools/config_tool.py set IP_AIZHAN_VALIDATE_TIMEOUT 20.0
```

**站长之家：**
```bash
python tools/config_tool.py set IP_CHINAZ_QUERY_TIMEOUT 30.0
python tools/config_tool.py set IP_CHINAZ_VALIDATE_TIMEOUT 20.0
```

**端口扫描（nmap）：**
```bash
python tools/config_tool.py set IP_TRACE_IP_PORT_SCAN_TIMEOUT 120
```

2. 检查网络连接是否正常
3. 部分超时可能是目标服务器问题，可跳过失败 IP 后续重查

## 目标不可达

**症状**：报 connection refused / 无法连接

**处理步骤**：

1. 确认目标 IP 是否存活（ping 或 curl 测试）
2. SSL 证书查询需要目标开放 443 端口，不开放则无法获取
3. 属于正常情况（不是所有 IP 都开放端口），可跳过

## 依赖缺失

**症状**：报 "未安装" / "not found" / "ImportError" / "nmap 不可用" 等

**各渠道依赖缺失场景及处理**：

| 渠道 | 依赖 | 错误表现 | 处理方式 |
|------|------|---------|---------|
| Whois | python-whois | `whois 库未安装，请运行: pip install python-whois` | `pip install python-whois` |
| 报告生成 | openpyxl | Excel 报告导出失败 | `pip install openpyxl` |
| 报告生成 | python-docx | Word 报告导出失败 | `pip install python-docx` |
| port_scan | nmap | `nmap 不可用（PATH 中未找到，配置路径: xxx）`，流水线阶段 5 跳过 | 安装 nmap 并配置路径 |

**nmap 未安装/不可用**：

port_scan 渠道依赖系统安装的 nmap。启动时会通过 `validate_engine()` 检测 nmap 是否可用：
1. 先尝试 PATH 中查找 `nmap`
2. 再尝试配置路径 `IP_TRACE_IP_PORT_SCAN_NMAP_PATH`
3. 均不可用时，单条查询直接报错退出，流水线阶段 5 自动跳过并记录 `status: nmap_unavailable`

处理方式：
```bash
# Windows：下载安装 nmap 并配置完整路径
python tools/config_tool.py set IP_TRACE_IP_PORT_SCAN_NMAP_PATH "C:\Tools\Nmap\nmap.exe"

# 或将 nmap 所在目录加入系统 PATH
```

**nmap 扫描超时**：

nmap 扫描通过 `subprocess.run` 执行，受 `IP_TRACE_IP_PORT_SCAN_TIMEOUT`（默认 90 秒）控制。超时后返回 `nmap timeout after {timeout}s`，该 IP 的端口扫描结果中会包含 `error` 字段。处理方式：

```bash
# 增大超时时间
python tools/config_tool.py set IP_TRACE_IP_PORT_SCAN_TIMEOUT 180
```

**python-whois 未安装**：

Whois 渠道在模块加载时尝试 `from whois import whois`，若失败则 `whois_query = None`。后续查询时返回 `whois 库未安装，请运行: pip install python-whois`。`validate_channel_key()` 也会直接报错退出。

处理方式：
```bash
pip install python-whois
```

## 页面结构变更

**症状**：爱站或站长之家返回 `页面缺少关键部分` 或 `页面结构异常: 未找到表格数据`

**爱站页面结构变更**：

爱站渠道解析页面时查找以下关键 DOM 元素：
- `div.dns-infos`：IP 归属地和运营商信息
- `div.dns-content`：反查域名表格

缺失时的错误信息：
- `页面缺少关键部分: dns-infos` — 归属地信息区域缺失
- `页面缺少关键部分: dns-content` — 域名数据区域缺失
- `页面缺少关键部分: dns-infos, dns-content` — 两个区域均缺失
- `页面结构异常: 未找到表格数据` — dns-content 存在但内部缺少 `tbody` 表格

**站长之家页面结构变更**：

站长之家渠道解析页面时查找以下关键 DOM 元素：
- `div.info[data-result="true"]`：IP 归属地和运营商信息
- `div#J_domain`：反查域名列表

缺失时的错误信息：
- `页面缺少关键部分: info section` — 归属地信息区域缺失
- `页面缺少关键部分: domain section` — 域名数据区域缺失

**处理步骤**：

1. 用浏览器手动访问对应页面，确认页面结构是否变更
2. 若页面结构确实变更，需更新渠道代码中的 DOM 选择器
3. 临时方案：跳过该渠道，使用其他渠道补充数据
4. Cookie 失效也可能导致返回异常页面，先排除凭证问题

## 渠道特有异常

### port_scan 渠道

| 异常场景 | 错误信息 | 处理方式 |
|---------|---------|---------|
| nmap 未安装/不可用 | `nmap not found: {path}` | 安装 nmap 并配置路径，见"依赖缺失" |
| nmap 扫描超时 | `nmap timeout after {timeout}s` | 增大 `IP_TRACE_IP_PORT_SCAN_TIMEOUT` |
| nmap 返回非零退出码 | 结果中包含 `nmap_returncode` 字段 | 检查 nmap 版本和权限 |
| XML 解析失败 | `open_ports` 为空，`host_alive` 为 False | 可能是 nmap 输出异常，查看日志 |
| 端口列表文件不存在 | 流水线阶段 5 跳过，`status: port_list_empty` | 检查 `config/port_scan/top1000.txt` 是否存在 |

### whois 渠道

| 异常场景 | 错误信息 | 处理方式 |
|---------|---------|---------|
| python-whois 未安装 | `whois 库未安装，请运行: pip install python-whois` | `pip install python-whois` |
| 未找到 Whois 信息 | `未找到 Whois 信息` | 正常情况，部分 IP 无 Whois 记录 |
| 查询超时 | `查询超时（超过 {timeout} 秒）` | 增大 `IP_WHOIS_QUERY_TIMEOUT` |

### ssl_cert 渠道

| 异常场景 | 错误信息 | 处理方式 |
|---------|---------|---------|
| SSL 错误 | `ssl_error: {具体错误}` | 目标 SSL 配置异常，可跳过 |
| 目标无 SSL 证书 | `no_cert` | 目标未开放 443 端口或无证书，属正常情况 |
| 连接超时 | `connection_timeout` | 增大 `IP_SSL_CERT_TIMEOUT` |
| 连接被拒绝 | `connection_refused` | 目标未开放 443 端口，属正常情况 |
| OpenSSL 不可用 | 自动降级返回 PEM 文本 | 安装 OpenSSL 可获得更详细的证书解析结果 |

**SSL 证书 OpenSSL 降级机制**：

ssl_cert 渠道获取证书后，优先使用 `openssl x509 -text` 解析为可读文本（提取 CN、SAN、有效期等）。若系统未安装 OpenSSL（`FileNotFoundError`）或 openssl 命令执行失败，会自动降级返回原始 PEM 文本。降级后：
- 证书域名提取（`_parse_domains`）仍可工作，但依赖正则匹配 PEM 文本而非结构化输出
- 证书详情（颁发者、有效期等）可能不完整
- 日志中会记录 `openssl 命令不可用，尝试直接解析 PEM` 或 `openssl 解析证书失败: {error}`

建议在 Windows 上安装 OpenSSL 以获得最佳解析效果。

### ipinfo_api 渠道

**免费 API 降级模式**：

IPInfo 渠道有两种运行模式：
- **API 模式**（默认）：配置了 `IP_IPINFO_ACCESS_TOKEN` 时使用，调用 `api.ipinfo.io/lite/{ip}`，返回 ASN 等详细信息，渠道名为 `ipinfo_api`
- **免费 API 模式**（降级）：未配置 Token 时自动降级，调用 `ipinfo.io/{ip}/json`，返回基础地理信息，渠道名从 `ipinfo_api` 变为 `ipinfo`

降级触发条件：`validate_channel_key()` 检测到 Token 为空时自动切换。批量查询时使用 `--no-api` 参数可手动指定降级模式。

降级模式差异：
- 返回字段较少（无 ASN 详细信息）
- 有更严格的频率限制
- 渠道名不同，数据存储键名不同

### 爱站渠道

| 异常场景 | 错误信息 | 处理方式 |
|---------|---------|---------|
| Cookie 未配置 | `AIZHAN_COOKIE 未配置` | 配置 Cookie |
| Cookie 失效（重定向） | `Cookie 已失效（被重定向到登录页）` | 重新获取 Cookie |
| 页面缺少关键部分 | `页面缺少关键部分: dns-infos, dns-content` | 见"页面结构变更" |
| 页面结构异常 | `页面结构异常: 未找到表格数据` | 见"页面结构变更" |
| 禁止请求 | `爱站网禁止请求` | 降低查询频率 |

### 站长之家渠道

| 异常场景 | 错误信息 | 处理方式 |
|---------|---------|---------|
| Cookie 未配置 | `CHINAZ_COOKIE 未配置` | 配置 Cookie |
| Cookie 缺少必要字段 | `Cookie 缺少必要字段: toolUserGrade, chinaz_zxuser` | 重新获取完整 Cookie |
| Cookie 可能无效 | `站长之家查询页面结构异常，Cookie 可能无效` | 检查 Cookie 是否过期 |
| 页面缺少关键部分 | `页面缺少关键部分: info section, domain section` | 见"页面结构变更" |
| 禁止请求 | `站长之家禁止请求` | 降低查询频率 |

## 批量异常

**症状**：大量 IP 查询失败，日志中出现大量错误

**处理步骤**：

1. 查看日志确认错误类型（见下方"查看日志"）
2. 根据错误类型对应处理（凭证失效 / 频率限制 / 网络问题 / 依赖缺失）
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
| data/logs/port_scan.log | 端口扫描 |

日志自动轮转：单文件最大 10MB，保留 3 份备份。日志级别为 DEBUG，包含详细的请求和响应信息。

查看日志命令：

```bash
Get-Content data/logs/aizhan.log -Tail 50
Get-Content data/logs/fofa_host.log -Tail 100
Get-Content data/logs/port_scan.log -Tail 50
```

## 重新查询特定 IP

如果某些 IP 因异常导致数据不正确，可以：

1. 删除错误数据：`python writer.py delete-channel "<IP>" "<渠道名>"`
2. 删除进度记录：`python tools/progress_tool.py remove <progress_file> "<IP>"`
3. 重新查询：`python channel/<channel>.py "<IP>"` 或重新运行批量命令
