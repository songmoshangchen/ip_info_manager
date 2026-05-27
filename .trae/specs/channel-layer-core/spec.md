# 渠道层核心（Channel Layer Core）规格文档

> **对应重构方案**：第六节 "Skills 使用推荐"，Step 2.1-2.4
>
> **Skills 链**：`tdd` → `git-commit`（Step 2.1-2.3），`brainstorming` → `tdd` → `git-commit`（Step 2.4）
>
> **范围**：仅 Step 2.1-2.4（ChannelProtocol + ChannelRegistry + InMemoryChannel + BaseChannelAdapter），不含具体渠道迁移

## Why

渠道层是 ip_info_manager 系统的信息采集核心。当前 `legacy/protocols.py` 中混放了 `ChannelProtocol`、`ChannelFetcher`、`InMemoryChannel`、`ChannelRegistry` 以及存储层的类。需要将渠道层的核心协议、注册表、测试替身和适配器基类独立到 `src/ip_info/channel/` 包中，去除 Settings 依赖，统一错误处理策略。

## What Changes

- 从 `legacy/protocols.py` 提取 `ChannelProtocol` 和 `ChannelFetcher`，放入 `src/ip_info/channel/protocols.py`
- 新增 `ChannelError`（临时性/可重试）和 `ChannelPermanentError`（永久性/禁用渠道）异常类，放入 `src/ip_info/channel/errors.py`
- 从 `legacy/protocols.py` 提取 `ChannelRegistry`，放入 `src/ip_info/channel/registry.py`
- 从 `legacy/protocols.py` 提取 `InMemoryChannel` 测试替身，放入 `src/ip_info/channel/in_memory.py`
- 新建 `src/ip_info/channel/adapter.py`，定义 `BaseChannelAdapter` 适配器基类，统一 validate / fetch / disabled / format_output / apply_delay 模式
- 新建 `src/ip_info/channel/__init__.py` 统一导出
- 新增 `tests/unit/channel/` 存放新测试

## Impact

- Affected specs: 依赖 `store-layer` spec（`IPDataWriter` Protocol）
- Affected code: `src/ip_info/channel/`（全新）、`tests/unit/channel/`（全新）
- 不修改 `legacy/` 中的任何文件

---

## ADDED Requirements

### Requirement: ChannelProtocol 协议

系统 SHALL 提供 `ChannelProtocol` Protocol（`@runtime_checkable`），定义渠道接口：

```python
@runtime_checkable
class ChannelProtocol(Protocol):
    channel_name: str
    def validate(self) -> bool: ...
    def fetch(self, ip: str, **kwargs) -> dict: ...
```

#### Scenario: isinstance 检查通过
- **WHEN** 一个类有 `channel_name` 属性（str），且实现了 `validate()` -> bool 和 `fetch(ip, **kwargs)` -> dict
- **THEN** `isinstance(instance, ChannelProtocol)` 返回 `True`

#### Scenario: 缺少 channel_name 的类不匹配
- **WHEN** 一个类实现了 `validate()` 和 `fetch()` 但没有 `channel_name` 属性
- **THEN** `isinstance(instance, ChannelProtocol)` 返回 `False`

---

### Requirement: ChannelFetcher 协议

系统 SHALL 提供 `ChannelFetcher` Protocol（`@runtime_checkable`），定义可调用 fetcher 接口：

```python
@runtime_checkable
class ChannelFetcher(Protocol):
    def __call__(self, ip: str, **kwargs) -> dict: ...
```

#### Scenario: isinstance 检查通过
- **WHEN** 一个可调用对象接受 `(ip: str, **kwargs)` -> dict 签名
- **THEN** `isinstance(fn, ChannelFetcher)` 返回 `True`

---

### Requirement: ChannelError 异常体系

系统 SHALL 提供两级渠道异常，用于区分临时性错误和永久性错误：

```python
class ChannelError(Exception):
    """临时性错误（可重试）：网络超时、连接失败、限流等"""

class ChannelPermanentError(ChannelError):
    """永久性错误（不可重试）：API Key 无效、Cookie 过期等"""
```

#### Scenario: ChannelError 是临时性错误
- **WHEN** 渠道 fetch 过程中发生网络超时
- **THEN** 抛出 `ChannelError`，上层捕获后**不写入存储**，不改变 `disabled` 状态

#### Scenario: ChannelPermanentError 是永久性错误
- **WHEN** 渠道 fetch 过程中发现 API Key 无效
- **THEN** 抛出 `ChannelPermanentError`，上层捕获后**不写入存储**，同时将渠道 `disabled` 设为 `True`

#### Scenario: ChannelPermanentError 是 ChannelError 的子类
- **WHEN** 检查 `issubclass(ChannelPermanentError, ChannelError)`
- **THEN** 返回 `True`，允许上层统一捕获 `ChannelError`

#### Scenario: 错误消息可读
- **WHEN** 抛出 `ChannelError("连接超时: 1.2.3.4")`
- **THEN** `str(error)` 返回 `"连接超时: 1.2.3.4"`

---

### Requirement: ChannelRegistry 注册表

系统 SHALL 提供 `ChannelRegistry` 类，管理渠道的注册、查找、验证和委托调用。

#### Scenario: 注册渠道
- **WHEN** 调用 `registry.register(channel)` 且 channel 满足 `ChannelProtocol`
- **THEN** 通过 `registry.get(channel.channel_name)` 可获取该渠道

#### Scenario: 注册非 ChannelProtocol 对象抛出 TypeError
- **WHEN** 调用 `registry.register(obj)` 且 obj 不满足 `ChannelProtocol`
- **THEN** 抛出 `TypeError`，消息包含实际类型名

#### Scenario: 重复注册覆盖旧渠道（S25）
- **WHEN** 注册同名渠道两次
- **THEN** 第二次注册覆盖第一次，`get()` 返回新的渠道实例

#### Scenario: 获取不存在的渠道返回 None（S26）
- **WHEN** 调用 `registry.get('nonexistent')`
- **THEN** 返回 `None`（不抛异常）

#### Scenario: 列出所有已注册渠道名（S21）
- **WHEN** 注册了 3 个渠道后调用 `registry.list_names()`
- **THEN** 返回包含 3 个渠道名的 list

#### Scenario: 列出所有已注册渠道实例（S21）
- **WHEN** 注册了 3 个渠道后调用 `registry.list_channels()`
- **THEN** 返回包含 3 个渠道实例的 list

#### Scenario: 验证单个渠道（S28）
- **WHEN** 调用 `registry.validate('rdns_ptr')` 且该渠道的 `validate()` 返回 True
- **THEN** 返回 `True`

#### Scenario: 验证不存在的渠道返回 False（S28）
- **WHEN** 调用 `registry.validate('nonexistent')`
- **THEN** 返回 `False`（不抛异常）

#### Scenario: 批量验证所有渠道（S22）
- **WHEN** 调用 `registry.validate_all()`
- **THEN** 返回 dict，key 为渠道名，value 为该渠道 `validate()` 的结果

#### Scenario: 委托 fetch 调用成功（S23）
- **WHEN** 调用 `registry.fetch('rdns_ptr', '1.2.3.4')` 且该渠道已注册且 fetch 成功
- **THEN** 返回该渠道 `fetch('1.2.3.4')` 的结果 dict

#### Scenario: 委托 fetch 透传 ChannelError（S27）
- **WHEN** 调用 `registry.fetch('ipinfo_api', '1.2.3.4')` 且该渠道 fetch 抛出 `ChannelError`
- **THEN** `ChannelError` 直接透传给调用者，不吞异常

#### Scenario: 委托 fetch 不存在的渠道抛出 KeyError（S27）
- **WHEN** 调用 `registry.fetch('nonexistent', '1.2.3.4')`
- **THEN** 抛出 `KeyError`，消息包含渠道名

---

### Requirement: InMemoryChannel 测试替身

系统 SHALL 提供 `InMemoryChannel` 类，实现 `ChannelProtocol`，用于测试。支持通过构造函数配置 validate 和 fetch 的行为。

#### Scenario: 默认行为
- **WHEN** 构造 `InMemoryChannel()` 不传参数
- **THEN** `channel_name` 为 `'test_channel'`，`validate()` 返回 `True`，`fetch()` 返回空 dict

#### Scenario: 自定义名称
- **WHEN** 构造 `InMemoryChannel(name='my_channel')`
- **THEN** `channel_name` 为 `'my_channel'`

#### Scenario: 自定义 validate 结果
- **WHEN** 构造 `InMemoryChannel(validate_result=False)`
- **THEN** `validate()` 返回 `False`

#### Scenario: 自定义 fetch 结果
- **WHEN** 构造 `InMemoryChannel(fetch_result={'country': 'CN'})`
- **THEN** `fetch('1.2.3.4')` 返回 `{'country': 'CN'}`

#### Scenario: fetch 可配置抛出异常
- **WHEN** 构造 `InMemoryChannel(fetch_error=ChannelError("模拟超时"))`
- **THEN** `fetch('1.2.3.4')` 抛出 `ChannelError("模拟超时")`

#### Scenario: 记录 fetch 调用
- **WHEN** 调用 `fetch('1.2.3.4', timeout=5)` 后检查 `fetch_calls`
- **THEN** `fetch_calls` 包含 `('1.2.3.4', {'timeout': 5})` 元组

#### Scenario: fetch 返回副本（非引用）
- **WHEN** 调用 `fetch('1.2.3.4')` 两次并修改返回值
- **THEN** 两次返回的是独立副本，互不影响

#### Scenario: 满足 ChannelProtocol
- **WHEN** 创建 `InMemoryChannel` 实例
- **THEN** `isinstance(instance, ChannelProtocol)` 返回 `True`

---

### Requirement: BaseChannelAdapter 适配器基类

系统 SHALL 提供 `BaseChannelAdapter` 抽象基类（ABC），统一渠道适配器的通用模式。子类只需实现 `_request()` 和可选的 `_validate_key()` / `_parse()`。

**设计决策（brainstorming 确认）**：
1. `_request()` 只返回成功结果，失败时抛 `ChannelError` / `ChannelPermanentError`
2. `_request()` 负责请求+判断成功/失败（包括 HTTP 200 但业务失败的场景），爬虫类在 `_parse()` 中解析
3. `fetch()` 调用链：`delay → _request() → _parse() → format_output(query_time)`
4. `fetch()` 从 kwargs 中弹出 `delay` 参数，不传给 `_request()`
5. `fetch()` 捕获 `ChannelPermanentError` 时设 `disabled=True`，`ChannelError` 不改变 disabled
6. 基类不内置 logger，子类自行管理日志

```python
class BaseChannelAdapter(ABC):
    channel_name: str = ""
    disabled: bool = False

    @abstractmethod
    def _request(self, ip: str, **kwargs) -> dict | str: ...

    def _validate_key(self) -> None: ...
    def _parse(self, raw, ip: str) -> dict: ...
    def validate(self) -> bool: ...
    def fetch(self, ip: str, **kwargs) -> dict: ...
```

#### Scenario: validate 成功
- **WHEN** 子类的 `_validate_key()` 正常返回（不抛异常）
- **THEN** `validate()` 返回 `True`，`disabled` 被设为 `False`

#### Scenario: validate 失败（_validate_key 抛出异常）
- **WHEN** 子类的 `_validate_key()` 抛出任意异常
- **THEN** `validate()` 捕获异常，返回 `False`，`disabled` 被设为 `True`

#### Scenario: disabled 标志替代 sys.exit 的作用
- **WHEN** validate() 返回 False 或 fetch() 抛出 ChannelPermanentError
- **THEN** 渠道的 `disabled` 被设为 `True`，上层（批量查询层）检查 `disabled` 后跳过该渠道的后续 IP 查询
- **NOTE**：这替代了 legacy 中 `sys.exit(1)` 的"终止后续查询"功能，但粒度更细（只禁用单个渠道，不终止进程）

#### Scenario: validate 是无状态调用
- **WHEN** 上层调用 `validate()` 时
- **THEN** 每次都会重新执行 `_validate_key()`，根据结果更新 `disabled` 标志
- **NOTE**：上层自行决定何时调用 validate()（如批次开始前调用一次），渠道层不自动在每次 fetch 前调用 validate

#### Scenario: fetch 标准调用链
- **WHEN** 调用 `fetch('1.2.3.4', delay=0)` 且 `_request()` 返回 `{'country': 'CN'}`
- **THEN** 返回结果包含 `_request()` 返回的数据 + 自动注入的 `query_time` 字段

#### Scenario: fetch 透传 kwargs 给 _request
- **WHEN** 调用 `fetch('1.2.3.4', timeout=5, key='abc')`
- **THEN** `_request('1.2.3.4', timeout=5, key='abc')` 被调用

#### Scenario: fetch 网络错误抛出 ChannelError（S36/S46/S56）
- **WHEN** `_request()` 抛出 `ChannelError("连接超时")`
- **THEN** `fetch()` 直接透传 `ChannelError`，不返回 dict，不写入存储

#### Scenario: fetch 永久错误抛出 ChannelPermanentError（S38/S49）
- **WHEN** `_request()` 抛出 `ChannelPermanentError("API Key 无效")`
- **THEN** `fetch()` 透传 `ChannelPermanentError`，同时将 `disabled` 设为 `True`

#### Scenario: _parse 覆盖（爬虫类渠道）
- **WHEN** 子类覆盖 `_parse()` 将 HTML str 解析为 dict
- **THEN** `fetch()` 调用 `_parse()` 后返回解析结果 + `query_time`

#### Scenario: _parse 默认实现
- **WHEN** 子类未覆盖 `_parse()`，`_request()` 返回 dict
- **THEN** `_parse()` 直接返回该 dict（透传）

#### Scenario: delay 参数触发延迟
- **WHEN** 调用 `fetch('1.2.3.4', delay=0.1)`
- **THEN** 在调用 `_request()` 前有至少 0.1 秒的延迟
- **NOTE**：`delay` 参数由 `fetch()` 消费，不传给 `_request()`

#### Scenario: 满足 ChannelProtocol
- **WHEN** 创建一个实现了 `_request()` 的子类实例
- **THEN** `isinstance(instance, ChannelProtocol)` 返回 `True`

#### Scenario: 未实现 _request 的子类无法实例化
- **WHEN** 定义一个子类继承 `BaseChannelAdapter` 但未实现 `_request()`
- **THEN** 实例化时抛出 `TypeError`

---

## MODIFIED Requirements

无（全新构建）。

## REMOVED Requirements

### Requirement: 对 config.Settings 的直接依赖
**Reason**: 渠道核心层（协议+注册表+基类）不应直接依赖应用配置层。子类通过构造函数或 kwargs 接收配置。
**Migration**: 具体渠道迁移时，子类自行管理配置注入方式。

### Requirement: create_default_registry() 工厂函数
**Reason**: 该函数依赖所有具体渠道类的 import，属于应用组装层，不属于渠道核心层。
**Migration**: 在应用层（pipeline/scenario）或独立的工厂模块中实现。

### Requirement: 模块级函数（validate_channel_key / request_channel / fetch_channel / main）
**Reason**: 新架构使用类+方法替代模块级函数。`BaseChannelAdapter` 的 `_request()` / `_validate_key()` / `fetch()` 取代了模块级函数。
**Migration**: 具体渠道迁移时，将模块级函数转为类方法。

### Requirement: sys.exit(1) 作为 validate 失败信号
**Reason**: sys.exit(1) 会终止整个进程，不适合作为库代码的错误信号。
**Migration**: 替代方案是"异常 + disabled 标志"的组合：
1. `_validate_key()` 失败时抛出异常，基类 `validate()` 捕获后返回 False + 设 disabled=True
2. `_request()` 遇到永久错误时抛出 `ChannelPermanentError`，基类设 disabled=True
3. 上层（批量查询层）在每次查询前检查 `channel.disabled`，为 True 则跳过该渠道的后续 IP
4. 这实现了与 sys.exit 相同的"终止后续查询"效果，但粒度更细（只禁用单个渠道，不终止进程）

### Requirement: {"raw_error": True, "error_message": "..."} 错误返回格式
**Reason**: 新架构使用异常（ChannelError / ChannelPermanentError）替代错误 dict，上层通过 try/except 区分成功和失败，不再通过检查返回值中的 raw_error 字段。
**Migration**: 成功返回 dict，失败抛异常。上层捕获 ChannelError 后不写入存储。

---

## 数据结构约定

### 成功返回格式（所有渠道统一）
```json
{
  "country": "CN",
  "org": "ISP-A",
  "query_time": "2026-05-20T10:30:00.000000"
}
```

### 错误处理约定（异常替代 dict）

| 错误类型 | 异常类 | 行为 |
|---------|--------|------|
| 网络超时 | `ChannelError` | 不写入存储，不改变 disabled |
| 连接失败 | `ChannelError` | 不写入存储，不改变 disabled |
| 限流 | `ChannelError` | 不写入存储，不改变 disabled |
| 页面解析失败 | `ChannelError` | 不写入存储，不改变 disabled |
| API Key 无效 | `ChannelPermanentError` | 不写入存储，设 disabled=True |
| Cookie 过期 | `ChannelPermanentError` | 不写入存储，设 disabled=True |
| 依赖缺失 | `ChannelError` | 不写入存储，不改变 disabled（S31/S32） |

关键约定：
- `fetch()` 成功返回 dict（含 query_time），失败抛异常（不返回 dict）
- 上层通过 `try/except ChannelError` 统一捕获，不检查返回值
- `BaseChannelAdapter.fetch()` 保证成功返回的 dict 包含 `query_time`

## 与 legacy 的差异

| 项目 | Legacy | 新实现 |
|------|--------|--------|
| Settings 依赖 | 每个渠道导入专属 Settings 类 | **无依赖**，基类不含配置 |
| disabled 标志 | 7/11 渠道有，4/11 无 | **统一提供**，所有子类都有 |
| apply_delay / format_output | 11 份重复定义 | **基类统一提供**，1 份 |
| validate() 的 try/except | 捕获 SystemExit（sys.exit(1)） | **捕获异常**，不再 sys.exit |
| fetch 错误处理 | 返回 `{"raw_error": True, ...}` dict | **抛出 ChannelError 异常** |
| 永久错误 vs 临时错误 | 无区分 | **ChannelPermanentError vs ChannelError** |
| 模块级函数 | 5 个标准函数/文件 | **类方法替代** |
| CLI main() 函数 | 每个渠道文件末尾 | **不在核心层**，由上层处理 |
