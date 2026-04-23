---
name: ip-info-manager
description: IP 信息管理工具，用于批量采集、存储、查询和导出 IP 地址的多维度情报信息。当用户需要查询 IP 信息、批量处理 IP 列表、导出 IP 数据到 Excel、对 IP 进行情报分析（Fofa/IPInfo/RDNS/Whois/爱站/站长之家/ZoomEye/SSL证书）、管理 IP 数据库、溯源IP处理、IP自动分类、攻击IP分析、IP域名反查、域名DNS验证时使用此 skill。即使用户只是提到 "IP 查询"、"IP 信息"、"攻击 IP"、"威胁情报"、"IP 归属"、"IP 反查"、"批量查 IP"、"IP 导出"、"IP 反查域名"、"域名绑定"、"溯源"、"IP 分类"、"云主机识别"、"扫描器识别" 等关键词，也应触发此 skill。
---

# IP Info Manager — IP 信息管理 Skill

本 skill 封装了一套完整的 IP 信息管理工作流，帮助 AI 助手高效地完成 IP 情报采集、数据管理和导出任务。

## 核心能力

1. **单条/批量写入 IP 数据** — 通过 `writer.py` 添加、更新、删除 IP 及其渠道数据
2. **多维度查询 IP 数据** — 通过 `reader.py` 按 IP、渠道、字段等条件检索
3. **多渠道情报采集** — Fofa（Host聚合/搜索）、IPInfo（API/免 API）、RDNS PTR、Whois、爱站（域名反查）、站长之家（域名反查）、ZoomEye、SSL 证书
4. **Excel 导出** — 通过 `exporter.py` 将查询结果导出为格式化的 Excel 文件
5. **IP 列表处理** — 验证、去重、合并 IP 文件
6. **溯源IP处理流水线** — 通过 `scenarios/trace_ip/` 自动采集、分类、深度查询，支持规则自定义和断点续跑
7. **IP域名反查流水线** — 通过 `scenarios/ip_domain_lookup/` 域名收集、DNS正向验证、汇总报告
8. **日志系统** — 通过 `scripts/logger_utils.py` 统一的 channel 和 batch 日志，支持控制台+文件双输出，自动轮转

## 项目结构

```
ip_info_manager/
├── .env                        # API Key 等环境变量
├── .env.example                # 环境变量模板
├── config.py                   # 集中配置管理（Pydantic Settings）
├── writer.py                   # IP 数据写入器
├── reader.py                   # IP 数据读取器（含 Excel 导出入口）
├── exporter.py                 # Excel 导出引擎
├── channel/                    # 数据采集渠道
│   ├── _template.py            # 渠道模板（规范参考）
│   ├── fofa_host.py            # Fofa Host 聚合查询（需 IP_FOFA_API_KEY）
│   ├── fofa_search.py          # Fofa 搜索查询（需 IP_FOFA_API_KEY）
│   ├── ipinfo_api.py           # IPInfo 查询（API模式+免API模式合并）
│   ├── rdns_ptr.py             # RDNS PTR 反向解析
│   ├── whois_query.py          # Whois 查询（需 python-whois）
│   ├── aizhan.py               # 爱站网 IP 反查域名（需 IP_AIZHAN_COOKIE）
│   ├── chinaz.py               # 站长之家 IP 反查域名（需 IP_CHINAZ_COOKIE）
│   ├── zoomeye.py              # ZoomEye 网络空间测绘（需 IP_ZOOMEYE_API_KEY）
│   └── ssl_cert.py             # SSL 证书域名提取（无需 API Key）
├── scripts/                    # 批量查询脚本
│   ├── logger_utils.py         # 日志工具（get_batch_logger / get_channel_logger）
│   ├── batch_fofa_host.py      # 批量 Fofa Host 聚合查询
│   ├── batch_fofa_search.py    # 批量 Fofa 搜索查询
│   ├── batch_ipinfo_api.py     # 批量 IPInfo 查询（支持 --no-api）
│   ├── batch_rdns_ptr.py       # 批量 RDNS（单线程）
│   ├── batch_rdns_ptr_concurrent.py  # 批量 RDNS（多线程，--workers）
│   ├── batch_whois.py          # 批量 Whois 查询
│   ├── batch_aizhan.py         # 批量爱站网查询
│   ├── batch_chinaz.py         # 批量站长之家查询
│   ├── batch_zoomeye.py        # 批量 ZoomEye 查询
│   └── batch_ssl_cert.py       # 批量 SSL 证书域名提取
├── scenarios/                  # 场景工作流
│   ├── trace_ip/               # 溯源IP处理流水线
│   │   ├── trace_ip.py         # 入口脚本
│   │   ├── pipeline.py         # 流水线核心逻辑
│   │   ├── classifier.py       # IP分类器
│   │   ├── progress.py         # 进度管理 + 批量写入
│   │   ├── reporter.py         # 报告生成
│   │   └── classifiers/        # 分类规则
│   │       ├── builtin_rules.json  # 内置分类规则（稳定）
│   │       └── custom_rules.json   # 外部分类规则（试运行/离散）
│   └── ip_domain_lookup/       # IP域名反查流水线
│       ├── ip_domain_lookup.py # 入口脚本
│       ├── pipeline.py         # 流水线核心逻辑
│       ├── dns_validator.py    # DNS正向验证
│       ├── progress.py         # 进度管理 + 批量写入
│       └── reporter.py         # 报告生成
├── tools/                      # 辅助工具
│   ├── merge_ip_files.py       # IP 文件合并/去重/验证
│   ├── config_tool.py          # .env 配置管理工具
│   ├── progress_tool.py        # .progress 进度文件管理工具
│   └── verify_ip_domain.py     # IP-域名映射验证
├── utils/                      # 通用工具
│   ├── file_utils.py           # 文件工具
│   └── ip_utils.py             # IP 工具
└── data/                       # 数据存储根目录
    ├── {storage_dir}/          # channel/batch 通用数据（由 IP_STORAGE_DIR 决定）
    │   ├── {storage_name}.json # 主数据文件（由 IP_STORAGE_NAME 命名）
    │   └── logs/               # 日志目录（自动创建，按渠道分文件）
    │       ├── fofa_host.log
    │       ├── fofa_search.log
    │       ├── ipinfo_api.log
    │       ├── rdns_ptr.log
    │       ├── whois.log
    │       ├── aizhan.log
    │       ├── chinaz.log
    │       ├── zoomeye.log
    │       └── ssl_cert.log
    ├── ip_domain_lookup/       # IP域名反查场景数据
    │   └── {project_name}/     # 由 IP_IP_DOMAIN_LOOKUP_PROJECT_NAME 决定
    │       ├── {project_name}.json
    │       ├── {project_name}.domain_lookup_report
    │       └── {project_name}.domain_lookup_matched
    └── trace_ip/               # 溯源IP场景数据
        └── {project_name}/     # 由 IP_TRACE_IP_PROJECT_NAME 决定
            ├── {project_name}.json
            ├── {project_name}.trace_report
            ├── {project_name}.trace_filtered_ips
            ├── {project_name}.unclassified_rdns
            └── {project_name}.unclassified_no_info
```

## 渠道模块规范

每个 channel 文件遵循统一模板结构，提供以下标准函数：

| 函数 | 说明 |
|------|------|
| `validate_channel_key()` | 校验渠道凭证（Key/Token/Cookie）是否有效 |
| `request_channel(ip, ...)` | 执行实际查询请求 |
| `parse_response(raw, ip)` | 解析查询结果（部分渠道省略） |
| `fetch_channel(ip, ...)` | 完整查询流程（delay → request → parse → format） |
| `apply_delay(delay)` | 查询前等待 |
| `format_output(data)` | 补充 query_time 等元数据 |
| `main(ip)` | 单条查询入口，自动写入数据库 |

**各渠道差异：**

| 渠道 | 凭证类型 | validate 方式 | parse_response | delay 默认值 |
|------|---------|--------------|----------------|-------------|
| fofa_host | key | key 非空 + 调用 `/api/v1/info/my` | 省略，直接返回 JSON | 2 |
| fofa_search | key | key 非空 + 调用 `/api/v1/info/my` | 省略，直接返回 JSON | 2 |
| zoomeye | key | 仅检查 key 非空（不在线校验） | 省略，直接返回 JSON | 1 |
| ssl_cert | 无 | 无需校验 | openssl 解析证书文本 | 0.5 |
| ipinfo_api | token（可选） | token 时验证 API，否则验证免费 API | 省略，直接返回 JSON | 2 |
| rdns_ptr | 无 | 测试 socket.gethostbyaddr 功能 | 省略，直接返回结果 | 0 |
| whois_query | 无 | 检查 whois 库安装 + 测试查询 | ✅ 解析字段 | 0 |
| aizhan | cookie | cookie 非空 + 访问用户页验证 | ✅ BeautifulSoup 解析 | 2 |
| chinaz | cookie（可选） | cookie 字段检查 + 访问查询页验证 | ✅ BeautifulSoup 解析 | 2 |

**ipinfo_api 双模式**：合并了原 ipinfo_noapi.py，通过 `use_api` 参数分流：
- API 模式（`use_api=True`）：`https://api.ipinfo.io/lite/{ip}` + Bearer Token
- 免 API 模式（`use_api=False`）：`https://ipinfo.io/{ip}/json`，无需 Token

## 批量查询脚本规范

所有批量脚本遵循统一结构，支持以下通用参数：

| 参数 | 说明 |
|------|------|
| `ip_file` | IP 文件路径（每行一个 IP） |
| `--no-validate` | 跳过渠道凭证校验 |

**各脚本独有参数：**

| 脚本 | 独有参数 | 说明 |
|------|---------|------|
| `batch_ipinfo_api.py` | `--no-api` | 使用免 API 模式查询 |
| `batch_rdns_ptr_concurrent.py` | `--workers N` | 并发线程数（默认 5） |

**进度文件**：统一存储在 `{storage_file}.{channel_name}.progress`，与数据文件同目录。

**日志输出**：每个批量脚本自动生成 `data/logs/{channel_name}.log`，支持 DEBUG 级别日志，文件自动轮转（10MB × 3 份）。

## 数据存储格式

所有 IP 数据存储在 `data/{storage_dir}/{storage_name}.json`（channel/batch 通用）或 `data/{场景名}/{project_name}/{project_name}.json`（场景专用），每个 IP 下包含 `ip` 字段和若干渠道数据：

```json
{
  "1.2.3.4": {
    "ip": "1.2.3.4",
    "fofa_host": { "country_name": "...", "org": "...", "query_time": "..." },
    "ipinfo_api": { "country": "...", "as_name": "...", "query_time": "..." },
    "rdns_ptr": { "has_ptr": true, "hostname": "...", "query_time": "..." },
    "whois": { "has_whois": true, "whois_data": { ... }, "query_time": "..." },
    "aizhan": {
      "success": true,
      "location": "中国广东广州",
      "isp": "电信",
      "domain_count": 5,
      "domains": [{"domain": "example.com", "title": "示例网站"}],
      "query_time": "..."
    },
    "chinaz": {
      "success": true,
      "location": "广东省广州市",
      "isp": "电信",
      "domains": [{"domain": "example.com", "start_time": "2024-01-01", "end_time": "2026-01-01"}],
      "query_time": "..."
    }
  }
}
```

## 操作指南

### 一、写入 IP 数据

使用 `writer.py` 添加、更新或删除 IP 数据。所有命令在项目根目录执行。

**添加/更新 IP 渠道数据：**

```bash
python writer.py add "<IP>" "<渠道名>" <key1>=<value1> <key2>=<value2> ...
```

值类型会自动推断：`true/false` → 布尔，纯数字 → 整数，含小数点 → 浮点，其余 → 字符串。

**示例 — 添加自定义渠道数据：**

```bash
python writer.py add "192.168.1.1" "analysis" severity="高" action="保留" note="疑似攻击者VPS"
```

**删除整个 IP 或某个渠道：**

```bash
python writer.py delete-ip "192.168.1.1"
python writer.py delete-channel "192.168.1.1" "analysis"
```

### 二、查询 IP 数据

使用 `reader.py` 查询已存储的 IP 数据。

**获取 IP 全部数据：**

```bash
python reader.py get "1.2.3.4"
```

**获取 IP 指定渠道数据：**

```bash
python reader.py get-channel "1.2.3.4" fofa_host
```

**列出所有 IP（支持分页和过滤）：**

```bash
python reader.py list                                    # 基础列表
python reader.py list --detail                           # 显示详细信息
python reader.py list --start 10 --end 50                # 分页
python reader.py list --include-channel fofa_host          # 仅含 fofa_host 渠道
python reader.py list --exclude-channel kimi              # 排除含 kimi 渠道
python reader.py list --detail --include-channel fofa_host --output result.txt  # 导出到文本文件
```

**导出为 Excel：**

```bash
python reader.py list --export-excel output.xlsx
python reader.py list --include-channel fofa_host ipinfo_api --export-excel output.xlsx
python reader.py list --exclude-channel kimi --export-excel output.xlsx
```

**搜索 IP：**

```bash
python reader.py search fofa_host                            # 含 fofa_host 渠道的所有 IP
python reader.py search fofa_host --key country_name --value "China"  # 按字段值搜索
```

### 三、单条渠道查询

各渠道脚本可单独运行查询单个 IP，结果自动写入数据库：

```bash
python channel/fofa_host.py "1.2.3.4"         # Fofa Host 聚合（需 API Key）
python channel/fofa_search.py "1.2.3.4"       # Fofa 搜索（需 API Key）
python channel/ipinfo_api.py "1.2.3.4"       # IPInfo（自动选择 API/免API 模式）
python channel/rdns_ptr.py "1.2.3.4"         # RDNS 反向解析
python channel/whois_query.py "1.2.3.4"      # Whois 查询
python channel/aizhan.py "1.2.3.4"           # 爱站网 IP 反查域名（需 Cookie）
python channel/chinaz.py "1.2.3.4"           # 站长之家 IP 反查域名（需 Cookie）
python channel/zoomeye.py "1.2.3.4"          # ZoomEye（需 API Key）
python channel/ssl_cert.py "1.2.3.4"         # SSL 证书域名提取（无需 Key）
```

### 四、批量查询

批量脚本从 IP 文件（每行一个 IP）读取并逐个查询，支持断点续查。

```bash
python scripts/batch_fofa_host.py ips.txt                    # 批量 Fofa Host 聚合
python scripts/batch_fofa_search.py ips.txt                  # 批量 Fofa 搜索
python scripts/batch_ipinfo_api.py ips.txt                   # 批量 IPInfo（API 模式）
python scripts/batch_ipinfo_api.py ips.txt --no-api          # 批量 IPInfo（免 API 模式）
python scripts/batch_rdns_ptr.py ips.txt                     # 批量 RDNS（单线程）
python scripts/batch_rdns_ptr_concurrent.py ips.txt --workers 20  # 批量 RDNS（20 线程）
python scripts/batch_whois.py ips.txt                        # 批量 Whois
python scripts/batch_aizhan.py ips.txt                       # 批量爱站网 IP 反查域名
python scripts/batch_chinaz.py ips.txt                       # 批量站长之家 IP 反查域名
python scripts/batch_zoomeye.py ips.txt                      # 批量 ZoomEye 查询
python scripts/batch_ssl_cert.py ips.txt                     # 批量 SSL 证书域名提取
```

所有批量脚本支持 `--no-validate` 跳过凭证校验。

**断点续查**：进度保存在 `{storage_file}.{channel_name}.progress` 文件中。中断后重新运行会自动跳过已处理的 IP。如需重新查询，删除 `.progress` 文件或使用 `tools/progress_tool.py` 管理。

### 五、辅助工具

**IP 文件合并/去重/验证：**

```bash
python tools/merge_ip_files.py ips.txt                                 # 单文件去重+验证
python tools/merge_ip_files.py file1.txt file2.txt file3.txt           # 多文件合并去重
python tools/merge_ip_files.py file1.txt file2.txt -o merged.txt       # 合并并输出到文件
python tools/merge_ip_files.py ips.txt --show-invalid                  # 显示被排除的无效IP
python tools/merge_ip_files.py base.txt source1.txt source2.txt -a     # 追加模式
```

支持 IPv4 和 IPv6 格式验证。单文件时执行去重和验证，多文件时合并后去重验证。追加模式将来源文件中不重复的有效IP追加到目标文件。

**配置管理：**

```bash
python tools/config_tool.py list                                       # 列出所有配置项
python tools/config_tool.py get IP_STORAGE_DIR                         # 获取配置值
python tools/config_tool.py set IP_STORAGE_DIR data/202604             # 设置配置值
python tools/config_tool.py delete IP_STORAGE_DIR                      # 删除配置项
python tools/config_tool.py bulk-set IP_STORAGE_DIR=data IP_STORAGE_NAME=ip_data  # 批量设置
```

所有配置项必须以 `IP_` 为前缀。

**进度文件管理：**

```bash
python tools/progress_tool.py generate data/ip_data.json --channel fofa_host          # 从 JSON 生成 progress 文件
python tools/progress_tool.py generate data/ip_data.json --channel fofa_host -o custom.progress  # 指定输出路径
python tools/progress_tool.py remove data/ip_data.fofa_host.progress 1.2.3.4 5.6.7.8 # 删除指定 IP
python tools/progress_tool.py remove data/ip_data.fofa_host.progress --from-file ips.txt  # 从文件读取要删除的 IP
```

**IP-域名映射验证：**

```bash
python tools/verify_ip_domain.py data/ip_data.json                     # 验证所有域名映射
python tools/verify_ip_domain.py data/ip_data.json --channel aizhan    # 仅验证爱站渠道
python tools/verify_ip_domain.py data/ip_data.json --dry-run           # 仅验证不写回
python tools/verify_ip_domain.py data/ip_data.json --show-all          # 显示全部结果
```

## 环境变量

在 `.env` 文件中配置，所有变量以 `IP_` 为前缀，由 `config.py` 统一管理：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `IP_STORAGE_DIR` | 否 | 空 | channel数据存储子目录（相对于 data/，可为空，不允许绝对路径和场景保留名 `ip_domain_lookup`/`trace_ip`） |
| `IP_STORAGE_NAME` | 否 | `ip_data` | 存储名称（用于数据文件命名前缀） |
| `IP_IP_DOMAIN_LOOKUP_PROJECT_NAME` | 否 | `temp` | ip_domain_lookup 场景项目名称（输出到 `data/ip_domain_lookup/{项目名称}/`） |
| `IP_TRACE_IP_PROJECT_NAME` | 否 | `temp` | trace_ip 场景项目名称（输出到 `data/trace_ip/{项目名称}/`） |
| `IP_FOFA_API_KEY` | Fofa 查询时 | — | Fofa API Key |
| `IP_FOFA_QUERY_DELAY` | 否 | `2.0` | Fofa 查询间隔（秒） |
| `IP_IPINFO_ACCESS_TOKEN` | IPInfo API 时 | — | IPInfo Access Token |
| `IP_IPINFO_QUERY_DELAY` | 否 | `1.2` | IPInfo 查询间隔（秒） |
| `IP_AIZHAN_COOKIE` | 爱站查询时 | — | 爱站网 Cookie（浏览器登录后获取） |
| `IP_AIZHAN_QUERY_DELAY` | 否 | `2.0` | 爱站查询间隔（秒） |
| `IP_CHINAZ_COOKIE` | 否 | 空 | 站长之家 Cookie（可选，有 Cookie 可查更多信息） |
| `IP_CHINAZ_QUERY_DELAY` | 否 | `2.0` | 站长之家查询间隔（秒） |
| `IP_RDNS_QUERY_TIMEOUT` | 否 | `1.5` | RDNS 查询超时（秒） |
| `IP_RDNS_QUERY_DELAY` | 否 | `0.1` | RDNS 批量查询间隔（秒） |
| `IP_WHOIS_QUERY_TIMEOUT` | 否 | `2.0` | Whois 查询超时（秒） |
| `IP_WHOIS_QUERY_DELAY` | 否 | `0.5` | Whois 批量查询间隔（秒） |
| `IP_ZOOMEYE_API_KEY` | ZoomEye 查询时 | — | ZoomEye API Key |
| `IP_ZOOMEYE_QUERY_DELAY` | 否 | `1.0` | ZoomEye 查询间隔（秒） |
| `IP_SSL_CERT_PORT` | 否 | `443` | SSL 证书获取端口 |
| `IP_SSL_CERT_TIMEOUT` | 否 | `5` | SSL 连接超时（秒） |
| `IP_SSL_CERT_QUERY_DELAY` | 否 | `0.5` | SSL 证书查询间隔（秒） |

## 典型工作流

### 工作流 1：批量采集新 IP 情报

用户给出一批 IP 地址文件，需要采集多渠道情报：

1. 用 `tools/merge_ip_files.py` 验证和去重 IP 列表
2. 用 `scripts/batch_ipinfo_api.py` 批量查询 IP 基本信息
3. 用 `scripts/batch_fofa_host.py` 批量查询端口和服务信息
4. 用 `scripts/batch_rdns_ptr.py` 批量查询反向域名
5. 用 `reader.py list --export-excel` 导出结果

### 工作流 2：IP 反查域名

用户需要查询 IP 绑定了哪些域名：

1. 用 `scripts/batch_aizhan.py` 批量通过爱站网查询 IP 绑定域名
2. 用 `scripts/batch_chinaz.py` 批量通过站长之家查询 IP 绑定域名
3. 用 `reader.py get-channel <IP> aizhan` 或 `chinaz` 查看域名列表
4. 用 `reader.py list --include-channel aizhan chinaz --export-excel domains.xlsx` 导出域名数据

### 工作流 3：查询和分析已知 IP

用户需要查看特定 IP 的已有情报：

1. 用 `reader.py get` 获取 IP 全部数据
2. 用 `reader.py search` 按渠道或字段搜索相关 IP
3. 用 `reader.py list --export-excel` 导出筛选后的数据

### 工作流 4：添加自定义分析结果

用户有分析结论需要录入：

1. 用 `writer.py add` 逐条添加分析渠道数据（如 kimi 分析结果）
2. 用 `reader.py get` 验证录入是否正确
3. 用 `reader.py list --export-excel` 导出完整报告

### 工作流 5：溯源IP处理流水线（自动化）

用户有一批溯源IP需要处理，需要自动采集基础情报、分类过滤、深度查询：

```bash
python -m scenarios.trace_ip ips.txt                       # 完整流水线
python -m scenarios.trace_ip ips.txt --no-deep-query       # 只采集+分类，不深度查询
python -m scenarios.trace_ip ips.txt --from-phase 2         # 从阶段2开始（跳过已完成的阶段1）
python -m scenarios.trace_ip ips.txt --only-phase 2         # 只执行分类阶段
python -m scenarios.trace_ip ips.txt --no-custom-rules      # 不加载外部规则
python -m scenarios.trace_ip ips.txt --custom-rules my_rules.json  # 使用指定规则文件
python -m scenarios.trace_ip ips.txt --channel-timeout 30   # 单渠道超时30秒
```

**流水线阶段：**

| 阶段 | 说明 | 输出 |
|------|------|------|
| Phase 1 | 基础情报采集（IPInfo + RDNS，并行查询） | 数据写入 `data/trace_ip/{project_name}/{project_name}.json` |
| Phase 2 | 自动分类过滤 | `trace_classify` 渠道 + `{project_name}.trace_filtered_ips` + `{project_name}.unclassified_rdns` + `{project_name}.unclassified_no_info` |
| Phase 3 | 深度查询（爱站 + 站长 + Fofa Host，并行查询） | 数据写入 `{project_name}.json` |
| Phase 4 | 汇总报告 | `{project_name}.trace_report` |

**分类类别：**

| 类别 | 说明 | 是否深度查询 |
|------|------|-------------|
| cloud_provider | 云服务商（AWS/阿里云/腾讯云等） | ✅ |
| cdn | CDN/WAF 节点 | ❌ |
| crawler_scanner | 爬虫/扫描器 | ❌ |
| residential | 家用宽带 | ✅ |
| other | 未识别（需人工确认） | ✅ |

**分类规则管理：**

- 内置规则：`scenarios/trace_ip/classifiers/builtin_rules.json`（稳定，勿随意修改）
- 外部规则：`scenarios/trace_ip/classifiers/custom_rules.json`（试运行，验证后合并到内置）
- 未识别的 RDNS 记录输出到 `data/trace_ip/{project_name}/{project_name}.unclassified_rdns`
- 信息不足的 IP 输出到 `data/trace_ip/{project_name}/{project_name}.unclassified_no_info`
- `{project_name}` 由 `IP_TRACE_IP_PROJECT_NAME` 决定

**断点续跑**：每个阶段完成后写入标记文件（`{project_name}.trace_phase{N}_done`），使用 `--from-phase` 跳过已完成阶段。标记文件名由 `IP_TRACE_IP_PROJECT_NAME` 决定，不同项目互不干扰。

### 工作流 6：IP域名反查流水线

用户需要批量查询 IP 绑定域名并进行 DNS 正向验证：

```bash
python -m scenarios.ip_domain_lookup ips.txt                       # 完整流水线
python -m scenarios.ip_domain_lookup ips.txt --from-phase 2         # 从阶段2开始
python -m scenarios.ip_domain_lookup ips.txt --only-phase 1         # 只执行域名收集
python -m scenarios.ip_domain_lookup ips.txt --channel-timeout 30   # 单渠道超时30秒
python -m scenarios.ip_domain_lookup ips.txt --dns-timeout 5        # DNS超时5秒
python -m scenarios.ip_domain_lookup ips.txt --dns-concurrency 20   # DNS并发20线程
```

**流水线阶段：**

| 阶段 | 说明 | 输出 |
|------|------|------|
| Phase 1 | 域名收集（RDNS + 爱站 + 站长之家 + ZoomEye + Fofa Search + SSL 证书，并行查询） | `ip_domain_lookup` 渠道写入 `data/ip_domain_lookup/{project_name}/{project_name}.json` |
| Phase 2 | DNS 正向验证（批量并发验证域名是否仍解析到原 IP） | `verified_domains` 字段写入 `{project_name}.json` |
| Phase 3 | 汇总报告 | `{project_name}.domain_lookup_report` + `{project_name}.domain_lookup_matched` |

**验证结果状态：**
- `matched` — 域名仍解析到原始 IP ✅
- `changed` — 域名已解析到其他 IP 🔄
- `unresolved` — DNS 解析失败（域名可能已过期）❌
- `timeout` — DNS 解析超时
- `error` — 其他错误

## 注意事项

- 批量查询前先用 `merge_ip_files.py` 验证 IP 格式，避免浪费 API 调用
- Fofa 和 IPInfo API 有速率限制，不要将查询间隔设得太短
- 爱站和站长之家通过爬虫抓取页面，Cookie 会过期，需要定期更新 `.env` 中的 Cookie 值
- 爱站和站长之家建议查询间隔不低于 2 秒，过快可能被封 IP
- 数据存储为 JSON 文件，并发写入可能导致数据丢失，批量脚本和流水线已内置串行/批量写入
- 渠道数据结构由各采集脚本决定，不同渠道的字段名可能不同
- 日志文件存储在 `data/logs/` 目录，自动轮转（单文件最大 10MB，保留 3 份备份）
- 读取 `README.md` 可获取更详细的文档信息
