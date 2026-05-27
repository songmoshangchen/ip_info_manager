# IP Info Manager — 架构审查 + 测试质量审计报告

> 更新时间: 2026-05-27（第二轮审查，Issue 009-015 完成后）

---

## 一、架构深化机会（10 项）

### 1. Pipeline 双生子：两个 Pipeline 类，Builder 与脚本脱节 [P0]

**文件**: `pipeline/builder.py`、`pipeline/pipeline.py`、`scripts/run_pipeline.py`

**问题**: 代码库中存在两个 `Pipeline` 类：
- `builder.py` 的 `Pipeline` 是简单 dataclass，只有 `phases` + `context` + 顺序 `run()`
- `pipeline.py` 的 `Pipeline` 支持 `register()`、`from_phase`/`only_phase`/`skip_phases`、失败中断

`PipelineBuilder` 构建的是简单 Pipeline，但 `run_pipeline.py` **两者都不用**——手动创建 Phase、手动调用 `.run()`、手动做 Phase 间过滤。Builder 的 `with_channel()`/`skip_channel()`/`skip_dynamic_ips()` 在生产代码中零调用。

**解决方案**: 合并为一个 Pipeline 类，让 Builder 构建它。将 `run_pipeline.py` 中的 Phase 间过滤逻辑内化为 Pipeline 的阶段间钩子。

**收益**: 局部性（编排逻辑集中一处）、杠杆（新增 Phase 只需 `add_phase()`）

---

### 2. PipelineContext 浅层透传：Phase 构造函数仍然臃肿 [P0]

**文件**: `pipeline/context.py`、`pipeline/phases/phase1-4`

**问题**: `PipelineContext` 是 5 字段 dataclass，但每个 Phase 仍接受 `writer`/`reader`/`progress_tracker`/`domain_cache` 作为独立参数，用 `if context is not None` 做回退。接口反而更复杂——调用者既传 context 又传独立参数，还要理解优先级规则。

`VerifyScanPhase` 有 13 个构造参数，其中 4 个与 context 重叠。

**解决方案**: Phase 只接受 `context: PipelineContext` + 自身特有参数。去掉重叠的独立参数。

**收益**: Phase 接口从 8-13 参数缩减到 3-5，依赖来源单一

---

### 3. Phase 内部重复渠道禁用检查 — 与 run_concurrent 职责重叠 [P1]

**文件**: `pipeline/phases/phase1_basic.py`、`phase3_deep.py`、`batch/core/concurrent.py`

**问题**: 每个 Phase 的 `run()` 内部都有 `if channel.disabled: 统计已处理/跳过/日志` 的逻辑，但 `run_concurrent()` 内部已做了完全相同的检查。同一逻辑写了两遍，统计口径不一致。

**解决方案**: 删除 Phase 内的 `channel.disabled` 检查，让 `run_concurrent()` 统一处理。

**收益**: 局部性（禁用逻辑只存在于 `run_concurrent` 一处）

---

### 4. BatchTagger 鸭子类型读取 — 接缝泄漏 [P1]

**文件**: `processors/tagger/runner.py`（L117-122）

**问题**: `BatchTagger._read_channel_data()` 用 `getattr(self._writer, "get_channel_data", None)` 从 writer 上读取数据。`IPDataWriter` 协议没有 `get_channel_data` 方法——这是 `IPDataReader` 的方法。如果 writer 是纯 `IPDataWriter`，Tagger 的 accumulate 模式会静默失效。

**解决方案**: `BatchTagger` 显式使用 `self._reader.get_channel_data()`（BaseProcessor 已有 reader 参数）。

**收益**: 走正规接缝，不再依赖实现细节

---

### 5. InMemoryIPWriter 实现了完整的 IPDataReader — 违反单一职责 [P2]

**文件**: `store/in_memory.py`

**问题**: `InMemoryIPWriter` 同时实现了 `IPDataWriter` 和 `IPDataReader` 的全部方法，而 `InMemoryIPReader` 是独立类，实现了完全相同的读取逻辑。两份代码几乎逐行相同。

**解决方案**: 让 `InMemoryIPWriter` 只实现 `IPDataWriter`，读取走 `InMemoryIPReader`。

---

### 6. _try_flush 模式三处重复 — 进度刷新的鸭子类型散落 [P2]

**文件**: `batch/core/query.py`、`batch/core/concurrent.py`、`processors/core/base.py`

**问题**: `_try_flush()` / `_flush_progress()` 是同一个"检查 tracker 是否有 flush 方法"的鸭子类型模式，被复制了三遍。

**解决方案**: 将 flush 检查提升到 `ProgressTracker` 协议中，或共享一个工具函数。

---

### 7. filter_ips.py 是流水线逻辑的孤儿 — Phase 间过滤游离于 Pipeline 之外 [P1]

**文件**: `pipeline/filter_ips.py`、`scripts/run_pipeline.py`

**问题**: `filter_dynamic_ips()` 和 `filter_ips_by_classification()` 是流水线的核心编排逻辑，但它们是独立函数，在脚本中手动调用，不属于任何 Phase 或 Pipeline 抽象。

**解决方案**: 将过滤逻辑内化为 Pipeline 的阶段间钩子，或定义 `FilterPhase` 作为 Phase 2.5。

---

### 8. Phase 的双层 run() 抽象 — Phase.run() 和 Processor.run() 职责模糊 [P2]

**文件**: `pipeline/phases/phase2_classify.py`、`phase4_verify_scan.py`

**问题**: Phase 2 的 `run()` 只是创建 Processor 并调用其 `run()`，然后转换 `BatchResult` → `PhaseResult`。这个转换层很薄——Phase 没有增加任何行为。

**解决方案**: 让 Processor 直接满足 `Phase` 协议，或让 Phase 做实质性编排。

---

### 9. run_pipeline.py 是上帝脚本 — 所有组装逻辑集中在一处 [P1]

**文件**: `scripts/run_pipeline.py`

**问题**: 脚本承担了太多职责：解析参数、初始化渠道、初始化存储、创建 Phase、执行过滤、处理禁用、汇总结果。`PipelineBuilder` 完全没被使用。

**解决方案**: 用 `PipelineBuilder` 重写脚本。Builder 负责组装，脚本只负责解析参数和调用 `builder.build().run()`。

---

### 10. IPDataWriter 协议缺少批量操作 — 导致 JSON Store 每次写入都全量读写 [P2]

**文件**: `store/protocols.py`、`store/json_store.py`

**问题**: `IPDataWriter` 只有单条写入。`IPWriter` 每次调用都全量读 JSON → 修改 → 全量写 JSON。1000 个 IP = 1000 次全量文件读写。

**解决方案**: 增加 `add_or_update_batch()` 方法，或引入"事务"概念。

---

## 二、测试质量审计

### 模块评级

| 模块 | 评级 | 说明 |
|------|------|------|
| channel/adapter | **B** | 1 处 mock_sleep 内省；FakeChannel 模式优秀 |
| channel/aizhan,chinaz,ipinfo_api,etc. | **C** | 大量 `_request()`/`_parse()`/`_validate_key()` 私有方法直接调用 |
| channel/port_scan | **C+** | 私有属性读取 + mock 内省，但隔离完整 |
| channel/registry,protocols,errors | **A** | 纯逻辑，测试充分 |
| batch/core/query | **A** | Fake 模式优秀，结果导向 |
| batch/core/concurrent | **A** | Fake 模式优秀，线程安全测试到位 |
| batch/core/runner | **D** | 无直接测试 |
| batch/batch_* (全部) | **D** | 无直接测试（薄包装层） |
| processors/dns_verify/runner | **B-** | 5 处 mock 内省断言 |
| processors/dns_verify/verifier | **B** | 1 处 assert_called_with |
| processors/dns_verify/extractor | **A** | 纯函数测试，无 mock |
| processors/classifier/engine | **A** | 纯逻辑，测试充分 |
| processors/tagger/runner | **C** | 仅协议一致性测试 |
| pipeline/pipeline | **A** | FakePhase 模式好 |
| pipeline/builder | **A** | FakeChannel 模式好 |
| pipeline/context | **D** | 无直接测试 |
| pipeline/filter_ips | **A** | 测试充分 |
| pipeline/phases (1-4) | **B+** | FakeChannel + 集成测试好 |
| store/sqlite_cache | **A** | 真实 SQLite + 并发测试 |
| store/json_store | **A** | 真实文件系统测试 |
| integration (整体) | **B+** | 场景覆盖全面 |

### 遗留 Mock 内省断言（9 处）

| 文件 | 问题 |
|------|------|
| `test_dns_runner.py` ×5 | `assert_called_once()` / `call_count == 1` |
| `test_adapter.py` ×1 | `mock_sleep.assert_called_once_with(0.15)` |
| `test_port_scan.py` ×2 | `mock_nm.scan.assert_called_once()` |
| `test_dns_verifier.py` ×1 | `mock_socket.setdefaulttimeout.assert_called_with(5.0)` |

### 遗留私有方法/属性访问（20+ 处）

主要集中在 **channel 测试**（`_request()`/`_parse()`/`_validate_key()`）和 **test_port_scan.py**（`_arguments`/`_port_list`）。

### 场景导向集成测试覆盖

| 场景 | 状态 |
|------|------|
| Phase 1→2→filter→3→4 全流程 | ✅ |
| 分类结果跨阶段传递 | ✅ |
| 动态 IP 跳过流程 | ✅ |
| 断点续传/Resume | ✅ |
| Domain trace: aizhan→extract→verify | ✅ |
| Domain trace: 双渠道合并 | ✅ |
| Domain cache 集成 | ✅ |
| Phase 4 读取 Phase 3 数据 | ✅ |
| 全流程 Mock 模式 | ✅ |
| Phase 执行失败后重试 | ❌ |
| 多 IP 并发写入一致性 | ❌ |
| SqliteProgressTracker 跨进程 | ❌ |

---

## 三、测试全景图

### 单元测试模块边界图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        单元测试 (849 个)                              │
├─────────────────┬───────────────────┬───────────────────────────────┤
│   Channel 层    │   Processor 层     │      Pipeline 层              │
│   (C~A)         │   (B-~A)          │      (A~B+)                   │
├─────────────────┼───────────────────┼───────────────────────────────┤
│ aizhan [C]      │ classifier [A]     │ phase.py [A]                  │
│ chinaz [C]      │   engine ★         │ pipeline.py [A]               │
│ ipinfo_api [C]  │   rules ★          │ builder.py [A]                │
│ ipinfo_free [C] │   runner [B]       │ context.py [D] ⚠️             │
│ fofa_host [C]   │ tagger [C~A]       │ filter_ips.py [A]             │
│ fofa_search [C] │   matcher ★        │ phases/                        │
│ rdns_ptr [C]    │   manifest [B]     │   phase1_basic [B+]           │
│ ssl_cert [C]    │   runner [C] ⚠️    │   phase2_classify [B+]        │
│ whois_query [C] │ dns_verify [B-~A]  │   phase3_deep [B+]            │
│ port_scan [C+]  │   runner [B-] ⚠️   │   phase4_verify_scan [B+]     │
│ adapter [B]     │   verifier [B]     │                                │
│ registry [A]    │   extractor [A] ★  │                                │
│ protocols [A]   │                    │                                │
│ errors [A]      │                    │                                │
│ in_memory [A]   │                    │                                │
├─────────────────┼───────────────────┼───────────────────────────────┤
│   Store 层      │   Batch 层         │      Utils 层                 │
│   (A)           │   (A~D)            │      (B)                      │
├─────────────────┼───────────────────┼───────────────────────────────┤
│ json_store [A]  │ core/query [A] ★   │ progress [A]                  │
│ sqlite_cache[A] │ core/concurrent[A]★│ load_ips [B]                  │
│ in_memory [A]   │ core/runner [D] ⚠️ │ cache_converter [B]           │
│ protocols [A]   │ batch_* [D] ⚠️     │ verify_mapping [B]            │
│                 │                    │ quick_query [B]               │
│                 │                    │ query_status [B]              │
└─────────────────┴───────────────────┴───────────────────────────────┘

★ = 结果导向 + Fake 模式优秀   ⚠️ = 需要改进
```

### 集成测试场景覆盖图

```
┌──────────────────────────────────────────────────────────────────────┐
│                     集成测试 (33 个)                                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  test_phase_data_flow.py (9 个)                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐       │
│  │ Phase 1  │───→│ Phase 2  │───→│ filter   │───→│ Phase 3  │       │
│  │ ipinfo   │    │ classify │    │ by_class │    │ aizhan   │       │
│  │ rdns     │    │ tagger   │    │ dynamic  │    │ chinaz   │       │
│  └──────────┘    └──────────┘    └──────────┘    │ fofa     │       │
│       ↑              ↑              ↑             └────┬─────┘       │
│       │  writer 数据累积验证         │                  │             │
│       │  tracker 进度验证            │ 跳过验证         ↓             │
│       └──────────────────────────────┘          ┌──────────┐        │
│                                                 │ Phase 4  │        │
│                                                 │ dns_verify│       │
│                                                 │ port_scan │       │
│                                                 └──────────┘        │
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
│  ┌──────────────┐    ┌──────────────┐                               │
│  │ BatchDns     │───→│ writer +     │                               │
│  │ Verify       │    │ cache        │                               │
│  └──────────────┘    └──────────────┘                               │
│  单IP/缓存/无数据/verify_time 验证                                    │
│                                                                      │
│  test_phase_full_run.py (3 个)                                       │
│  ┌──────────────────────────────────────────┐                        │
│  │ Phase 1 → 2 → 3 → 4 全流程 Mock 模式     │                        │
│  │ + 执行顺序验证 + 数据累积验证              │                        │
│  └──────────────────────────────────────────┘                        │
│  (--live 参数保留真实模式入口)                                         │
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
│              │ channel 测试 — 20+ 处私有方法调用                      │
│              │ test_port_scan.py — 私有属性 + mock 内省               │
└──────────────┴───────────────────────────────────────────────────────┘
```

### 数据流测试路径图

```
IP 列表
  │
  ▼
┌─────────┐  writer  ┌─────────┐  writer  ┌──────────┐
│ Phase 1 │─────────→│ Phase 2 │─────────→│ filter   │
│ ipinfo  │  rdns    │ classif │  tagger  │ by_class │
│ rdns    │  ipinfo  │         │          │ dynamic  │
└─────────┘          └─────────┘          └────┬─────┘
                                               │
                          filtered_ips ────────┘
                                               │
                     ┌─────────┐        ┌─────────┐
                     │ Phase 3 │───────→│ Phase 4 │
                     │ aizhan  │ writer │ dns_verify│
                     │ chinaz  │        │ port_scan│
                     │ fofa    │        │          │
                     └─────────┘        └─────────┘

测试覆盖路径:
  ✅ Phase1→Phase2→filter→Phase3→Phase4 全链路
  ✅ aizhan→extract→verify→cache 溯源链路
  ✅ 动态IP跳过: Phase3/4 skip_ips
  ✅ 断点续传: tracker 阻止重复
  ✅ 数据累积: 每阶段 writer 数据验证
  ❌ Phase 失败→重试
  ❌ 并发写入一致性
```

---

## 四、优先改进建议

### P0 — 架构

1. 合并 Pipeline 双生子，让 Builder 成为唯一组装入口
2. Phase 构造函数去掉重叠参数，只接受 context + 特有参数

### P0 — 测试

3. 消除 `test_dns_runner.py` 的 5 处 mock 内省断言
4. 将 `_run_live()` 移出测试目录或标记 `@pytest.mark.live`

### P1 — 测试

5. Channel 测试消除私有方法直接调用（20+ 处）
6. `test_port_scan.py` 消除私有属性读取
7. `test_dns_runner.py` 将 `@patch(batch_verify)` 改为构造器注入

### P1 — 架构

8. Phase 内渠道禁用检查与 `run_concurrent` 去重
9. `filter_ips.py` 内化为 Pipeline 阶段间钩子
10. `run_pipeline.py` 用 Builder 重写

### P2

11. `BatchTagger` 鸭子类型读取改为显式 reader
12. `InMemoryIPWriter` 去除冗余读取方法
13. `_try_flush` 模式统一
14. `IPDataWriter` 增加批量操作
15. 补充 `pipeline/context.py` 和 `batch/core/runner.py` 测试
