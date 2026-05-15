---
name: ip-info-manager
description: >
  IP 信息管理工具，用于批量采集、存储、查询和导出 IP 地址的多维度情报信息。
  当用户需要查询 IP 信息、批量处理 IP 列表、导出 IP 数据到 Excel、对 IP 进行情报分析
  （Fofa/IPInfo/RDNS/Whois/爱站/站长之家/ZoomEye/SSL证书）、管理 IP 数据库、
  溯源IP处理、IP自动分类、攻击IP分析、IP域名反查、域名DNS验证、溯源优先级分级、
  攻击IP排序、IP标签打标、威胁情报匹配、IP信誉查询、排除已溯源IP、端口扫描时使用此 skill。
  即使用户只是提到 "IP 查询"、"IP 信息"、"攻击 IP"、"威胁情报"、"IP 归属"、"IP 反查"、
  "批量查 IP"、"IP 导出"、"IP 反查域名"、"域名绑定"、"溯源"、"IP 分类"、"云主机识别"、
  "扫描器识别"、"溯源优先级"、"攻击排序"、"IP标签"、"标签打标"、"IP信誉"、"威胁情报匹配"、
  "排除已溯源"、"排除IP"、"端口扫描"、"nmap" 等关键词，也应触发此 skill。
---

# IP Info Manager

本 skill 封装了一套完整的 IP 信息管理工作流。遇到用户请求时，根据下方功能路由表读取对应的 references/ 文件获取详细操作步骤。

**核心原则：所有操作都应通过项目提供的工具（writer.py / reader.py / config_tool.py 等）完成，不要直接编辑 .env 文件，不要修改源代码。**

## 功能路由表

根据用户的意图，读取对应的 references/ 文件获取决策树和完整命令：

| 用户意图 | 参考文档 | 关键工具 |
|---------|---------|---------|
| 首次安装、环境搭建、依赖安装、凭证配置 | references/setup.md | tools/config_tool.py |
| 查看、添加、删除、搜索、导出 IP 数据 | references/data-management.md | writer.py, reader.py, exporter.py |
| 查询单个 IP 的渠道情报（Fofa/IPInfo/RDNS 等） | references/channel-query.md | channel/*.py |
| 批量查询一批 IP（某个渠道） | references/batch-query.md | scripts/batch_*.py |
| 溯源 IP 自动化处理（采集→标签打标→分类→深度查询→DNS域名验证→端口扫描→报告→AI研判） | references/trace-ip-pipeline.md | scenarios/trace_ip/ |
| IP 域名反查 + DNS 正向验证 | references/ip-domain-lookup-pipeline.md | scenarios/ip_domain_lookup/ |
| IP 文件合并/去重、进度管理、域名验证、AI研判 | references/tools.md | tools/*.py |
| 查看任务运行状态、进度、ETA | references/tools.md | tools/status_tool.py |
| 更新 API Key / Cookie、调整查询间隔 | references/config.md | tools/config_tool.py |
| IP 标签打标、威胁情报匹配、标签源更新 | references/ip-tagger.md | tools/ip_tagger.py |
| 采集异常、凭证失效、限频报错 | references/troubleshooting.md | — |

## 项目结构

```
ip_info_manager/
├── .env / .env.example       # 环境变量（通过 config_tool.py 管理）
├── config.py                 # 配置管理（Pydantic Settings）
├── writer.py                 # IP 数据写入
├── reader.py                 # IP 数据读取（含 Excel 导出）
├── exporter.py               # Excel 导出器
├── channel/                  # 10 个数据采集渠道
├── scripts/                  # 10 个批量查询脚本
├── scenarios/trace_ip/       # 溯源 IP 流水线（7 阶段）
├── scenarios/ip_domain_lookup/ # IP 域名反查流水线（4 阶段）
├── tools/                    # 辅助工具集
├── utils/                    # 通用工具模块
├── config/                   # 静态配置（IP标签源、端口列表）
├── data/                     # 数据存储根目录
└── references/               # 操作手册（AI Agent 参考文档）
```

## 数据存储路径

**所有命令必须在项目根目录 `ip_info_manager/` 下执行**，否则会找不到模块。AI 启动命令时务必设置 `cwd` 为项目根目录。

- **channel/batch 通用数据**：`data/{IP_STORAGE_DIR}/{IP_STORAGE_NAME}.json`（`IP_STORAGE_DIR` 为空时直接存储在 `data/` 下）
- **溯源 IP 场景数据**：`data/trace_ip/{IP_TRACE_IP_PROJECT_NAME}/`
- **IP 域名反查数据**：`data/ip_domain_lookup/{IP_IP_DOMAIN_LOOKUP_PROJECT_NAME}/`

## 渠道速查表

所有渠道查询命令在项目根目录下执行，查询结果自动写入数据库。

| 渠道 | 单条查询命令 | 凭证需求 | 批量查询命令 |
|------|-------------|---------|-------------|
| Fofa Host 聚合 | `python channel/fofa_host.py "<IP>"` | IP_FOFA_API_KEY | `python scripts/batch_fofa_host.py ips.txt` |
| Fofa 搜索 | `python channel/fofa_search.py "<IP>"` | IP_FOFA_API_KEY | `python scripts/batch_fofa_search.py ips.txt` |
| IPInfo | `python channel/ipinfo_api.py "<IP>"` | Token 可选 | `python scripts/batch_ipinfo_api.py ips.txt [--no-api]` |
| RDNS PTR | `python channel/rdns_ptr.py "<IP>"` | 无 | `python scripts/batch_rdns_ptr.py ips.txt` |
| RDNS 多线程 | — | 无 | `python scripts/batch_rdns_ptr_concurrent.py ips.txt --workers 20` |
| Whois | `python channel/whois_query.py "<IP>"` | 需 python-whois | `python scripts/batch_whois.py ips.txt` |
| 爱站 | `python channel/aizhan.py "<IP>"` | IP_AIZHAN_COOKIE | `python scripts/batch_aizhan.py ips.txt` |
| 站长之家 | `python channel/chinaz.py "<IP>"` | Cookie 可选 | `python scripts/batch_chinaz.py ips.txt` |
| ZoomEye | `python channel/zoomeye.py "<IP>"` | IP_ZOOMEYE_API_KEY | `python scripts/batch_zoomeye.py ips.txt` |
| SSL 证书 | `python channel/ssl_cert.py "<IP>"` | 无（需 openssl） | `python scripts/batch_ssl_cert.py ips.txt` |
| 端口扫描 | `python channel/port_scan.py "<IP>"` | 需 nmap | — |

## 快捷命令

流水线支持语义化参数别名，比 `--only-phase N` 更直观：

| 快捷命令 | 等同于 | 说明 |
|---------|--------|------|
| `--collect-only` | `--only-phase 1` | 只执行基础采集 |
| `--classify-only` | `--only-phase 2` | 只执行分类过滤（仅溯源流水线） |
| `--deep-query-only` | `--only-phase 3` | 只执行深度查询（仅溯源流水线） |
| `--dns-verify-only` | `--only-phase 4` | 只执行DNS域名验证（仅溯源流水线） |
| `--port-scan-only` | `--only-phase 5` | 只执行端口扫描（仅溯源流水线） |
| `--summary-only` | `--only-phase 6` | 只执行汇总输出 |
| `--generate-report` | `--only-phase 7` | 只生成报告（Word + Excel） |

## 溯源 IP 处理流水线

### 运行命令

```bash
python -m scenarios.trace_ip ips.txt                       # 默认执行 Phase 1-5
python -m scenarios.trace_ip ips.txt --collect-only         # 只执行基础采集
python -m scenarios.trace_ip ips.txt --generate-report      # 只生成报告
python -m scenarios.trace_ip ips.txt --from-phase 3         # 从阶段3开始
python -m scenarios.trace_ip ips.txt --port-scan-only       # 只执行端口扫描
python -m scenarios.trace_ip ips.txt --exclude-ips traced.txt --generate-report
python -m scenarios.trace_ip ips.txt --no-tagger            # 跳过 IP 标签打标
python -m scenarios.trace_ip ips.txt --tagger-level 1       # 快速标签（21源）
python -m scenarios.trace_ip ips.txt --channel-timeout 30   # 单渠道超时30秒
python -m scenarios.trace_ip ips.txt --port-scan-concurrency 5   # 临时设置端口扫描并发5
# Phase 6-7 需单独触发
```

### 流水线阶段

| 阶段 | 说明 | 输出 |
|------|------|------|
| Phase 1 | 基础情报采集（IPInfo + RDNS，并行） | 数据写入 JSON |
| Phase 2 | IP标签打标 + 自动分类过滤 | `trace_classify` + `.trace_filtered_ips` |
| Phase 3 | 深度查询（爱站+站长+Fofa Host，并行） | 数据写入 JSON |
| Phase 4 | DNS 域名正向验证 | `domain_verify` 字段 |
| Phase 5 | 端口扫描（nmap，默认关闭） | `port_scan` 渠道 |
| Phase 6 | 汇总报告 | `.trace_report` |
| Phase 7 | Word + Excel 报告（P1-P4 分级） | `.docx` + `.xlsx` |

默认执行 Phase 1-5（采集→标签→分类→深度查询→DNS验证→端口扫描）。Phase 6（汇总）和 Phase 7（报告）需通过 `--summary-only` / `--generate-report` 单独触发。

### Excel 报告

Phase 7 生成 Excel（`.trace_report.xlsx`），P1-P4 四个 sheet，统一 **13 列**：IP、国家、ASN/组织、分类、分类说明、建议溯源路径、域名数、反查域名列表、端口数、开放端口列表、实时扫描端口数、实时开放端口列表、标签。

### Word 报告

Phase 7 生成 Word 报告，**6 个章节**：一、报告概述；二、处理概览；三、溯源优先级；四、端口扫描结果；五、AI研判结果；六、未识别RDNS记录。

### 断点续跑

Phase 1/3/4/5 完成后写入进度文件 `{prefix}.trace_phase{N}.progress`（Phase 2/6/7 无进度文件，因为是全量一次性操作）。使用 `--from-phase N` 跳过已完成阶段。支持 Ctrl+C 安全中断，自动保存进度。

### 溯源优先级决策树

| 级别 | 判定条件 | 溯源路径建议 |
|------|---------|------------|
| P1 核心溯源 | 有反查域名 + 国内IP | ICP备案查询域名持有者实名信息 |
| P2 重点溯源 | 有反查域名（国外），或无域名但有端口（国内） | WHOIS查询；排查端口服务泄露信息 |
| P3 辅助溯源 | 无域名但有端口（国外），或仅国内IP | 端口服务辅助分析；公开信息检索 |
| P4 暂缓 | 无域名、无端口、国外IP | 信息不足，建议持续监控 |

### IP 分类类别

| 类别 | 说明 | 是否深度查询 |
|------|------|-------------|
| cloud_provider | 云服务商 | ✅ |
| cdn | CDN/WAF 节点 | ❌ |
| crawler_scanner | 爬虫/扫描器 | ❌ |
| residential | 家用宽带 | ✅ |
| invalid_rdns | 无效RDNS（纯IP格式主机名） | ❌ |
| excluded_domain | 排除域名 | ❌ |
| other | 未识别（需人工确认） | ✅ |

### 分类规则匹配类型

5 种匹配类型：`suffix`（后缀）、`contains`（包含）、`prefix`（前缀）、`exact`（精确）、`regex`（正则表达式）。

### 排除已溯源 IP

报告生成时可通过 `--exclude-ips` 排除已溯源 IP，使报告聚焦于剩余待溯源 IP。仅在 Phase 7 生效。

```bash
python -m scenarios.trace_ip ips.txt --generate-report --exclude-ips traced_ips.txt
```

排除后报告所有统计重新计算，概述中明确显示排除信息。详见 references/trace-ip-pipeline.md。

## Phase 5 端口扫描（可选增强）

端口扫描使用 **nmap** 对目标IP进行实时端口探测，**默认关闭**，需显式启用。

### 启用配置

```bash
python tools/config_tool.py set IP_TRACE_IP_PHASE5_PORT_SCAN_ENABLED true
python tools/config_tool.py set IP_TRACE_IP_PORT_SCAN_NMAP_PATH "E:\01Tools\NMAP\nmap.exe"
python tools/config_tool.py set IP_TRACE_IP_PORT_SCAN_TIMEOUT 120
python tools/config_tool.py set IP_TRACE_IP_PORT_SCAN_CONCURRENCY 1
```

### 使用方式

```bash
python -m scenarios.trace_ip ips.txt --port-scan-only      # 只运行端口扫描
python -m scenarios.trace_ip ips.txt                        # 完整流水线（包含端口扫描）
python -m scenarios.trace_ip ips.txt --from-phase 5         # 断点续跑
```

### 扫描范围

1. **历史端口验证** — 扫描 Fofa/ZoomEye 返回的历史端口，验证当前是否仍开放
2. **Top 1000 端口** — 扫描最常见的 1000 个端口
3. **合并扫描** — 两者合并去重后一次性扫描

### 输出数据

端口扫描结果写入 `port_scan` 渠道字段，包含 `open_ports`（开放端口列表含服务指纹）、`historical_ports_verified`（仍开放的历史端口）、`historical_ports_closed`（已关闭的历史端口）、`open_count`、`total_scanned`。

并发数通过 `IP_TRACE_IP_PORT_SCAN_CONCURRENCY` 控制，默认 1（串行）。

### 注意事项

- 端口扫描耗时较长（每IP约60-120秒），建议先用 `--only-phase 5` 测试少量IP
- 逐 IP 写入：每完成一个 IP 立即保存数据和进度，中断仅损失当前正在扫描的 IP
- 需预先安装 nmap，Windows 上需要 TCP Connect（`-sT`），速度比 Linux SYN 扫描慢

## IP 域名反查流水线

批量收集域名并进行 DNS 正向验证：

```bash
python -m scenarios.ip_domain_lookup ips.txt                       # 完整流水线
python -m scenarios.ip_domain_lookup ips.txt --only-phase 1         # 只执行域名收集
python -m scenarios.ip_domain_lookup ips.txt --generate-report      # 只生成报告
python -m scenarios.ip_domain_lookup ips.txt --dns-timeout 5        # DNS超时5秒
python -m scenarios.ip_domain_lookup ips.txt --dns-concurrency 20   # DNS并发20线程
```

| 阶段 | 说明 | 使用渠道 |
|------|------|---------|
| Phase 1 | 域名收集 | RDNS + 爱站 + 站长 + ZoomEye + Fofa Search + SSL（并行） |
| Phase 2 | DNS 正向验证 | 验证域名是否仍解析到原 IP |
| Phase 3 | 汇总报告 | `.domain_lookup_report` + `.domain_lookup_matched` |
| Phase 4 | Word 报告 | `.domain_lookup_report.docx` |

DNS 验证结果状态：`matched`（✅ 仍指向原IP）、`changed`（🔄 指向其他IP）、`unresolved`（❌ 解析失败）、`timeout`、`error`。

## AI 异步执行模式

长时间任务（溯源流水线、域名反查、批量查询）执行时间可能很长，AI 应使用异步模式管理：

### 推荐流程

1. **启动任务**：用 `blocking=false` 启动命令，不等待完成
2. **查看进度**：用 `python tools/status_tool.py trace_ip` 查看运行状态、进度和 ETA
3. **等待完成**：根据 ETA 定期查看状态，直到任务完成
4. **继续操作**：任务完成后继续后续步骤

### 状态查询命令

```bash
python tools/status_tool.py trace_ip              # 溯源流水线
python tools/status_tool.py ip_domain_lookup      # 域名反查
python tools/status_tool.py batch                 # 批量查询
python tools/status_tool.py cleanup trace_ip      # 清理残留 PID
```

### 状态说明

| 状态 | 含义 |
|------|------|
| 🟢 运行中 | 任务正在执行，心跳正常 |
| ⏳ 疑似卡死 | 进程存在但心跳超过 120 秒未更新 |
| ⚠️ 异常终止 | PID 文件存在但进程已不存在，可断点续跑 |
| ⬜ 未运行 | 任务未启动或已完成 |

## IP 域名验证（独立工具）

在以下情况下建议运行域名验证：

1. **月度报告生成前**：更新域名验证状态，提高报告时效性
2. **历史数据复核**：对过往 IP 数据进行定期验证，追踪威胁变化
3. **高价值 IP 研判**：对 P1/P2 级 IP 的域名进行重点验证

```bash
python tools/verify_ip_domain.py data/trace_ip/202605/202605.json                # 验证并写回
python tools/verify_ip_domain.py data/trace_ip/202605/202605.json --dry-run      # 仅预览
python tools/verify_ip_domain.py data/trace_ip/202605/202605.json --channel aizhan --concurrency 20
```

验证结果写入 JSON 的 `domain_verify` 字段，溯源报告中会自动纳入验证状态。

## AI 研判流程

流水线完成后，对分类为 `other`、`cloud_provider`、`residential` 的 IP 可进行 AI 研判：

```bash
python tools/ai_analysis.py count                                    # 查看待研判数量
python tools/ai_analysis.py batch --size 20                          # 批量获取数据
python tools/ai_analysis.py batch --categories other,cloud_provider  # 按分类筛选

# 分析后写入研判结果
python writer.py add "<IP>" ai_analysis severity="高" action="保留" note="疑似攻击者VPS"

# 重新生成报告
python -m scenarios.trace_ip ips.txt --only-phase 7
```

研判结果会自动展示在 Word 报告的 AI 研判章节中。

## IP 标签打标

基于本地威胁情报文件批量匹配 IP 标签，纯本地计算，无网络请求。流水线 Phase 2 中自动调用。

```bash
python tools/ip_tagger.py data/ips.txt                    # 累加模式（默认）
python tools/ip_tagger.py data/ips.txt --level 1          # 快速模式（21 源，~1s）
python tools/ip_tagger.py data/ips.txt --level 2          # 正常模式（31 源，~2s）
python tools/ip_tagger.py data/ips.txt --mode overwrite   # 覆盖模式
python tools/ip_tagger_updater.py --from-git              # 更新标签源（推荐每月）
```

标签级别：`1`（快速21源）、`2`（正常31源）、`3`（全量35源）。详见 references/ip-tagger.md。

## 渠道配置

可通过环境变量控制各阶段渠道的启用/禁用。通过 `config_tool.py` 设置：

```bash
python tools/config_tool.py set IP_TRACE_IP_PHASE3_FOFA_HOST_ENABLED false  # 禁用 Fofa Host
python tools/config_tool.py set IP_TRACE_IP_PHASE4_DNS_VERIFY_ENABLED true  # Phase 4 DNS 域名验证
python tools/config_tool.py set IP_TRACE_IP_PHASE5_PORT_SCAN_ENABLED true   # 启用端口扫描
python tools/config_tool.py set IP_TRACE_IP_DNS_VERIFY_CONCURRENCY 20       # DNS 20线程
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_ZOOMEYE_ENABLED false    # 禁用 ZoomEye
```

运行流水线时会显示每个渠道的启用/禁用状态。完整配置项见 references/config.md。
