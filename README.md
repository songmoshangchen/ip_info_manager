# IP Info Manager

批量采集、存储、查询和导出 IP 地址多维度情报信息的命令行工具。

## 特性

- **10 个数据渠道**：Fofa（Host聚合/搜索）、IPInfo（API/免API）、RDNS PTR、Whois、爱站、站长之家、ZoomEye、SSL 证书、端口扫描（nmap）
- **两条自动化流水线**：溯源IP处理（7阶段）、IP域名反查（4阶段）
- **IP 威胁标签打标**：35 个情报源本地匹配，支持分级（快速/正常/全量）
- **Word + Excel 报告**：溯源优先级决策树分级（P1-P4）、DNS 域名验证、AI 研判
- **断点续查**：批量查询和流水线均支持进度保存，中断后可继续
- **任务状态监控**：实时查看运行状态、进度和 ETA
- **并发查询**：多渠道并行采集，RDNS 多线程批量查询

## 快速开始

```bash
git clone https://github.com/songmoshangchen/ip_info_manager.git
cd ip_info_manager
pip install -r requirements.txt
cp .env.example .env
python tools/config_tool.py set IP_FOFA_API_KEY "你的Key"
python channel/rdns_ptr.py 8.8.8.8
```

详细的初始化步骤（可选依赖、API 凭证获取、安装验证等）请参阅 [references/setup.md](references/setup.md)。

## 架构概览

```
ip_info_manager/
├── config.py                 # 配置管理（Pydantic Settings）
├── writer.py / reader.py / exporter.py   # 数据读写与导出
├── channel/                  # 10 个数据采集渠道
├── scripts/                  # 10 个批量查询脚本
├── scenarios/
│   ├── trace_ip/             # 溯源IP流水线（7 阶段）
│   └── ip_domain_lookup/     # IP域名反查流水线（4 阶段）
├── tools/                    # 辅助工具集
├── utils/                    # 通用工具模块
├── config/                   # 静态配置（IP标签源、端口列表）
├── data/                     # 数据存储根目录
└── references/               # 操作手册（AI Agent 参考文档）
```

**数据存储路径：**

| 数据类型 | 路径 |
|---------|------|
| channel/batch 通用数据 | `data/{IP_STORAGE_DIR}/{IP_STORAGE_NAME}.json` |
| 溯源IP场景数据 | `data/trace_ip/{IP_TRACE_IP_PROJECT_NAME}/` |
| IP域名反查数据 | `data/ip_domain_lookup/{IP_IP_DOMAIN_LOOKUP_PROJECT_NAME}/` |

## 环境配置

> 完整配置指南请参阅 [references/setup.md](references/setup.md) 和 [references/config.md](references/config.md)。
> **所有配置变更必须通过 `tools/config_tool.py` 执行，不要直接编辑 `.env` 文件。**

### 依赖安装

```bash
pip install -r requirements.txt                    # 核心依赖
pip install openpyxl python-docx python-whois      # 可选依赖（报告生成、Whois）
```

### API 凭证

| 渠道 | 环境变量 | 必填 | 获取方式 |
|------|---------|------|---------|
| Fofa | `IP_FOFA_API_KEY` | 使用时必填 | [fofa.info](https://fofa.info) → 个人中心 |
| IPInfo | `IP_IPINFO_ACCESS_TOKEN` | API 模式时必填 | [ipinfo.io](https://ipinfo.io) → Token 管理 |
| 爱站 | `IP_AIZHAN_COOKIE` | 使用时必填 | 浏览器登录 [dns.aizhan.com](https://dns.aizhan.com) → F12 复制 Cookie |
| 站长之家 | `IP_CHINAZ_COOKIE` | 否 | 有 Cookie 可查更多信息 |
| ZoomEye | `IP_ZOOMEYE_API_KEY` | 使用时必填 | [zoomeye.org](https://zoomeye.org) → 个人中心 |

无需凭证的渠道：RDNS PTR（DNS 本地查询）、SSL 证书（直连提取）、IPInfo 免 API 模式。

```bash
python tools/config_tool.py set IP_FOFA_API_KEY "你的Key"
python tools/config_tool.py set IP_IPINFO_ACCESS_TOKEN "你的Token"
python tools/config_tool.py status    # 查看配置状态
python tools/config_tool.py check     # 检查配置完整性
```

## 核心模块

### 数据读写

```bash
python writer.py add "1.2.3.4" "analysis" severity="高" action="保留" note="测试"
python writer.py delete-ip "1.2.3.4"
python writer.py delete-channel "1.2.3.4" "analysis"

python reader.py get "1.2.3.4"
python reader.py list --detail --export-excel output.xlsx
python reader.py search fofa_host --key country_name --value "China"
```

值类型自动推断：`true/false` → 布尔，纯数字 → 整数，含小数点 → 浮点，其余 → 字符串。

详细操作请参阅 [references/data-management.md](references/data-management.md)。

### 单条渠道查询

```bash
python channel/fofa_host.py "1.2.3.4"       # Fofa Host 聚合
python channel/fofa_search.py "1.2.3.4"     # Fofa 搜索
python channel/ipinfo_api.py "1.2.3.4"      # IPInfo（自动选择 API/免API 模式）
python channel/rdns_ptr.py "1.2.3.4"        # RDNS 反向解析（无需凭证）
python channel/whois_query.py "1.2.3.4"     # Whois 查询
python channel/aizhan.py "1.2.3.4"          # 爱站 IP 反查域名
python channel/chinaz.py "1.2.3.4"          # 站长之家 IP 反查域名
python channel/zoomeye.py "1.2.3.4"         # ZoomEye 网络空间测绘
python channel/ssl_cert.py "1.2.3.4"        # SSL 证书域名提取（无需凭证）
```

查询结果自动写入数据库。各渠道返回数据说明请参阅 [references/channel-query.md](references/channel-query.md)。

### 批量查询

```bash
python scripts/batch_fofa_host.py ips.txt                       # Fofa Host 聚合
python scripts/batch_ipinfo_api.py ips.txt --no-api             # IPInfo 免 API 模式
python scripts/batch_rdns_ptr_concurrent.py ips.txt --workers 20  # RDNS 多线程
python scripts/batch_aizhan.py ips.txt                          # 爱站
```

所有批量脚本支持断点续查（自动生成 `.progress` 文件），通用参数：`ip_file`（必填）、`--no-validate`（跳过凭证校验）。

详细用法请参阅 [references/batch-query.md](references/batch-query.md)。

## 场景流水线

### 溯源IP处理流水线

自动完成：基础采集 → IP标签打标 → 自动分类 → 深度查询 → DNS域名验证 → 端口扫描 → Word+Excel 报告。

```bash
python -m scenarios.trace_ip ips.txt                       # 默认执行 Phase 1-5（采集→标签→分类→深度查询→DNS验证→端口扫描）
python -m scenarios.trace_ip ips.txt --collect-only         # 只执行基础采集
python -m scenarios.trace_ip ips.txt --summary-only         # Phase 6：只执行汇总
python -m scenarios.trace_ip ips.txt --generate-report      # Phase 7：只生成报告
python -m scenarios.trace_ip ips.txt --from-phase 3         # 从阶段3开始
python -m scenarios.trace_ip ips.txt --port-scan-only       # 只执行端口扫描
python -m scenarios.trace_ip ips.txt --exclude-ips traced.txt --generate-report
python -m scenarios.trace_ip ips.txt --no-tagger            # 跳过 IP 标签打标
python -m scenarios.trace_ip ips.txt --tagger-level 1       # 快速标签（21源）
python -m scenarios.trace_ip ips.txt --channel-timeout 30   # 单渠道超时30秒
python -m scenarios.trace_ip ips.txt --port-scan-concurrency 5   # 临时设置端口扫描并发5
```

**流水线阶段：**

| 阶段 | 说明 | 输出 |
|------|------|------|
| Phase 1 | 基础情报采集（IPInfo + RDNS，并行） | 数据写入 JSON |
| Phase 2 | IP标签打标 + 自动分类过滤 | `trace_classify` + `.trace_filtered_ips` |
| Phase 3 | 深度查询（爱站+站长+Fofa Host，并行） | 数据写入 JSON |
| Phase 4 | DNS 域名正向验证 | `domain_verify` 字段 |
| Phase 5 | 端口扫描（nmap，默认关闭） | `port_scan` 渠道 |
| Phase 6 | 汇总报告 | `.trace_report` |
| Phase 7 | Word + Excel 报告（P1-P4 分级） | `.docx` + `.xlsx` |

默认执行 Phase 1-5。Phase 6（汇总）和 Phase 7（报告）需通过 `--summary-only` / `--generate-report` 单独触发。

**分类类别：**

| 类别 | 说明 | 是否深度查询 |
|------|------|-------------|
| `cloud_provider` | 云服务商（AWS/阿里云/腾讯云等） | ✅ |
| `cdn` | CDN/WAF 节点 | ❌ |
| `crawler_scanner` | 爬虫/扫描器 | ❌ |
| `residential` | 家用宽带 | ✅ |
| `other` | 未识别（需人工确认） | ✅ |
| `invalid_rdns` | 无效RDNS（纯IP格式主机名，regex 匹配） | ❌ |
| `excluded_domain` | 排除域名 | ❌ |

**溯源优先级决策树：**

| 级别 | 判定条件 | 溯源路径建议 |
|------|---------|------------|
| P1 核心溯源 | 有反查域名 + 国内IP | ICP备案查询域名持有者实名信息 |
| P2 重点溯源 | 有反查域名（国外），或无域名但有端口（国内） | WHOIS查询；排查端口服务泄露信息 |
| P3 辅助溯源 | 无域名但有端口（国外），或仅国内IP | 端口服务辅助分析；公开信息检索 |
| P4 暂缓 | 无域名、无端口、国外IP | 信息不足，建议持续监控 |

完整参数和用法请参阅 [references/trace-ip-pipeline.md](references/trace-ip-pipeline.md)。

#### Phase 5 端口扫描（可选增强）

端口扫描使用 **nmap**，**默认关闭**，需显式启用：

```bash
python tools/config_tool.py set IP_TRACE_IP_PHASE5_PORT_SCAN_ENABLED true
python tools/config_tool.py set IP_TRACE_IP_PORT_SCAN_NMAP_PATH "C:\Tools\Nmap\nmap.exe"
python tools/config_tool.py set IP_TRACE_IP_PORT_SCAN_CONCURRENCY 1
```

- 逐 IP 写入：每完成一个 IP 立即保存数据和进度，中断仅损失当前正在扫描的 IP
- 支持并发：通过 `IP_TRACE_IP_PORT_SCAN_CONCURRENCY` 控制并发数（默认 1=串行）
- 扫描范围：历史端口验证 + Top 1000 端口
- 需预先安装 [nmap](https://nmap.org/download.html)

### IP域名反查流水线

批量收集域名并进行 DNS 正向验证：域名收集 → DNS验证 → 汇总报告 → Word 报告。

```bash
python -m scenarios.ip_domain_lookup ips.txt                       # 完整流水线
python -m scenarios.ip_domain_lookup ips.txt --only-phase 1         # 只执行域名收集
python -m scenarios.ip_domain_lookup ips.txt --generate-report      # 只生成报告
```

| 阶段 | 说明 | 使用渠道 |
|------|------|---------|
| Phase 1 | 域名收集 | RDNS + 爱站 + 站长 + ZoomEye + Fofa Search + SSL（并行） |
| Phase 2 | DNS 正向验证 | 验证域名是否仍解析到原 IP |
| Phase 3 | 汇总报告 | `.domain_lookup_report` + `.domain_lookup_matched` |
| Phase 4 | Word 报告 | `.domain_lookup_report.docx` |

完整参数请参阅 [references/ip-domain-lookup-pipeline.md](references/ip-domain-lookup-pipeline.md)。

## 辅助工具

| 工具 | 用途 | 详细文档 |
|------|------|---------|
| `tools/config_tool.py` | 环境变量管理（增删改查、状态检查） | [references/config.md](references/config.md) |
| `tools/merge_ip_files.py` | IP 文件合并/去重/验证 | [references/tools.md](references/tools.md) |
| `tools/progress_tool.py` | 批量查询进度文件管理 | [references/tools.md](references/tools.md) |
| `tools/status_tool.py` | 任务状态查询（运行状态/进度/ETA） | [references/tools.md](references/tools.md) |
| `tools/verify_ip_domain.py` | IP-域名映射验证 | [references/tools.md](references/tools.md) |
| `tools/ai_analysis.py` | AI 研判辅助（筛选待研判 IP） | [references/tools.md](references/tools.md) |
| `tools/ip_tagger.py` | IP 威胁标签打标（35 个情报源） | [references/ip-tagger.md](references/ip-tagger.md) |
| `tools/ip_tagger_updater.py` | 标签源自动更新（从 FireHOL 下载） | [references/ip-tagger.md](references/ip-tagger.md) |
| `tools/docx_builder.py` | Word 报告生成公共引擎 | — |

### 任务状态查询

```bash
python tools/status_tool.py trace_ip              # 溯源流水线
python tools/status_tool.py ip_domain_lookup      # 域名反查
python tools/status_tool.py batch                 # 批量查询
python tools/status_tool.py cleanup trace_ip      # 清理残留 PID
```

| 状态 | 含义 |
|------|------|
| 🟢 运行中 | 任务正在执行，心跳正常 |
| ⏳ 疑似卡死 | 进程存在但心跳超过 120 秒未更新 |
| ⚠️ 异常终止 | PID 文件存在但进程已不存在，可断点续跑 |
| ⬜ 未运行 | 任务未启动或已完成 |

### IP 标签打标

基于本地威胁情报文件批量匹配 IP 标签，纯本地计算，无网络请求。

```bash
python tools/ip_tagger.py data/ips.txt                    # 累加模式（默认）
python tools/ip_tagger.py data/ips.txt --level 1          # 快速模式（21 源）
python tools/ip_tagger.py data/ips.txt --mode overwrite   # 覆盖模式
python tools/ip_tagger_updater.py --from-git              # 更新标签源
```

详细用法请参阅 [references/ip-tagger.md](references/ip-tagger.md)。

## 数据格式

所有 IP 数据以 JSON 格式统一存储，按 IP + 渠道组织：

```json
{
  "1.2.3.4": {
    "ip": "1.2.3.4",
    "fofa_host": { "country_name": "China", "org": "China Telecom", "query_time": "..." },
    "ipinfo_api": { "country": "CN", "as_name": "China Telecom", "query_time": "..." },
    "rdns_ptr": { "has_ptr": true, "hostname": "example.com", "query_time": "..." },
    "tags": ["银狐", "SSH暴力破解"]
  }
}
```

每个 IP 下包含 `ip` 字段和若干渠道数据，渠道名作为 key。

## 配置参考

所有配置项由 `config.py` 统一管理，以 `IP_` 为前缀，从 `.env` 文件读取。

### 查询间隔与超时

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `IP_FOFA_QUERY_DELAY` | `2.0` | Fofa 查询间隔（秒） |
| `IP_IPINFO_QUERY_DELAY` | `1.2` | IPInfo 查询间隔（秒） |
| `IP_RDNS_QUERY_DELAY` | `0.1` | RDNS 批量查询间隔（秒） |
| `IP_RDNS_QUERY_TIMEOUT` | `1.5` | RDNS 查询超时（秒） |
| `IP_WHOIS_QUERY_DELAY` | `0.5` | Whois 查询间隔（秒） |
| `IP_AIZHAN_QUERY_DELAY` | `2.0` | 爱站查询间隔（秒） |
| `IP_CHINAZ_QUERY_DELAY` | `2.0` | 站长之家查询间隔（秒） |
| `IP_ZOOMEYE_QUERY_DELAY` | `2.0` | ZoomEye 查询间隔（秒） |
| `IP_SSL_CERT_QUERY_DELAY` | `0.5` | SSL 证书查询间隔（秒） |

### 流水线渠道开关

**溯源IP流水线：**

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `IP_TRACE_IP_PHASE1_IPINFO_ENABLED` | `true` | Phase 1：IPInfo |
| `IP_TRACE_IP_PHASE1_RDNS_PTR_ENABLED` | `true` | Phase 1：RDNS |
| `IP_TRACE_IP_PHASE3_AIZHAN_ENABLED` | `true` | Phase 3：爱站 |
| `IP_TRACE_IP_PHASE3_CHINAZ_ENABLED` | `true` | Phase 3：站长之家 |
| `IP_TRACE_IP_PHASE3_FOFA_HOST_ENABLED` | `true` | Phase 3：Fofa Host |
| `IP_TRACE_IP_PHASE4_DNS_VERIFY_ENABLED` | `true` | Phase 4：DNS 域名验证 |
| `IP_TRACE_IP_DNS_VERIFY_TIMEOUT` | `3.0` | DNS 验证超时（秒） |
| `IP_TRACE_IP_DNS_VERIFY_CONCURRENCY` | `10` | DNS 验证并发线程数 |
| `IP_TRACE_IP_PHASE5_PORT_SCAN_ENABLED` | `false` | Phase 5：端口扫描（默认关闭） |
| `IP_TRACE_IP_PORT_SCAN_NMAP_PATH` | `nmap` | nmap 可执行文件路径 |
| `IP_TRACE_IP_PORT_SCAN_TIMEOUT` | `90` | 单 IP 扫描超时（秒） |
| `IP_TRACE_IP_PORT_SCAN_CONCURRENCY` | `1` | 端口扫描并发数 |
| `IP_TRACE_IP_PORT_SCAN_PORT_LIST` | `config/port_scan/top1000.txt` | 端口列表文件路径 |

**IP域名反查流水线：**

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `IP_IP_DOMAIN_LOOKUP_RDNS_PTR_ENABLED` | `true` | RDNS PTR 反向解析 |
| `IP_IP_DOMAIN_LOOKUP_AIZHAN_ENABLED` | `true` | 爱站 IP 反查域名 |
| `IP_IP_DOMAIN_LOOKUP_CHINAZ_ENABLED` | `true` | 站长之家 IP 反查域名 |
| `IP_IP_DOMAIN_LOOKUP_ZOOMEYE_ENABLED` | `true` | ZoomEye 网络空间测绘 |
| `IP_IP_DOMAIN_LOOKUP_FOFA_SEARCH_ENABLED` | `true` | Fofa 搜索查询 |
| `IP_IP_DOMAIN_LOOKUP_SSL_CERT_ENABLED` | `true` | SSL 证书域名提取 |

完整配置参考请参阅 [references/config.md](references/config.md)。

## 日志系统

- 渠道日志：`data/logs/{channel_name}.log`
- 自动轮转：单文件最大 10MB，保留 3 份备份
- 日志级别：DEBUG（包含详细请求和响应信息）

## 故障排除

遇到凭证失效、限频报错、网络超时等问题，请参阅 [references/troubleshooting.md](references/troubleshooting.md)。

```bash
python tools/config_tool.py check                     # 检查配置完整性
Get-Content data/logs/aizhan.log -Tail 50             # 查看最近日志
python tools/status_tool.py cleanup trace_ip          # 清理残留 PID
```

## 文档索引

| 文档 | 说明 |
|------|------|
| [references/setup.md](references/setup.md) | 初始化与快速上手 |
| [references/channel-query.md](references/channel-query.md) | 单条渠道查询 |
| [references/batch-query.md](references/batch-query.md) | 批量查询 |
| [references/data-management.md](references/data-management.md) | 数据读写操作 |
| [references/trace-ip-pipeline.md](references/trace-ip-pipeline.md) | 溯源IP处理流水线 |
| [references/ip-domain-lookup-pipeline.md](references/ip-domain-lookup-pipeline.md) | IP域名反查流水线 |
| [references/tools.md](references/tools.md) | 辅助工具 |
| [references/config.md](references/config.md) | 凭证管理与环境配置 |
| [references/ip-tagger.md](references/ip-tagger.md) | IP 标签打标 |
| [references/troubleshooting.md](references/troubleshooting.md) | 异常处理与故障排除 |
