# IP Info Manager - 项目上下文

## 项目定位

IP Info Manager 是一个命令行 IP 情报管理工具，用于批量采集、存储、查询和导出 IP 地址的多维度情报信息。面向安全分析师，支撑攻击 IP 溯源、威胁情报匹配、域名反查等安全运营场景。

## 技术栈

| 层面 | 技术 | 版本/说明 |
|------|------|----------|
| 语言 | Python | 3.11+ |
| 配置管理 | Pydantic Settings | ≥2.0.0，`IP_` 前缀环境变量 |
| 数据存储 | JSON 文件 | 无数据库，按 IP + 渠道组织 |
| HTTP 请求 | requests | ≥2.28.0 |
| HTML 解析 | beautifulsoup4 | ≥4.12.0（爱站/站长之家） |
| IP 信息查询 | ipinfo | ≥5.0.0 |
| 报告生成 | python-docx + openpyxl | 可选依赖 |
| 端口扫描 | nmap（外部） | 需独立安装 |
| 测试框架 | pytest | ≥7.4.0 |

## 核心领域概念

| 术语 | 定义 | 代码体现 |
|------|------|---------|
| **Channel（渠道）** | 一个数据采集源，对应一个 API 或爬虫 | `channel/*.py`，每个文件一个渠道 |
| **IP Record** | 一个 IP 的完整情报记录，包含多个渠道数据 | JSON 中以 IP 为 key，渠道名为子 key |
| **Scenario（场景）** | 一条自动化流水线，串联多个阶段 | `scenarios/trace_ip/`、`scenarios/ip_domain_lookup/` |
| **Phase（阶段）** | 流水线中的一个处理步骤 | `pipeline.py` 中的 `_phase{N}_*` 方法 |
| **Progress（进度）** | 断点续查机制，记录已完成 IP | `progress.py`，`.progress` 文件 |
| **Classification（分类）** | 根据 IP 属性自动归类 | `classifier.py`，7 个类别 |
| **Tag（标签）** | 基于威胁情报的 IP 威胁标记 | `tools/ip_tagger.py`，35 个情报源 |
| **Priority（优先级）** | 溯源优先级分级 P1-P4 | `excel_exporter.py` 中 `_trace_priority()` |

## 目录结构与职责

```
ip_info_manager/
├── config.py                    # 配置中心（Pydantic Settings 多配置类）
├── writer.py                    # IP 数据写入（IPWriter 类）
├── reader.py                    # IP 数据读取 + CLI（IPReader 类）
├── exporter.py                  # Excel 导出（IPExcelExporter 类）
│
├── channel/                     # 数据采集渠道层
│   ├── _template.py             # 渠道开发模板（5 部分结构）
│   ├── fofa_host.py             # Fofa Host 聚合查询
│   ├── fofa_search.py           # Fofa 搜索查询
│   ├── ipinfo_api.py            # IPInfo API / 免 API 模式
│   ├── rdns_ptr.py              # RDNS 反向解析（无凭证）
│   ├── whois_query.py           # Whois 查询
│   ├── aizhan.py                # 爱站 IP 反查域名（Cookie）
│   ├── chinaz.py                # 站长之家 IP 反查域名
│   ├── zoomeye.py               # ZoomEye 网络空间测绘
│   ├── ssl_cert.py              # SSL 证书域名提取（无凭证）
│   └── port_scan.py             # 端口扫描（nmap）
│
├── scripts/                     # 批量查询脚本层
│   ├── _template.py             # 批量脚本模板
│   └── batch_*.py               # 10 个批量脚本（与 channel 一一对应）
│
├── scenarios/
│   ├── trace_ip/                # 溯源 IP 流水线（7 阶段）
│   │   ├── __main__.py          # CLI 入口（argparse）
│   │   ├── trace_ip.py          # CLI 解析 + 启动
│   │   ├── pipeline.py          # TraceIPPipeline 核心类（~1180 行）
│   │   ├── classifier.py        # IP 自动分类器
│   │   ├── classifiers/         # 分类规则（builtin + custom JSON）
│   │   ├── progress.py          # ProgressManager + BatchIPWriter
│   │   ├── reporter.py          # 文本/Word 报告生成
│   │   └── excel_exporter.py    # Excel 报告生成
│   └── ip_domain_lookup/        # IP 域名反查流水线（4 阶段）
│       ├── __main__.py          # CLI 入口
│       ├── ip_domain_lookup.py  # CLI 解析
│       ├── pipeline.py          # 流水线核心
│       ├── dns_validator.py     # DNS 验证逻辑
│       ├── progress.py          # 进度管理
│       └── reporter.py          # 报告生成
│
├── tools/                       # 辅助工具集
│   ├── config_tool.py           # 环境变量管理 CLI
│   ├── ip_tagger.py             # IP 威胁标签打标
│   ├── ip_tagger_updater.py     # 标签源自动更新
│   ├── docx_builder.py          # Word 报告公共引擎
│   ├── status_tool.py           # 任务状态查询
│   ├── progress_tool.py         # 进度文件管理
│   ├── merge_ip_files.py        # IP 文件合并去重
│   ├── verify_ip_domain.py      # IP-域名映射验证
│   └── ai_analysis.py           # AI 研判辅助
│
├── utils/                       # 通用工具模块
│   ├── logger_utils.py          # 日志（RotatingFileHandler，10MB/3份）
│   ├── dns_verify.py            # DNS 正向验证底层
│   ├── ip_utils.py              # IP 格式验证/标准化
│   ├── file_utils.py            # 文件读写工具
│   └── pid_manager.py           # PID 文件管理（心跳检测）
│
├── config/                      # 静态配置
│   ├── ip_tagger/               # 35 个威胁情报源文件
│   └── port_scan/               # 端口列表（top100/top1000）
│
├── data/                        # 数据存储根目录（运行时生成）
├── tests/                       # 测试目录
├── references/                  # AI Agent 操作手册
└── docs/                        # 设计文档
```

## 数据流

```
IP 列表文件 (.txt)
    │
    ▼
┌───────────────────────────────────────────────────────┐
│  Scenario Pipeline（溯源/域名反查）                     │
│                                                       │
│  Phase 1: 基础采集 ──→ Channel.fetch_channel()        │
│       │                    │                          │
│       │                    ▼                          │
│       │              IPWriter.add_or_update_ip()      │
│       │                    │                          │
│       │                    ▼                          │
│       │              {IP}.json (JSON 文件存储)         │
│       │                                               │
│  Phase 2: 分类过滤 ──→ IPClassifier.classify()         │
│  Phase 3: 深度查询 ──→ Channel.fetch_channel() × N    │
│  Phase 4: DNS 验证 ──→ dns_verify.batch_verify()      │
│  Phase 5: 端口扫描 ──→ port_scan.fetch_channel()      │
│  Phase 6: 汇总    ──→ Reporter.generate_summary()     │
│  Phase 7: 报告    ──→ Reporter + ExcelExporter         │
└───────────────────────────────────────────────────────┘
```

## 配置体系

所有配置通过 `config.py` 管理，使用 Pydantic Settings 的 `BaseSettings`：

- 环境变量前缀：`IP_`
- 存储文件：`.env`
- 管理工具：`tools/config_tool.py`（禁止直接编辑 .env）
- 配置类继承链：`BaseIPSettings` → 各渠道/场景 Settings

```
BaseIPSettings（存储路径、项目名）
  ├── Settings（通用）
  ├── FofaSettings（API Key + 超时 + 延迟）
  ├── IpinfoSettings（Token + 超时 + 延迟）
  ├── AizhanSettings（Cookie + 超时 + 延迟）
  ├── ChinazSettings（Cookie + 超时 + 延迟）
  ├── WhoisSettings（超时 + 延迟）
  ├── RdnsSettings（超时 + 延迟）
  ├── ZoomeyeSettings（API Key + 超时 + 延迟）
  ├── SslCertSettings（端口 + 超时 + 延迟）
  ├── TraceIPSettings（7 阶段渠道开关 + 端口扫描配置）
  ├── IPDomainLookupSettings（6 渠道开关）
  └── IpTaggerSettings（配置目录）
```

## 渠道开发模式

每个渠道遵循 `_template.py` 定义的 5 部分结构：

1. **validate_channel_key()** — 凭证有效性校验
2. **request_channel()** — 网络请求（仅请求，不解析）
3. **parse_response()** — 响应解析（仅解析，不请求）
4. **fetch_channel()** — 数据采集入口（组合 request + parse + delay）
5. **main()** — CLI 入口（读取配置 → fetch → 写入）

调用链：`apply_delay(delay)` → `request_channel()` → `parse_response()` → `format_output()`

## 关键设计决策

1. **JSON 文件存储而非数据库** — 简单、可移植、无需额外服务
2. **渠道模板模式** — 统一接口，新渠道按模板开发
3. **断点续查** — 每完成一个 IP 立即保存进度，支持中断恢复
4. **渠道级进度** — 不仅跟踪阶段进度，还跟踪每个渠道的完成情况
5. **Pydantic Settings 配置管理** — 类型安全 + 验证 + 环境变量
6. **BatchIPWriter 上下文管理器** — 批量写入减少 IO，异常安全

## 当前测试状况

| 模块 | 测试文件 | 覆盖范围 |
|------|---------|---------|
| progress.py | `tests/test_progress.py` | ProgressManager 渠道级进度（17 个测试用例） |
| 其他所有模块 | 无 | ❌ 零覆盖 |

**已有测试覆盖的行为：**
- record(ip, phase, channel) 创建渠道进度文件
- record(ip, phase, channel) 同时写入阶段进度
- record(ip, phase) 仅写入阶段进度
- load_completed(phase, channels) 取渠道交集
- 向后兼容（无渠道文件时退化为阶段级）
- clear_from() 同时清理渠道级文件
- 多 IP 多渠道场景

## 已知问题（来自 code-coverage-audit.md）

- references 文档与代码存在 66 处不一致
- trace-ip-pipeline.md 阶段划分严重错误（文档 5 阶段 vs 代码 7 阶段）
- .env.example 配置变量名与 config.py 不一致
- 多个 references 文档缺失重要参数和功能描述

## 编码约定

- 所有命令必须在项目根目录 `ip_info_manager/` 下执行
- 配置变更必须通过 `tools/config_tool.py`，禁止直接编辑 `.env`
- 渠道名作为 JSON 中 IP 记录的子 key
- 值类型自动推断：`true/false` → bool，纯数字 → int，含小数点 → float
- 日志文件：`data/logs/{channel_name}.log`，自动轮转 10MB × 3
- 测试文件命名：`test_*.py`
- 进度文件命名：`{prefix}.trace_phase{N}.progress`、`{prefix}.trace_phase{N}.{channel}.progress`
