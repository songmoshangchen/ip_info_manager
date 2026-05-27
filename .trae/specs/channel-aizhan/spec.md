# aizhan 渠道迁移规格文档

> **对应重构方案**：Step 2.10
>
> **Legacy 源文件**：`legacy/channel/aizhan.py`
>
> **PRD 需求**：S40-S49

## Why

aizhan（爱站网）是一个基于 Cookie 认证 + HTML 页面解析的渠道。它请求爱站网 DNS 反查页面，使用 BeautifulSoup 从 HTML 中提取地域信息和关联域名列表。它是第一个需要覆盖 `_parse()` 的渠道（`_request()` 返回 HTML 字符串，`_parse()` 解析为 dict）。

## What Changes

* 新建 `src/ip_info/channel/aizhan.py`，包含 `AizhanChannel` 类（继承 `BaseChannelAdapter`）

* 新建 `tests/unit/channel/test_aizhan.py`，包含完整单元测试

* 不修改 `legacy/` 中的任何文件

## Impact

* Affected specs: 依赖 `channel-layer-core` spec

* Affected code: `src/ip_info/channel/`（新增文件）、`tests/unit/channel/`（新增文件）

***

## ADDED Requirements

### Requirement: AizhanChannel 类

```python
class AizhanChannel(BaseChannelAdapter):
    channel_name = "aizhan"

    def __init__(self, cookie: str, timeout: float = 15.0): ...
    def _validate_key(self) -> None: ...
    def _request(self, ip: str, **kwargs) -> str: ...
    def _parse(self, raw: str, ip: str) -> dict: ...
```

**构造函数约定**：

* `cookie`：爱站网登录 Cookie（必填），空字符串视为无效

* `timeout`：HTTP 请求超时时间（秒），默认 15.0

**需要覆盖** **`_parse()`**：`_request()` 返回 HTML 字符串（str），`_parse()` 使用 BeautifulSoup 解析为 dict

***

### Requirement: \_validate\_key — Cookie 有效性验证（S49）

`_validate_key()` SHALL 验证 Cookie 的有效性：检查非空 + 请求爱站网用户页面验证。

#### Scenario: Cookie 有效

* **WHEN** `cookie` 非空且 `GET https://member.aizhan.com/user.php`（带 Cookie header，`allow_redirects=False`）返回 HTTP 200

* **THEN** 正常返回

#### Scenario: Cookie 为空或空白（S49）

* **WHEN** `cookie` 为空字符串或仅含空白字符

* **THEN** 抛出 `ChannelPermanentError`，消息为 `"爱站网 Cookie 未配置"`

#### Scenario: Cookie 已失效（重定向到登录页）（S49）

* **WHEN** 验证请求返回 HTTP 301/302（重定向到登录页）

* **THEN** 抛出 `ChannelPermanentError`，消息为 `"爱站网 Cookie 已失效"`

#### Scenario: Cookie 无效（HTTP 403）（S49）

* **WHEN** 验证请求返回 HTTP 403

* **THEN** 抛出 `ChannelPermanentError`，消息为 `"爱站网 Cookie 无效"`

#### Scenario: 验证请求网络错误

* **WHEN** 验证请求抛出网络异常

* **THEN** 异常向上抛出，基类 `validate()` 捕获后设 disabled=True

***

### Requirement: \_request — HTML 页面请求（S40、S46）

`_request(ip)` SHALL 使用 `requests.get()` 请求 `https://dns.aizhan.com/{ip}/`，携带 Cookie 和浏览器 User-Agent，返回 HTML 文本。

**请求 Headers**：

* `Host`: `dns.aizhan.com`

* `Cookie`: 构造函数传入的 cookie

* `User-Agent`: 浏览器 UA 字符串

#### Scenario: 请求成功

* **WHEN** `requests.get()` 返回 HTTP 200

* **THEN** 返回 `response.text`（HTML 字符串）

#### Scenario: HTTP 403（S49）

* **WHEN** 响应状态码为 403

* **THEN** 抛出 `ChannelPermanentError`，消息为 `"爱站网 Cookie 无效: {ip}"`

#### Scenario: 网络超时（S46）

* **WHEN** `requests.get()` 抛出 `requests.exceptions.Timeout`

* **THEN** 抛出 `ChannelError`，消息为 `"爱站网查询超时: {ip} - {error}"`

#### Scenario: 连接失败（S46）

* **WHEN** `requests.get()` 抛出 `requests.exceptions.ConnectionError`

* **THEN** 抛出 `ChannelError`，消息为 `"爱站网连接失败: {ip} - {error}"`

#### Scenario: 其他 HTTP 错误（S46）

* **WHEN** `response.raise_for_status()` 抛出 `requests.exceptions.HTTPError`（非 403）

* **THEN** 抛出 `ChannelError`，消息为 `"爱站网查询失败: {ip} - HTTP {status_code}"`

#### Scenario: 其他异常（S48）

* **WHEN** 抛出其他异常

* **THEN** 抛出 `ChannelError`，消息为 `"爱站网查询错误: {ip} - {error}"`

***

### Requirement: \_parse — HTML 页面解析（S41-S45、S47）

`_parse(raw, ip)` SHALL 使用 BeautifulSoup 从 HTML 中提取地域信息和域名列表。

#### Scenario: 完整解析成功（S41、S42、S43）

* **WHEN** HTML 包含 `div.dns-infos` 和 `div.dns-content`，且地域为中国省份

* **THEN** 返回 dict：

  ```python
  {
      "query_ip": ip,
      "location": "中国广东深圳",
      "isp": "电信",
      "domains": [{"domain": "example.com", "title": "示例网站"}, ...],
      "domain_count": 5,
  }
  ```

#### Scenario: 中国地域格式化（S41）

* **WHEN** 地域信息为 `广东 深圳 电信`（省份在城市列表中）

* **THEN** `location` 格式化为 `"中国广东深圳"`，`isp` 为 `"电信"`

#### Scenario: 非中国地域保留原样（S41）

* **WHEN** 地域信息为 `美国 加利福尼亚 Google`

* **THEN** `location` 保留原始文本，`isp` 为最后一部分

#### Scenario: 无关联域名（S45）

* **WHEN** `dns-content` 中包含 "暂无域名解析到该IP" 文本

* **THEN** `domains` 为空列表 `[]`，`domain_count` 为 0

#### Scenario: 域名去重 + 上限 20 + 过滤无点号（S44）

* **WHEN** 提取到多个域名

* **THEN** 去重（保留首次出现）、上限 20 个、过滤不含 `.` 的无效域名（域名长度 > 3 且包含 `.`）

#### Scenario: 页面结构异常（S47）

* **WHEN** HTML 缺少 `div.dns-infos` 或 `div.dns-content`

* **THEN** 抛出 `ChannelError`，消息为 `"爱站网页面结构异常: 缺少 {missing_sections}"`

#### Scenario: 表格数据异常（S47）

* **WHEN** `dns-content` 中没有 "暂无域名" 文本，但也找不到 `tbody`

* **THEN** 抛出 `ChannelError`，消息为 `"爱站网页面结构异常: 未找到表格数据"`

***

### Requirement: fetch 调用链完整性

继承 `BaseChannelAdapter.fetch()`，无需覆盖。

* 执行链路：`delay → _request(ip) → _parse(html, ip) → setdefault(query_time)`

* `ChannelPermanentError` → disabled=True

* `ChannelError` → disabled 不变

### Requirement: 满足 ChannelProtocol

`isinstance(instance, ChannelProtocol)` 返回 `True`

***

## 关键设计决策

1. **Cookie 认证**：与 API Key 渠道类似，但使用 Cookie header
2. **覆盖** **`_parse()`**：`_request()` 返回 HTML str，`_parse()` 使用 BeautifulSoup 解析
3. **HTTP 403 是永久性错误**：Cookie 失效 → `ChannelPermanentError`
4. **页面结构异常是临时性错误**：可能是爱站网页面改版 → `ChannelError`（S47）
5. **中国省份列表硬编码**：与 legacy 一致，用于判断地域格式化
6. **域名过滤规则**：长度 > 3 且包含 `.`（与 legacy 一致）

