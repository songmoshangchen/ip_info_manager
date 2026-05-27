# 批量查询层核心（BaseBatchQuery）规格文档

## Why

将 legacy 的 `BaseBatchQuery` 批量查询基类迁移到新架构，作为第 3 层的核心组件。该基类封装了批量查询的通用逻辑：查询循环、进度管理、错误处理、熔断保护、统计输出。子类（Step 3.2-N）只需通过构造函数注入不同渠道适配器即可复用全部逻辑。

## What Changes

* 新增 `src/ip_info/batch/protocols.py`：`ProgressTracker` 协议

* 新增 `src/ip_info/batch/progress.py`：`FileProgressTracker` + `InMemoryProgressTracker` 实现

* 新增 `src/ip_info/batch/query.py`：`BaseBatchQuery` 类 + `BatchResult` 数据类

* 新增 `tests/unit/batch/` 测试目录 + 测试文件

* 依赖第 1 层 `IPDataWriter` 协议（`src/ip_info/store/protocols.py`）

* 依赖第 2 层 `BaseChannelAdapter`（`src/ip_info/channel/adapter.py`）和 `ChannelError` 异常体系（`src/ip_info/channel/errors.py`）

## Impact

* Affected specs: store-layer (`IPDataWriter`), channel-layer-core (`BaseChannelAdapter`, `ChannelError`, `ChannelPermanentError`)

* Affected code: `src/ip_info/batch/` (new), `tests/unit/batch/` (new)

***

## ADDED Requirements

### Requirement: BatchResult 数据类

系统 SHALL 提供 `BatchResult` 数据类封装批量查询结果统计。

```python
@dataclass
class BatchResult:
    success_count: int = 0
    fail_count: int = 0
    total_elapsed: float = 0.0
    stopped_early: bool = False
    stop_reason: str = ""
```

#### Scenario: 成功完成批量查询

* **WHEN** 批量查询正常完成（3 个 IP，2 成功 1 失败）

* **THEN** `BatchResult(success_count=2, fail_count=1, total_elapsed>=0, stopped_early=False, stop_reason="")`

#### Scenario: 熔断提前终止

* **WHEN** 连续网络错误触发熔断，还剩 IP 未处理

* **THEN** `BatchResult(stopped_early=True, stop_reason="circuit_break")`

#### Scenario: 永久错误终止

* **WHEN** `ChannelPermanentError` 导致提前终止

* **THEN** `BatchResult(stopped_early=True, stop_reason="permanent_error")`

#### Scenario: 依赖不可用跳过

* **WHEN** 渠道不可用，跳过所有查询

* **THEN** `BatchResult(success_count=0, fail_count=0, total_elapsed>=0, stopped_early=False, stop_reason="")`

***

### Requirement: ProgressTracker 协议

系统 SHALL 定义 `ProgressTracker` 协议抽象进度跟踪行为，并提供文件和内存两种实现。

```python
@runtime_checkable
class ProgressTracker(Protocol):
    def is_processed(self, ip: str) -> bool: ...
    def mark_processed(self, ip: str) -> None: ...
```

#### Scenario: InMemoryProgressTracker 基本使用

* **WHEN** 创建 `InMemoryProgressTracker` 并调用 `mark_processed("1.1.1.1")`

* **THEN** `is_processed("1.1.1.1")` 返回 `True`，`is_processed("2.2.2.2")` 返回 `False`

#### Scenario: FileProgressTracker 基本使用

* **WHEN** 创建 `FileProgressTracker(path)` 并调用 `mark_processed("1.1.1.1")`

* **THEN** 数据持久化到文件，重新创建实例后 `is_processed("1.1.1.1")` 返回 `True`

#### Scenario: FileProgressTracker 文件不存在

* **WHEN** 进度文件不存在

* **THEN** 所有 `is_processed()` 返回 `False`

#### Scenario: isinstance 检查

* **WHEN** 对实现了 `is_processed` 和 `mark_processed` 的类实例做 `isinstance(obj, ProgressTracker)` 检查

* **THEN** 返回 `True`

***

### Requirement: 构造函数依赖注入

系统 SHALL 通过构造函数注入所有依赖，不依赖全局 `settings` 或 `logger` 实例。

构造函数签名：

```python
class BaseBatchQuery:
    def __init__(
        self,
        channel_name: str,
        channel: BaseChannelAdapter,
        writer: IPDataWriter,
        ips: list[str],
        *,
        delay: float = 0,
        no_validate: bool = False,
        progress_tracker: ProgressTracker | None = None,
        max_consecutive_network_failures: int = 5,
    ): ...
```

#### Scenario: 必需参数

* **WHEN** 创建 `BaseBatchQuery` 实例

* **THEN** 需要提供 `channel_name`、`channel`、`writer`、`ips` 四个必需参数

#### Scenario: 可选参数默认值

* **WHEN** 不提供可选参数

* **THEN** `delay=0`, `no_validate=False`, `progress_tracker=None`, `max_consecutive_network_failures=5`

#### Scenario: IP 列表直接传入

* **WHEN** 传入 `ips=["1.1.1.1", "2.2.2.2"]`

* **THEN** 内部使用该列表作为待查询 IP 集合，不做文件加载

#### Scenario: IP 列表去重

* **WHEN** 传入 `ips=["1.1.1.1", "2.2.2.2", "1.1.1.1"]`

* **THEN** 内部去重后只处理 `["1.1.1.1", "2.2.2.2"]`

***

### Requirement: 进度跟踪（断点续传）

系统 SHALL 通过 `ProgressTracker` 协议支持断点续查。当 `progress_tracker` 为 `None` 时禁用进度跟踪。

**核心原则：只有在数据实际写入 store 时才标记进度。** 所有 ChannelError（无论网络/非网络）都不写入 store，因此不标记进度，下次运行时可重试。错误信息通过日志记录，方便排查。

#### Scenario: 无进度跟踪器（所有 IP 待处理）

* **WHEN** `progress_tracker=None`

* **THEN** 所有 IP 视为待处理，`run()` 处理全部 IP

#### Scenario: 有进度跟踪器（排除已处理 IP）

* **WHEN** `progress_tracker` 中 `"1.1.1.1"` 已标记为 processed

* **THEN** IP 列表中 `"1.1.1.1"` 被排除，只查询未处理的 IP

#### Scenario: 成功查询标记进度

* **WHEN** 一个 IP 查询成功，数据写入 store

* **THEN** 调用 `progress_tracker.mark_processed(ip)` 标记为已处理

#### Scenario: ChannelError 不标记进度（可重试）

* **WHEN** 一个 IP 查询遇到 `ChannelError`（不写入 store）

* **THEN** 不调用 `progress_tracker.mark_processed(ip)`，下次运行时该 IP 可被重试

#### Scenario: ChannelPermanentError 不标记进度

* **WHEN** 一个 IP 查询遇到 `ChannelPermanentError`（不写入 store，渠道被 disabled）

* **THEN** 不调用 `progress_tracker.mark_processed(ip)`，下次运行时该 IP 可被重试

***

### Requirement: 延迟控制

系统 SHALL 通过 `channel.fetch(ip, delay=X)` 传递延迟参数给渠道适配器。

#### Scenario: 设置延迟

* **WHEN** `delay=2.0`

* **THEN** 每次 `channel.fetch()` 调用时传入 `delay=2.0`

#### Scenario: 零延迟

* **WHEN** `delay=0`（默认）

* **THEN** `channel.fetch()` 调用时传入 `delay=0`

***

### Requirement: 错误检测 + 网络错误不写入

系统 SHALL 区分成功、非网络错误、网络错误、永久错误四种结果。

#### Scenario: 成功查询

* **WHEN** `channel.fetch(ip)` 正常返回 dict

* **THEN** 调用 `writer.add_or_update_ip(ip, channel_name, data)`，计为 success

#### Scenario: ChannelError（非网络错误）

* **WHEN** `channel.fetch(ip)` 抛出 `ChannelError`，且错误消息不含网络关键词

* **THEN** 将 `{"raw_error": True, "error_message": str(e)}` 写入 store，计为 failure，不增加熔断计数

#### Scenario: ChannelError（网络错误）

* **WHEN** `channel.fetch(ip)` 抛出 `ChannelError`，且错误消息含网络关键词（timeout、timed out、connectionerror、连接、网络、connection refused、network）

* **THEN** 不写入 store，计为 failure，增加熔断计数

#### Scenario: ChannelPermanentError

* **WHEN** `channel.fetch(ip)` 抛出 `ChannelPermanentError`

* **THEN** `BaseChannelAdapter` 内部设置 `channel.disabled=True`，batch 层检测到 disabled 后立即终止查询循环，不写入 store，返回 `stopped_early=True, stop_reason="permanent_error"`

#### Scenario: 渠道在运行中被 disabled

* **WHEN** 查询循环中某个 IP 触发 `ChannelPermanentError`，导致 `channel.disabled=True`

* **THEN** 后续所有未查询的 IP 均被跳过，不再调用 `channel.fetch()`

#### Scenario: 非 ChannelError 异常

* **WHEN** `channel.fetch(ip)` 抛出非 `ChannelError` 类型的异常

* **THEN** 异常向上传播，不做捕获

***

### Requirement: 熔断保护

系统 SHALL 在连续 N 次网络错误后自动停止查询。

#### Scenario: 触发熔断（默认阈值 5）

* **WHEN** 连续 5 次（默认）网络错误

* **THEN** 停止查询剩余 IP，返回 `stopped_early=True, stop_reason="circuit_break"`

#### Scenario: 成功重置计数

* **WHEN** 连续 2 次网络错误后有 1 次成功查询

* **THEN** 熔断计数器归零，继续正常查询

#### Scenario: 非网络错误不计数

* **WHEN** 连续 5 次非网络错误

* **THEN** 不触发熔断，继续查询

#### Scenario: 自定义熔断阈值

* **WHEN** `max_consecutive_network_failures=3`

* **THEN** 连续 3 次网络错误即触发熔断

***

### Requirement: 依赖检查

系统 SHALL 在查询前检查渠道可用性。

#### Scenario: 渠道 disabled=True

* **WHEN** `channel.disabled=True`

* **THEN** 跳过所有查询，`success_count=0, fail_count=0`

#### Scenario: 渠道 disabled=False

* **WHEN** `channel.disabled=False`

* **THEN** 正常执行查询循环

#### Scenario: no\_validate=False 时调用 validate

* **WHEN** `no_validate=False`

* **THEN** 调用 `channel.validate()`，validate 失败则设 `disabled=True`

#### Scenario: no\_validate=True 时跳过 validate

* **WHEN** `no_validate=True`

* **THEN** 不调用 `channel.validate()`，使用当前 `disabled` 状态

***

### Requirement: 统计接口

系统 SHALL 在 `run()` 完成后返回 `BatchResult` 统计信息。

#### Scenario: 成功和失败计数

* **WHEN** 查询了 3 个 IP，2 个成功 1 个失败

* **THEN** `BatchResult.success_count=2, fail_count=1`

#### Scenario: 总耗时记录

* **WHEN** 查询完成

* **THEN** `BatchResult.total_elapsed >= 0`

#### Scenario: 总 IP 数可通过属性获取

* **WHEN** 构造完成

* **THEN** `instance.total_count` 返回去重后的 IP 总数

#### Scenario: 待处理 IP 数可通过属性获取

* **WHEN** 构造完成且 progress\_tracker 标记了部分 IP

* **THEN** `instance.pending_count` 返回排除已处理后剩余的 IP 数

***

## 与 legacy 的差异

| 方面                    | Legacy                                                                         | 新架构                                          |
| --------------------- | ------------------------------------------------------------------------------ | -------------------------------------------- |
| **类性质**               | ABC（抽象方法 `_query_ip`、`_print_result`）                                          | 具体类（通过构造函数注入渠道）                              |
| **IP 来源**             | `ip_file` 文件路径，内部加载去重                                                          | `ips: list[str]`，调用方负责加载                     |
| **进度跟踪**              | `_load_progress()`/`_save_progress()` 文件操作                                     | `ProgressTracker` 协议 + 可选实现                  |
| **错误处理**              | `_query_ip()` 返回含 `raw_error`/`error` 的 dict                                   | `channel.fetch()` 抛 `ChannelError` 异常        |
| **依赖注入**              | `self.settings`/`self.logger`/`self.ip_writer` 紧耦合                             | 构造函数注入 `channel`/`writer`/`delay`            |
| **PID 管理**            | `hasattr(self, '_pid_mgr')` 检查                                                 | **移除**（不属于批量查询层职责）                           |
| **日志**                | 注入的 `self.logger`                                                              | `logging.getLogger(__name__)`                |
| **delay**             | `_get_delay()` 从 settings 获取                                                   | 构造函数 `delay` 参数                              |
| **返回值**               | 设置 `self.run_stats` dict                                                       | 返回 `BatchResult` 数据类                         |
| **`_print_result`**   | 抽象方法                                                                           | **移除**（非核心逻辑，由调用方处理）                         |
| **`_query_ip`**       | 抽象方法                                                                           | **移除**（使用 `channel.fetch()`）                 |
| **`_do_validate`**    | 可覆盖钩子                                                                          | **移除**（使用 `channel.validate()`）              |
| **`_get_delay`**      | 从 settings 动态获取                                                                | **移除**（构造函数参数）                               |
| **KeyboardInterrupt** | 捕获 + sys.exit(0)                                                               | **移除**（由调用方处理）                               |
| **batch\_mode**       | 类属性 + `_cross_channels`（single/cross/standalone）                               | **移除**（固定写入 `channel_name`）                  |
| **ETA 估算**            | `estimate_eta()` 方法内置                                                          | **移除**（不属于核心逻辑，后续工具模块处理）                     |
| **load\_stats**       | 包含 raw\_count/unique\_count/duplicate\_count/already\_processed/pending\_count | **简化**：提供 `total_count` 和 `pending_count` 属性 |

