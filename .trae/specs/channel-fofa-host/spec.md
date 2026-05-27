# fofa_host 渠道迁移规格文档

> **对应重构方案**：Step 2.8（第四个具体渠道迁移）
>
> **Skills 链**：`/spec`（本文档）→ 用户审核 → `tdd` → `git-commit`
>
> **Legacy 源文件**：`legacy/channel/fofa_host.py`
>
> **PRD 需求**：S33-S39
>
> **FOFA Host API 文档**：`https://fofa.info/api/stats/host`

## Why

fofa_host 使用 FOFA Host 聚合 API（`/api/v1/host/{ip}`）获取 IP 的资产信息。它是一个"认证 + 业务级错误"型渠道——FOFA API 即使在 Key 无效时也返回 HTTP 200，错误通过 JSON body 的 `error` 字段标识。迁移它建立了"业务级错误处理"的迁移模式。

## What Changes

- 新建 `src/ip_info/channel/fofa_host.py`，包含 `FofaHostChannel` 类（继承 `BaseChannelAdapter`）
- 新建 `tests/unit/channel/test_fofa_host.py`，包含完整单元测试
- 不修改 `legacy/` 中的任何文件

## Impact

- Affected specs: 依赖 `channel-layer-core` spec（`BaseChannelAdapter`、`ChannelError`、`ChannelPermanentError`）
- Affected code: `src/ip_info/channel/`（新增文件）、`tests/unit/channel/`（新增文件）

---

## ADDED Requirements

### Requirement: FofaHostChannel 类

系统 SHALL 提供 `FofaHostChannel` 类，继承 `BaseChannelAdapter`，封装 FOFA Host 聚合 API 查询逻辑。

```python
class FofaHostChannel(BaseChannelAdapter):
    channel_name = "fofa_host"

    def __init__(self, key: str, timeout: float = 30.0): ...
    def _validate_key(self) -> None: ...
    def _request(self, ip: str, **kwargs) -> dict: ...
```

**构造函数约定**：
- `key`：FOFA API Key（必填），空字符串视为无效
- `timeout`：HTTP 请求超时时间（秒），默认 30.0
- 不依赖 `config.Settings`，通过构造函数注入

**不覆盖 `_parse()`**：
- `_request()` 返回 dict（API JSON 响应），基类 `_parse()` 直接透传

---

### Requirement: _validate_key — API Key 有效性验证（S38）

`_validate_key()` SHALL 验证 API Key 的有效性：检查非空 + 请求 FOFA 用户信息接口验证。

#### Scenario: Key 有效
- **WHEN** `key` 非空且 `GET https://fofa.info/api/v1/info/my?key={key}` 返回 `{"error": false, ...}`
- **THEN** `_validate_key()` 正常返回（不抛异常）

#### Scenario: Key 为空或空白（S38）
- **WHEN** `key` 为空字符串或仅含空白字符
- **THEN** 抛出 `ChannelPermanentError`，消息为 `"FOFA API Key 未配置"`

#### Scenario: Key 无效（API 返回 error=true）（S38）
- **WHEN** 验证请求返回 `{"error": true, "errmsg": "[-700] Account Invalid"}`
- **THEN** 抛出 `ChannelPermanentError`，消息为 `"FOFA API Key 无效: {errmsg}"`

#### Scenario: 验证请求网络错误
- **WHEN** 验证请求抛出网络异常
- **THEN** 异常正常向上抛出，基类 `validate()` 捕获后返回 False + 设 disabled=True

---

### Requirement: _request — Host 聚合 API 请求（S33-S39）

`_request(ip)` SHALL 使用 `requests.get()` 请求 `https://fofa.info/api/v1/host/{ip}?key={key}&detail=true`，并根据 HTTP 响应和 JSON body 中的业务错误码区分成功和失败。

**关键设计**：FOFA API 即使在 Key 无效时也可能返回 HTTP 200，错误通过 JSON body 的 `error` 字段标识。因此 `_request()` 需要同时检查 HTTP 状态码和 JSON body。

#### Scenario: 查询成功（HTTP 200 + error=false）（S33、S34、S35）
- **WHEN** API 返回 HTTP 200，JSON body 为 `{"error": false, "host": "8.8.8.8", "ip": "8.8.8.8", "asn": 15169, ...}`
- **THEN** 返回该 JSON dict（原样透传 API 响应，包含 host, ip, asn, org, country_name, protocol, port, category, product 等字段）

#### Scenario: API Key 无效（JSON error=true + 账户错误）（S38）
- **WHEN** API 返回 HTTP 200，但 JSON body 为 `{"error": true, "errmsg": "[-700] Account Invalid"}`
- **THEN** 抛出 `ChannelPermanentError`，消息为 `"FOFA API Key 无效: {errmsg}"`
- **NOTE**：Key 无效是永久性错误，基类设 `disabled=True`

#### Scenario: API 业务错误（JSON error=true + 其他错误）（S39）
- **WHEN** API 返回 HTTP 200，但 JSON body 为 `{"error": true, "errmsg": "[-4] Params Error"}`
- **THEN** 抛出 `ChannelError`，消息为 `"FOFA Host 查询业务错误: {ip} - {errmsg}"`
- **NOTE**：非 Key 无效的业务错误视为临时性错误（S39：原样透传错误信息）

#### Scenario: 网络超时（S36）
- **WHEN** `requests.get()` 抛出 `requests.exceptions.Timeout`
- **THEN** 抛出 `ChannelError`，消息格式为 `"FOFA Host 查询超时: {ip} - {error}"`

#### Scenario: 连接失败（S36）
- **WHEN** `requests.get()` 抛出 `requests.exceptions.ConnectionError`
- **THEN** 抛出 `ChannelError`，消息格式为 `"FOFA Host 连接失败: {ip} - {error}"`

#### Scenario: HTTP 错误（如 429、500 等）（S36）
- **WHEN** `response.raise_for_status()` 抛出 `requests.exceptions.HTTPError`
- **THEN** 抛出 `ChannelError`，消息格式为 `"FOFA Host 查询失败: {ip} - HTTP {status_code}"`
- **NOTE**：HTTP 层面的 429 也使用 `ChannelError`（FOFA 的限流主要体现在业务错误中）

#### Scenario: 其他非预期异常（S37）
- **WHEN** `requests.get()` 抛出其他异常
- **THEN** 抛出 `ChannelError`，消息格式为 `"FOFA Host 查询错误: {ip} - {error}"`

---

### Requirement: fetch 调用链完整性

`FofaHostChannel` 继承 `BaseChannelAdapter.fetch()` 的标准调用链，无需覆盖。

#### Scenario: fetch 完整流程
- **WHEN** 调用 `fetch('8.8.8.8', delay=0, timeout=30.0)`
- **THEN** 返回 dict 包含 `query_time` 字段（由基类注入）

#### Scenario: fetch Key 无效设 disabled=True（S38）
- **WHEN** `_request()` 抛出 `ChannelPermanentError`
- **THEN** `fetch()` 透传异常，同时 `disabled` 变为 `True`

#### Scenario: fetch 网络错误不改变 disabled（S36）
- **WHEN** `_request()` 抛出 `ChannelError`
- **THEN** `fetch()` 透传异常，`disabled` 不变

---

### Requirement: 满足 ChannelProtocol

#### Scenario: isinstance 检查通过
- **WHEN** 创建 `FofaHostChannel(key="test_key")` 实例
- **THEN** `isinstance(instance, ChannelProtocol)` 返回 `True`

---

## 与 Legacy 的差异

| 项目 | Legacy | 新实现 |
|------|--------|--------|
| 结构 | 模块级函数 + `FofaHostChannel` 类 | 仅 `FofaHostChannel` 类（继承 `BaseChannelAdapter`） |
| Settings 依赖 | `from config import FofaSettings as Settings` | **无依赖**，`key`/`timeout` 通过构造函数注入 |
| validate | 请求 `/api/v1/info/my` 验证 Key，失败 `sys.exit(1)` | 覆盖 `_validate_key()`：空Key/无效Key 抛 `ChannelPermanentError` |
| 错误处理 | 返回 `{"raw_error": True, "error_message": "..."}` dict | **抛出异常**：ChannelError / ChannelPermanentError |
| 业务错误 | 未区分 Key 无效和普通业务错误 | **区分**：Key 无效(−700) → ChannelPermanentError, 其他 → ChannelError |
| delay / format_output | 模块级函数重复定义 | **基类统一提供** |

## 关键设计决策

1. **Key 通过构造函数注入**：不依赖 Settings，必填参数
2. **覆盖 `_validate_key()`**：验证 Key 非空 + 请求 FOFA 用户信息接口
3. **双层错误检查**：HTTP 状态码 + JSON body `error` 字段（FOFA 特色：Key 无效也可能返回 HTTP 200）
4. **Key 无效（−700）是永久性错误**：`ChannelPermanentError` → disabled=True（S38）
5. **其他业务错误是临时性错误**：`ChannelError`（S39：原样透传错误信息）
6. **不覆盖 _parse**：`_request()` 返回 dict（API JSON），基类 `_parse()` 直接透传
