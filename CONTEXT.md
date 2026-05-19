# IP Info Manager - 项目上下文

## 项目定位

IP Info Manager 是一个命令行 IP 情报管理工具，用于批量采集、存储、查询和导出 IP 地址的多维度情报信息。面向安全分析师，支撑攻击 IP 溯源、威胁情报匹配、域名反查等安全运营场景。

## 技术栈

| 层面 | 技术 | 版本/说明 |
|------|------|----------|
| 语言 | Python | 3.12+ |
| 配置管理 | Pydantic Settings V2 | `model_config = SettingsConfigDict(...)` |
| 数据存储 | JSON 文件 | 无数据库，按 IP + 渠道组织 |
| HTTP 请求 | requests | ≥2.28.0 |
| HTML 解析 | beautifulsoup4 | ≥4.12.0（爱站/站长之家） |
| IP 信息查询 | ipinfo | ≥5.0.0 |
| 报告生成 | python-docx + openpyxl | 可选依赖 |
| 端口扫描 | nmap（外部） | 需独立安装 |
| 测试框架 | pytest | ≥7.4.0，需加 `-p no:dash` |

## 核心领域概念

| 术语 | 定义 | 代码体现 |
|------|------|---------|
| **Channel（渠道）** | 一个数据采集源，对应一个 API 或爬虫 | `channel/*.py`，每个文件一个渠道 |
| **ChannelProtocol** | 渠道的结构化接口（`channel_name` + `validate()` + `fetch()`） | `protocols.py`，`@runtime_checkable` |
| **ChannelRegistry** | 渠道注册表，统一管理渠道的注册/查找/验证/查询 | `protocols.py`，`create_default_registry()` 工厂函数 |
| **IP Record** | 一个 IP 的完整情报记录，包含多个渠道数据 | JSON 中以 IP 为 key，渠道名为子 key |
| **Scenario（场景）** | 一条自动化流水线，串联多个阶段 | `scenarios/trace_ip/`、`scenarios/ip_domain_lookup/` |
| **Phase（阶段）** | 流水线中的一个处理步骤 | `pipeline.py` 中的 `_phase{N}_*` 方法 |
| **PhaseRunner** | 通用阶段循环骨架（进度检测 → 查询 → 写入） | `phase_runner.py` |
| **Progress（进度）** | 断点续查机制，记录已完成 IP | `progress.py`，`.progress` 文件，支持渠道级 |
| **Classification（分类）** | 根据 IP 属性自动归类 | `classifier.py`，7 个类别 |
| **Tag（标签）** | 基于威胁情报的 IP 威胁标记 | `tools/ip_tagger.py`，35 个情报源 |
| **Priority（优先级）** | 溯源优先级分级 P1-P4 | `trace_utils.py` 中 `trace_priority()` |
| **BaseBatchQuery** | 批量查询基类，提取通用 validate/PID/ETA/统计循环 | `scripts/base_batch.py` |

## 目录结构与职责

```
ip_info_manager/
├── config.py                    # 配置中心（Pydantic V2 SettingsConfigDict）
├── writer.py                    # IP 数据写入（IPWriter 类，满足 IPDataWriter Protocol）
├── reader.py                    # IP 数据读取 + CLI（IPReader 类，满足 IPDataReader Protocol）
├── exporter.py                  # Excel 导出（IPExcelExporter 类）
│
├── protocols.py                 # Protocol 定义 + 测试替身 + ChannelRegistry
│   ├── IPDataWriter             # 写入 Protocol（add_or_update_ip / delete_ip / delete_channel）
│   ├── IPDataReader             # 读取 Protocol（get_ip_data / get_channel_data / list_* / search_*）
│   ├── ChannelFetcher           # 旧版 Protocol（deprecated，仅 __call__）
│   ├── ChannelProtocol          # 完整版 Protocol（channel_name + validate + fetch）
│   ├── InMemoryIPReader         # 纯内存读取替身
│   ├── InMemoryIPWriter         # 纯内存写入+读取替身
│   ├── InMemoryChannel          # 纯内存渠道替身
│   ├── ChannelRegistry          # 渠道注册表（register/get/list_names/validate_all/fetch）
│   └── create_default_registry  # 工厂函数，注册 10 个内置渠道
│
├── channel/                     # 数据采集渠道层
│   ├── base.py                  # 公共工具函数（apply_delay + format_output）
│   ├── _template.py             # 渠道开发模板（5 部分结构）
│   ├── fofa_host.py             # FofaHostChannel 适配器 + fetch_channel
│   ├── fofa_search.py           # FofaSearchChannel 适配器 + fetch_channel
│   ├── ipinfo_api.py            # IpinfoApiChannel 适配器 + fetch_channel
│   ├── rdns_ptr.py              # RdnsPtrChannel 适配器 + fetch_channel
│   ├── whois_query.py           # WhoisChannel 适配器 + fetch_channel
│   ├── aizhan.py                # AizhanChannel 适配器 + fetch_channel
│   ├── chinaz.py                # ChinazChannel 适配器 + fetch_channel
│   ├── zoomeye.py               # ZoomeyeChannel 适配器 + fetch_channel
│   ├── ssl_cert.py              # SslCertChannel 适配器 + fetch_channel
│   └── port_scan.py             # PortScanChannel 适配器 + fetch_channel（特殊 validate）
│
├── scripts/                     # 批量查询脚本层
│   ├── base_batch.py            # BaseBatchQuery ABC（run() + _query_ip/_print_result/_get_delay）
│   ├── _template.py             # 批量脚本模板
│   ├── batch_fofa_host.py       # BatchFofaHostQuery（继承 BaseBatchQuery）
│   ├── batch_fofa_search.py     # BatchFofaSearchQuery
│   ├── batch_aizhan.py          # BatchAizhanQuery
│   ├── batch_chinaz.py          # BatchChinazQuery
│   ├── batch_zoomeye.py         # BatchZoomeyeQuery
│   ├── batch_rdns_ptr.py        # BatchRDNSQuery
│   ├── batch_whois.py           # BatchWhoisQuery
│   ├── batch_ssl_cert.py        # BatchSslCertQuery
│   ├── batch_ipinfo_api.py      # BatchIPInfoQuery
│   ├── batch_rdns_ptr_concurrent.py  # 并发版 RDNS（未迁移到 BaseBatchQuery）
│   └── batch_port_scan.py       # 端口扫描（未迁移）
│
├── scenarios/
│   ├── trace_ip/                # 溯源 IP 流水线（7 阶段）
│   │   ├── __main__.py          # CLI 入口（argparse）
│   │   ├── trace_ip.py          # CLI 解析 + 启动
│   │   ├── pipeline.py          # TraceIPPipeline（已迁移到 ChannelRegistry）
│   │   ├── phase_runner.py      # PhaseRunner 通用循环
│   │   ├── trace_utils.py       # 共享领域逻辑（9 个函数）
│   │   ├── classifier.py        # IP 自动分类器
│   │   ├── classifiers/         # 分类规则（builtin + custom JSON）
│   │   ├── progress.py          # ProgressManager + BatchIPWriter
│   │   ├── reporter.py          # 文本/Word 报告生成
│   │   └── excel_exporter.py    # Excel 报告生成
│   └── ip_domain_lookup/        # IP 域名反查流水线（4 阶段）
│       ├── __main__.py          # CLI 入口
│       ├── ip_domain_lookup.py  # CLI 解析
│       ├── pipeline.py          # 流水线核心（已迁移到 ChannelRegistry）
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
├── tests/                       # 测试目录（261 个测试，13 个文件）
├── references/                  # AI Agent 操作手册
└── docs/                        # 设计文档
    ├── adr/                     # 架构决策记录
    │   ├── 001-006              # 早期决策（存储/模板/流水线/配置/断点/分类）
    │   ├── 007-channel-protocol.md    # ChannelProtocol 架构决策
    │   ├── 008-channel-registry.md    # ChannelRegistry 架构决策
    │   └── 009-batch-run-extraction.md # BaseBatchQuery.run() 提取决策
    ├── architecture-analysis.md       # 架构分析报告
    └── issues/                        # Pipeline 拆分 issues
```

## 架构模式

### Protocol 系统

项目使用 Python `Protocol`（结构化子类型）定义接口，`@runtime_checkable` 支持运行时 `isinstance()` 检查：

```
IPDataWriter          IPDataReader          ChannelProtocol
├── add_or_update_ip  ├── get_ip_data       ├── channel_name: str
├── delete_ip         ├── get_channel_data  ├── validate() -> bool
└── delete_channel    ├── list_all_ips      └── fetch(ip, **kwargs) -> dict
                      ├── list_ip_channels
                      └── search_ips_by_channel
```

### 渠道适配器模式

每个渠道模块底部添加适配器类，统一实现 `ChannelProtocol`：

```python
class XxxChannel:
    channel_name = 'xxx'
    def validate(self) -> bool:
        try:
            validate_channel_key()
            return True
        except (SystemExit, Exception):
            return False
    def fetch(self, ip: str, **kwargs) -> dict:
        return fetch_channel(ip, **kwargs)
```

特殊：`PortScanChannel.validate()` 使用 `validate_engine()` 而非 `validate_channel_key()`。

### ChannelRegistry 模式

```python
reg = create_default_registry()   # 注册 10 个内置渠道
ch = reg.get('fofa_host')         # 按名查找
ch.validate()                      # 验证凭证
ch.fetch(ip, key=...)             # 查询数据
reg.validate_all()                 # 批量验证
reg.fetch('rdns_ptr', ip)         # 直接通过 registry 查询
```

### BaseBatchQuery 模式

批量脚本继承 `BaseBatchQuery`，只需实现 3 个抽象方法 + 1 个可选钩子：

```python
class BatchXxxQuery(BaseBatchQuery):
    channel_name = 'xxx'
    def _do_validate(self): ...        # 可选，验证钩子
    def _query_ip(self, ip): ...       # 必须实现
    def _print_result(self, ip, data): ...  # 必须实现
    def _get_delay(self): ...          # 可选，默认从 settings 读取
```

`run()` 方法封装了完整循环：validate → PID → 遍历 pending_ips → 查询 → 写入 → 进度 → ETA → 心跳 → 统计 → KeyboardInterrupt 处理。

## 数据流

```
IP 列表文件 (.txt)
    │
    ▼
┌───────────────────────────────────────────────────────┐
│  Scenario Pipeline（溯源/域名反查）                     │
│                                                       │
│  ChannelRegistry.get('xxx').fetch(ip, **kwargs)       │
│       │                                               │
│       ▼                                               │
│  IPWriter.add_or_update_ip()                          │
│       │                                               │
│       ▼                                               │
│  {IP}.json (JSON 文件存储)                             │
│                                                       │
│  Phase 1: 基础采集 (ipinfo_api + rdns_ptr)            │
│  Phase 2: 分类过滤 ──→ IPClassifier.classify()         │
│  Phase 3: 深度查询 (aizhan/chinaz/fofa_host)          │
│  Phase 4: DNS 验证 ──→ dns_verify.batch_verify()      │
│  Phase 5: 端口扫描 ──→ port_scan                      │
│  Phase 6: 汇总    ──→ Reporter.generate_summary()     │
│  Phase 7: 报告    ──→ Reporter + ExcelExporter         │
└───────────────────────────────────────────────────────┘
```

## 配置体系

所有配置通过 `config.py` 管理，已迁移到 Pydantic V2：

```python
class BaseIPSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='IP_',
        env_file=ENV_FILE,
        extra='ignore',
    )
```

配置类继承链（共 11 个 Settings 类）：

```
BaseIPSettings（model_config = SettingsConfigDict(...)）
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

每个渠道遵循 `_template.py` 定义的 5 部分结构 + 底部适配器类：

1. **validate_channel_key()** — 凭证有效性校验
2. **request_channel()** — 网络请求（仅请求，不解析）
3. **parse_response()** — 响应解析（仅解析，不请求）
4. **fetch_channel()** — 数据采集入口（组合 request + parse + delay）
5. **XxxChannel 适配器类** — 实现 ChannelProtocol（validate + fetch）
6. **main()** — CLI 入口（读取配置 → fetch → 写入）

调用链：`apply_delay(delay)` → `request_channel()` → `parse_response()` → `format_output()`

## 当前测试状况

运行命令：`python -m pytest tests/ -v -p no:dash`

**总计：13 个测试文件，261 个测试用例，全部通过。**

| 测试文件 | 覆盖模块 | 测试数 | Mock 策略 |
|---------|---------|--------|----------|
| `test_progress.py` | `scenarios/trace_ip/progress.py` | 11 | 无 mock，真实文件 I/O |
| `test_in_memory_writer.py` | `protocols.py` (InMemoryIPWriter) | 9 | 无 mock，测试替身自身 |
| `test_in_memory_reader.py` | `protocols.py` (InMemoryIPReader) | 17 | 无 mock，测试替身自身 |
| `test_protocol_conformance.py` | `writer.py` + `reader.py` | 8 | 无 mock，Protocol 兼容性 |
| `test_channel_base.py` | `channel/base.py` + ChannelFetcher | 10 | 无 mock，真实函数调用 |
| `test_channel_protocol.py` | ChannelProtocol + 3 适配器 | 36 | `patch` mock validate/fetch |
| `test_channel_registry.py` | ChannelRegistry + 7 适配器 | 46 | `patch` mock validate/fetch |
| `test_batch_run.py` | BaseBatchQuery.run() + 9 迁移 | 36 | Dummy 替身 |
| `test_trace_utils.py` | `scenarios/trace_ip/trace_utils.py` | 26 | 无 mock，纯函数 |
| `test_phase_runner.py` | `scenarios/trace_ip/phase_runner.py` | 10 | InMemoryIPWriter |
| `test_base_batch.py` | `scripts/base_batch.py` | 14 | 内联子类替身 |
| `test_config.py` | `config.py` Pydantic V2 | 25 | monkeypatch + `_env_file=None` |
| `test_pipeline_registry.py` | ChannelRegistry + Pipeline 模式 | 8 | InMemoryChannel |

测试文档：
- `tests/doc/TESTING.md` — 测试索引 + TDD 路线图
- `tests/doc/MOCK_INVENTORY.md` — Mock 清单 + 排查指南

## 重构完成情况

按执行顺序 `③ → ④/⑦ → ⑤ → ① → ② → ⑥`：

| 编号 | 重构项 | 状态 | 说明 |
|------|--------|------|------|
| ③ | IPWriter/Reader Protocol | ✅ 完成 | IPDataWriter + IPDataReader Protocol，InMemory 替身 |
| ④ | Channel Protocol | ✅ 完成 | ChannelProtocol + 10 个适配器 + InMemoryChannel |
| ⑦ | Channel 公共函数提取 | ✅ 完成 | channel/base.py（apply_delay + format_output） |
| ⑤ | Reporter 领域逻辑分离 | ✅ 完成 | trace_utils.py（9 个共享函数）+ PhaseRunner |
| ① | Pipeline 拆分 | ✅ 完成 | ChannelRegistry 替代硬编码导入，PhaseRunner 创建 |
| ② | 批量脚本去重 | ✅ 完成 | BaseBatchQuery.run() + 9/10 脚本迁移 |
| ⑥ | 渠道注册表 | ✅ 完成 | ChannelRegistry + create_default_registry() |
| — | Pydantic V2 迁移 | ✅ 完成 | `class Config` → `model_config = SettingsConfigDict(...)` |
| — | Pipeline ChannelRegistry 迁移 | ✅ 完成 | 2 个 Pipeline 文件使用 registry |

### 可选改进（未执行）

- `batch_rdns_ptr_concurrent.py` 迁移（需设计 ConcurrentBaseBatchQuery）
- `ChannelFetcher` Protocol 清理（标记为 deprecated）
- rdns_ptr `has_ptr_count` 统计恢复
- dateutil DeprecationWarning（第三方库问题）
- Pipeline `_query_channels_parallel` 提取到共享模块

## 关键设计决策

1. **JSON 文件存储而非数据库** — 简单、可移植、无需额外服务（ADR-001）
2. **渠道模板模式** — 统一接口，新渠道按模板开发（ADR-002）
3. **多阶段流水线** — 7 阶段溯源流程（ADR-003）
4. **Pydantic V2 SettingsConfigDict** — 类型安全 + 验证 + 环境变量（ADR-004）
5. **断点续查** — 每完成一个 IP 立即保存进度（ADR-005）
6. **IP 自动分类** — 7 类分类 + 自定义规则（ADR-006）
7. **ChannelProtocol** — 结构化子类型 + runtime_checkable（ADR-007）
8. **ChannelRegistry** — 集中管理渠道注册/查找/验证（ADR-008）
9. **BaseBatchQuery.run()** — 提取通用批量查询循环（ADR-009）

## 已知问题

- references 文档与代码存在 66 处不一致
- trace-ip-pipeline.md 阶段划分严重错误（文档 5 阶段 vs 代码 7 阶段）
- .env.example 配置变量名与 config.py 不一致
- 多个 references 文档缺失重要参数和功能描述
- `batch_rdns_ptr_concurrent.py` 和 `batch_port_scan.py` 未迁移到 BaseBatchQuery
- `ChannelFetcher` Protocol 标记为 deprecated 但未清理

## 编码约定

- 所有命令必须在项目根目录 `ip_info_manager/` 下执行
- 配置变更必须通过 `tools/config_tool.py`，禁止直接编辑 `.env`
- 渠道名作为 JSON 中 IP 记录的子 key
- 值类型自动推断：`true/false` → bool，纯数字 → int，含小数点 → float
- 日志文件：`data/logs/{channel_name}.log`，自动轮转 10MB × 3
- 测试文件命名：`test_*.py`
- 进度文件命名：`{prefix}.trace_phase{N}.progress`、`{prefix}.trace_phase{N}.{channel}.progress`
- 测试替身放在 `protocols.py`（InMemory*），内联替身放在测试文件内
- 渠道适配器 validate() 捕获 `(SystemExit, Exception)` 返回 bool，不 sys.exit
- 测试运行：`python -m pytest tests/ -v -p no:dash`
