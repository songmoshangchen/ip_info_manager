# 架构深化优化 Spec

## Why

第二轮架构审查发现 10 个深化机会：Pipeline 双生子导致编排逻辑散落在脚本中、PipelineContext 浅层透传未真正简化 Phase 接口、渠道禁用逻辑重复、BatchTagger 鸭子类型读取有静默失效风险。这些问题导致局部性差、杠杆低、可测试性受限。

## What Changes

- **合并 Pipeline 双生子**：删除 `builder.py` 中的简单 `Pipeline`，让 `PipelineBuilder` 构建 `pipeline.py` 中的完整 `Pipeline`
- **Phase 构造函数去重**：Phase 只接受 `context: PipelineContext` + 自身特有参数，去掉 `writer`/`reader`/`progress_tracker`/`domain_cache` 独立参数
- **渠道禁用逻辑去重**：删除 Phase 内的 `channel.disabled` 检查，统一由 `run_concurrent()` 处理
- **BatchTagger 修复**：用 `self._reader.get_channel_data()` 替代鸭子类型 `getattr(self._writer, "get_channel_data")`
- **run_pipeline.py 迁移到 Builder**：用 `PipelineBuilder` 重写脚本，内化 filter_ips 为阶段间钩子
- **_try_flush 统一**：提取公共 `flush_progress()` 工具函数
- **InMemoryIPWriter 去冗余**：移除读取方法，统一使用 `InMemoryIPReader`

## Impact

- Affected specs: `build-pipeline-framework`, `implement-pipeline-phases`, `store-layer`
- Affected code:
  - `src/ip_info/pipeline/builder.py` — 合并到 `pipeline.py`
  - `src/ip_info/pipeline/pipeline.py` — 接受 Builder 构建
  - `src/ip_info/pipeline/context.py` — 无变化
  - `src/ip_info/pipeline/phases/phase1-4` — 构造函数简化
  - `src/ip_info/pipeline/filter_ips.py` — 集成到 Builder
  - `src/ip_info/processors/tagger/runner.py` — 修复鸭子类型
  - `src/ip_info/store/in_memory.py` — InMemoryIPWriter 去冗余
  - `src/ip_info/batch/core/query.py` — _try_flush 提取
  - `src/ip_info/batch/core/concurrent.py` — _try_flush 提取
  - `src/ip_info/processors/core/base.py` — _try_flush 提取
  - `scripts/run_pipeline.py` — 用 Builder 重写

## ADDED Requirements

### Requirement: PipelineBuilder 构建完整 Pipeline

系统 SHALL 让 `PipelineBuilder.build()` 返回 `pipeline.py` 中的完整 `Pipeline` 实例（支持 `register()`、`from_phase`/`only_phase`/`skip_phases`、失败中断），而非 `builder.py` 中的简单 dataclass。

#### Scenario: Builder 构建完整 Pipeline
- **WHEN** 调用 `PipelineBuilder(context).with_ips(ips).add_phase(phase1).add_phase(phase2).build()`
- **THEN** 返回的 Pipeline 支持 `from_phase`/`only_phase`/`skip_phases` 和失败中断

#### Scenario: Builder 内化 filter_ips
- **WHEN** 调用 `builder.skip_dynamic_ips()` 并 `build()`
- **THEN** Pipeline 在 Phase 2→3 之间自动执行 `filter_dynamic_ips`，Phase 3/4 自动接收 `skip_ips`

### Requirement: Phase 构造函数只接受 context + 特有参数

系统 SHALL 让 Phase 1-4 的构造函数只接受 `context: PipelineContext` + 自身特有参数（如 `rules_dir`、`skip_ips`、渠道实例），不再接受 `writer`/`reader`/`progress_tracker`/`domain_cache` 独立参数。**BREAKING**

#### Scenario: Phase 从 context 获取公共依赖
- **WHEN** 构造 `BasicCollectPhase(ips, context=ctx, ipinfo_channel=ch1, rdns_channel=ch2)`
- **THEN** Phase 从 `ctx.writer`/`ctx.reader`/`ctx.progress_tracker` 获取依赖

#### Scenario: 不传 context 报错
- **WHEN** 构造 `BasicCollectPhase(ips, ipinfo_channel=ch1, rdns_channel=ch2)` 不传 context
- **THEN** 抛出 `TypeError` 或 `ValueError`

### Requirement: 渠道禁用逻辑统一到 run_concurrent

系统 SHALL 让渠道禁用检查和日志只存在于 `run_concurrent()` 中，Phase 不再重复检查 `channel.disabled`。

#### Scenario: 禁用渠道由 concurrent 处理
- **WHEN** Phase 1 的 `ipinfo_channel.disabled = True`
- **THEN** Phase 1 的 `run()` 不做 disabled 检查，`run_concurrent()` 统一跳过并记录日志

### Requirement: BatchTagger 使用显式 reader

系统 SHALL 让 `BatchTagger._read_channel_data()` 使用 `self._reader.get_channel_data()` 替代 `getattr(self._writer, "get_channel_data")`。

#### Scenario: accumulate 模式正确读取已有标签
- **WHEN** BatchTagger 以 accumulate 模式运行，且 writer 是纯 `IPDataWriter`（无 `get_channel_data` 方法）
- **THEN** Tagger 通过 `self._reader.get_channel_data()` 正确读取已有标签并合并

### Requirement: flush_progress 统一工具函数

系统 SHALL 提供公共 `flush_progress(tracker)` 函数，替代 `batch/core/query.py`、`batch/core/concurrent.py`、`processors/core/base.py` 中的三处重复 `_try_flush`。

#### Scenario: 统一 flush 调用
- **WHEN** 任何模块需要 flush 进度
- **THEN** 调用 `flush_progress(tracker)`，无需重复实现鸭子类型检查

### Requirement: InMemoryIPWriter 只实现 IPDataWriter

系统 SHALL 让 `InMemoryIPWriter` 只实现 `IPDataWriter` 协议的写入方法，读取方法由 `InMemoryIPReader` 独立提供。**BREAKING**

#### Scenario: Writer 不再有读取方法
- **WHEN** 测试需要读取写入的数据
- **THEN** 使用 `InMemoryIPReader` 实例，而非 `InMemoryIPWriter` 的读取方法

### Requirement: run_pipeline.py 使用 PipelineBuilder

系统 SHALL 让 `run_pipeline.py` 使用 `PipelineBuilder` 组装 Phase 和渠道，脚本只负责解析参数和调用 `builder.build().run()`。

#### Scenario: 脚本简化为 Builder 调用
- **WHEN** 运行 `python run_pipeline.py`
- **THEN** 脚本创建 Builder、注册渠道和 Phase、调用 `build().run()`，不再手动创建每个 Phase

## MODIFIED Requirements

### Requirement: PipelineBuilder API

`PipelineBuilder` 新增 `with_filter()` 方法注册阶段间过滤器，`build()` 时自动在 Phase 之间插入过滤逻辑。

## REMOVED Requirements

### Requirement: builder.py 中的简单 Pipeline

**Reason**: 与 `pipeline.py` 中的完整 Pipeline 重复，合并后只保留一个
**Migration**: `builder.py` 中的 `Pipeline` dataclass 删除，`PipelineBuilder.build()` 返回 `pipeline.py` 的 `Pipeline`
