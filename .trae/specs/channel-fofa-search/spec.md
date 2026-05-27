# fofa_search 渠道迁移规格文档

> **对应重构方案**：Step 2.9
>
> **Legacy 源文件**：`legacy/channel/fofa_search.py`
>
> **PRD 需求**：S107-S116

## Why

fofa_search 使用 FOFA 搜索 API（`/api/v1/search/all`）查询 IP 关联的资产信息。它与 fofa_host 共享同一 API Key 和验证逻辑，但查询接口和响应结构不同。它支持追加额外查询条件（query_suffix）来缩小搜索范围。

## What Changes

- 新建 `src/ip_info/channel/fofa_search.py`，包含 `FofaSearchChannel` 类（继承 `BaseChannelAdapter`）
- 新建 `tests/unit/channel/test_fofa_search.py`，包含完整单元测试
- 不修改 `legacy/` 中的任何文件

## Impact

- Affected specs: 依赖 `channel-layer-core` spec
- Affected code: `src/ip_info/channel/`（新增文件）、`tests/unit/channel/`（新增文件）

---

## ADDED Requirements

### Requirement: FofaSearchChannel 类

```python
class FofaSearchChannel(BaseChannelAdapter):
    channel_name = "fofa_search"

    FIELDS = "host,ip,port,domain,protocol,title,server,os,country,country_name,region,city,asn,org,link,lastupdatetime"

    def __init__(self, key: str, timeout: float = 30.0): ...
    def _validate_key(self) -> None: ...
    def _request(self, ip: str, **kwargs) -> dict: ...
```

**构造函数约定**：
- `key`：FOFA API Key（必填），空字符串视为无效
- `timeout`：HTTP 请求超时时间（秒），默认 30.0

**不覆盖 `_parse()`**：`_request()` 返回 dict，基类 `_parse()` 直接透传

---

### Requirement: _validate_key — API Key 验证（S112、S113）

与 fofa_host 一致：检查非空 + 请求 `/api/v1/info/my` 验证。

#### Scenario: Key 有效
- **WHEN** `key` 非空且 `/api/v1/info/my?key={key}` 返回 `{"error": false, ...}`
- **THEN** 正常返回

#### Scenario: Key 为空或空白（S112）
- **WHEN** `key` 为空字符串或仅含空白字符
- **THEN** 抛出 `ChannelPermanentError`，消息为 `"FOFA API Key 未配置"`

#### Scenario: Key 无效（S113）
- **WHEN** 验证请求返回 `{"error": true, "errmsg": "[-700] Account Invalid"}`
- **THEN** 抛出 `ChannelPermanentError`，消息为 `"FOFA API Key 无效: {errmsg}"`

#### Scenario: 验证请求网络错误
- **WHEN** 验证请求抛出网络异常
- **THEN** 异常向上抛出，基类 `validate()` 捕获后设 disabled=True

---

### Requirement: _request — 搜索 API 请求（S107-S116）

`_request(ip)` SHALL 使用 `requests.get()` 请求 `https://fofa.info/api/v1/search/all`，查询条件为 `ip="{ip}"`（base64 编码），支持通过 `query_suffix` 追加额外条件。

**请求参数**：
- `key`：API Key
- `qbase64`：`base64(b'ip="{ip}"{query_suffix}')`
- `fields`：`FIELDS` 常量
- `page`：1
- `size`：20

#### Scenario: 查询成功有结果（S107、S110）
- **WHEN** API 返回 `{"error": false, "results": [[...], [...]], "size": 2, "query": "...", "fields": "..."}`
- **THEN** 返回该 JSON dict（原样透传）

#### Scenario: 查询成功无结果（S109、S111）
- **WHEN** API 返回 `{"error": false, "results": [], "size": 0, "query": "..."}`
- **THEN** 返回该 JSON dict（results 为空列表，不是错误）

#### Scenario: query_suffix 追加条件（S108）
- **WHEN** 调用 `_request(ip, query_suffix=' && port="80"')`
- **THEN** 查询字符串为 `ip="{ip}" && port="80"`（base64 编码后传入 qbase64）

#### Scenario: API Key 无效（error=true + -700）（S113）
- **WHEN** API 返回 `{"error": true, "errmsg": "[-700] Account Invalid"}`
- **THEN** 抛出 `ChannelPermanentError`，消息为 `"FOFA API Key 无效: {errmsg}"`

#### Scenario: API 业务错误（error=true + 其他）（S114）
- **WHEN** API 返回 `{"error": true, "errmsg": "[-4] Params Error"}`
- **THEN** 抛出 `ChannelError`，消息为 `"FOFA Search 查询业务错误: {ip} - {errmsg}"`

#### Scenario: 网络超时（S114）
- **WHEN** `requests.get()` 抛出 `requests.exceptions.Timeout`
- **THEN** 抛出 `ChannelError`，消息为 `"FOFA Search 查询超时: {ip} - {error}"`

#### Scenario: 连接失败（S114）
- **WHEN** `requests.get()` 抛出 `requests.exceptions.ConnectionError`
- **THEN** 抛出 `ChannelError`，消息为 `"FOFA Search 连接失败: {ip} - {error}"`

#### Scenario: HTTP 错误（S114）
- **WHEN** `response.raise_for_status()` 抛出 `requests.exceptions.HTTPError`
- **THEN** 抛出 `ChannelError`，消息为 `"FOFA Search 查询失败: {ip} - HTTP {status_code}"`

#### Scenario: 非 JSON 响应（S116）
- **WHEN** `response.json()` 抛出 `ValueError`（非 JSON 格式）
- **THEN** 抛出 `ChannelError`，消息为 `"FOFA Search 响应非JSON: {ip} - {error}"`

#### Scenario: 其他非预期异常（S115）
- **WHEN** 抛出其他异常
- **THEN** 抛出 `ChannelError`，消息为 `"FOFA Search 查询错误: {ip} - {error}"`

---

### Requirement: fetch 调用链完整性

继承 `BaseChannelAdapter.fetch()`，无需覆盖。

- 返回 dict 包含 `query_time`（基类注入）
- `ChannelPermanentError` → disabled=True
- `ChannelError` → disabled 不变

### Requirement: 满足 ChannelProtocol

`isinstance(instance, ChannelProtocol)` 返回 `True`

---

## 关键设计决策

1. **与 fofa_host 共享 Key 验证逻辑**：`_validate_key()` 实现一致（请求 `/api/v1/info/my`）
2. **query_suffix 支持追加条件**：通过 kwargs 传入，追加到 `ip="{ip}"` 后面
3. **双层错误检查**：HTTP 状态码 + JSON body `error` 字段（FOFA 特色）
4. **非 JSON 响应单独处理**（S116）：`response.json()` 抛 ValueError → `ChannelError`
5. **错误分类原则**：Key 无效(-700) → `ChannelPermanentError`，其他 → `ChannelError`
6. **FIELDS 作为类常量**：与 legacy 一致
