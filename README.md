# IP Info Manager — IP 信息管理工具

一个用于批量采集、存储、查询和导出 IP 地址多维度情报信息的命令行工具。

## 快速开始

```bash
git clone https://github.com/songmoshangchen/ip_info_manager.git
cd ip_info_manager
pip install -r requirements.txt
cp .env.example .env
python tools/config_tool.py set IP_FOFA_API_KEY "你的Key"
python channel/rdns_ptr.py 8.8.8.8
```

详细的初始化步骤（可选依赖安装、API 凭证获取、数据存储配置等）请参阅 **[references/setup.md](references/setup.md)**。

## 功能概述

- **多渠道情报采集**：通过 Fofa（Host聚合/搜索）、IPInfo（API/免API）、RDNS PTR、Whois、爱站、站长之家、ZoomEye、SSL 证书等渠道批量查询 IP 信息
- **IP标签打标**：基于本地威胁情报文件批量匹配 IP 标签（银狐、僵尸网络C&C等），支持累加/覆盖模式
- **JSON 数据存储**：所有 IP 数据以 JSON 格式统一存储，按 IP + 渠道组织
- **命令行查询**：支持按 IP、渠道、字段等条件检索数据
- **Excel 导出**：将 IP 数据导出为格式化的 Excel 文件
- **断点续查**：批量查询和流水线均支持进度保存，中断后可继续
- **任务状态查询**：通过 `status_tool.py` 查看流水线/批量查询的运行状态、进度和 ETA，支持 AI 异步执行模式
- **启动前检查**：流水线启动时自动检查依赖、预估各阶段耗时，缺失依赖时明确报错而非静默跳过
- **报告摘要**：Phase 5 完成后自动输出 P1-P4 各级 IP 数量和高价值 IP
- **并发查询**：RDNS 查询提供多线程并发版本，流水线内部并行查询多渠道
- **IP 反查域名**：通过爱站网和站长之家查询 IP 绑定的域名信息
- **溯源IP处理流水线**：自动采集、IP标签打标、分类过滤、深度查询、溯源优先级分级、汇总报告（Word + Excel）
- **IP域名反查流水线**：域名收集、DNS正向验证、汇总报告
- **Word + Excel 报告自动生成**：流水线末尾自动生成 Word 分析报告和 Excel 溯源优先级表格（P1-P4 四个 sheet），含决策树优先级分级、价值分级统计、动态溯源路径建议（需 python-docx、openpyxl）
- **统一日志系统**：控制台+文件双输出，自动轮转

## 目录结构

```
ip_info_manager/
├── .env                    # 环境变量配置（API Key 等）
├── .env.example            # 环境变量配置模板
├── config.py               # 集中配置管理（Pydantic Settings）
├── requirements.txt        # Python 依赖
├── writer.py               # IP 数据写入器
├── reader.py               # IP 数据读取器
├── exporter.py             # Excel 导出器
├── config/                 # 配置文件目录
│   └── ip_tagger/          # IP标签打标配置
│       ├── manifest.json   # 标签清单（文件 → 标签名映射）
│       └── *.ipset/netset  # 威胁情报源文件
├── channel/                # 数据采集渠道
│   ├── _template.py        # 渠道模板（规范参考）
│   ├── fofa_host.py        # Fofa Host 聚合查询
│   ├── fofa_search.py      # Fofa 搜索查询
│   ├── ipinfo_api.py       # IPInfo 查询（API模式+免API模式）
│   ├── rdns_ptr.py         # RDNS PTR 反向解析
│   ├── whois_query.py      # Whois 查询
│   ├── aizhan.py           # 爱站网 IP 反查域名
│   ├── chinaz.py           # 站长之家 IP 反查域名
│   ├── zoomeye.py          # ZoomEye 网络空间测绘
│   └── ssl_cert.py         # SSL 证书域名提取
├── scripts/                # 批量查询脚本
│   ├── logger_utils.py     # 日志工具
│   ├── batch_fofa_host.py  # 批量 Fofa Host 聚合查询
│   ├── batch_fofa_search.py # 批量 Fofa 搜索查询
│   ├── batch_ipinfo_api.py # 批量 IPInfo 查询
│   ├── batch_rdns_ptr.py   # 批量 RDNS 查询（单线程）
│   ├── batch_rdns_ptr_concurrent.py  # 批量 RDNS 查询（多线程）
│   ├── batch_whois.py      # 批量 Whois 查询
│   ├── batch_aizhan.py     # 批量爱站网查询
│   ├── batch_chinaz.py     # 批量站长之家查询
│   ├── batch_zoomeye.py    # 批量 ZoomEye 查询
│   └── batch_ssl_cert.py   # 批量 SSL 证书查询
├── scenarios/              # 场景工作流
│   ├── trace_ip/           # 溯源IP处理流水线
│   │   ├── trace_ip.py     # 入口脚本
│   │   ├── pipeline.py     # 流水线核心逻辑
│   │   ├── classifier.py   # IP分类器
│   │   ├── progress.py     # 进度管理 + 批量写入
│   │   ├── reporter.py     # 报告生成
│   │   └── classifiers/    # 分类规则
│   │       ├── builtin_rules.json
│   │       └── custom_rules.json
│   └── ip_domain_lookup/   # IP域名反查流水线
│       ├── ip_domain_lookup.py  # 入口脚本
│       ├── pipeline.py     # 流水线核心逻辑
│       ├── dns_validator.py # DNS正向验证
│       ├── progress.py     # 进度管理 + 批量写入
│       └── reporter.py     # 报告生成
├── tools/                  # 辅助工具
│   ├── docx_builder.py   # Word 报告生成公共引擎（python-docx）
│   ├── ai_analysis.py    # AI 研判辅助工具（筛选待研判IP、统计）
│   ├── ip_tagger.py      # IP标签打标工具（基于本地威胁情报文件批量匹配）
│   ├── ip_tagger_updater.py # IP标签源自动更新工具（从FireHOL下载）
│   ├── merge_ip_files.py   # IP 文件合并/去重/验证
│   ├── config_tool.py      # .env 配置管理工具
│   ├── progress_tool.py    # .progress 进度文件管理工具
│   ├── status_tool.py      # 任务状态查询工具（运行状态/进度/ETA）
│   └── verify_ip_domain.py # IP-域名映射验证
├── utils/                  # 通用工具
│   ├── file_utils.py
│   ├── ip_utils.py
│   ├── dns_verify.py      # DNS 域名验证共享模块
│   └── pid_manager.py      # PID 文件管理（任务运行状态检测）
└── data/                   # 数据存储根目录
    ├── {storage_dir}/      # channel/batch 通用数据（由 IP_STORAGE_DIR 决定）
    │   ├── {storage_name}.json  # 主数据文件
    │   └── logs/           # 日志目录
    ├── ip_domain_lookup/   # IP域名反查场景数据
    │   └── {project_name}/ # 由 IP_IP_DOMAIN_LOOKUP_PROJECT_NAME 决定
    │       ├── {project_name}.json
    │       ├── {project_name}.domain_lookup_report
    │       └── {project_name}.domain_lookup_matched
    └── trace_ip/           # 溯源IP场景数据
        └── {project_name}/ # 由 IP_TRACE_IP_PROJECT_NAME 决定
            ├── {project_name}.json
            ├── {project_name}.trace_report
            ├── {project_name}.trace_filtered_ips
            ├── {project_name}.unclassified_rdns
            └── {project_name}.unclassified_no_info
```

## 环境配置

> 完整的初始化指南请参阅 **[references/setup.md](references/setup.md)**，包含依赖安装、API 凭证获取、数据存储配置和安装验证等详细步骤。

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

当前依赖：

- `pydantic-settings>=2.0.0` — 配置管理
- `ipinfo>=5.0.0` — IPInfo SDK
- `beautifulsoup4>=4.12.0` — HTML 解析（爱站/站长之家）
- `requests>=2.28.0` — HTTP 请求
- `python-whois` — Whois 查询（可选，手动安装）
- `openpyxl` — Excel 导出（可选，手动安装）
- `python-docx>=1.0.0` — Word 报告生成（可选，未安装时流水线跳过报告生成阶段）

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入实际值：

```bash
# 输出文件配置
IP_STORAGE_DIR=
IP_STORAGE_NAME=ip_data
IP_IP_DOMAIN_LOOKUP_PROJECT_NAME=temp
IP_TRACE_IP_PROJECT_NAME=temp

# API Key / Cookie 凭证
IP_FOFA_API_KEY=your_fofa_api_key_here
IP_IPINFO_ACCESS_TOKEN=your_ipinfo_access_token_here
IP_AIZHAN_COOKIE=your_aizhan_cookie_here
IP_CHINAZ_COOKIE=your_chinaz_cookie_here
IP_ZOOMEYE_API_KEY=your_zoomeye_api_key_here

# 查询间隔与超时
IP_FOFA_QUERY_DELAY=2.0
IP_IPINFO_QUERY_DELAY=1.2
IP_RDNS_QUERY_DELAY=0.1
IP_RDNS_QUERY_TIMEOUT=1.5
IP_WHOIS_QUERY_DELAY=0.5
IP_WHOIS_QUERY_TIMEOUT=2.0
IP_AIZHAN_QUERY_DELAY=2.0
IP_CHINAZ_QUERY_DELAY=2.0
IP_ZOOMEYE_QUERY_DELAY=1.0
IP_SSL_CERT_PORT=443
IP_SSL_CERT_TIMEOUT=5
IP_SSL_CERT_QUERY_DELAY=0.5
```

**输出文件配置：**

| 变量                                 | 必填 | 默认值       | 说明                                          |
| ---------------------------------- | -- | --------- | ------------------------------------------- |
| `IP_STORAGE_DIR`                   | 否  | 空         | channel数据存储子目录（相对于 data/，可为空，不允许绝对路径和场景保留名） |
| `IP_STORAGE_NAME`                  | 否  | `ip_data` | 存储名称（用于数据文件命名前缀）                            |
| `IP_IP_DOMAIN_LOOKUP_PROJECT_NAME` | 否  | `temp`    | ip\_domain\_lookup 场景项目名称                   |
| `IP_TRACE_IP_PROJECT_NAME`         | 否  | `temp`    | trace\_ip 场景项目名称                            |

**API Key / Cookie 凭证配置：**

| 变量                       | 必填               | 默认值 | 说明                              |
| ------------------------ | ---------------- | --- | ------------------------------- |
| `IP_FOFA_API_KEY`        | 使用 Fofa 时必填      | —   | Fofa API Key                    |
| `IP_IPINFO_ACCESS_TOKEN` | IPInfo API 模式时必填 | —   | IPInfo Access Token             |
| `IP_AIZHAN_COOKIE`       | 使用爱站时必填          | —   | 爱站网 Cookie（浏览器登录后获取）            |
| `IP_CHINAZ_COOKIE`       | 否                | 空   | 站长之家 Cookie（可选，有 Cookie 可查更多信息） |
| `IP_ZOOMEYE_API_KEY`     | 使用 ZoomEye 时必填   | —   | ZoomEye API Key                 |

**查询间隔与超时配置：**

| 变量                           | 必填 | 默认值    | 说明                   |
| ---------------------------- | -- | ------- | -------------------- |
| `IP_FOFA_QUERY_DELAY`        | 否  | `2.0`   | Fofa 查询间隔（秒）         |
| `IP_FOFA_QUERY_TIMEOUT`      | 否  | `30.0`  | Fofa 查询超时（秒）         |
| `IP_FOFA_VALIDATE_TIMEOUT`   | 否  | `10.0`  | Fofa 凭证验证超时（秒）       |
| `IP_IPINFO_QUERY_DELAY`      | 否  | `1.2`   | IPInfo 查询间隔（秒）       |
| `IP_IPINFO_QUERY_TIMEOUT`    | 否  | `30.0`  | IPInfo 查询超时（秒）       |
| `IP_IPINFO_VALIDATE_TIMEOUT` | 否  | `30.0`  | IPInfo 凭证验证超时（秒）     |
| `IP_RDNS_QUERY_TIMEOUT`      | 否  | `1.5`   | RDNS 查询超时（秒）         |
| `IP_RDNS_QUERY_DELAY`        | 否  | `0.1`   | RDNS 批量查询间隔（秒）       |
| `IP_WHOIS_QUERY_TIMEOUT`     | 否  | `2.0`   | Whois 查询超时（秒）        |
| `IP_WHOIS_QUERY_DELAY`       | 否  | `0.5`   | Whois 批量查询间隔（秒）      |
| `IP_AIZHAN_QUERY_DELAY`      | 否  | `2.0`   | 爱站查询间隔（秒）           |
| `IP_AIZHAN_QUERY_TIMEOUT`    | 否  | `15.0`  | 爱站查询超时（秒）           |
| `IP_AIZHAN_VALIDATE_TIMEOUT` | 否  | `10.0`  | 爱站凭证验证超时（秒）         |
| `IP_CHINAZ_QUERY_DELAY`      | 否  | `2.0`   | 站长之家查询间隔（秒）         |
| `IP_CHINAZ_QUERY_TIMEOUT`    | 否  | `15.0`  | 站长之家查询超时（秒）         |
| `IP_CHINAZ_VALIDATE_TIMEOUT` | 否  | `10.0`  | 站长之家凭证验证超时（秒）       |
| `IP_ZOOMEYE_QUERY_DELAY`     | 否  | `1.0`   | ZoomEye 查询间隔（秒）      |
| `IP_SSL_CERT_PORT`           | 否  | `443`   | SSL 证书获取端口           |
| `IP_SSL_CERT_TIMEOUT`        | 否  | `5`     | SSL 连接超时（秒）          |
| `IP_SSL_CERT_OPENSSL_TIMEOUT`| 否  | `10.0`  | SSL 证书 OpenSSL 超时（秒） |
| `IP_SSL_CERT_QUERY_DELAY`    | 否  | `0.5`   | SSL 证书查询间隔（秒）        |

**IP域名反查流水线渠道开关：**

| 变量                                        | 必填 | 默认值    | 说明                           |
| ----------------------------------------- | -- | ------ | ---------------------------- |
| `IP_IP_DOMAIN_LOOKUP_RDNS_PTR_ENABLED`    | 否  | `true` | IP域名反查流水线：启用 RDNS PTR 反向解析   |
| `IP_IP_DOMAIN_LOOKUP_AIZHAN_ENABLED`      | 否  | `true` | IP域名反查流水线：启用爱站网 IP 反查域名      |
| `IP_IP_DOMAIN_LOOKUP_CHINAZ_ENABLED`      | 否  | `true` | IP域名反查流水线：启用站长之家 IP 反查域名     |
| `IP_IP_DOMAIN_LOOKUP_ZOOMEYE_ENABLED`     | 否  | `true` | IP域名反查流水线：启用 ZoomEye 网络空间测绘  |
| `IP_IP_DOMAIN_LOOKUP_FOFA_SEARCH_ENABLED` | 否  | `true` | IP域名反查流水线：启用 Fofa 搜索查询       |
| `IP_IP_DOMAIN_LOOKUP_SSL_CERT_ENABLED`    | 否  | `true` | IP域名反查流水线：启用 SSL 证书域名提取      |
| `IP_TRACE_IP_PHASE1_IPINFO_ENABLED`       | 否  | `true` | 溯源IP流水线阶段1：启用 IPInfo 查询      |
| `IP_TRACE_IP_PHASE1_RDNS_PTR_ENABLED`     | 否  | `true` | 溯源IP流水线阶段1：启用 RDNS PTR 反向解析  |
| `IP_TRACE_IP_PHASE3_AIZHAN_ENABLED`       | 否  | `true` | 溯源IP流水线阶段3：启用爱站网 IP 反查域名     |
| `IP_TRACE_IP_PHASE3_CHINAZ_ENABLED`       | 否  | `true` | 溯源IP流水线阶段3：启用站长之家 IP 反查域名    |
| `IP_TRACE_IP_PHASE3_FOFA_HOST_ENABLED`    | 否  | `true` | 溯源IP流水线阶段3：启用 Fofa Host 聚合查询 |
| `IP_TRACE_IP_PHASE3_DNS_VERIFY_ENABLED`   | 否  | `true` | 溯源IP流水线阶段3：启用 DNS 域名正向验证   |
| `IP_TRACE_IP_DNS_VERIFY_TIMEOUT`          | 否  | `3.0`  | DNS 域名验证超时（秒）                   |
| `IP_TRACE_IP_DNS_VERIFY_CONCURRENCY`      | 否  | `10`   | DNS 域名验证并发线程数                   |

所有配置项由 `config.py` 统一管理，以 `IP_` 为前缀。可通过 `tools/config_tool.py` 查看和管理。

## 数据存储格式

所有 IP 数据存储在 `data/{storage_dir}/{storage_name}.json`（channel/batch 通用）或 `data/{场景名}/{project_name}/{project_name}.json`（场景专用），结构如下：

```json
{
  "1.2.3.4": {
    "ip": "1.2.3.4",
    "fofa_host": {
      "country_name": "China",
      "org": "China Telecom",
      "query_time": "2026-04-20T10:00:00"
    },
    "ipinfo_api": {
      "country": "CN",
      "as_name": "China Telecom",
      "query_time": "2026-04-20T10:00:00"
    },
    "rdns_ptr": {
      "has_ptr": true,
      "hostname": "example.com",
      "aliases": [],
      "ip_addresses": ["1.2.3.4"],
      "query_time": "2026-04-20T10:00:00"
    },
    "whois": {
      "has_whois": true,
      "whois_data": { "registrar": "...", "organization": "..." },
      "query_time": "2026-04-20T10:00:00"
    },
    "aizhan": {
      "success": true,
      "location": "中国广东广州",
      "isp": "电信",
      "domain_count": 5,
      "domains": [{"domain": "example.com", "title": "示例网站"}],
      "query_time": "2026-04-20T10:00:00"
    },
    "chinaz": {
      "success": true,
      "location": "广东省广州市",
      "isp": "电信",
      "domains": [{"domain": "example.com", "start_time": "2024-01-01", "end_time": "2026-01-01"}],
      "query_time": "2026-04-20T10:00:00"
    }
  }
}
```

每个 IP 下包含 `ip` 字段和若干渠道数据，渠道名作为 key。不同渠道的数据结构由对应采集脚本决定。

## 核心模块

### writer.py — IP 数据写入器

用于添加、更新和删除 IP 数据。

```bash
# 添加/更新 IP 渠道数据
python writer.py add <IP> <渠道名> <key1=value1> <key2=value2> ...

# 删除整个 IP
python writer.py delete-ip <IP>

# 删除 IP 的某个渠道
python writer.py delete-channel <IP> <渠道名>
```

**示例：**

```bash
python writer.py add "1.2.3.4" "kimi" net_type="阿里云ECS" trace_value="高" action="保留" note="测试"
```

值类型自动推断：`true/false` → 布尔，纯数字 → 整数，含小数点 → 浮点，其余 → 字符串。

### reader.py — IP 数据读取器

用于查询和检索已存储的 IP 数据。

```bash
# 获取 IP 全部数据
python reader.py get <IP>

# 获取 IP 指定渠道数据
python reader.py get-channel <IP> <渠道名>

# 列出所有 IP
python reader.py list
python reader.py list --detail                    # 显示详细信息
python reader.py list --start 10 --end 20         # 分页
python reader.py list --include-channel fofa_host  # 仅显示含 fofa_host 渠道的 IP
python reader.py list --exclude-channel kimi       # 排除含 kimi 渠道的 IP
python reader.py list --export-excel output.xlsx   # 导出到 Excel
python reader.py list --output result.txt          # 输出到文件

# 列出 IP 的所有渠道
python reader.py list-channels <IP>

# 按渠道搜索 IP
python reader.py search <渠道名>
python reader.py search <渠道名> --key <字段> --value <值>
```

### exporter.py — Excel 导出器

一般通过 `reader.py` 的 `--export-excel` 参数调用，也可单独使用。导出的 Excel 包含：

- 蓝色表头、白色加粗字体
- 自动列宽适配
- 按渠道分组的字段展示

## 数据采集渠道

### channel/fofa\_host.py — Fofa Host 聚合查询

调用 Fofa Host 聚合 API 获取 IP 的主机详情（端口、服务、操作系统等）。

```bash
python channel/fofa_host.py <IP地址>
```

需要配置 `IP_FOFA_API_KEY`。

**校验方式**：Key 非空 + 调用 `https://fofa.info/api/v1/info/my` 验证用户信息。

### channel/fofa\_search.py — Fofa 搜索查询

调用 Fofa 搜索 API（`GET /api/v1/search/all`）查询 IP 关联的资产信息，保存完整原始 API 响应。

```bash
python channel/fofa_search.py <IP地址>
```

需要配置 `IP_FOFA_API_KEY`（与 fofa\_host 共享）。支持 `query_suffix` 可选参数，场景可自定义附加查询条件（如  ` && is_domain=true`）。默认每次请求 1 页 20 条记录。

**校验方式**：Key 非空 + 调用 `https://fofa.info/api/v1/info/my` 验证用户信息。

### channel/ipinfo\_api.py — IPInfo 查询

支持两种模式，通过 `use_api` 参数切换：

- **API 模式**：`https://api.ipinfo.io/lite/{ip}` + Bearer Token，返回 ASN 等详细信息
- **免 API 模式**：`https://ipinfo.io/{ip}/json`，无需 Token，返回基础地理信息

```bash
python channel/ipinfo_api.py <IP地址>    # 自动根据是否有 Token 选择模式
```

单条查询时自动判断：有 Token 用 API 模式，无 Token 用免 API 模式。

### channel/rdns\_ptr.py — RDNS PTR 反向解析

通过 DNS PTR 记录查询 IP 的反向域名。

```bash
python channel/rdns_ptr.py <IP地址>
```

无需配置，使用 `socket.gethostbyaddr()` 本地查询。支持 `IP_RDNS_QUERY_TIMEOUT` 设置超时。

### channel/whois\_query.py — Whois 查询

查询 IP 或域名的注册信息。

```bash
python channel/whois_query.py <IP地址或域名>
```

需要安装 `python-whois`：`pip install python-whois`。支持 `IP_WHOIS_QUERY_TIMEOUT` 设置超时。

**标准函数**：`validate_channel_key()` → `request_channel()` → `parse_response()` → `fetch_channel()` → `main()`

### channel/aizhan.py — 爱站网 IP 反查域名

通过爱站网（dns.aizhan.com）查询 IP 绑定的域名信息，包括域名、网站标题、归属地、运营商。

```bash
python channel/aizhan.py <IP地址>
```

需要配置 `IP_AIZHAN_COOKIE`（浏览器登录爱站网后获取 Cookie）。

返回数据格式：

```json
{
  "success": true,
  "location": "中国广东广州",
  "isp": "电信",
  "domain_count": 5,
  "domains": [{"domain": "example.com", "title": "示例网站"}],
  "query_time": "2026-04-20T10:00:00"
}
```

### channel/chinaz.py — 站长之家 IP 反查域名

通过站长之家（ipchaxun.com）查询 IP 绑定的域名信息，包括域名、绑定时间段、归属地、运营商。

```bash
python channel/chinaz.py <IP地址>
```

Cookie 可选配置（`IP_CHINAZ_COOKIE`），有 Cookie 可查询更多信息。

返回数据格式：

```json
{
  "success": true,
  "location": "广东省广州市",
  "isp": "电信",
  "domains": [{"domain": "example.com", "start_time": "2024-01-01", "end_time": "2026-01-01"}],
  "query_time": "2026-04-20T10:00:00"
}
```

### channel/zoomeye.py — ZoomEye 网络空间测绘

通过 ZoomEye v2 API 查询 IP 关联的网络资产信息（域名、端口等）。

```bash
python channel/zoomeye.py <IP地址>
```

需要配置 `IP_ZOOMEYE_API_KEY`。默认每次请求 1 页 20 条记录，保存完整 API 原始响应。

**校验方式**：仅检查 Key 非空，不进行在线校验（避免消耗额度）。

返回数据格式（ZoomEye API 原始响应）：

```json
{
  "code": 60000,
  "message": "success",
  "query": "ip:1.2.3.4",
  "total": 15,
  "data": [{"ip": "1.2.3.4", "port": 443, "domain": "example.com"}],
  "facets": {},
  "query_time": "2026-04-23T10:00:00"
}
```

### channel/ssl\_cert.py — SSL 证书域名提取

直连目标 IP 的 443 端口获取 SSL 证书，从中提取 Subject CN 和 SubjectAltName 域名。无需外部 API。

```bash
python channel/ssl_cert.py <IP地址>
```

无需 API Key。需要系统安装 `openssl` 命令。支持 `IP_SSL_CERT_PORT`、`IP_SSL_CERT_TIMEOUT` 配置。

**返回数据格式：**

```json
{
  "ip": "1.2.3.4",
  "port": 443,
  "subject_cn": "example.com",
  "issuer_cn": "Let's Encrypt",
  "not_before": "Apr 23 00:00:00 2026 GMT",
  "not_after": "Jul 22 23:59:59 2026 GMT",
  "san_domains": ["example.com", "www.example.com"],
  "domains": ["example.com", "www.example.com"],
  "query_time": "2026-04-23T10:00:00"
}
```

## 批量查询脚本

所有批量脚本的使用方式一致：

```bash
python scripts/<脚本名> <IP文件路径> [选项]
```

IP 文件为纯文本，每行一个 IP 地址。

| 脚本                             | 渠道           | 独有参数          | 说明                      |
| ------------------------------ | ------------ | ------------- | ----------------------- |
| `batch_fofa_host.py`           | fofa\_host   | —             | 批量 Fofa Host 聚合查询       |
| `batch_fofa_search.py`         | fofa\_search | —             | 批量 Fofa 搜索查询            |
| `batch_ipinfo_api.py`          | ipinfo\_api  | `--no-api`    | 批量 IPInfo 查询，支持免 API 模式 |
| `batch_rdns_ptr.py`            | rdns\_ptr    | —             | 批量 RDNS 查询（单线程）         |
| `batch_rdns_ptr_concurrent.py` | rdns\_ptr    | `--workers N` | 批量 RDNS 查询（多线程，默认 5）    |
| `batch_whois.py`               | whois        | —             | 批量 Whois 查询             |
| `batch_aizhan.py`              | aizhan       | —             | 批量爱站网 IP 反查域名           |
| `batch_chinaz.py`              | chinaz       | —             | 批量站长之家 IP 反查域名          |
| `batch_zoomeye.py`             | zoomeye      | —             | 批量 ZoomEye 查询           |
| `batch_ssl_cert.py`            | ssl\_cert    | —             | 批量 SSL 证书域名提取           |

**所有脚本通用参数**：

- `ip_file` — IP 文件路径（必填）
- `--no-validate` — 跳过渠道凭证校验

**使用示例：**

```bash
python scripts/batch_fofa_host.py ips.txt                      # 批量 Fofa Host 聚合
python scripts/batch_fofa_search.py ips.txt                    # 批量 Fofa 搜索
python scripts/batch_ipinfo_api.py ips.txt                     # 批量 IPInfo（API 模式）
python scripts/batch_ipinfo_api.py ips.txt --no-api            # 批量 IPInfo（免 API 模式）
python scripts/batch_rdns_ptr.py ips.txt                       # 批量 RDNS（单线程）
python scripts/batch_rdns_ptr_concurrent.py ips.txt --workers 20  # 批量 RDNS（20 线程）
python scripts/batch_whois.py ips.txt                          # 批量 Whois
python scripts/batch_aizhan.py ips.txt                         # 批量爱站网
python scripts/batch_chinaz.py ips.txt                         # 批量站长之家
python scripts/batch_zoomeye.py ips.txt                        # 批量 ZoomEye
python scripts/batch_ssl_cert.py ips.txt                       # 批量 SSL 证书域名提取
```

### 断点续查机制

每个批量脚本会自动在数据文件同目录生成 `{storage_file}.{channel_name}.progress` 进度文件，记录已处理的 IP。中断后重新运行会自动跳过已处理的 IP。如需重新查询，删除对应的 `.progress` 文件即可。

可使用 `tools/progress_tool.py` 管理进度文件（生成、删除指定 IP）。

### 日志系统

每个批量脚本和渠道模块自动生成日志文件，存储在 `data/logs/` 目录：

- 渠道日志：`data/logs/{channel_name}.log`（仅文件输出，DEBUG 级别）
- 批量脚本日志：`data/logs/{channel_name}.log`（控制台 INFO + 文件 DEBUG）
- 日志自动轮转：单文件最大 10MB，保留 3 份备份

## 场景工作流

### 溯源IP处理流水线

通过 `scenarios/trace_ip/` 运行，自动完成采集、分类、深度查询和汇总：

```bash
python -m scenarios.trace_ip ips.txt                       # 完整流水线
python -m scenarios.trace_ip ips.txt --no-deep-query       # 只采集+分类，不深度查询
python -m scenarios.trace_ip ips.txt --no-dns-verify        # 深度查询后不做 DNS 域名验证
python -m scenarios.trace_ip ips.txt --from-phase 2         # 从阶段2开始
python -m scenarios.trace_ip ips.txt --only-phase 2         # 只执行分类阶段
python -m scenarios.trace_ip ips.txt --generate-report      # 只生成报告（等同于 --only-phase 5）
python -m scenarios.trace_ip ips.txt --collect-only         # 只执行基础采集（等同于 --only-phase 1）
python -m scenarios.trace_ip ips.txt --no-custom-rules      # 不加载外部规则
python -m scenarios.trace_ip ips.txt --custom-rules my.json # 使用指定规则文件
python -m scenarios.trace_ip ips.txt --channel-timeout 30   # 单渠道超时30秒
```

**流水线阶段：**

| 阶段      | 说明                             | 输出                                                                                                                                     |
| ------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| Phase 1 | 基础情报采集（IPInfo + RDNS，并行查询）     | 数据写入 `data/trace_ip/{project_name}/{project_name}.json`                                                                                |
| Phase 2 | 自动分类过滤                         | `trace_classify` 渠道 + `{project_name}.trace_filtered_ips` + `{project_name}.unclassified_rdns` + `{project_name}.unclassified_no_info` |
| Phase 3 | 深度查询（爱站 + 站长 + Fofa Host，并行查询）+ DNS 域名正向验证 | 数据写入 `{project_name}.json`，验证结果写入 `domain_verify` 字段 |
| Phase 4 | 汇总报告                           | `{project_name}.trace_report`                                                                                                          |
| Phase 5 | 生成 Word + Excel 报告（含溯源优先级分级） | `{project_name}.trace_report.docx`、`{project_name}.trace_report.xlsx` |

**分类类别：**

| 类别               | 说明                 | 是否深度查询 |
| ---------------- | ------------------ | ------ |
| cloud\_provider  | 云服务商（AWS/阿里云/腾讯云等） | ✅      |
| cdn              | CDN/WAF 节点         | ❌      |
| crawler\_scanner | 爬虫/扫描器             | ❌      |
| residential      | 家用宽带               | ✅      |
| other            | 未识别（需人工确认）         | ✅      |

**Word 报告章节结构（Phase 5）：**

| 章节 | 说明 |
|------|------|
| 一、报告概述 | 分析目标、分析方法、数据源统计 |
| 二、处理概览 | 基础情报采集统计、自动分类统计、深度查询统计、待确认IP、价值分级统计（高/中/低） |
| 三、溯源优先级 | IP-域名验证状态表（仅展示 DNS 验证通过的映射）+ 基于决策树模型的 P1-P4 分级（域名→端口→国内IP优先），含动态溯源路径建议 |
| 四、AI研判结果 | 通过 ai_analysis 工具写入的研判结果展示 |
| 五、未识别RDNS记录 | 未匹配规则的 RDNS 主机名列表 |

**溯源优先级决策树：**

| 级别 | 判定条件 | 溯源路径建议 |
|------|---------|------------|
| P1 核心溯源 | 有反查域名 + 国内IP | ICP备案查询域名持有者实名信息 |
| P2 重点溯源 | 有反查域名（国外），或无域名但有端口信息（国内） | WHOIS查询域名注册信息；排查端口服务泄露信息 |
| P3 辅助溯源 | 无域名但有端口信息（国外），或仅国内IP | 端口服务辅助分析；公开信息检索IP历史行为 |
| P4 暂缓 | 无域名、无端口、国外IP | 信息不足，建议持续监控 |

**Excel 报告：**

- 4 个 sheet 分别对应 P1-P4 优先级
- 统一字段：IP、国家、ASN/组织、分类、分类说明、建议溯源路径、域名数、反查域名列表（含DNS验证状态标记，换行分隔）、端口数、开放端口列表、标签
- 自动筛选 + 冻结首行 + 自动列宽

**IP 标签打标：**

- Phase 2 中自动调用 `ip_tagger`，35 个威胁情报源批量匹配
- 标签写入 JSON 的 `tags` 字段，同步展示在 Excel 报告中
- 可通过 `--no-tagger` 跳过，通过 `--tagger-level` 控制匹配级别（1=快速21源/2=正常31源/3=全量35源）

**分类规则管理：**

- 内置规则：`scenarios/trace_ip/classifiers/builtin_rules.json`（稳定，勿随意修改）
- 外部规则：`scenarios/trace_ip/classifiers/custom_rules.json`（试运行，验证后合并到内置）
- 未识别的 RDNS 记录输出到 `{project_name}.unclassified_rdns`
- 信息不足的 IP 输出到 `{project_name}.unclassified_no_info`

**规则文件格式：**

```json
{
  "category_key": {
    "label": "显示名称",
    "description": "类别说明",
    "need_deep_query": true,
    "patterns": [
      { "field": "rdns_ptr.hostname", "match": ".amazonaws.com", "type": "suffix", "note": "AWS Amazon 云服务" },
      { "field": "ipinfo_api.as_name", "match": "Amazon", "type": "contains", "note": "AWS Amazon 云服务" }
    ]
  }
}
```

- 匹配类型：`suffix`（后缀）、`contains`（包含）、`prefix`（前缀）、`exact`（精确）
- `note`（可选）：规则说明，分类结果中会在 `matched_by` 里输出此字段，便于分析人员快速理解匹配到的域名/ASN 含义

**断点续跑**：每个阶段完成后写入标记文件（`{project_name}.trace_phase{N}_done`），使用 `--from-phase` 跳过已完成阶段。支持 Ctrl+C 安全中断，自动保存进度。

**渠道配置**：

可通过环境变量控制各阶段采集渠道的启用/禁用（默认全部启用）：

| 阶段      | 环境变量                                   | 默认值    | 说明                |
| ------- | -------------------------------------- | ------ | ----------------- |
| Phase 1 | `IP_TRACE_IP_PHASE1_IPINFO_ENABLED`    | `true` | 启用 IPInfo 查询      |
| Phase 1 | `IP_TRACE_IP_PHASE1_RDNS_PTR_ENABLED`  | `true` | 启用 RDNS PTR 反向解析  |
| Phase 3 | `IP_TRACE_IP_PHASE3_AIZHAN_ENABLED`    | `true` | 启用爱站网 IP 反查域名     |
| Phase 3 | `IP_TRACE_IP_PHASE3_CHINAZ_ENABLED`    | `true` | 启用站长之家 IP 反查域名    |
| Phase 3 | `IP_TRACE_IP_PHASE3_FOFA_HOST_ENABLED` | `true` | 启用 Fofa Host 聚合查询 |
| Phase 3 | `IP_TRACE_IP_PHASE3_DNS_VERIFY_ENABLED`| `true` | 启用 DNS 域名正向验证   |
| Phase 3 | `IP_TRACE_IP_DNS_VERIFY_TIMEOUT`       | `3.0`  | DNS 验证超时（秒）     |
| Phase 3 | `IP_TRACE_IP_DNS_VERIFY_CONCURRENCY`   | `10`   | DNS 验证并发线程数     |

**使用示例**：

在 `.env` 文件中配置（例如只禁用阶段3的 Fofa Host）：

```bash
# 溯源IP流水线渠道配置
IP_TRACE_IP_PHASE1_IPINFO_ENABLED=true
IP_TRACE_IP_PHASE1_RDNS_PTR_ENABLED=true
IP_TRACE_IP_PHASE3_AIZHAN_ENABLED=true
IP_TRACE_IP_PHASE3_CHINAZ_ENABLED=true
IP_TRACE_IP_PHASE3_FOFA_HOST_ENABLED=false  # 禁用 Fofa Host
```

运行流水线时会显示每个渠道的启用/禁用状态。如果某个阶段的所有渠道都被禁用，会跳过该阶段或报错提示。

### IP域名反查流水线

通过 `scenarios/ip_domain_lookup/` 运行，批量收集域名并进行 DNS 正向验证：

```bash
python -m scenarios.ip_domain_lookup ips.txt                       # 完整流水线
python -m scenarios.ip_domain_lookup ips.txt --from-phase 2         # 从阶段2开始
python -m scenarios.ip_domain_lookup ips.txt --only-phase 1         # 只执行域名收集
python -m scenarios.ip_domain_lookup ips.txt --generate-report      # 只生成报告（等同于 --only-phase 4）
python -m scenarios.ip_domain_lookup ips.txt --channel-timeout 30   # 单渠道超时30秒
python -m scenarios.ip_domain_lookup ips.txt --dns-timeout 5        # DNS超时5秒
python -m scenarios.ip_domain_lookup ips.txt --dns-concurrency 20   # DNS并发20线程
```

**流水线阶段：**

| 阶段      | 说明                                                           | 输出                                                                                 |
| ------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| Phase 1 | 域名收集（RDNS + 爱站 + 站长之家 + ZoomEye + Fofa Search + SSL 证书，并行查询） | `ip_domain_lookup` 渠道写入 `data/ip_domain_lookup/{project_name}/{project_name}.json` |
| Phase 2 | DNS 正向验证（批量并发验证域名是否仍解析到原 IP）                                 | `verified_domains` 字段写入 `{project_name}.json`                                      |
| Phase 3 | 汇总报告                                                         | `{project_name}.domain_lookup_report` + `{project_name}.domain_lookup_matched`     |
| Phase 4 | 生成 Word 报告                                                   | `{project_name}.domain_lookup_report.docx`                                         |

**DNS 验证结果状态：**

- `matched` — 域名仍解析到原始 IP ✅
- `changed` — 域名已解析到其他 IP 🔄
- `unresolved` — DNS 解析失败（域名可能已过期）❌
- `timeout` — DNS 解析超时
- `error` — 其他错误

**渠道配置**：

可通过环境变量控制各采集渠道的启用/禁用（默认全部启用）：

| 环境变量                                      | 默认值    | 说明                |
| ----------------------------------------- | ------ | ----------------- |
| `IP_IP_DOMAIN_LOOKUP_RDNS_PTR_ENABLED`    | `true` | 启用 RDNS PTR 反向解析  |
| `IP_IP_DOMAIN_LOOKUP_AIZHAN_ENABLED`      | `true` | 启用爱站网 IP 反查域名     |
| `IP_IP_DOMAIN_LOOKUP_CHINAZ_ENABLED`      | `true` | 启用站长之家 IP 反查域名    |
| `IP_IP_DOMAIN_LOOKUP_ZOOMEYE_ENABLED`     | `true` | 启用 ZoomEye 网络空间测绘 |
| `IP_IP_DOMAIN_LOOKUP_FOFA_SEARCH_ENABLED` | `true` | 启用 Fofa 搜索查询      |
| `IP_IP_DOMAIN_LOOKUP_SSL_CERT_ENABLED`    | `true` | 启用 SSL 证书域名提取     |

**示例 - 禁用 ZoomEye 和 Fofa Search**：

在 `.env` 文件中添加：

```bash
IP_IP_DOMAIN_LOOKUP_ZOOMEYE_ENABLED=false
IP_IP_DOMAIN_LOOKUP_FOFA_SEARCH_ENABLED=false
```

运行流水线时会显示已启用/已禁用的渠道状态，如果没有启用任何渠道，流水线会报错退出。

## 辅助工具

### tools/docx\_builder.py — Word 报告生成公共引擎

提供 `DocxBuilder` 类，用于生成公文排版格式的 Word 分析报告。各场景的 reporter 通过继承调用自动生成报告。

**排版规范：**

- 字体：正文宋体 + 黑体标题 + Times New Roman 西文
- 表格：三线表（顶线底线粗线，表头下细线，无左右边框）
- 页面：A4 公文版心（上37.3mm/下35.3mm/左28mm/右26mm）
- 题注：章节制编号（表 1-1、表 2-3）
- 样式：Word 样式系统绑定（非内联格式）

**环境检查：**

- 需安装 `python-docx`（`pip install python-docx`）
- 未安装时流水线自动跳过报告生成阶段，输出警告信息，不影响其他功能

### tools/ip\_tagger.py — IP标签打标工具

基于本地威胁情报文件（`.ipset`/`.netset`）批量匹配 IP 并写入标签数据。纯本地计算，无网络请求。

```bash
python tools/ip_tagger.py data/ips.txt                                         # 累加模式（默认）
python tools/ip_tagger.py data/ips.txt --mode overwrite                        # 覆盖模式
python tools/ip_tagger.py data/ips.txt --output data/202604/202604_ip_data.json  # 指定输出 JSON
python tools/ip_tagger.py data/ips.txt --config-dir config/ip_tagger           # 指定配置目录
```

**参数说明：**

| 参数 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `ip_file` | 是 | — | IP 文件路径（每行一个 IP） |
| `--mode` | 否 | `accumulate` | 写入模式：`accumulate`（累加）或 `overwrite`（覆盖） |
| `--output` | 否 | Settings 定位 | 输出 JSON 文件路径 |
| `--config-dir` | 否 | `config/ip_tagger` | 标签配置文件目录 |
| `--manifest` | 否 | `{config-dir}/manifest.json` | 清单文件路径 |

**写入模式：**

- `accumulate`（累加）：将新标签合并到已有 `tags` 字段，按标签名去重
- `overwrite`（覆盖）：清空已有 `tags` 字段后重新写入

**标签配置：**

配置目录 `config/ip_tagger/` 包含：
- `manifest.json` — 标签清单，声明每个文件对应的标签名
- `*.ipset` / `*.netset` — 威胁情报源文件（每行一个 IP 或 CIDR 网段，`#` 开头为注释）

`manifest.json` 格式：

```json
[
  {"file": "yinhu.ipset", "label": "银狐", "source_url": "", "note": "自定义维护"},
  {"file": "feodo_badips.ipset", "label": "僵尸网络C&C", "source_url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/feodo_badips.ipset"}
]
```

**写入的 JSON 数据格式（tags 渠道）：**

只写入命中标签的 IP，格式为标签名列表：

```json
{
  "tags": ["银狐", "高危威胁", "SSH暴力破解"]
}
```

**月度更新提醒：** ip_tagger 运行时检查 `.last_update` 标记，过月未更新则提醒。

**场景集成：**

可通过 `run_tagger()` 公共接口在流水线中直接调用：

```python
from tools.ip_tagger import run_tagger
run_tagger('data/ips.txt', mode='accumulate')
run_tagger('data/ips.txt', level=1)
```

**核心算法：** 统一 IPv4/IPv6 整数排序双指针扫描，O(n+m) 复杂度。

### tools/ip\_tagger\_updater.py — IP标签源自动更新工具

从 [FireHOL blocklist-ipsets](https://github.com/firehol/blocklist-ipsets) 自动下载更新标签源文件，支持三种导入方式：

```bash
python tools/ip_tagger_updater.py                    # 从 GitHub 逐文件下载
python tools/ip_tagger_updater.py --from-git         # git clone 整个仓库（推荐）
python tools/ip_tagger_updater.py --from-archive ./blocklist-ipsets-main.zip  # 从本地 ZIP 导入
python tools/ip_tagger_updater.py --dry-run          # 仅检查
python tools/ip_tagger_updater.py --force            # 强制更新
```

**导入方式：**

| 方式 | 说明 | 适用场景 |
|---|---|---|
| 默认 | 逐文件从 GitHub raw 下载 | 少量文件更新 |
| `--from-git` | git clone 浅克隆整个仓库 | 推荐，一次性获取所有文件 |
| `--from-archive` | 从本地 ZIP 压缩包导入 | 离线环境、网络不稳定 |

**更新策略：** 对比本地与远程文件大小，相同则跳过。临时文件自动清理（使用 `tempfile.TemporaryDirectory`）。

**标签级别（ip\_tagger 查询时使用）：**

| 级别 | 标签源数 | 说明 |
|---|---|---|
| `--level 1`（快速） | 21 | 核心威胁：银狐、C&C、Tor、SSH、Bot、高危/中危/低危威胁、各类攻击 |
| `--level 2`（正常） | 31 | + Spamhaus、GreenSnow、PHP系列、乌克兰Blocklist、Spam30天 |
| `--level 3`（全量） | 35 | + AbuseIPDB（74万+16万条）、匿名IP全量（190万条） |
| 不指定 | 35 | 使用全部标签源 |

### tools/merge\_ip\_files.py — IP 文件合并/去重/验证

```bash
python tools/merge_ip_files.py ips.txt                                 # 单文件去重+验证
python tools/merge_ip_files.py file1.txt file2.txt file3.txt           # 多文件合并去重
python tools/merge_ip_files.py file1.txt file2.txt -o merged.txt       # 合并并输出到文件
python tools/merge_ip_files.py ips.txt --show-invalid                  # 显示被排除的无效IP
python tools/merge_ip_files.py base.txt source1.txt source2.txt -a     # 追加模式
```

支持 IPv4 和 IPv6 格式验证。单文件时执行去重和验证，多文件时合并后去重验证。追加模式将来源文件中不重复的有效IP追加到目标文件。

### tools/config\_tool.py — .env 配置管理工具

```bash
python tools/config_tool.py list                                       # 列出所有配置项
python tools/config_tool.py get IP_STORAGE_DIR                         # 获取配置值
python tools/config_tool.py set IP_STORAGE_DIR data/202604             # 设置配置值
python tools/config_tool.py delete IP_STORAGE_DIR                      # 删除配置项
python tools/config_tool.py bulk-set IP_STORAGE_DIR=data IP_STORAGE_NAME=ip_data  # 批量设置
```

所有配置项必须以 `IP_` 为前缀。

### tools/progress\_tool.py — 进度文件管理工具

```bash
# 从 JSON 数据生成 progress 文件（将已有渠道数据的 IP 标记为已完成）
python tools/progress_tool.py generate data/ip_data.json --channel fofa_host
python tools/progress_tool.py generate data/ip_data.json --channel fofa_host -o custom.progress

# 从 progress 文件中删除指定 IP（用于重新查询特定 IP）
python tools/progress_tool.py remove data/ip_data.fofa_host.progress 1.2.3.4 5.6.7.8
python tools/progress_tool.py remove data/ip_data.fofa_host.progress --from-file ips.txt
```

### tools/status\_tool.py — 任务状态查询工具

查看流水线或批量查询任务的运行状态、进度和预计剩余时间（ETA）。

```bash
python tools/status_tool.py trace_ip              # 查看溯源流水线状态
python tools/status_tool.py ip_domain_lookup      # 查看IP域名反查状态
python tools/status_tool.py batch                 # 查看批量查询状态
python tools/status_tool.py cleanup trace_ip      # 清理残留 PID 文件
python tools/status_tool.py cleanup ip_domain_lookup
python tools/status_tool.py cleanup batch
```

**状态说明：**

| 状态 | 含义 |
|------|------|
| 🟢 运行中 | 任务正在执行，心跳正常 |
| ⏳ 疑似卡死 | 进程存在但心跳超过 120 秒未更新 |
| ⚠️ 异常终止 | PID 文件存在但进程已不存在，可断点续跑 |
| ⬜ 未运行 | 任务未启动或已完成 |

**AI 异步执行模式：** 长时间任务建议用 `blocking=false` 启动，通过 `status_tool.py` 定期查看进度，任务完成后再继续后续操作。

### tools/verify\_ip\_domain.py — IP-域名映射验证

验证 IP 反查到的域名是否仍然解析到原始 IP（检测域名是否已过期或重新映射）。

```bash
python tools/verify_ip_domain.py <JSON数据文件> [选项]
```

**参数：**

| 参数              | 说明                                     |
| --------------- | -------------------------------------- |
| `data_file`     | JSON 数据文件路径（必填）                        |
| `--channel`     | 验证渠道：`aizhan`、`chinaz`、`all`（默认 `all`） |
| `--concurrency` | 并发线程数（默认 10）                           |
| `--timeout`     | DNS 解析超时秒数（默认 3）                       |
| `--dry-run`     | 仅输出验证结果，不写回 JSON 文件                    |
| `--show-all`    | 显示所有域名验证结果（默认只显示变更/无法解析）               |

**示例：**

```bash
python tools/verify_ip_domain.py data/ip_data.json
python tools/verify_ip_domain.py data/ip_data.json --dry-run --show-all
python tools/verify_ip_domain.py data/ip_data.json --channel aizhan --concurrency 20
```

**验证结果状态：**

- `matched` — 域名仍解析到原始 IP ✅
- `changed` — 域名已解析到其他 IP 🔄
- `unresolved` — DNS 解析失败（域名可能已过期）❌

验证结果会写入 JSON 文件中每个 IP 条目的 `domain_verify` 字段。

### tools/ai\_analysis.py — AI 研判辅助工具

从溯源IP数据中筛选待 AI 研判的 IP（按分类过滤：other/cloud_provider/residential），批量输出供人工或 AI 分析。研判结果通过 `writer.py add <IP> ai_analysis key=value ...` 写入，Word 报告中会自动展示 AI 研判结果章节。

```bash
python tools/ai_analysis.py batch                                       # 批量读取待研判IP数据
python tools/ai_analysis.py batch --size 20 --offset 10                 # 指定批量大小和偏移量
python tools/ai_analysis.py batch --categories other,cloud_provider     # 按分类筛选
python tools/ai_analysis.py count                                       # 统计待研判IP数量
```

**参数说明：**

| 参数 | 说明 |
| --- | --- |
| `--size` | 每批读取数量（默认 10） |
| `--offset` | 偏移量（默认 0） |
| `--categories` | 筛选分类，逗号分隔（默认 other,cloud_provider,residential） |

## 配置管理

所有配置集中在 `config.py`，使用 Pydantic Settings 管理，从 `.env` 文件读取：

| Settings 类               | 管理的配置项                                                                                                                       |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `BaseIPSettings`         | `storage_dir`、`storage_name`、`ip_domain_lookup_project_name`、`trace_ip_project_name`                                         |
| `FofaSettings`           | `fofa_api_key`、`fofa_query_delay`                                                                                            |
| `IpinfoSettings`         | `ipinfo_access_token`、`ipinfo_query_delay`                                                                                   |
| `AizhanSettings`         | `aizhan_cookie`、`aizhan_query_delay`                                                                                         |
| `ChinazSettings`         | `chinaz_cookie`、`chinaz_query_delay`                                                                                         |
| `RdnsSettings`           | `rdns_query_timeout`、`rdns_query_delay`                                                                                      |
| `WhoisSettings`          | `whois_query_timeout`、`whois_query_delay`                                                                                    |
| `ZoomeyeSettings`        | `zoomeye_api_key`、`zoomeye_query_delay`                                                                                      |
| `SslCertSettings`        | `ssl_cert_port`、`ssl_cert_timeout`、`ssl_cert_query_delay`                                                                    |
| `IPDomainLookupSettings` | `rdns_ptr_enabled`、`aizhan_enabled`、`chinaz_enabled`、`zoomeye_enabled`、`fofa_search_enabled`、`ssl_cert_enabled`              |
| `TraceIPSettings`        | `phase1_ipinfo_enabled`、`phase1_rdns_ptr_enabled`、`phase3_aizhan_enabled`、`phase3_chinaz_enabled`、`phase3_fofa_host_enabled`、`phase3_dns_verify_enabled`、`dns_verify_timeout`、`dns_verify_concurrency` |
| `IpTaggerSettings`       | `ip_tagger_config_dir` |

