# IP Info Manager — 架构审查 + 测试质量审计报告

> 生成时间: 2026-05-26

---

## 一、架构审查报告

### 1.1 发现的架构摩擦点

| # | 问题 | 涉及文件 | 严重度 |
|---|------|----------|--------|
| 1 | **编排逻辑泄漏到脚本层** — Phase 初始化、渠道创建、IP 过滤等编排逻辑全部在 `run_pipeline.py` 中，而非框架层。如果需要另一种编排方式（如只运行 Phase 3），必须重写脚本 | `scripts/run_pipeline.py` | 高 |
| 2 | **Phase 之间数据传递无统一上下文** — 每个 Phase 独立持有 `writer/reader`，Phase 间的数据流转依赖 JSON 文件作为中间存储，缺少内存中的上下文对象 | `phases/phase*.py` | 高 |
| 3 | **`_try_channel()` 模式硬编码** — 渠道初始化逻辑在 `run_pipeline.py` 中用 if-elif 硬编码，新增渠道必须修改脚本 | `scripts/run_pipeline.py:25-38` | 中 |
| 4 | **filter_ips 与 Phase 耦合不清晰** — `filter_ips_by_classification` 和 `filter_dynamic_ips` 在 Phase 2 和 Phase 3 之间被调用，但它们不属于任何 Phase，是游离的编排逻辑 | `pipeline/filter_ips.py`, `run_pipeline.py` | 中 |
| 5 | **DeepQueryPhase 的渠道回退逻辑** — `aizhan_ch or chinaz_ch` 这种回退在 Phase 构造时决定，但回退策略应该在渠道注册层而非 Phase 层 | `run_pipeline.py:154-156` | 低 |

### 1.2 改进建议

1. **引入 PipelineContext** — 将 writer/reader/progress_tracker/domain_cache 等共享资源封装为上下文对象，Phase 之间通过上下文传递数据
2. **引入 PipelineBuilder** — 将 `run_pipeline.py` 中的编排逻辑收回到框架层，提供声明式的 Phase 配置方式
3. **渠道注册表自动发现** — 用注册表模式替代 `_try_channel()` 的硬编码

---

## 二、测试质量审计报告

### 2.1 模块评级

| 模块 | 文件数 | 评级 | 主要问题 |
|------|--------|------|----------|
| channel/ | 14 | **A** | Mock 使用规范，外部 API 全部 mock，覆盖全面 |
| store/ | 12 | **B+** | 覆盖全面，但 `test_json_threadsafe` 检查了 `_lock` 内部属性 |
| batch/ | 4 | **A-** | 使用 Fake 替身，较好；少量 `writes` 列表检查 |
| pipeline/ | 4 | **C+** | **严重依赖 mock 调用次数/参数**，缺乏结果导向验证 |
| processors/ | 8 | **B** | `dns_runner` 部分检查 mock 调用次数；`classifier_engine` 测试了私有方法 |
| utils/ | 6 | **A** | 纯函数测试，结果导向，质量好 |
| integration/ | 2 | **D** | 无 mock、`test_dns_verify_only` 无断言、不可靠 |

### 2.2 关键问题

#### 问题 1：结果导向不足（pipeline 模块最严重）

`test_phases.py` 大量验证内部调用细节而非最终结果：

| 测试方法 | 问题代码 | 应改为 |
|----------|----------|--------|
| `test_normal_execution` | `mock_run.call_count == 3` | 验证 writer 中写入了 3 个渠道的数据 |
| `test_partial_channel_disabled` | `mock_run.call_count == 2` | 验证 writer 中只有 2 个渠道的数据 |
| `test_delay_auto_passed` | `call.kwargs["delay"] == 2.0` | 验证数据被正确写入（delay 是内部传递细节） |
| `test_progress_tracker_passed` | `call.kwargs["progress_tracker"] is tracker` | 验证进度被正确记录 |
| `test_skip_ips_excludes_from_all_channels` | 检查 `call.kwargs["ips"]` | 验证 writer 中不包含 skip_ips 的数据 |
| `TestClassifyTagPhase.test_normal_execution` | `MockClassifier.assert_called_once_with(...)` | 验证 writer 中有 classifier 和 tagger 数据 |

#### 问题 2：集成测试覆盖缺口

| 缺失场景 | 说明 | 优先级 |
|----------|------|--------|
| Phase 间数据流转 | Phase1→2→filter→3→4 的完整数据传递 | P0 |
| 溯源 IP 拼接 | 域名采集→域从提取→DNS验证端到端链路 | P0 |
| 分类过滤链 | Phase2 分类→filter_ips→Phase3 输入 | P1 |
| 断点续传 | 中途中断→恢复运行 | P1 |
| 动态 IP 跳过 | 分类→skip_ips→Phase3/4 行为验证 | P1 |

#### 问题 3：测试边界越界

| 文件 | 越界内容 | 应改为 |
|------|----------|--------|
| `test_classifier_engine.py` | 直接测试 `_extract_field`、`_match_pattern` 私有方法 | 通过 `classify()` 公开接口间接覆盖 |
| `test_json_threadsafe.py` | 检查 `_lock` 内部属性 | 验证并发写入后数据完整 |
| `test_progress_tracker.py` | 检查 `_db_path` 私有属性 | 通过公开行为验证 |
| `test_dns_runner.py` | 检查 `_max_age_days`、`_force_days` 私有属性 | 通过 `run()` 结果验证过期逻辑 |

#### 问题 4：集成测试不可靠

- `test_phase_full_run.py` — **完全没有 mock**，直接使用真实渠道，依赖外部服务可用性
- `test_dns_verify_only.py` — **无 pytest 断言**，只有 print 输出，不算自动化测试

---

## 三、测试全景图

### 3.1 测试层级与模块分布

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          IP Info Manager 测试全景图                               │
│                        843 单元测试 | 2 集成测试(脚本式)                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        集成测试 (Integration)                           │    │
│  │  ┌──────────────────────┐  ┌──────────────────────────────────────┐    │    │
│  │  │ test_phase_full_run  │  │ test_dns_verify_only                 │    │    │
│  │  │ Phase1→2→3→4 全流程  │  │ DNS验证全流程                        │    │    │
│  │  │ ⚠ 无mock,不可靠      │  │ ⚠ 无断言,手动脚本                    │    │    │
│  │  └──────────────────────┘  └──────────────────────────────────────┘    │    │
│  │                                                                         │    │
│  │  ❌ 缺失: Phase间数据流转 | 溯源IP拼接 | 场景导向测试                    │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                          单元测试 (Unit)                                │    │
│  │                                                                         │    │
│  │  ┌─── Pipeline 层 ─────────────────────────────────────────────────┐   │    │
│  │  │ test_filter_ips   [A]  filter_dynamic_ips / filter_by_class    │   │    │
│  │  │ test_phase        [A]  Phase协议 / PhaseResult                  │   │    │
│  │  │ test_phases       [C+] Phase1-4 run() ⚠ mock调用次数/参数       │   │    │
│  │  │ test_pipeline     [A]  Pipeline注册/运行/跳过                    │   │    │
│  │  └─────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                         │    │
│  │  ┌─── Channel 层 ──────────────────────────────────────────────────┐   │    │
│  │  │ test_adapter      [A]  BaseChannelAdapter 协议/validate/fetch   │   │    │
│  │  │ test_aizhan       [A]  爱站渠道 (mock requests.get)             │   │    │
│  │  │ test_chinaz       [A]  站长之家渠道 (mock requests.get)          │   │    │
│  │  │ test_fofa_host    [A]  FOFA主机渠道 (mock requests.get)         │   │    │
│  │  │ test_fofa_search  [A]  FOFA搜索渠道 (mock requests.get)         │   │    │
│  │  │ test_ipinfo_api   [A]  IPInfo API渠道 (mock requests.get)       │   │    │
│  │  │ test_ipinfo_free  [A]  IPInfo免费渠道 (mock requests.get)       │   │    │
│  │  │ test_port_scan    [A]  Nmap扫描渠道 (mock PortScanner)          │   │    │
│  │  │ test_rdns_ptr     [A]  RDNS反解渠道 (mock socket)              │   │    │
│  │  │ test_ssl_cert     [A]  SSL证书渠道 (mock _get_ssl_cert_text)   │   │    │
│  │  │ test_whois_query  [A]  WHOIS查询渠道 (mock whois)              │   │    │
│  │  │ test_config       [A]  11个Config类 (monkeypatch env)           │   │    │
│  │  │ test_registry     [A]  ChannelRegistry 注册/查找/验证           │   │    │
│  │  │ test_protocols    [A]  ChannelProtocol 协议检查                  │   │    │
│  │  │ test_errors       [A]  ChannelError 异常层次                     │   │    │
│  │  │ test_in_memory    [A]  InMemoryChannel 测试替身                  │   │    │
│  │  └─────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                         │    │
│  │  ┌─── Processors 层 ───────────────────────────────────────────────┐   │    │
│  │  │ test_classifier_engine  [B]  IPClassifier ⚠ 测试了私有方法       │   │    │
│  │  │ test_classifier_rules   [A]  load_rules 规则加载                 │   │    │
│  │  │ test_classifier_runner  [A]  BatchClassifier 批量分类            │   │    │
│  │  │ test_dns_extractor      [A]  extract_domain_mappings 域名提取   │   │    │
│  │  │ test_dns_runner         [B]  BatchDnsVerify ⚠ mock调用次数      │   │    │
│  │  │ test_dns_verifier       [A]  resolve/verify/batch_verify        │   │    │
│  │  │ test_matcher            [A]  IP范围匹配                          │   │    │
│  │  │ test_manifest           [A]  标签清单加载/验证                    │   │    │
│  │  │ test_runner             [A]  BatchTagger 批量打标                │   │    │
│  │  └─────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                         │    │
│  │  ┌─── Batch 层 ────────────────────────────────────────────────────┐   │    │
│  │  │ test_concurrent   [A-] run_concurrent (Fake替身)                │   │    │
│  │  │ test_query        [A-] BaseBatchQuery (Fake替身)                │   │    │
│  │  │ test_progress     [A]  ProgressTracker 进度跟踪                  │   │    │
│  │  └─────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                         │    │
│  │  ┌─── Store 层 ────────────────────────────────────────────────────┐   │    │
│  │  │ test_in_memory_reader  [A]  InMemoryIPReader 全接口             │   │    │
│  │  │ test_in_memory_writer  [A]  InMemoryIPWriter 全接口             │   │    │
│  │  │ test_json_reader       [A]  IPReader JSON文件读取               │   │    │
│  │  │ test_json_writer       [A]  IPWriter JSON文件写入               │   │    │
│  │  │ test_json_threadsafe   [B+] IPWriter线程安全 ⚠ 检查_lock       │   │    │
│  │  │ test_sqlite_cache      [A]  SqliteDomainCache                   │   │    │
│  │  │ test_progress_tracker  [A]  进度跟踪器工厂/功能                  │   │    │
│  │  │ test_protocols         [A]  存储协议检查                         │   │    │
│  │  │ test_batch_query       [A]  批量查询                             │   │    │
│  │  │ test_edge_cases        [A]  边界情况                             │   │    │
│  │  │ test_read_write_cons   [A]  读写一致性                           │   │    │
│  │  │ test_protocol_conf     [A]  协议一致性                           │   │    │
│  │  └─────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                         │    │
│  │  ┌─── Utils 层 ────────────────────────────────────────────────────┐   │    │
│  │  │ test_load_ips         [A]  IP列表加载/去重/校验                  │   │    │
│  │  │ test_cache_converter  [A]  进度/域名缓存转换与清理               │   │    │
│  │  │ test_query_status     [A]  进度查询/格式化                       │   │    │
│  │  │ test_quick_query      [A]  快速查询参数解析                      │   │    │
│  │  │ test_sqlite_progress  [A]  SQLite进度跟踪器                      │   │    │
│  │  │ test_verify_mapping   [A]  IP-域名映射验证                       │   │    │
│  │  └─────────────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 测试边界与数据流图

```
                    ┌─────────────────────────────────────────────┐
                    │            外部依赖边界 (Mock 线)             │
                    │  requests.get | socket | nmap | whois       │
                    └──────────────────┬──────────────────────────┘
                                       │ 全部 mock ✅
                    ┌──────────────────▼──────────────────────────┐
                    │              Channel 层测试                   │
                    │  每个渠道: validate → request → parse → fetch │
                    │  替身: MagicMock + patch(外部调用)             │
                    └──────────────────┬──────────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
   ┌──────────▼──────────┐  ┌─────────▼─────────┐  ┌──────────▼──────────┐
   │   Batch 层测试       │  │  Processors 层测试  │  │   Store 层测试       │
   │  run_concurrent      │  │  classifier engine  │  │  InMemory R/W       │
   │  BaseBatchQuery      │  │  dns_verify/runner  │  │  JSON R/W (tmp_path)│
   │  ProgressTracker     │  │  tagger matcher     │  │  SQLite (tmp_path)  │
   │  替身: Fake          │  │  替身: InMemory+Mock│  │  替身: 真实文件+DB   │
   └──────────┬──────────┘  └─────────┬─────────┘  └──────────┬──────────┘
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────────┐
                    │            Pipeline 层测试                    │
                    │  Phase1-4 编排 | Pipeline 注册/运行           │
                    │  替身: MagicMock渠道 + patch(run_concurrent) │
                    │  ⚠ 问题: 验证mock调用次数而非最终结果         │
                    └──────────────────┬──────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────────┐
                    │            集成测试 (缺口区)                  │
                    │                                             │
                    │  ❌ Phase间数据流转: Phase1→2→3→4            │
                    │  ❌ 溯源IP拼接: 域名采集→提取→DNS验证         │
                    │  ❌ 分类过滤链: Phase2→filter→Phase3          │
                    │  ❌ 断点续传场景: 中断→恢复                   │
                    │  ❌ 动态IP跳过: 分类→skip_ips→Phase3/4       │
                    └─────────────────────────────────────────────┘
```

### 3.3 替身策略分布图

```
┌─────────────────────────────────────────────────────────────────┐
│                      替身策略分布                                │
├────────────┬──────────┬──────────┬──────────┬──────────────────┤
│   模块      │  Mock    │  Fake    │ InMemory │  真实文件/DB     │
├────────────┼──────────┼──────────┼──────────┼──────────────────┤
│  channel   │ ████████ │          │          │                  │
│  batch     │          │ ██████   │ ███      │                  │
│  pipeline  │ ██████   │          │ ███      │                  │
│  processors│ ████     │          │ █████    │                  │
│  store     │ █        │          │ ██████   │ ██████           │
│  utils     │ ██       │          │          │ ████████         │
├────────────┼──────────┼──────────┼──────────┼──────────────────┤
│  集成测试   │          │          │          │ ████████ (无替身)│
└────────────┴──────────┴──────────┴──────────┴──────────────────┘
```

### 3.4 测试文件与源码模块映射详表

#### batch 模块（3 个文件，22 个类，85 个方法）

| 测试文件 | 被测源码模块 | 测试类数 | 方法数 | 替身策略 | 覆盖的接口/方法 |
|----------|-------------|---------|--------|----------|---------------|
| `test_concurrent.py` | `batch.core.concurrent.run_concurrent` | 9 | 31 | Fake + InMemory | 基本执行、多worker、进度跟踪、错误处理、熔断 |
| `test_progress.py` | `utils.progress.InMemoryProgressTracker` | 2 | 13 | InMemory + tmp_path | `mark_processed()`, `is_processed()`, 渠道隔离 |
| `test_query.py` | `batch.core.query.BaseBatchQuery` | 11 | 41 | Fake + InMemory | `run()`, IP去重、进度跟踪、错误处理 |

#### channel 模块（17 个文件，52 个类，234 个方法）

| 测试文件 | 被测源码模块 | 测试类数 | 方法数 | 替身策略 | 覆盖的接口/方法 |
|----------|-------------|---------|--------|----------|---------------|
| `test_adapter.py` | `channel.adapter.BaseChannelAdapter` | 4 | 18 | Stub + Mock | `validate()`, `fetch()`, `_request()`, `_parse()` |
| `test_aizhan.py` | `channel.aizhan.AizhanChannel` | 4 | 22 | Mock(requests.get) | `_validate_key()`, `_request()`, `_parse()`, `fetch()` |
| `test_chinaz.py` | `channel.chinaz.ChinazChannel` | 4 | 17 | Mock(requests.get) | 同上 |
| `test_fofa_host.py` | `channel.fofa_host.FofaHostChannel` | 4 | 17 | Mock(requests.get) | 同上 |
| `test_fofa_search.py` | `channel.fofa_search.FofaSearchChannel` | 3 | 19 | Mock(requests.get) | 同上 |
| `test_ipinfo_api.py` | `channel.ipinfo_api.IpinfoApiChannel` | 5 | 17 | Mock(requests.get) | 同上 + readme过滤 |
| `test_ipinfo_free.py` | `channel.ipinfo_free.IpinfoFreeChannel` | 3 | 12 | Mock(requests.get) | `_request()`, `fetch()`, 限流 |
| `test_port_scan.py` | `channel.port_scan.PortScanChannel` | 3 | 19 | Mock(PortScanner) | `fetch()`, `validate()`, Config集成 |
| `test_rdns_ptr.py` | `channel.rdns_ptr.RdnsPtrChannel` | 3 | 10 | Mock(socket) | `_request()`, `fetch()`, 错误处理 |
| `test_ssl_cert.py` | `channel.ssl_cert.SslCertChannel` | 3 | 16 | Mock(_get_ssl_cert_text) | CN/SAN解析, port透传 |
| `test_whois_query.py` | `channel.whois_query.WhoisQueryChannel` | 3 | 20 | Mock(whois) | 多值字段、日期转换、dnssec |
| `test_config.py` | `channel.config.*Config` | 13 | 26 | Stub + monkeypatch | 11个Config的默认值/必填/env覆盖 |
| `test_registry.py` | `channel.registry.ChannelRegistry` | 5 | 14 | Stub(FakeChannel) | `register()`, `get()`, `list_*()`, `validate()` |
| `test_protocols.py` | `channel.protocols.ChannelProtocol` | 2 | 5 | Stub | 协议`isinstance`检查 |
| `test_protocol_conformance.py` | `channel.protocols` | 1 | 3 | Stub | 协议一致性检查 |
| `test_errors.py` | `channel.errors` | 2 | 5 | 无 | 异常继承关系 |
| `test_in_memory_channel.py` | `channel.in_memory.InMemoryChannel` | 4 | 10 | InMemory | 默认行为、自定义名称 |

#### pipeline 模块（4 个文件，16 个类，58 个方法）

| 测试文件 | 被测源码模块 | 测试类数 | 方法数 | 替身策略 | 覆盖的接口/方法 |
|----------|-------------|---------|--------|----------|---------------|
| `test_filter_ips.py` | `pipeline.filter_ips` | 2 | 12 | InMemory | `filter_dynamic_ips()`, `filter_ips_by_classification()` |
| `test_phase.py` | `pipeline.phase.Phase` | 2 | 6 | Stub | `PhaseResult`, Phase协议 |
| `test_phases.py` | `phases.phase1-4` | 4 | 31 | Mock + InMemory | Phase1-4 `run()`, 空输入、禁用、skip_ips |
| `test_pipeline.py` | `pipeline.pipeline.Pipeline` | 8 | 9 | Stub(FakePhase) | `register()`, `run()`, 跳过/失败 |

#### processors 模块（9 个文件，48 个类，207 个方法）

| 测试文件 | 被测源码模块 | 测试类数 | 方法数 | 替身策略 | 覆盖的接口/方法 |
|----------|-------------|---------|--------|----------|---------------|
| `test_classifier_engine.py` | `processors.classifier.engine.IPClassifier` | 10 | 47 | InMemory(OrderedDict) | `classify()`, ⚠ `_extract_field()`, `_match_pattern()` |
| `test_classifier_rules.py` | `processors.classifier.rules.load_rules` | 1 | 9 | tmp_path | 规则加载、合并、覆盖 |
| `test_classifier_runner.py` | `processors.classifier.runner.BatchClassifier` | 6 | 19 | InMemory + tmp_path | `run()`, 协议、跳过、重处理 |
| `test_dns_extractor.py` | `processors.dns_verify.extractor` | 1 | 10 | InMemory(dict) | `extract_domain_mappings()` |
| `test_dns_runner.py` | `processors.dns_verify.runner.BatchDnsVerify` | 11 | 43 | InMemory + Mock | `run()`, ⚠ mock调用次数, 过期判断 |
| `test_dns_verifier.py` | `processors.dns_verify.verifier` | 5 | 20 | Mock(socket) | `resolve_domain()`, `batch_verify()` |
| `test_matcher.py` | `processors.tagger.matcher` | 4 | 29 | tmp_path | IP范围匹配 |
| `test_manifest.py` | `processors.tagger.manifest` | 2 | 10 | tmp_path | 标签清单加载/验证 |
| `test_runner.py` | `processors.tagger.runner.BatchTagger` | 8 | 20 | InMemory + tmp_path | `run()`, 累加/覆写模式 |

#### store 模块（12 个文件，32 个类，98 个方法）

| 测试文件 | 被测源码模块 | 测试类数 | 方法数 | 替身策略 | 覆盖的接口/方法 |
|----------|-------------|---------|--------|----------|---------------|
| `test_in_memory_reader.py` | `store.in_memory.InMemoryIPReader` | 7 | 24 | InMemory | 全接口 |
| `test_in_memory_writer.py` | `store.in_memory.InMemoryIPWriter` | 1 | 9 | InMemory | 全接口 |
| `test_json_reader.py` | `store.json_store.IPReader` | 7 | 9 | tmp_path + Mock | 文件读取、不存在、IOError |
| `test_json_writer.py` | `store.json_store.IPWriter` | 6 | 10 | tmp_path + Mock | 文件创建、写入、删除 |
| `test_json_threadsafe.py` | `store.json_store.IPWriter` | 1 | 2 | tmp_path + threading | ⚠ `_lock`检查, 并发写入 |
| `test_sqlite_cache.py` | `store.sqlite_cache.SqliteDomainCache` | 1 | 13 | tmp_path + threading | `set()`, `get()`, 并发安全 |
| `test_progress_tracker.py` | `store.*.progress_tracker()` | 2 | 7 | 真实SQLite + InMemory | 工厂方法、功能验证 |
| `test_protocols.py` | `store.protocols` | 2 | 4 | Stub | 协议检查 |
| `test_protocol_conformance.py` | `store.protocols` | 4 | 6 | 真实/InMemory | 协议一致性 |
| `test_batch_query.py` | `store.in_memory.InMemoryIPReader` | 2 | 5 | InMemory | 批量查询 |
| `test_edge_cases.py` | `store.in_memory.InMemoryIPWriter` | 1 | 9 | InMemory | 边界情况 |
| `test_read_write_consistency.py` | `store.in_memory` | 1 | 7 | InMemory | 读写一致性 |

#### utils 模块（6 个文件，27 个类，119 个方法）

| 测试文件 | 被测源码模块 | 测试类数 | 方法数 | 替身策略 | 覆盖的接口/方法 |
|----------|-------------|---------|--------|----------|---------------|
| `test_load_ips.py` | `utils.load_ips.load_ips` | 2 | 10 | tmp_path | 去空行、去重、校验 |
| `test_cache_converter.py` | `utils.cache_converter` | 9 | 26 | 真实SQLite + tmp_path | 导入导出、合并、清理 |
| `test_query_status.py` | `utils.query_status` | 7 | 20 | 真实SQLite + tmp_path | 进度查询、格式化 |
| `test_quick_query.py` | `utils.quick_query` | 3 | 25 | Mock(datetime) + tmp_path | 参数解析、目录生成 |
| `test_sqlite_progress.py` | `utils.progress.SqliteProgressTracker` | 2 | 15 | 真实SQLite + tmp_path | CRUD、缓冲区、并发 |
| `test_verify_mapping.py` | `utils.verify_mapping` | 4 | 23 | tmp_path + Mock(datetime) | 映射提取、报告格式化 |

#### 集成测试（2 个文件，脚本式）

| 测试文件 | 被测模块 | 替身策略 | 覆盖范围 | 问题 |
|----------|---------|----------|---------|------|
| `test_phase_full_run.py` | Phase1-4 全流程 | **无替身** | 全流程 | 依赖外部服务，不可靠 |
| `test_dns_verify_only.py` | DNS验证 | **无替身** | DNS验证 | 无断言，手动脚本 |

---

## 四、优先改进建议

| 优先级 | 改进项 | 说明 | 预估工作量 |
|--------|--------|------|-----------|
| **P0** | 新增 Phase 间数据流转集成测试 | 使用 InMemory 组件测试 Phase1→2→filter→3→4，这是最大覆盖缺口 | 中 |
| **P0** | 新增溯源 IP 拼接场景测试 | 域名采集→域从提取→DNS验证端到端链路 | 中 |
| **P1** | 重构 `test_phases.py` | mock 调用次数/参数断言 → 结果导向断言（验证 writer 最终数据） | 中 |
| **P1** | 改造集成测试 | `test_phase_full_run` 增加 mock 模式；`test_dns_verify_only` 改为带断言 | 小 |
| **P1** | 新增动态 IP 跳过场景测试 | 分类→skip_ips→Phase3/4 行为验证 | 小 |
| **P2** | 消除私有方法/属性测试 | `_extract_field`/`_match_pattern`/`_lock`/`_db_path` 通过公开接口间接覆盖 | 小 |
| **P2** | 统一替身策略 | pipeline 用 MagicMock → 改为 Fake/InMemory，与 batch 模块一致 | 中 |
| **P3** | 引入 PipelineContext | 封装 writer/reader/progress_tracker 为上下文对象 | 大 |
| **P3** | 引入 PipelineBuilder | 将编排逻辑收回到框架层 | 大 |
