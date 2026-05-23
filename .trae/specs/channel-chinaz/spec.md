# chinaz 渠道迁移规格文档

> **对应重构方案**：Step 2.11
>
> **Legacy 源文件**：`legacy/channel/chinaz.py`
>
> **PRD 需求**：S50-S59

## Why

chinaz（站长之家）与 aizhan 类似，也是 Cookie 认证 + HTML 解析渠道。差异在于：Cookie 需检查必需字段、域名含备案起止日期、页面结构不同。它与 aizhan 共享相似的迁移模式。

## What Changes

* 新建 `src/ip_info/channel/chinaz.py`，包含 `ChinazChannel` 类

* 新建 `tests/unit/channel/test_chinaz.py`

* 不修改 `legacy/` 中的任何文件

## Impact

* Affected specs: 依赖 `channel-layer-core` spec

* Affected code: `src/ip_info/channel/`（新增）、`tests/unit/channel/`（新增）

***

## ADDED Requirements

### Requirement: ChinazChannel 类

```python
class ChinazChannel(BaseChannelAdapter):
    channel_name = "chinaz"
    REQUIRED_COOKIE_KEYS = ["toolUserGrade", "chinaz_zxuser"]

    def __init__(self, cookie: str, timeout: float = 15.0): ...
    def _validate_key(self) -> None: ...
    def _request(self, ip: str, **kwargs) -> str: ...
    def _parse(self, raw: str, ip: str) -> dict: ...
```

**构造函数约定**：

* `cookie`：站长之家登录 Cookie（必填），需包含必需字段

* `timeout`：HTTP 请求超时时间（秒），默认 15.0

**覆盖** **`_parse()`**：`_request()` 返回 HTML str，`_parse()` 用 BeautifulSoup 解析

***

### Requirement: \_validate\_key — Cookie 有效性验证（S59）

#### Scenario: Cookie 有效

* **WHEN** `cookie` 非空、包含必需字段、且请求 `https://ipchaxun.com/8.8.8.8/` 返回 HTTP 200

* **THEN** 正常返回

#### Scenario: Cookie 为空或空白（S59）

* **WHEN** `cookie` 为空字符串或仅含空白字符

* **THEN** 抛出 `ChannelPermanentError`，消息为 `"站长之家 Cookie 未配置"`

#### Scenario: Cookie 缺少必需字段（S59）

* **WHEN** `cookie` 不包含 `toolUserGrade` 或 `chinaz_zxuser`

* **THEN** 抛出 `ChannelPermanentError`，消息为 `"站长之家 Cookie 缺少必要字段: {missing_keys}"`

#### Scenario: 验证请求网络错误

* **WHEN** 验证请求抛出网络异常

* **THEN** 异常向上抛出，基类 `validate()` 捕获后设 disabled=True

**NOTE**：验证请求即使页面结构异常也不视为 Cookie 无效（与 legacy 一致），只检查网络可达性。

***

### Requirement: \_request — HTML 页面请求（S50、S56）

`_request(ip)` SHALL 请求 `https://ipchaxun.com/{ip}/`，携带 Cookie 和浏览器 UA，返回 HTML 文本。

#### Scenario: 请求成功

* **WHEN** 返回 HTTP 200

* **THEN** 返回 `response.text`

#### Scenario: 网络超时（S56）

* **THEN** 抛出 `ChannelError`，消息为 `"站长之家查询超时: {ip} - {error}"`

#### Scenario: 连接失败（S56）

* **THEN** 抛出 `ChannelError`，消息为 `"站长之家连接失败: {ip} - {error}"`

#### Scenario: 其他 HTTP 错误（S56）

* **THEN** 抛出 `ChannelError`，消息为 `"站长之家查询失败: {ip} - HTTP {status_code}"`

#### Scenario: 其他异常（S58）

* **THEN** 抛出 `ChannelError`，消息为 `"站长之家查询错误: {ip} - {error}"`

***

### Requirement: _parse — HTML 页面解析（S51-S55、S57）

`_parse(raw, ip)` 接收 HTML 字符串，解析为结构化 dict。

#### Scenario: 完整解析成功（S51、S52、S53）
- **WHEN** HTML 包含地域信息、运营商信息和域名列表
- **THEN** 返回 dict：
  ```python
  {
      "query_ip": ip,
      "location": "广东深圳",
      "isp": "电信",
      "domains": [{"domain": "example.com", "start_time": "2020-01-01", "end_time": "2025-12-31"}, ...],
      "domain_count": 5,
  }
  ```

#### Scenario: 无关联域名（S55）
- **WHEN** 页面表示无关联域名
- **THEN** `domains` 为空列表，`domain_count` 为 0

#### Scenario: 域名去重 + 上限 20 + 过滤无点号（S54）
- **WHEN** 提取到多个域名
- **THEN** 去重（保留首次出现）、上限 20 个、过滤不含 `.` 的无效域名（长度 > 3 且包含 `.`）

#### Scenario: 域名含备案起止日期（S52）
- **WHEN** 域名信息中包含日期范围（格式 `"起始日期-----结束日期"`）
- **THEN** 解析为 `start_time` 和 `end_time` 字段

#### Scenario: 页面结构异常（S57）
- **WHEN** HTML 缺少地域信息或域名区域
- **THEN** 抛出 `ChannelError`，消息为 `"站长之家页面结构异常: ..."`

***

### Requirement: fetch 调用链完整性

继承 `BaseChannelAdapter.fetch()`，无需覆盖。

### Requirement: 满足 ChannelProtocol

`isinstance(instance, ChannelProtocol)` 返回 `True`

***

## 关键设计决策

1. **Cookie 需检查必需字段**：`toolUserGrade` 和 `chinaz_zxuser`（与 legacy 一致）
2. **覆盖** **`_parse()`**：与 aizhan 类似，`_request()` 返回 HTML str
3. **域名含备案起止日期**：`start_time` / `end_time`（chinaz 独有）
4. **页面结构异常是临时性错误**：`ChannelError`（S57）
5. **所有网络错误统一 ChannelError**：chinaz 无 403 特殊处理（与 aizhan 不同）

