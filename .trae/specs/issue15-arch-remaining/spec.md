# Issue #15 收尾 + 剩余架构机会 Spec

## Why

Issue #15（PipelineBuilder）仍有 3 项未完成：渠道注册表自动发现、`skip_dynamic_ips()` 未实际生效、脚本简化。同时 handoff.md 中有 4 个 P2 架构机会。本 spec 统一规划这些收尾工作，引入 **BatchStep 统一协议**，将工作流的管理粒度从 channel 提升到 batch。

## What Changes

### A. 目录重构 — pipeline/core/ + pipeline/trace_steps/ 两层

将 pipeline/ 下的框架代码移入 `core/`，将 `phases/` 重命名为 `trace_steps/`：

```
pipeline/
├── core/                    # 通用流水线框架（从 pipeline/ 移入）
│   ├── batch_factory.py     # NEW: BatchFactory + _CHANNEL_MAP + _PROCESSOR_MAP
│   ├── batch_step.py        # NEW: BatchStep 协议
│   ├── builder.py           # MOVED
│   ├── channel_batch_step.py # NEW: ChannelBatchStep 适配器
│   ├── context.py           # MOVED
│   ├── filter_ips.py        # MOVED
│   ├── phase.py             # MOVED
│   └── pipeline.py          # MOVED
├── trace_steps/             # IP 溯源工作流步骤（从 phases/ 重命名）
│   ├── phase1_basic.py
│   ├── phase2_classify.py
│   ├── phase3_deep.py
│   └── phase4_verify_scan.py
└── __init__.py
```

### B. BatchStep 统一协议

定义 `BatchStep` 协议（`name` + `run() → BatchResult`），使工作流管理粒度从 channel 提升到 batch：

- **BatchStep Protocol**: `name: str` + `run() → BatchResult`
- **ChannelBatchStep**: 适配器，将 channel + `run_concurrent()` 包装为 BatchStep
- **BatchFactory**: 自动发现，维护 `_CHANNEL_MAP`（10 个渠道）+ `_PROCESSOR_MAP`（3 个处理器），`try_create()` 返回 `BatchStep | None`
- **BaseProcessor**: 新增 `name` 属性（返回 `self.channel_name`），使现有处理器直接满足 BatchStep 协议

### C. Phase 迁移到 BatchStep

Phase 构造函数从接收 channel 实例改为接收 BatchStep 实例。Phase 内部只编排 BatchStep，不直接依赖 channel 或 processor。

- Phase 1: 接收 `[ipinfo_step, rdns_step]` 并行执行
- Phase 2: 接收 `classify_step` + `tagger_step` 顺序执行 + 导出逻辑
- Phase 3: 接收 `[aizhan_step, chinaz_step, fofa_step]` 并行执行
- Phase 4: 接收 `dns_verify_step` + `port_scan_step` 并行执行

### D. 脚本迁移 + CLI 改进

- `run_pipeline.py` 和 `quick_query.py` 使用 `BatchFactory.try_create()` 替代 `_try_channel()`
- 删除两个脚本中的 `_try_channel()` 函数定义
- `run_pipeline.py` 新增 `--only-phase N` 参数，映射到 `Pipeline.run(only_phase=N)`

### E. IPDataWriter 批量操作（#10）

- `IPWriter` 新增 `add_or_update_ip_batch(updates) → int`
- 单次加载 JSON → 批量更新 → 单次写回
- `IPDataWriter` Protocol 新增方法签名
- `InMemoryIPWriter` 同步实现

### F. skip_dynamic_ips() 实际生效（Issue #15）

- `PipelineBuilder.skip_dynamic_ips()` 自动注册 `filter_dynamic_ips_for_pipeline` 过滤器
- 移除无用的 `self._skip_dynamic` 标记字段

### G. Phase 双层 run() 评估（#8）

**通过 BatchStep 迁移自然解决**。迁移后 Phase.run() 的职责清晰为"编排 BatchStep"，BatchStep.run() 的职责为"执行批处理"，两层抽象各有明确定位。

## Impact

- Affected specs: Issue #15（收尾）、架构机会 #8/#9/#10/#11
- Affected code:
  - `src/ip_info/pipeline/` — 目录重构 + 新增 batch_step/batch_factory/channel_batch_step
  - `src/ip_info/processors/core/base.py` — 新增 `name` 属性
  - `src/ip_info/store/json_store.py` — 新增 `add_or_update_ip_batch()`
  - `src/ip_info/store/protocols.py` — Protocol 新增方法
  - `src/ip_info/store/in_memory.py` — 同步实现
  - `src/ip_info/pipeline/core/builder.py` — `skip_dynamic_ips()` 改为注册过滤器
  - `scripts/run_pipeline.py` — 使用新 API，新增 `--only-phase`
  - `scripts/quick_query.py` — 使用 BatchFactory
- 全部导入路径从 `pipeline.X` → `pipeline.core.X`，`pipeline.phases.X` → `pipeline.trace_steps.X`

## ADDED Requirements

### Requirement: BatchStep 协议

系统 SHALL 定义 `BatchStep` 协议（`@runtime_checkable`），要求实现 `name: str` 属性和 `run() → BatchResult` 方法。所有批处理步骤（channel-based 和 processor-based）SHALL 满足此协议。

#### Scenario: ChannelBatchStep 满足 BatchStep 协议

- **WHEN** 创建 `ChannelBatchStep(channel_name="aizhan", channel=..., ips=..., writer=...)`
- **THEN** `isinstance(step, BatchStep)` 为 True
- **AND** `step.name == "aizhan"`
- **AND** `step.run()` 返回 `BatchResult`

#### Scenario: BatchClassifier 满足 BatchStep 协议

- **WHEN** 创建 `BatchClassifier(ips=..., writer=..., reader=..., rules_dir=...)`
- **THEN** `isinstance(classifier, BatchStep)` 为 True
- **AND** `classifier.name == "classifier"`

### Requirement: BatchFactory 自动发现

系统 SHALL 提供 `BatchFactory` 类，支持按名称延迟导入并创建 BatchStep 实例。

- `_CHANNEL_MAP` 覆盖全部 10 个内置渠道
- `_PROCESSOR_MAP` 覆盖 3 个处理器（classify, tagger, dns_verify）
- `try_create(name, *, ips, context, **kwargs) → BatchStep | None`
- 导入/初始化失败返回 None，不抛异常
- 未知名称返回 None

#### Scenario: 通过工厂创建渠道 BatchStep

- **WHEN** 调用 `BatchFactory.try_create("aizhan", ips=ips, context=ctx, workers=1)`
- **THEN** 返回 `ChannelBatchStep` 实例（底层为 `AizhanChannel`）

#### Scenario: 通过工厂创建处理器 BatchStep

- **WHEN** 调用 `BatchFactory.try_create("classify", ips=ips, context=ctx, rules_dir="/path")`
- **THEN** 返回 `BatchClassifier` 实例

#### Scenario: 未知名称返回 None

- **WHEN** 调用 `BatchFactory.try_create("unknown")`
- **THEN** 返回 `None`

#### Scenario: 初始化失败返回 None

- **WHEN** 调用 `BatchFactory.try_create("port_scan", ...)` 但 nmap 未安装
- **THEN** 返回 `None`，不抛异常

### Requirement: ChannelBatchStep 适配器

系统 SHALL 提供 `ChannelBatchStep` 类，将 channel 实例 + `run_concurrent()` 包装为 BatchStep。

- 构造参数：`channel_name`, `channel`, `ips`, `writer`, 可选 `workers`, `delay`, `progress_tracker`
- `name` 属性返回 `channel_name`
- `run()` 内部调用 `run_concurrent()` 并返回 `BatchResult`
- `delay` 默认使用 `channel.default_delay`

### Requirement: IPDataWriter 批量操作

`IPDataWriter` Protocol SHALL 提供 `add_or_update_ip_batch(updates) → int` 方法。

- `updates` 类型为 `list[tuple[str, str, dict]]`，每个元组为 `(ip, channel, data)`
- 返回实际更新/新增的数量
- `IPWriter` 实现：单次 `_load_data()` → 批量修改 → 单次 `_save_data()`
- 空列表为 no-op，返回 0

### Requirement: PipelineBuilder.skip_dynamic_ips() 自动注册过滤器

`PipelineBuilder.skip_dynamic_ips()` 调用后 SHALL 自动注册动态 IP 过滤器。

### Requirement: run_pipeline.py --only-phase 参数

`run_pipeline.py` SHALL 支持 `--only-phase N` 命令行参数，仅执行指定编号的阶段。

## MODIFIED Requirements

### Requirement: BaseProcessor 新增 name 属性

`BaseProcessor` 新增 `name` 属性（`@property`），返回 `self.channel_name`。使所有 Processor 子类直接满足 BatchStep 协议。

### Requirement: PipelineBuilder.skip_dynamic_ips()

原有行为：设置 `self._skip_dynamic = True` 标记（从未被消费）。
新行为：自动注册 `filter_dynamic_ips_for_pipeline` 过滤器到"分类与标签"阶段，移除无用标记字段。

### Requirement: Phase 构造函数

Phase 构造函数从接收具体 channel/processor 实例改为接收 BatchStep 实例。Phase 内部只编排 BatchStep 的执行顺序（并行/串行），不直接依赖 channel 或 processor 类型。

### Requirement: IPDataWriter Protocol

新增 `add_or_update_ip_batch(updates: list[tuple[str, str, dict]]) -> int` 方法签名。

## REMOVED Requirements

（无移除。`_try_channel()` 函数在脚本中删除，由 BatchFactory 替代。）

## Testing Strategy

### 开发方法论：TDD + Fake-Driven Testing

每个 Task（Task 2-8）严格遵循以下工作流：

```
1. TDD Red Phase: 使用 tdd skill 编写失败测试
   ↓
2. Fake-Driven Testing 审核: 使用 fake-driven-testing skill 审查测试质量
   - 检查是否使用了 unittest.mock.patch / MagicMock
   - 检查是否应使用 Fake 替身（FakeChannel, InMemoryIPWriter 等）
   - 检查 Gateway 接口是否清晰
   ↓
3a. 如果审核发现问题 → 使用 fdt-refactor-mock-to-fake skill 修复
   - 将 @patch 装饰器替换为 Fake 实现
   - 将 MagicMock 替换为明确的 Fake/Stub
   - 必要时抽取 Gateway 接口
   → 回到步骤 2 重新审核
   ↓
3b. 如果审核通过 → TDD Green Phase: 使用 tdd skill 编写实现代码
   ↓
4. TDD Refactor Phase: 重构确认
   ↓
5. 运行全量测试确认无回归
```

### 测试替身策略

| 替身类型           | 使用场景                       | 现有实现                                                    |
| ------------------ | ------------------------------ | ----------------------------------------------------------- |
| **Fake**           | 需要真实行为的存储/渠道替身    | `FakeChannel`（test_builder.py）, `InMemoryIPWriter/Reader` |
| **Stub**           | 需要固定返回值的查询           | `_fake_batch_verify`（dns_verify 测试）                     |
| **Fake BatchStep** | Phase 测试中替代真实 BatchStep | 新增：`FakeBatchStep`（返回固定 BatchResult）               |

### 禁止模式

- **禁止** `unittest.mock.patch` 替换模块级属性（如 `patch("module.attribute")`）
- **禁止** `MagicMock` 模拟协议行为 — 使用显式 Fake 类
- **允许** `patch` 仅用于 I/O 边界（如 `patch("requests.get")`），但优先考虑 Fake

### 测试文件组织

| 测试文件                                         | 覆盖范围                               |
| ------------------------------------------------ | -------------------------------------- |
| `tests/unit/pipeline/core/test_batch_step.py`    | BatchStep 协议 + ChannelBatchStep      |
| `tests/unit/pipeline/core/test_batch_factory.py` | BatchFactory 自动发现                  |
| `tests/unit/pipeline/core/test_builder.py`       | PipelineBuilder（含 skip_dynamic_ips） |
| `tests/unit/pipeline/core/test_pipeline.py`      | Pipeline 运行逻辑                      |
| `tests/unit/pipeline/trace_steps/test_phase*.py` | Phase 1-4（使用 FakeBatchStep）        |
| `tests/unit/store/test_json_store.py`            | IPWriter 批量操作                      |
