# Handoff: Issue #15 收尾 + 架构机会 #8/#9/#10/#11（未提交）

## 项目概况

IP 信息采集流水线，4 阶段架构：

- Phase 1: 基础情报采集 (ipinfo_api, rdns_ptr)
- Phase 2: 分类+标签 (classifier, tagger) — 分类后自动导出未分类 RDNS
- Phase 3: 深度查询 (aizhan, chinaz, fofa_host) — 并发
- Phase 4: 验证+扫描 (dns_verify, port_scan/nmap) — 并发

## 当前状态

**994 测试全部通过，ruff lint 全部通过。未提交。**

```
issues/
├── 008-add-fscan-channel.md     ← ❌ 未开始（用户说排到最后）
├── 015-pipeline-builder.md      ← ✅ 已完成（BatchStep + BatchFactory + 脚本迁移 + skip_dynamic_ips）
├── 016-trace-judge-excel.md     ← ✅ 已完成
└── 017-trace-judge-excel-lessons.md ← ✅ 已完成
```

Spec 文档: `.trae/specs/issue15-arch-remaining/` (全部完成)

## 已完成：Issue #15 收尾 + 架构机会

### 设计文档

`.trae/specs/issue15-arch-remaining/spec.md`

### 核心变更：BatchStep 统一协议

工作流管理粒度从 channel 提升到 batch：

- **BatchStep Protocol** (`pipeline/core/batch_step.py`): `@runtime_checkable`，`name: str` + `run() → BatchResult`
- **ChannelBatchStep** (`pipeline/core/channel_batch_step.py`): 适配器，将 channel + `run_concurrent()` 包装为 BatchStep
- **BatchFactory** (`pipeline/core/batch_factory.py`): 延迟导入自动发现，`_CHANNEL_MAP`(10 渠道) + `_PROCESSOR_MAP`(3 处理器)，`try_create()` 返回 `BatchStep | None`
- **BaseProcessor** 新增 `name` 属性（返回 `self.channel_name`），使现有处理器直接满足 BatchStep 协议

### 目录重构

```
pipeline/
├── core/                    # 通用流水线框架
│   ├── batch_factory.py     # BatchFactory 自动发现
│   ├── batch_step.py        # BatchStep 协议
│   ├── channel_batch_step.py # ChannelBatchStep 适配器
│   ├── builder.py           # PipelineBuilder
│   ├── context.py           # PipelineContext
│   ├── filter_ips.py        # 过滤器
│   ├── phase.py             # Phase 协议 + PhaseResult
│   └── pipeline.py          # Pipeline 运行引擎
├── trace_steps/             # IP 溯源工作流步骤（原 phases/）
│   ├── phase1_basic.py
│   ├── phase2_classify.py
│   ├── phase3_deep.py
│   └── phase4_verify_scan.py
└── __init__.py
```

### Phase 迁移到 BatchStep

Phase 构造函数新增 `steps: list[BatchStep]` 参数，内部只编排 BatchStep 执行顺序（并行/串行），不直接依赖 channel/processor 类型。保留 legacy 参数向后兼容。

### 其他变更

| 变更                       | 说明                                                            |
| -------------------------- | --------------------------------------------------------------- |
| `--only-phase N`           | `run_pipeline.py` 新增参数，映射到 `Pipeline.run(only_phase=N)` |
| `add_or_update_ip_batch()` | `IPWriter`/`InMemoryIPWriter` 批量操作，单次 I/O                |
| `skip_dynamic_ips()`       | `PipelineBuilder` 自动注册过滤器，移除 `_skip_dynamic` 无用标记 |
| `_try_channel()` 删除      | 两个脚本中硬编码函数已由 `BatchFactory.try_create()` 替代       |

### 已解决的技术债

| #   | 问题                              | 解决方式                                              |
| --- | --------------------------------- | ----------------------------------------------------- |
| 8   | Phase 双层 run() 抽象职责模糊     | BatchStep 迁移后 Phase 编排 BatchStep，两层职责明确   |
| 9   | 渠道注册表自动发现                | BatchFactory + \_CHANNEL_MAP/\_PROCESSOR_MAP 延迟导入 |
| 10  | IPDataWriter 缺少批量操作         | `add_or_update_ip_batch()` 单次 I/O                   |
| 11  | run_pipeline.py 缺少 --only-phase | `--only-phase N` 参数                                 |
| 15  | skip_dynamic_ips() 未生效         | 自动注册过滤器                                        |
| 15  | \_try_channel() 硬编码            | BatchFactory.try_create() 替代                        |

### 新增文件

| 文件                                                        | 说明                                        |
| ----------------------------------------------------------- | ------------------------------------------- |
| `src/ip_info/pipeline/core/batch_step.py`                   | BatchStep 协议                              |
| `src/ip_info/pipeline/core/channel_batch_step.py`           | ChannelBatchStep 适配器                     |
| `src/ip_info/pipeline/core/batch_factory.py`                | BatchFactory 自动发现                       |
| `tests/unit/pipeline/core/test_batch_step.py`               | BatchStep 协议 + ChannelBatchStep 测试 (14) |
| `tests/unit/pipeline/core/test_batch_factory.py`            | BatchFactory 测试 (11)                      |
| `tests/unit/pipeline/trace_steps/test_phases_batch_step.py` | Phase BatchStep 测试 (17)                   |
| `tests/unit/store/test_json_writer_batch.py`                | IPWriter 批量操作测试 (6)                   |

### 修改文件

| 文件                                        | 说明                                                          |
| ------------------------------------------- | ------------------------------------------------------------- |
| `src/ip_info/processors/core/base.py`       | 新增 `name` 属性                                              |
| `src/ip_info/store/protocols.py`            | IPDataWriter 新增 `add_or_update_ip_batch`                    |
| `src/ip_info/store/json_store.py`           | IPWriter 实现 `add_or_update_ip_batch`                        |
| `src/ip_info/store/in_memory.py`            | InMemoryIPWriter 实现 `add_or_update_ip_batch`                |
| `src/ip_info/pipeline/core/builder.py`      | `skip_dynamic_ips()` 自动注册过滤器，移除 `_skip_dynamic`     |
| `src/ip_info/pipeline/trace_steps/phase1-4` | 新增 `steps` 参数，保留 legacy 向后兼容                       |
| `scripts/run_pipeline.py`                   | 使用 BatchFactory，新增 `--only-phase`，删除 `_try_channel()` |
| `scripts/quick_query.py`                    | 使用 BatchFactory，删除 `_try_channel()`                      |
| `tests/unit/pipeline/test_phases.py`        | mock 替换为 FakeBatchStep                                     |
| `tests/integration/test_phase_data_flow.py` | mock 替换为 FakeBatchStep                                     |
| `tests/integration/test_phase_full_run.py`  | mock 替换为 FakeBatchStep                                     |
| `tests/integration/test_domain_trace.py`    | mock 替换为 FakeBatchStep                                     |
| `tests/unit/store/test_protocols.py`        | StubWriter 新增 `add_or_update_ip_batch`                      |

### 新增技术债

| #   | 潜在问题                  | 优先级 | 说明                                                |
| --- | ------------------------- | ------ | --------------------------------------------------- |
| A   | Phase 向后兼容参数过多    | P3     | Phase 1-4 保留 legacy 构造参数，长期应移除          |
| B   | BatchFactory 静态方法模式 | P3     | 可考虑改为模块级函数或实例化配置                    |
| C   | CONTEXT.md 未更新         | P2     | 仍标记 pipeline 为"未开始"，缺少 BatchStep 等新概念 |
| D   | FakeBatchStep 重复定义    | P3     | 在 3 个测试文件中各自定义，应提取到 `tests/fakes/`  |

## 后续测试改进计划

### P1: vcr.py 替换手工 mock response

| Channel                  | 当前方式            | vcr.py 收益                       |
| ------------------------ | ------------------- | --------------------------------- |
| ipinfo_api / ipinfo_free | MagicMock 返回 JSON | 录制真实响应，验证字段完整性      |
| fofa_search / fofa_host  | MagicMock 返回 JSON | Fofa 响应结构复杂，录制更可靠     |
| aizhan / chinaz          | MagicMock 返回 HTML | HTML 结构易变，录制真实响应更可靠 |

### P1: freezegun 替换 time.sleep mock

### P2: 端到端测试

## 测试替身策略

| 类型 | 使用位置                                                                                      |
| ---- | --------------------------------------------------------------------------------------------- |
| Fake | FakeChannel, FakeBatchStep, InMemoryIPWriter/Reader                                           |
| Stub | `_fake_batch_verify`                                                                          |
| Mock | patch(requests.get) — channel HTTP, patch(nmap.PortScanner), patch(socket), patch(time.sleep) |

## 技术栈

- Python 3.12+, pytest (`pytest tests/`)
- 994 测试全部通过
- pre-commit hooks: ruff-format + ruff-check
- Spec 文档: `.trae/specs/issue15-arch-remaining/` (全部完成)
- Spec 文档: `.trae/specs/arch-deepening/` (全部完成)

## 建议使用的 Skills

- `git-commit` — 提交当前变更
- `tdd` — 开发循环
- `fake-driven-testing` — 集成测试策略
- `fdt-refactor-mock-to-fake` — channel 层 mock 替换（vcr.py 前置）
