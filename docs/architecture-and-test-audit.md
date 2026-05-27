# IP Info Manager — 架构审查 + 测试质量审计报告

> 更新时间: 2026-05-27（第四轮，全面数据校准）
> 基准: 892 测试通过 (865 单元 + 27 集成), commit c537775

---

## 一、架构深化状态

### 已解决（7/10）

| # | 问题 | 解决方案 | Commit |
|---|------|----------|--------|
| 1 | Pipeline 双生子 | Builder 构建完整 Pipeline，删除简单 dataclass | c537775 |
| 2 | PipelineContext 浅层透传 | Phase 构造函数 context 必填，移除 writer/reader/progress_tracker/domain_cache 独立参数 | c537775 |
| 3 | Phase 内重复渠道禁用检查 | 删除 Phase 内 disabled 检查，统一由 run_concurrent 处理 | c537775 |
| 4 | BatchTagger 鸭子类型读取 | 显式 `self._reader.get_channel_data()` 替代 `getattr(self._writer, ...)` | c537775 |
| 5 | InMemoryIPWriter 冗余读取方法 | 移除 4 个读取方法，统一使用 InMemoryIPReader | c537775 |
| 6 | _try_flush 三处重复 | 提取 `flush_progress()` 公共工具函数 | c537775 |
| 7 | filter_ips 游离 + 脚本上帝模式 | Builder `with_filter()` + run_pipeline.py 用 Builder 重写 | c537775 |

### 未解决（3/10）

| # | 问题 | 优先级 | 说明 |
|---|------|--------|------|
| 8 | Phase 双层 run() 抽象职责模糊 | P2 | Phase 2/4 的 run() 只是薄包装，转换 BatchResult→PhaseResult |
| 9 | 渠道注册表自动发现 | P2 | `_try_channel()` if-elif 硬编码仍在 run_pipeline.py |
| 10 | IPDataWriter 缺少批量操作 | P2 | 1000 IP = 1000 次全量 JSON 读写 |

---

## 二、测试质量审计

### 总览

| 指标 | 数值 |
|------|------|
| 总测试数 | 892 |
| 单元测试 | 865 |
| 集成测试 | 27 |
| Mock 内省断言 | 9 处 |
| 私有方法/属性调用 | ~92 处 |
| 测试文件数 | 62 |

### 模块评级

#### Channel 层

| 模块 | 评级 | 测试数 | 说明 |
|------|------|--------|------|
| adapter | **B** | 18 | 1 处 mock_sleep 内省 |
| aizhan | **C** | 22 | 15 处私有方法调用 (_validate_key×5, _request×5, _parse×5) |
| chinaz | **C** | 17 | 12 处私有方法调用 (_validate_key×4, _request×4, _parse×4) |
| ipinfo_api | **C** | 18 | 12 处私有方法调用 (_validate_key×4, _request×8) |
| ipinfo_free | **C** | 13 | 7 处私有方法调用 (_request×7) |
| fofa_host | **C** | 17 | 12 处私有方法调用 (_validate_key×4, _request×8) |
| fofa_search | **C** | 20 | 15 处私有方法调用 (_validate_key×4, _request×11) |
| rdns_ptr | **C** | 10 | 5 处私有方法调用 (_request×5) |
| ssl_cert | **C** | 17 | 6 处私有方法调用 (_request×6) |
| whois_query | **C** | 22 | 4 处私有方法调用 (_request×4) |
| port_scan | **C+** | 21 | 4 处私有属性读取 + 2 处 mock 内省 |
| registry | **A** | 14 | 纯逻辑 |
| protocols | **A** | 5 | 纯逻辑 |
| errors | **A** | 5 | 纯逻辑 |
| config | **A** | 26 | 纯配置 |
| in_memory | **A** | 10 | 纯逻辑 |
| protocol_conformance | **A** | 3 | 协议验证 |

#### Processor 层

| 模块 | 评级 | 测试数 | 说明 |
|------|------|--------|------|
| classifier/engine | **A** | 50 | 纯逻辑，结果导向 |
| classifier/rules | **A** | 9 | 纯函数测试 |
| classifier/runner | **A** | 19 | 结果导向 |
| tagger/matcher | **A** | 29 | 结果导向 |
| tagger/manifest | **B** | 10 | 1 处 assert_called_with |
| tagger/runner | **B** | 22 | accumulate 纯 writer 测试 |
| dns_verify/runner | **B-** | 43 | 5 处 mock 内省 |
| dns_verify/verifier | **B** | 20 | 1 处 assert_called_with |
| dns_verify/extractor | **A** | 9 | 纯函数测试 |

#### Pipeline 层

| 模块 | 评级 | 测试数 | 说明 |
|------|------|--------|------|
| phase.py | **A** | 6 | Phase 协议测试 |
| pipeline.py | **A** | 15 | FakePhase + 阶段间过滤器测试 |
| builder.py | **A** | 12 | FakeChannel + with_filter 测试 |
| context.py | **B** | 6 | 6 个单元测试 |
| filter_ips.py | **A** | 13 | 测试充分 |
| phase1_basic | **A-** | 33 | context 必填简化了构造 |
| phase2_classify | **A-** | (含在 test_phases) | context 必填 |
| phase3_deep | **A-** | (含在 test_phases) | context 必填 |
| phase4_verify_scan | **A-** | (含在 test_phases) | context 必填 |

#### Store 层

| 模块 | 评级 | 测试数 | 说明 |
|------|------|--------|------|
| json_store (writer) | **A** | 10 | 真实文件系统测试 |
| json_store (reader) | **A** | 9 | 真实文件系统测试 |
| sqlite_cache | **A** | 14 | 真实 SQLite + 并发测试 |
| in_memory_writer | **A** | 10 | Writer/Reader 职责分离 |
| in_memory_reader | **A** | 24 | 完整读取测试 |
| protocols | **A** | 4 | 协议定义 |
| progress_tracker | **B** | 7 | 文件+内存 tracker |
| edge_cases | **A** | 9 | 边界条件 |
| read_write_consistency | **A** | 7 | 读写一致性 |
| protocol_conformance | **A** | 5 | 协议一致性 |
| batch_query | **A** | 5 | 批量查询 |
| json_threadsafe | **A** | 1 | 线程安全 |

#### Batch 层

| 模块 | 评级 | 测试数 | 说明 |
|------|------|--------|------|
| core/query | **A** | 41 | Fake 模式优秀 |
| core/concurrent | **A** | 31 | 线程安全测试到位 |
| core/runner | **D** | 0 | 无直接测试 |
| batch_* (薄包装) | **D** | 0 | 薄包装层，无独立测试 |
| progress | **B** | 15 | 进度追踪 |

#### Utils 层

| 模块 | 评级 | 测试数 | 说明 |
|------|------|--------|------|
| progress | **A** | 16 | flush_progress 统一 |
| cache_converter | **B** | 26 | 格式转换 |
| load_ips | **B** | 10 | IP 加载 |
| verify_mapping | **B** | 22 | 映射验证 |
| quick_query | **B** | 25 | 快速查询 |
| query_status | **B** | 20 | 状态查询 |
| sqlite_progress | **A** | 16 | SQLite 进度追踪 |

#### 集成测试

| 文件 | 评级 | 测试数 | 覆盖场景 |
|------|------|--------|----------|
| test_phase_data_flow.py | **A** | 9 | 全流程、分类过滤、动态IP跳过、断点续传 |
| test_domain_trace.py | **A** | 11 | 域名提取、端到端溯源、验证状态、缓存集成 |
| test_dns_verify_only.py | **B+** | 4 | DNS 验证独立测试 |
| test_phase_full_run.py | **B+** | 3 | 全流程 Mock 模式 |

### Mock 内省断言（9 处）

| 文件 | 行号 | 断言 | 改进方向 |
|------|------|------|----------|
| test_dns_runner.py | 407 | `mock_batch_verify.assert_called_once()` | 验证 writer 最终数据 |
| test_dns_runner.py | 436 | `mock_batch_verify.assert_called_once()` | 验证 writer 最终数据 |
| test_dns_runner.py | 478 | `mock_batch_verify.assert_called_once()` | 验证 writer 最终数据 |
| test_dns_runner.py | 579 | `mock_batch_verify.call_count == 1` | 验证 writer 最终数据 |
| test_dns_runner.py | 625 | `mock_batch_verify.assert_called_once()` | 验证 writer 最终数据 |
| test_adapter.py | 109 | `mock_sleep.assert_called_once_with(0.15)` | 验证延迟行为结果 |
| test_port_scan.py | 271 | `mock_nm.scan.assert_called_once()` | 验证扫描结果数据 |
| test_port_scan.py | 290 | `mock_nm.scan.assert_called_once()` | 验证扫描结果数据 |
| test_dns_verifier.py | 47 | `mock_socket.setdefaulttimeout.assert_called_with(5.0)` | 验证超时行为结果 |

### 私有方法/属性调用（~92 处）

Channel 测试是重灾区，所有渠道测试都直接调用 `_request()`/`_parse()`/`_validate_key()` 等私有方法：

| 文件 | _request | _parse | _validate_key | _arguments/_port_list | 合计 |
|------|----------|--------|---------------|----------------------|------|
| test_aizhan.py | 5 | 5 | 5 | — | 15 |
| test_fofa_search.py | 11 | — | 4 | — | 15 |
| test_chinaz.py | 4 | 4 | 4 | — | 12 |
| test_fofa_host.py | 8 | — | 4 | — | 12 |
| test_ipinfo_api.py | 8 | — | 4 | — | 12 |
| test_ssl_cert.py | 6 | — | — | — | 6 |
| test_ipinfo_free.py | 7 | — | — | — | 7 |
| test_rdns_ptr.py | 5 | — | — | — | 5 |
| test_whois_query.py | 4 | — | — | — | 4 |
| test_port_scan.py | — | — | — | 4 | 4 |
| **合计** | **58** | **9** | **21** | **4** | **92** |

> 注: FakeChannel 实现中的 `_request()`/`_parse()` 是实现抽象接口，不算私有方法调用问题。

### 场景导向集成测试覆盖

| 场景 | 状态 | 测试文件 |
|------|------|----------|
| Phase 1→2→filter→3→4 全流程 | ✅ | test_phase_data_flow |
| 分类结果跨阶段传递 | ✅ | test_phase_data_flow |
| 动态 IP 跳过流程 | ✅ | test_phase_data_flow |
| 断点续传/Resume | ✅ | test_phase_data_flow |
| Domain trace: aizhan→extract→verify | ✅ | test_domain_trace |
| Domain trace: 双渠道合并 | ✅ | test_domain_trace |
| Domain cache 集成 | ✅ | test_domain_trace |
| Phase 4 读取 Phase 3 数据 | ✅ | test_domain_trace |
| 全流程 Mock 模式 | ✅ | test_phase_full_run |
| Pipeline 阶段间过滤器 | ✅ | test_pipeline |
| BatchTagger accumulate 纯 writer | ✅ | test_runner |
| DNS 验证独立场景 | ✅ | test_dns_verify_only |
| Phase 失败后重试 | ❌ | — |
| 多 IP 并发写入一致性 | ❌ | — |
| SqliteProgressTracker 跨进程 | ❌ | — |

---

## 三、测试全景图

### 单元测试模块边界图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        单元测试 (865 个)                              │
├─────────────────┬───────────────────┬───────────────────────────────┤
│   Channel 层    │   Processor 层     │      Pipeline 层              │
│   (C~A)         │   (B-~A)          │      (A)                      │
├─────────────────┼───────────────────┼───────────────────────────────┤
│ aizhan [C]  22  │ classifier [A] 78  │ phase.py [A] 6               │
│ chinaz [C]  17  │   engine ★ 50     │ pipeline.py [A] 15           │
│ ipinfo_api [C]18│   rules ★ 9       │ builder.py [A] 12            │
│ ipinfo_free[C]13│   runner ★ 19     │ context.py [B] 6             │
│ fofa_host [C]17 │ tagger [B~A] 61   │ filter_ips.py [A] 13         │
│ fofa_search[C]20│   matcher ★ 29    │ phases/                       │
│ rdns_ptr [C] 10 │   manifest [B] 10 │   phase1-4 [A-] 33          │
│ ssl_cert [C] 17 │   runner [B] 22 ↑ │                               │
│ whois_query[C]22│ dns_verify [B-~A] │                               │
│ port_scan [C+]21│   runner [B-] 43⚠ │                               │
│ adapter [B]  18 │   verifier [B] 20 │                               │
│ registry [A] 14 │   extractor [A]★9 │                               │
│ protocols [A] 5 │                    │                               │
│ errors [A]    5 │                    │                               │
│ config [A]   26 │                    │                               │
│ in_memory [A]10 │                    │                               │
│ conf_test [A] 3 │                    │                               │
├─────────────────┼───────────────────┼───────────────────────────────┤
│   Store 层      │   Batch 层         │      Utils 层                 │
│   (A)           │   (A~D)            │      (A~B)                    │
├─────────────────┼───────────────────┼───────────────────────────────┤
│ json_writer[A]10│ core/query [A]41★ │ progress [A] 16 ↑            │
│ json_reader[A] 9│ core/concur [A]31★│ cache_conv [B] 26            │
│ sqlite [A]    14│ core/runner [D]⚠  │ load_ips [B] 10              │
│ in_mem_w [A]  10│ batch_* [D] ⚠     │ verify_map [B] 22            │
│ in_mem_r [A]  24│ progress [B] 15   │ quick_query [B] 25           │
│ protocols [A]  4│                    │ query_status[B] 20           │
│ progress [B]   7│                    │ sqlite_prog [A] 16           │
│ edge [A]       9│                    │                               │
│ rw_consist[A]  7│                    │                               │
│ proto_conf[A]  5│                    │                               │
│ batch_query[A] 5│                    │                               │
│ threadsafe[A]  1│                    │                               │
└─────────────────┴───────────────────┴───────────────────────────────┘

★ = 结果导向 + Fake 模式优秀   ⚠️ = 需要改进   ↑ = 本轮提升
```

### 集成测试场景覆盖图

```
┌──────────────────────────────────────────────────────────────────────┐
│                     集成测试 (27 个)                                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  test_phase_data_flow.py (9 个)                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐       │
│  │ Phase 1  │───→│ Phase 2  │───→│ Pipeline │───→│ Phase 3  │       │
│  │ ipinfo   │    │ classify │    │ filter   │    │ aizhan   │       │
│  │ rdns     │    │ tagger   │    │ by_class │    │ chinaz   │       │
│  └──────────┘    └──────────┘    │ dynamic  │    │ fofa     │       │
│       ↑              ↑          └──────────┘    └────┬─────┘       │
│       │  writer 数据累积验证         ↑                  │             │
│       │  tracker 进度验证            │ Pipeline.run()   ↓             │
│       └─────────────────────────────│ 自动执行    ┌──────────┐       │
│                                      └──────────→ │ Phase 4  │       │
│                                                   │ dns_verify│      │
│                                                   │ port_scan │      │
│                                                   └──────────┘       │
│                                                                      │
│  test_domain_trace.py (11 个)                                        │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │ aizhan/  │───→│ extract_     │───→│ BatchDns     │               │
│  │ chinaz   │    │ domain_      │    │ Verify       │               │
│  │ domains  │    │ mappings     │    │ → writer     │               │
│  └──────────┘    └──────────────┘    │ → cache      │               │
│       ↑              ↑               └──────────────┘               │
│       │  单渠道/双渠道 │  合并/去重      ↑                             │
│       │  提取验证      │  验证          │  matched/changed/           │
│       └──────────────┘               │  unresolved/timeout         │
│                                      │  缓存命中/过期/写入          │
│                                      └────────────────              │
│                                                                      │
│  test_dns_verify_only.py (4 个)                                      │
│  test_phase_full_run.py (3 个)                                       │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  未覆盖: Phase 失败重试 | 并发写入一致性 | SQLite 跨进程断点续传       │
└──────────────────────────────────────────────────────────────────────┘
```

### 测试替身策略分布图

```
┌──────────────────────────────────────────────────────────────────────┐
│                    测试替身使用分布                                    │
├──────────────┬───────────────────────────────────────────────────────┤
│ Fake         │ FakeChannel (test_phases, test_builder,              │
│ (最优)       │   test_phase_data_flow, test_domain_trace)           │
│              │ _FakeChannel/_FakeWriter (test_query, test_concurrent)│
│              │ FakePhase (test_pipeline)                             │
│              │ InMemoryIPWriter/Reader (集成测试)                     │
│              │ PipelineContext + InMemory 组件 (Phase 测试)          │
├──────────────┼───────────────────────────────────────────────────────┤
│ Stub         │ _fake_batch_verify (test_domain_trace,               │
│ (良好)       │   test_dns_verify_only)                               │
├──────────────┼───────────────────────────────────────────────────────┤
│ Mock         │ patch(requests.get) — channel 测试                    │
│ (可接受)     │ patch(BatchDnsVerify) — Phase 4 测试                  │
│              │ patch(BatchClassifier/Tagger) — Phase 2 测试          │
│              │ patch(batch_verify) — dns_runner 测试                 │
│              │ MagicMock(nmap.PortScanner) — port_scan 测试          │
├──────────────┼───────────────────────────────────────────────────────┤
│ ⚠️ 需改进    │ test_dns_runner.py — 5 处 mock 内省                   │
│              │ test_adapter.py — 1 处 mock_sleep 内省                │
│              │ test_port_scan.py — 2 处 mock 内省 + 4 处私有属性     │
│              │ test_dns_verifier.py — 1 处 mock 内省                 │
│              │ Channel 测试 — 92 处私有方法调用                       │
└──────────────┴───────────────────────────────────────────────────────┘
```

### 数据流测试路径图

```
IP 列表
  │
  ▼
┌─────────┐  context  ┌─────────┐  context  ┌──────────┐
│ Phase 1 │──────────→│ Phase 2 │──────────→│ Pipeline │
│ ipinfo  │  writer   │ classif │  writer   │ filter   │
│ rdns    │  rdns     │ tagger  │  tagger   │ by_class │
└─────────┘          └─────────┘          │ dynamic  │
                                           └────┬─────┘
                                                │
                          filtered_ips ─────────┘
                                                │
                     ┌─────────┐        ┌─────────┐
                     │ Phase 3 │───────→│ Phase 4 │
                     │ aizhan  │ writer │ dns_verify│
                     │ chinaz  │        │ port_scan│
                     │ fofa    │        │          │
                     └─────────┘        └─────────┘

测试覆盖路径:
  ✅ Phase1→Phase2→Pipeline.filter→Phase3→Phase4 全链路
  ✅ aizhan→extract→verify→cache 溯源链路
  ✅ 动态IP跳过: Pipeline with_filter 自动传播 skip_ips
  ✅ 断点续传: tracker 阻止重复
  ✅ 数据累积: 每阶段 writer 数据验证
  ✅ Pipeline 阶段间过滤器: with_filter() 注册 + 自动执行
  ✅ BatchTagger accumulate: 纯 writer + 显式 reader
  ❌ Phase 失败→重试
  ❌ 并发写入一致性
```

---

## 四、优先改进建议

### P0 — 测试（9 处 mock 内省）

1. **消除 `test_dns_runner.py` 的 5 处 mock 内省断言** — 改为验证 writer 最终数据
2. **消除 `test_adapter.py` 的 mock_sleep 内省** — 改为验证延迟行为结果
3. **消除 `test_port_scan.py` 的 2 处 mock 内省** — 改为验证扫描结果数据
4. **消除 `test_dns_verifier.py` 的 mock 内省** — 改为验证超时行为结果

### P1 — 测试（92 处私有方法调用）

5. **Channel 测试消除私有方法直接调用** — 通过公共接口 `fetch()` 替代 `_request()`/`_parse()`/`_validate_key()` 直接调用，需要重构测试为结果导向
6. **`test_port_scan.py` 消除私有属性读取** — `_arguments`/`_port_list` 改为通过配置对象或 fetch 结果验证

### P2 — 架构

7. **Phase 双层 run() 抽象** — 让 Processor 直接满足 Phase 协议，消除薄包装
8. **渠道注册表自动发现** — 替代 `_try_channel()` 硬编码
9. **IPDataWriter 批量操作** — 减少全量 JSON 读写次数
10. **补充 `batch/core/runner.py` 测试** — 核心调度器无直接测试
11. **补充缺失集成场景** — Phase 失败重试 / 并发写入一致性

---

## 五、架构依赖关系图

```
┌─────────────────────────────────────────────────────────────┐
│                        scripts/                              │
│                    run_pipeline.py                            │
│                    (PipelineBuilder 组装)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ build().run()
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     pipeline/                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Pipeline │←─│ Builder  │  │ Context  │  │filter_ips│   │
│  │  +filter │  │+with_flt │  │(dataclass)│  │ (纯函数) │   │
│  └────┬─────┘  └──────────┘  └──────────┘  └──────────┘   │
│       │ register(phase)                                      │
│  ┌────┴─────────────────────────────────────────────────┐   │
│  │  phases/                                              │   │
│  │  phase1_basic → phase2_classify → phase3_deep →      │   │
│  │  phase4_verify_scan                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ 使用
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  channel/          │  processors/       │  batch/            │
│  adapter (抽象)    │  classifier/       │  core/query ★      │
│  aizhan           │    engine ★        │  core/concurrent ★ │
│  chinaz           │    rules ★         │  core/runner ⚠️    │
│  ipinfo_api       │    runner ★        │  batch_tagger      │
│  ipinfo_free      │  tagger/           │  batch_classifier  │
│  fofa_host        │    matcher ★       │  batch_dns_verify  │
│  fofa_search      │    runner ↑        │  batch_nmap        │
│  rdns_ptr         │  dns_verify/       │  ...               │
│  ssl_cert         │    runner [B-]⚠    │                    │
│  whois_query      │    verifier [B]    │                    │
│  port_scan [C+]⚠  │    extractor ★     │                    │
│  registry [A]     │                    │                    │
│  protocols [A]    │                    │                    │
└───────────────────┴────────────────────┴────────────────────┘
                           │ 使用
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  store/             │  utils/                               │
│  json_store [A]     │  progress [A] ↑ flush_progress()      │
│  sqlite_cache [A]   │  cache_converter [B]                  │
│  in_memory [A] ↑    │  load_ips [B]                         │
│  protocols [A]      │  verify_mapping [B]                   │
│                     │  quick_query [B]                      │
│                     │  query_status [B]                     │
└─────────────────────┴──────────────────────────────────────┘

★ = 结果导向 + Fake 模式优秀   ⚠️ = 需要改进   ↑ = 本轮提升
```
