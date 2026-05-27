# Pipeline 编排框架 Spec

## Why

需要将已完成的 store/channel/batch/processors 各层组件串联为完整的 IP 溯源工作流。本次只实现编排框架（Phase Protocol + Pipeline 类），不实现具体阶段逻辑。

## What Changes

- 新建 `src/ip_info/pipeline/` 目录，包含 phase.py 和 pipeline.py
- 新建 `tests/unit/pipeline/` 测试目录

## Impact

- Affected code: `src/ip_info/pipeline/`（新建）
- 后续 Phase 1-5 实现将依赖此框架

## ADDED Requirements

### Requirement: Phase Protocol

系统 SHALL 提供 `Phase` Protocol，定义阶段接口：

```python
@runtime_checkable
class Phase(Protocol):
    @property
    def name(self) -> str: ...
    def run(self) -> PhaseResult: ...
```

#### Scenario: Protocol 一致性
- **WHEN** 一个类实现了 `name` 属性和 `run() -> PhaseResult` 方法
- **THEN** `isinstance(instance, Phase)` 返回 True

### Requirement: PhaseResult 数据类

系统 SHALL 提供 `PhaseResult` 数据类：

```python
@dataclass
class PhaseResult:
    success: bool = True
    message: str = ""
    elapsed: float = 0.0
    data: dict = field(default_factory=dict)
```

### Requirement: Pipeline 编排器

系统 SHALL 提供 `Pipeline` 类，负责阶段注册和执行。

**核心设计：阶段内各渠道/处理器并行执行，而非逐 IP 串行。** 例如 Phase 1 包含 ipinfo_api 和 rdns_ptr 两个渠道，它们各自独立批量处理所有 IP，全部完成后才进入 Phase 2。

#### Scenario: 注册阶段
- **WHEN** 调用 `pipeline.register(phase)`
- **THEN** 阶段被添加到执行列表末尾

#### Scenario: 顺序执行
- **WHEN** 调用 `pipeline.run()`
- **THEN** 按注册顺序依次执行所有阶段

#### Scenario: from_phase 控制
- **WHEN** 调用 `pipeline.run(from_phase=3)`
- **THEN** 跳过阶段 1-2，从阶段 3 开始执行

#### Scenario: only_phase 控制
- **WHEN** 调用 `pipeline.run(only_phase=2)`
- **THEN** 只执行阶段 2

#### Scenario: skip_phases 控制
- **WHEN** 调用 `pipeline.run(skip_phases={4, 5})`
- **THEN** 跳过阶段 4 和 5，执行其余阶段

#### Scenario: 阶段失败处理
- **WHEN** 某阶段 `run()` 返回 `PhaseResult(success=False)`
- **THEN** 后续阶段不执行，Pipeline 返回失败结果

#### Scenario: 空管道
- **WHEN** 没有注册任何阶段就调用 `run()`
- **THEN** 返回空的 PipelineResult

### Requirement: PipelineResult 数据类

系统 SHALL 提供 `PipelineResult` 数据类：

```python
@dataclass
class PipelineResult:
    success: bool = True
    total_elapsed: float = 0.0
    phase_results: dict[str, PhaseResult] = field(default_factory=dict)
    failed_phase: str = ""
```

### Requirement: 日志输出

Pipeline 执行时 SHALL 输出阶段开始/完成的日志：

#### Scenario: 阶段开始
- **WHEN** 阶段开始执行
- **THEN** 输出 INFO 日志：`阶段 N: {phase.name}`

#### Scenario: 阶段完成
- **WHEN** 阶段执行完成
- **THEN** 输出 INFO 日志：`阶段 N 完成: {result.message} ({elapsed:.1f}s)`

### Requirement: 开发流程

实现过程 SHALL 遵循 TDD + git-commit 循环：
1. 先写测试，再写实现
2. 每个逻辑单元完成后 git commit
3. 测试全部 mock 到存储层（InMemoryIPWriter/InMemoryIPReader）

## REMOVED Requirements

### Requirement: 具体阶段逻辑（Phase 1-5）
**Reason**: 本次只实现编排框架，具体阶段逻辑在下一步实现
**Migration**: 下一个 spec 实现 Phase 1-5

### Requirement: PidManager
**Reason**: 本次不实现进程管理
**Migration**: 后续按需添加

### Requirement: ProgressManager 多阶段进度
**Reason**: 各阶段使用各自的 ProgressTracker，不需要统一管理
**Migration**: 各 Phase 内部自行管理进度
