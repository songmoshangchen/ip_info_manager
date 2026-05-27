# ipinfo_free 渠道迁移规格文档

> **对应重构方案**：Step 2.6（第二个具体渠道迁移）
>
> **Skills 链**：`/spec`（本文档）→ 用户审核 → `tdd` → `git-commit`
>
> **Legacy 源文件**：`legacy/channel/ipinfo_free.py`
>
> **PRD 需求**：S66-S71

## Why

ipinfo_free 是一个基于 HTTP API 的免费渠道，使用 `requests` 库无认证请求 `ipinfo.io` 公开接口。它是第一个 HTTP API 类型渠道的迁移，需要处理 HTTP 状态码、超时、限流等网络异常场景。

## What Changes

- 新建 `src/ip_info/channel/ipinfo_free.py`，包含 `IpinfoFreeChannel` 类（继承 `BaseChannelAdapter`）
- 新建 `tests/unit/channel/test_ipinfo_free.py`，包含完整单元测试
- 不修改 `legacy/` 中的任何文件

## Impact

- Affected specs: 依赖 `channel-layer-core` spec（`BaseChannelAdapter`、`ChannelError`、`ChannelPermanentError`）
- Affected code: `src/ip_info/channel/`（新增文件）、`tests/unit/channel/`（新增文件）

---

## ADDED Requirements

### Requirement: IpinfoFreeChannel 类

系统 SHALL 提供 `IpinfoFreeChannel` 类，继承 `BaseChannelAdapter`，封装 IPInfo 免费 API 查询逻辑。

```python
class IpinfoFreeChannel(BaseChannelAdapter):
    channel_name = "ipinfo_free"

    def __init__(self, timeout: float = 30.0): ...
    def _request(self, ip: str, **kwargs) -> dict: ...
```

**构造函数约定**：
- `timeout`：HTTP 请求超时时间（秒），默认 30.0
- 不依赖 `config.Settings`，通过构造函数注入

**不覆盖 `_validate_key()`**：
- ipinfo_free 无需 API Key，使用基类默认空实现
- `validate()` 永远返回 `True`
- API 不可达的情况在 `_request()` 中自然暴露为 `ChannelError`
- 设计决策（与 rdns_ptr 一致）：YAGNI — 测试 8.8.8.8 不能保证后续查询都成功

**不覆盖 `_parse()`**：
- `_request()` 返回 dict（API JSON 响应），基类 `_parse()` 直接透传

---

### Requirement: _request — HTTP API 请求（S66-S71）

`_request(ip)` SHALL 使用 `requests.get()` 请求 `https://ipinfo.io/{ip}/json`，并根据 HTTP 响应状态码区分成功和失败。

#### Scenario: 查询成功（HTTP 200）（S66、S67、S68）
- **WHEN** `requests.get()` 返回 HTTP 200，JSON body 为 `{"ip": "8.8.8.8", "city": "Mountain View", "region": "California", "country": "US", "loc": "37.4056,-122.0775", "hostname": "dns.google"}`
- **THEN** 返回该 JSON dict（原样透传 API 响应）
- **NOTE**：ipinfo.io 返回的字段包括 `ip`, `city`, `region`, `country`, `loc`, `hostname`, `org`, `postal`, `timezone` 等，全部保留不做字段过滤

#### Scenario: 网络超时（S69）
- **WHEN** `requests.get()` 抛出 `requests.exceptions.Timeout`
- **THEN** 抛出 `ChannelError`，消息格式为 `"IPInfo 免费查询超时: {ip} - {error}"`

#### Scenario: 连接失败（S69）
- **WHEN** `requests.get()` 抛出 `requests.exceptions.ConnectionError`
- **THEN** 抛出 `ChannelError`，消息格式为 `"IPInfo 免费连接失败: {ip} - {error}"`

#### Scenario: 请求限流（HTTP 429）（S70）
- **WHEN** API 返回 HTTP 429 Too Many Requests
- **THEN** 抛出 `ChannelPermanentError`，消息格式为 `"IPInfo 免费请求限流: {ip}"`
- **NOTE**：429 表示已到达请求限额，需要停止该渠道的后续查询。基类 `fetch()` 捕获 `ChannelPermanentError` 后设 `disabled=True`，上层（批量查询层）检查 `disabled` 后跳过该渠道。过一段时间后可通过重新调用 `validate()` 重置 `disabled` 状态（重试逻辑由上层负责，渠道层不实现）

#### Scenario: 其他 HTTP 错误（如 500、502、503）（S69）
- **WHEN** `response.raise_for_status()` 抛出 `requests.exceptions.HTTPError`（非 429）
- **THEN** 抛出 `ChannelError`，消息格式为 `"IPInfo 免费查询失败: {ip} - HTTP {status_code}"`

#### Scenario: 其他非预期异常（S69）
- **WHEN** `requests.get()` 抛出其他异常（如 `ValueError`）
- **THEN** 抛出 `ChannelError`，消息格式为 `"IPInfo 免费查询错误: {ip} - {error}"`

---

### Requirement: fetch 调用链完整性

`IpinfoFreeChannel` 继承 `BaseChannelAdapter.fetch()` 的标准调用链，无需覆盖。

#### Scenario: fetch 完整流程
- **WHEN** 调用 `fetch('8.8.8.8', delay=0, timeout=30.0)`
- **THEN** 执行链路：`delay → _request(ip, timeout=30.0) → _parse(result, ip) → setdefault(query_time)`
- **AND** 返回 dict 包含 `query_time` 字段（由基类注入）

#### Scenario: fetch 透传 timeout 给 _request
- **WHEN** 调用 `fetch('8.8.8.8', timeout=10.0)`
- **THEN** `_request` 使用该 timeout 值

#### Scenario: fetch 网络错误透传 ChannelError
- **WHEN** `_request()` 抛出 `ChannelError`
- **THEN** `fetch()` 直接透传异常，不返回 dict

---

### Requirement: 满足 ChannelProtocol

#### Scenario: isinstance 检查通过
- **WHEN** 创建 `IpinfoFreeChannel()` 实例
- **THEN** `isinstance(instance, ChannelProtocol)` 返回 `True`

---

## 与 Legacy 的差异

| 项目 | Legacy | 新实现 |
|------|--------|--------|
| 结构 | 模块级函数 + `IpinfoFreeChannel` 类 | 仅 `IpinfoFreeChannel` 类（继承 `BaseChannelAdapter`） |
| Settings 依赖 | `from config import IpinfoSettings as Settings` | **无依赖**，`timeout` 通过构造函数注入 |
| validate | 请求 8.8.8.8 验证连通性，失败 `sys.exit(1)` | **不覆盖 `_validate_key()`**，validate() 永远返回 True |
| 错误处理 | 返回 `{"raw_error": True, "error_message": "..."}` dict | **抛出 `ChannelError` 异常** |
| 限流处理 | 无特殊处理（和其他错误一样返回 raw_error） | **HTTP 429 单独识别**，抛 `ChannelPermanentError`（disabled=True） |
| delay / format_output | 模块级函数重复定义 | **基类统一提供** |
| CLI main() | 文件末尾 | **不在渠道层**，由上层处理 |
| 日志 | `get_channel_logger('ipinfo_free')` | 基类不内置 logger，子类按需添加 |

## 关键设计决策

1. **HTTP 429 是永久性错误**：限流表示已到达请求限额，应停止该渠道后续查询（`ChannelPermanentError` → `disabled=True`），而非继续重试。重试时机由上层控制
2. **网络错误使用 ChannelError**：超时、连接失败等临时性错误不改变 `disabled` 状态
3. **不覆盖 _validate_key**：与 rdns_ptr 一致，YAGNI 原则
4. **构造函数注入 timeout**：不依赖 Settings，默认 30.0 秒
5. **不覆盖 _parse**：`_request()` 返回 dict（API JSON），基类 `_parse()` 直接透传
6. **透传 API 字段**：不过滤 ipinfo.io 返回的字段，全部保留
