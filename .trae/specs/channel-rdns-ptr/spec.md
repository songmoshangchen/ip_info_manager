# rdns_ptr 渠道迁移规格文档

> **对应重构方案**：Step 2.5（第一个具体渠道迁移）
>
> **Skills 链**：`/spec`（本文档）→ 用户审核 → `tdd` → `git-commit`
>
> **Legacy 源文件**：`legacy/channel/rdns_ptr.py`
>
> **PRD 需求**：S72-S78

## Why

rdns_ptr 是 11 个待迁移渠道中最简单的一个。它不依赖外部 API Key / Cookie，仅使用 Python 标准库 `socket.gethostbyaddr()` 进行 DNS 反向解析。迁移它可以为后续渠道建立可复用的迁移模式和测试模板。

## What Changes

- 新建 `src/ip_info/channel/rdns_ptr.py`，包含 `RdnsPtrChannel` 类（继承 `BaseChannelAdapter`）
- 新建 `tests/unit/channel/test_rdns_ptr.py`，包含完整单元测试
- 不修改 `legacy/` 中的任何文件

## Impact

- Affected specs: 依赖 `channel-layer-core` spec（`BaseChannelAdapter`、`ChannelError`、`ChannelPermanentError`）
- Affected code: `src/ip_info/channel/`（新增文件）、`tests/unit/channel/`（新增文件）

---

## ADDED Requirements

### Requirement: RdnsPtrChannel 类

系统 SHALL 提供 `RdnsPtrChannel` 类，继承 `BaseChannelAdapter`，封装 DNS 反向解析查询逻辑。

```python
class RdnsPtrChannel(BaseChannelAdapter):
    channel_name = "rdns_ptr"

    def __init__(self, timeout: float = 3.0): ...
    def _request(self, ip: str, **kwargs) -> dict: ...
```

**构造函数约定**：
- `timeout`：DNS 查询超时时间（秒），默认 3.0
- 不依赖 `config.Settings`，通过构造函数注入

**不覆盖 `_validate_key()`**：
- rdns_ptr 不依赖 API Key / Cookie，无需预验证
- 使用基类默认的空实现，`validate()` 永远返回 `True`
- 如果 DNS 真的不可用，`_request()` 会自然失败并抛 `ChannelError`
- 设计决策（brainstorming 确认）：YAGNI — 测试 8.8.8.8 不能保证所有 IP 都能解析，实际错误在 `_request` 中自然暴露

---

### Requirement: _request — DNS 反向解析查询（S72-S78）

`_request(ip)` SHALL 使用 `socket.gethostbyaddr(ip)` 执行 DNS 反向解析，并根据异常类型区分"正常无结果"和"网络错误"。

#### Scenario: 查询成功（有 PTR 记录）（S72、S74）
- **WHEN** `socket.gethostbyaddr(ip)` 返回 `(hostname, aliases, ip_addresses)`
- **THEN** 返回 dict：
  ```python
  {
      "query_ip": ip,
      "hostname": "dns.google",
      "aliases": ["dns.google"],
      "ip_addresses": ["8.8.8.8"],
      "ptr_count": 2,  # len(aliases) + 1
      "has_ptr": True
  }
  ```

#### Scenario: 无 PTR 记录（socket.herror）（S73、S75）
- **WHEN** `socket.gethostbyaddr(ip)` 抛出 `socket.herror`
- **THEN** 返回 dict：
  ```python
  {
      "query_ip": ip,
      "has_ptr": False,
      "error_type": "herror",
      "error_message": str(e)
  }
  ```
- **NOTE**：这不是错误，只是该 IP 无反向解析记录

#### Scenario: 地址查询失败（socket.gaierror）（S73、S75）
- **WHEN** `socket.gethostbyaddr(ip)` 抛出 `socket.gaierror`
- **THEN** 返回 dict：
  ```python
  {
      "query_ip": ip,
      "has_ptr": False,
      "error_type": "gaierror",
      "error_message": str(e)
  }
  ```

#### Scenario: DNS 查询超时（socket.timeout）（S76、S77）
- **WHEN** `socket.gethostbyaddr(ip)` 抛出 `socket.timeout`
- **THEN** 返回 dict：
  ```python
  {
      "query_ip": ip,
      "has_ptr": False,
      "error_type": "timeout",
      "error_message": "查询超时（超过 {timeout} 秒）"
  }
  ```
- **NOTE**：DNS 超时是常见现象，不代表网络异常，不抛 ChannelError。上层仍会写入存储（has_ptr=False 的结果）

#### Scenario: 网络不可用（非 DNS 超时的真正连接失败）（S78）
- **WHEN** `socket.gethostbyaddr(ip)` 抛出非预期的异常（如 `OSError`、`ConnectionError`）
- **THEN** 抛出 `ChannelError`，消息格式为 `"RDNS 查询网络错误: {ip} - {error}"`
- **NOTE**：这是真正的网络错误，上层捕获后**不写入存储**，计入通用熔断计数器

---

### Requirement: fetch 调用链完整性

`RdnsPtrChannel` 继承 `BaseChannelAdapter.fetch()` 的标准调用链，无需覆盖。

#### Scenario: fetch 完整流程
- **WHEN** 调用 `fetch('8.8.8.8', delay=0, timeout=3.0)`
- **THEN** 执行链路：`delay → _request(ip, timeout=3.0) → _parse(result, ip) → setdefault(query_time)`
- **AND** 返回 dict 包含 `query_time` 字段（由基类注入）

#### Scenario: fetch 透传 timeout 给 _request
- **WHEN** 调用 `fetch('8.8.8.8', timeout=5.0)`
- **THEN** `_request` 使用该 timeout 值设置 `socket.setdefaulttimeout()`

#### Scenario: fetch 网络错误透传 ChannelError
- **WHEN** `_request()` 抛出 `ChannelError`
- **THEN** `fetch()` 直接透传异常，不返回 dict

---

### Requirement: 满足 ChannelProtocol

#### Scenario: isinstance 检查通过
- **WHEN** 创建 `RdnsPtrChannel()` 实例
- **THEN** `isinstance(instance, ChannelProtocol)` 返回 `True`

---

## 与 Legacy 的差异

| 项目 | Legacy | 新实现 |
|------|--------|--------|
| 结构 | 模块级函数 + `RdnsPtrChannel` 类 | 仅 `RdnsPtrChannel` 类（继承 `BaseChannelAdapter`） |
| Settings 依赖 | `from config import RdnsSettings as Settings` | **无依赖**，`timeout` 通过构造函数注入 |
| validate 失败 | `sys.exit(1)` | **不覆盖 `_validate_key()`**，validate() 永远返回 True |
| 网络错误信号 | `{"raw_error": True, ...}` dict | 抛出 `ChannelError` 异常 |
| delay / format_output | 模块级函数重复定义 | **基类统一提供** |
| CLI main() | 文件末尾 | **不在渠道层**，由上层处理 |
| 日志 | `get_channel_logger('rdns_ptr')` | 基类不内置 logger，子类按需添加 |

## 关键设计决策

1. **DNS 超时不是网络错误**：`socket.timeout` 返回 has_ptr=False 结果（S76），不抛 `ChannelError`。只有非预期异常才抛 `ChannelError`（S78）
2. **herror/gaierror 不是错误**：DNS 无 PTR 记录和地址错误都是正常查询结果（S73、S75）
3. **不覆盖 _validate_key**：rdns_ptr 无 API Key，validate() 永远返回 True，DNS 不可用在 _request() 中自然暴露（brainstorming 确认）
4. **构造函数注入 timeout**：不依赖 Settings，默认 3.0 秒
5. **不覆盖 _parse**：`_request()` 返回 dict，基类 `_parse()` 直接透传
