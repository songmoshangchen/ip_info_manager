---
name: ip-info-manager
description: IP 信息管理工具，用于批量采集、存储、查询和导出 IP 地址的多维度情报信息。当用户需要查询 IP 信息、批量处理 IP 列表、导出 IP 数据到 Excel、比较 IP 文件、对 IP 进行情报分析（Fofa/IPInfo/RDNS/Whois/爱站/站长之家）、管理 IP 数据库、溯源IP处理、IP自动分类、攻击IP分析时使用此 skill。即使用户只是提到 "IP 查询"、"IP 信息"、"攻击 IP"、"威胁情报"、"IP 归属"、"IP 反查"、"批量查 IP"、"IP 导出"、"IP 反查域名"、"域名绑定"、"溯源"、"IP 分类"、"云主机识别"、"扫描器识别" 等关键词，也应触发此 skill。
---

# IP Info Manager — IP 信息管理 Skill

本 skill 封装了一套完整的 IP 信息管理工作流，帮助 AI 助手高效地完成 IP 情报采集、数据管理和导出任务。

## 核心能力

1. **单条/批量写入 IP 数据** — 通过 `writer.py` 添加、更新、删除 IP 及其渠道数据
2. **多维度查询 IP 数据** — 通过 `reader.py` 按 IP、渠道、字段等条件检索
3. **多渠道情报采集** — Fofa、IPInfo（API/免 API）、RDNS PTR、Whois、爱站（域名反查）、站长之家（域名反查）
4. **Excel 导出** — 通过 `exporter.py` 将查询结果导出为格式化的 Excel 文件
5. **IP 列表处理** — 验证、去重、比较 IP 文件
6. **溯源IP处理流水线** — 通过 `scenarios/trace_ip.py` 自动采集、分类、深度查询，支持规则自定义和断点续跑

## 项目结构

```
ip_info_manager/
├── .env                        # API Key 等环境变量
├── .env.example                # 环境变量模板
├── writer.py                   # IP 数据写入器
├── reader.py                   # IP 数据读取器（含 Excel 导出入口）
├── exporter.py                 # Excel 导出引擎
├── writer_example.py           # 写入器使用示例
├── channel/                    # 数据采集渠道
│   ├── fofa.py                 # Fofa API 查询（需 IP_FOFA_API_KEY）
│   ├── ipinfo_api.py           # IPInfo SDK 查询（需 IP_IPINFO_ACCESS_TOKEN）
│   ├── ipinfo_noapi.py         # IPInfo 免 API 查询
│   ├── rdns_ptr.py             # RDNS PTR 反向解析
│   ├── whois_query.py          # Whois 查询（需 python-whois）
│   ├── aizhan.py               # 爱站网 IP 反查域名（需 IP_AIZHAN_COOKIE）
│   └── chinaz.py               # 站长之家 IP 反查域名（需 IP_CHINAZ_COOKIE）
├── scripts/                    # 批量查询脚本
│   ├── batch_fofa.py           # 批量 Fofa 查询
│   ├── batch_ipinfo_api.py     # 批量 IPInfo 查询
│   ├── batch_rdns_ptr.py       # 批量 RDNS（单线程）
│   ├── batch_rdns_ptr_concurrent.py  # 批量 RDNS（多线程）
│   ├── batch_whois.py          # 批量 Whois 查询
│   ├── batch_aizhan.py         # 批量爱站网查询
│   └── batch_chinaz.py         # 批量站长之家查询
├── scenarios/                  # 场景工作流
│   ├── trace_ip.py             # 溯源IP处理流水线
│   └── classifiers/            # 分类规则
│       ├── builtin_rules.json  # 内置分类规则（稳定）
│       └── custom_rules.json   # 外部分类规则（试运行/离散）
├── tools/                      # 辅助工具
│   ├── compare_ip_files.py     # IP 文件比较
│   ├── process_ip_list.py      # IP 列表处理（验证/去重）
│   └── verify_ip_domain.py     # IP-域名映射验证
├── data/                       # 数据存储目录
│   ├── ip_data.json            # 主数据文件（由 IP_STORAGE_NAME 命名）
│   ├── ip_data.unclassified_rdns  # 未识别RDNS记录
│   └── ip_data.trace_report       # 溯源报告
└── README.md                   # 详细文档
```

## 数据存储格式

所有 IP 数据存储在 `data/ip_data.json`，每个 IP 下包含 `ip` 字段和若干渠道数据：

```json
{
  "1.2.3.4": {
    "ip": "1.2.3.4",
    "fofa": { "country_name": "...", "org": "..." },
    "ipinfo_api": { "country": "...", "as_name": "..." },
    "rdns_ptr": { "has_ptr": true, "hostname": "..." },
    "whois": { "has_whois": true, "whois_data": { ... } },
    "aizhan": {
      "success": true,
      "location": "中国广东广州",
      "isp": "电信",
      "domain_count": 5,
      "domains": [{"domain": "example.com", "title": "示例网站"}]
    },
    "chinaz": {
      "success": true,
      "location": "广东省广州市",
      "isp": "电信",
      "domains": [{"domain": "example.com", "start_time": "2024-01-01", "end_time": "2026-01-01"}]
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
python reader.py get-channel "1.2.3.4" fofa
```

**列出所有 IP（支持分页和过滤）：**

```bash
python reader.py list                                    # 基础列表
python reader.py list --detail                           # 显示详细信息
python reader.py list --start 10 --end 50                # 分页
python reader.py list --include-channel fofa              # 仅含 fofa 渠道
python reader.py list --exclude-channel kimi              # 排除含 kimi 渠道
python reader.py list --detail --include-channel fofa --output result.txt  # 导出到文本文件
```

**导出为 Excel：**

```bash
python reader.py list --export-excel output.xlsx
python reader.py list --include-channel fofa ipinfo_api --export-excel output.xlsx
python reader.py list --exclude-channel kimi --export-excel output.xlsx
```

**搜索 IP：**

```bash
python reader.py search fofa                             # 含 fofa 渠道的所有 IP
python reader.py search fofa --key country_name --value "China"  # 按字段值搜索
```

### 三、单条渠道查询

各渠道脚本可单独运行查询单个 IP，结果自动写入数据库：

```bash
python channel/fofa.py "1.2.3.4"             # Fofa（需 API Key）
python channel/ipinfo_api.py "1.2.3.4"       # IPInfo API（需 Token）
python channel/ipinfo_noapi.py "1.2.3.4"     # IPInfo 免 API
python channel/rdns_ptr.py "1.2.3.4"         # RDNS 反向解析
python channel/whois_query.py "1.2.3.4"      # Whois 查询
python channel/aizhan.py "1.2.3.4"           # 爱站网 IP 反查域名（需 Cookie）
python channel/chinaz.py "1.2.3.4"           # 站长之家 IP 反查域名（需 Cookie）
```

### 四、批量查询

批量脚本从 IP 文件（每行一个 IP）读取并逐个查询，支持断点续查。

```bash
python scripts/batch_fofa.py ips.txt                    # 批量 Fofa
python scripts/batch_ipinfo_api.py ips.txt              # 批量 IPInfo
python scripts/batch_rdns_ptr.py ips.txt                # 批量 RDNS（单线程）
python scripts/batch_rdns_ptr_concurrent.py ips.txt 20  # 批量 RDNS（20 线程）
python scripts/batch_whois.py ips.txt                   # 批量 Whois
python scripts/batch_aizhan.py ips.txt                  # 批量爱站网 IP 反查域名
python scripts/batch_chinaz.py ips.txt                  # 批量站长之家 IP 反查域名
```

**断点续查**：进度保存在 `文件名.渠道名.progress` 文件中。中断后重新运行会自动跳过已处理的 IP。如需重新查询，删除 `.progress` 文件即可。

### 五、辅助工具

**IP 文件比较：**

```bash
python tools/compare_ip_files.py old_ips.txt new_ips.txt
```

输出两个文件中重复的 IP 和只在第二个文件中的新增 IP。

**IP 列表处理（验证和去重）：**

```bash
python tools/process_ip_list.py ips.txt                 # 统计信息
python tools/process_ip_list.py ips.txt --show-valid    # 显示有效 IP
python tools/process_ip_list.py ips.txt --show-invalid  # 显示无效 IP
python tools/process_ip_list.py ips.txt --show-all      # 显示全部
```

支持 IPv4 和 IPv6 格式验证。

## 环境变量

在 `.env` 文件中配置，所有变量以 `IP_` 为前缀：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `IP_STORAGE_DIR` | 否 | `data` | 数据存储目录 |
| `IP_STORAGE_NAME` | 否 | `ip_data` | 存储名称（用于数据文件命名前缀，修改后所有输出文件名同步变更） |
| `IP_FOFA_API_KEY` | Fofa 查询时 | — | Fofa API Key |
| `IP_IPINFO_ACCESS_TOKEN` | IPInfo API 查询时 | — | IPInfo Access Token |
| `IP_AIZHAN_COOKIE` | 爱站查询时 | — | 爱站网 Cookie（浏览器登录后获取） |
| `IP_CHINAZ_COOKIE` | 否 | 空 | 站长之家 Cookie（可选，有 Cookie 可查更多信息） |
| `IP_FOFA_QUERY_DELAY` | 否 | `1.1` | Fofa 查询间隔（秒） |
| `IP_IPINFO_QUERY_DELAY` | 否 | `1.1` | IPInfo 查询间隔（秒） |
| `IP_AIZHAN_QUERY_DELAY` | 否 | `2` | 爱站查询间隔（秒） |
| `IP_CHINAZ_QUERY_DELAY` | 否 | `2` | 站长之家查询间隔（秒） |

## 典型工作流

### 工作流 1：批量采集新 IP 情报

用户给出一批 IP 地址文件，需要采集多渠道情报：

1. 用 `tools/process_ip_list.py` 验证和去重 IP 列表
2. 用 `scripts/batch_ipinfo_api.py` 批量查询 IP 基本信息
3. 用 `scripts/batch_fofa.py` 批量查询端口和服务信息
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
python scenarios/trace_ip.py ips.txt                       # 完整流水线
python scenarios/trace_ip.py ips.txt --no-deep-query       # 只采集+分类，不深度查询
python scenarios/trace_ip.py ips.txt --from-phase 2         # 从阶段2开始（跳过已完成的阶段1）
python scenarios/trace_ip.py ips.txt --only-phase 2         # 只执行分类阶段
python scenarios/trace_ip.py ips.txt --no-custom-rules      # 不加载外部规则
python scenarios/trace_ip.py ips.txt --custom-rules my_rules.json  # 使用指定规则文件
```

**流水线阶段：**

| 阶段 | 说明 | 输出 |
|------|------|------|
| Phase 1 | 基础情报采集（IPInfo + RDNS） | 数据写入 ip_data.json |
| Phase 2 | 自动分类过滤 | trace_classify 渠道 + `{prefix}.trace_filtered_ips` + `{prefix}.unclassified_rdns` |
| Phase 3 | 深度查询（爱站 + 站长 + Fofa） | 数据写入 `{prefix}.json` |
| Phase 4 | 汇总报告 | `{prefix}.trace_report` |

**分类类别：**

| 类别 | 说明 | 是否深度查询 |
|------|------|-------------|
| cloud_provider | 云服务商（AWS/阿里云/腾讯云等） | ✅ |
| cdn | CDN/WAF 节点 | ❌ |
| crawler_scanner | 爬虫/扫描器 | ❌ |
| residential | 家用宽带 | ✅ |
| other | 未识别（需人工确认） | ✅ |

**分类规则管理：**

- 内置规则：`scenarios/classifiers/builtin_rules.json`（稳定，勿随意修改）
- 外部规则：`scenarios/classifiers/custom_rules.json`（试运行，验证后合并到内置）
- 未识别的 RDNS 记录输出到 `data/{prefix}.unclassified_rdns`，可据此补充规则（`{prefix}` 由 `IP_STORAGE_NAME` 决定）

**规则文件格式：**

```json
{
  "category_key": {
    "label": "显示名称",
    "description": "类别说明",
    "need_deep_query": true,
    "patterns": [
      { "field": "rdns_ptr.hostname", "match": ".amazonaws.com", "type": "suffix" },
      { "field": "ipinfo_api.as_name", "match": "Amazon", "type": "contains" }
    ]
  }
}
```

匹配类型：`suffix`（后缀）、`contains`（包含）、`prefix`（前缀）、`exact`（精确）

**断点续跑**：每个阶段完成后写入标记文件（`{prefix}.trace_phase1_done` 等），使用 `--from-phase` 跳过已完成阶段。标记文件名由 `IP_STORAGE_NAME` 决定，不同批次互不干扰。

## 注意事项

- 批量查询前先用 `process_ip_list.py` 验证 IP 格式，避免浪费 API 调用
- Fofa 和 IPInfo API 有速率限制，不要将查询间隔设得太短
- 爱站和站长之家通过爬虫抓取页面，Cookie 会过期，需要定期更新 `.env` 中的 Cookie 值
- 爱站和站长之家建议查询间隔不低于 2 秒，过快可能被封 IP
- 数据存储为 JSON 文件，并发写入可能导致数据丢失，批量脚本已内置串行写入
- 渠道数据结构由各采集脚本决定，不同渠道的字段名可能不同
- 读取 `README.md` 可获取更详细的文档信息
