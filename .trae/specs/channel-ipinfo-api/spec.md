# ipinfo_api 渠道迁移规格文档

> **对应重构方案**：Step 2.7（第三个具体渠道迁移）
>
> **Skills 链**：`/spec`（本文档）→ 用户审核 → `tdd` → `git-commit`
>
> **Legacy 源文件**：`legacy/channel/ipinfo_api.py`
>
> **PRD 需求**：S60-S65

## Why

ipinfo_api 是 ip_info_manager 中第一个需要 Token 认证的渠道。它使用 `api.ipinfo.io/lite/` 认证接口，需要处理 Token 验证、Token 失效、限流等场景。迁移它建立了"认证型 API 渠道"的迁移模式，后续的 fofa、zoomeye 等渠道可复用此模式。

## What Changes

- 新建 `src/ip_info/channel/ipinfo_api.py`，包含 `IpinfoApiChannel` 类（继承 `BaseChannelAdapter`）
- 新建 `tests/unit/channel/test_ipinfo_api.py`，包含完整单元测试
- 不修改 `legacy/` 中的任何文件

## Impact

- Affected specs: 依赖 `channel-layer-core` spec（`BaseChannelAdapter`、`ChannelError`、`ChannelPermanentError`）
- Affected code: `src/ip_info/channel/`（新增文件）、`tests/unit/channel/`（新增文件）

---

## ADDED Requirements

### Requirement: IpinfoApiChannel 类

系统 SHALL 提供 `IpinfoApiChannel` 类，继承 `BaseChannelAdapter`，封装 IPInfo 认证 API 查询逻辑。

```python
class IpinfoApiChannel(BaseChannelAdapter):
    channel_name = "ipinfo_api"

    def __init__(self, token: str, timeout: float = 30.0): ...
    def _validate_key(self) -> None: ...
    def _request(self, ip: str, **kwargs) -> dict: ...
```

**构造函数约定**：
- `token`：IPInfo API Token（必填），空字符串视为无效
- `timeout`：HTTP 请求超时时间（秒），默认 30.0
- 不依赖 `config.Settings`，通过构造函数注入

**职责范围（brainstorming 确认）**：
- 仅负责 Token 认证模式（`api.ipinfo.io/lite/`）
- 无 Token 的免费模式由已有的 `IpinfoFreeChannel` 处理
- Token 为空时 `_validate_key()` 抛异常（disabled=True）

**不覆盖 `_parse()`**：
- `_request()` 返回 dict（API JSON 响应），基类 `_parse()` 直接透传

---

### Requirement: _validate_key — Token 有效性验证（S61、S65）

`_validate_key()` SHALL 验证 Token 的有效性：检查非空 + 实际请求验证。

#### Scenario: Token 有效
- **WHEN** `token` 非空且 `GET https://api.ipinfo.io/lite/8.8.8.8`（带 `Authorization: Bearer {token}`）返回 HTTP 200
- **THEN** `_validate_key()` 正常返回（不抛异常）

#### Scenario: Token 为空或空白（S65）
- **WHEN** `token` 为空字符串或仅含空白字符
- **THEN** 抛出 `ChannelPermanentError`，消息为 `"IPInfo API Token 未配置"`

#### Scenario: Token 无效（HTTP 401/403）（S65）
- **WHEN** 验证请求返回 HTTP 401 或 403
- **THEN** 抛出 `ChannelPermanentError`，消息为 `"IPInfo API Token 无效"`

#### Scenario: 验证请求网络错误
- **WHEN** 验证请求抛出网络异常（Timeout、ConnectionError 等）
- **THEN** 异常正常向上抛出，基类 `validate()` 捕获后返回 False + 设 disabled=True
- **NOTE**：不在 `_validate_key()` 内部吞异常，由基类统一处理

---

### Requirement: _request — 认证 API 请求（S60、S62-S64）

`_request(ip)` SHALL 使用 `requests.get()` 带 `Authorization: Bearer {token}` 请求 `https://api.ipinfo.io/lite/{ip}`，并根据 HTTP 响应状态码区分成功和失败。

#### Scenario: 查询成功（HTTP 200）（S60、S62）
- **WHEN** `requests.get()` 返回 HTTP 200，JSON body 包含 IP 地理信息
- **THEN** 返回该 JSON dict（原样透传 API 响应）
- **NOTE**：API 返回的字段全部保留不做字段过滤

#### Scenario: Token 无效（HTTP 401/403）（S65）
- **WHEN** API 返回 HTTP 401 或 403
- **THEN** 抛出 `ChannelPermanentError`，消息为 `"IPInfo API Token 无效: {ip}"`
- **NOTE**：Token 失效是永久性错误，基类设 `disabled=True`，后续 IP 跳过

#### Scenario: 请求限流（HTTP 429）
- **WHEN** API 返回 HTTP 429 Too Many Requests
- **THEN** 抛出 `ChannelPermanentError`，消息为 `"IPInfo API 请求限流: {ip}"`
- **NOTE**：与 ipinfo_free 一致，429 为永久性错误（disabled=True）

#### Scenario: 网络超时（S63）
- **WHEN** `requests.get()` 抛出 `requests.exceptions.Timeout`
- **THEN** 抛出 `ChannelError`，消息格式为 `"IPInfo API 查询超时: {ip} - {error}"`

#### Scenario: 连接失败（S63）
- **WHEN** `requests.get()` 抛出 `requests.exceptions.ConnectionError`
- **THEN** 抛出 `ChannelError`，消息格式为 `"IPInfo API 连接失败: {ip} - {error}"`

#### Scenario: 其他 HTTP 错误（如 500、502、503）（S63）
- **WHEN** `response.raise_for_status()` 抛出 `requests.exceptions.HTTPError`（非 401/403/429）
- **THEN** 抛出 `ChannelError`，消息格式为 `"IPInfo API 查询失败: {ip} - HTTP {status_code}"`

#### Scenario: 其他非预期异常（S64）
- **WHEN** `requests.get()` 抛出其他异常
- **THEN** 抛出 `ChannelError`，消息格式为 `"IPInfo API 查询错误: {ip} - {error}"`

---

### Requirement: fetch 调用链完整性

`IpinfoApiChannel` 继承 `BaseChannelAdapter.fetch()` 的标准调用链，无需覆盖。

#### Scenario: fetch 完整流程
- **WHEN** 调用 `fetch('8.8.8.8', delay=0, timeout=30.0)`
- **THEN** 执行链路：`delay → _request(ip, timeout=30.0) → _parse(result, ip) → setdefault(query_time)`
- **AND** 返回 dict 包含 `query_time` 字段（由基类注入）

#### Scenario: fetch 透传 timeout 给 _request
- **WHEN** 调用 `fetch('8.8.8.8', timeout=10.0)`
- **THEN** `_request` 使用该 timeout 值

#### Scenario: fetch Token 无效设 disabled=True（S65）
- **WHEN** `_request()` 抛出 `ChannelPermanentError`
- **THEN** `fetch()` 透传异常，同时 `disabled` 变为 `True`

#### Scenario: fetch 网络错误不改变 disabled（S63）
- **WHEN** `_request()` 抛出 `ChannelError`
- **THEN** `fetch()` 透传异常，`disabled` 不变

---

### Requirement: 满足 ChannelProtocol

#### Scenario: isinstance 检查通过
- **WHEN** 创建 `IpinfoApiChannel(token="test_token")` 实例
- **THEN** `isinstance(instance, ChannelProtocol)` 返回 `True`

---

## 与 Legacy 的差异

| 项目 | Legacy | 新实现 |
|------|--------|--------|
| 结构 | 模块级函数 + `IpinfoApiChannel` 类 | 仅 `IpinfoApiChannel` 类（继承 `BaseChannelAdapter`） |
| Settings 依赖 | `from config import IpinfoSettings as Settings` | **无依赖**，`token`/`timeout` 通过构造函数注入 |
| 双模式 | 有 Token 用 API，无 Token 回退免费 | **仅认证模式**，免费由 `IpinfoFreeChannel` 处理 |
| validate | 请求 8.8.8.8 验证，失败 `sys.exit(1)` | 覆盖 `_validate_key()`：空 Token/无效 Token 抛 `ChannelPermanentError` |
| 错误处理 | 返回 `{"raw_error": True, ...}` dict | **抛出异常**：ChannelError / ChannelPermanentError |
| 限流处理 | 无特殊处理 | **HTTP 429 → ChannelPermanentError**（disabled=True） |
| Token 失效 | 无特殊处理 | **HTTP 401/403 → ChannelPermanentError**（disabled=True） |
| delay / format_output | 模块级函数重复定义 | **基类统一提供** |

## 关键设计决策

1. **仅认证模式**：无 Token 的免费模式由 `IpinfoFreeChannel` 处理，`IpinfoApiChannel` 只负责 `api.ipinfo.io/lite/` 认证接口（brainstorming 确认）
2. **Token 通过构造函数注入**：不依赖 Settings，必填参数
3. **覆盖 `_validate_key()`**：验证 Token 非空 + 实际请求验证有效性
4. **HTTP 401/403 是永久性错误**：Token 无效 → disabled=True（S65）
5. **HTTP 429 是永久性错误**：限流 → disabled=True（与 ipinfo_free 一致）
6. **网络错误使用 ChannelError**：超时、连接失败不改变 disabled（S63）
7. **不覆盖 _parse**：`_request()` 返回 dict（API JSON），基类 `_parse()` 直接透传
