# ssl_cert 渠道迁移规格文档

> **对应重构方案**：Step 2.5（渠道迁移第 9 个，共 11 个）
>
> **Skills 链**：`/spec`（本文档）→ 用户审核 → `tdd` → `git-commit`
>
> **Legacy 源文件**：`legacy/channel/ssl_cert.py`
>
> **PRD 需求**：S86-S93（参考）

## Why

ssl_cert 渠道通过 SSL 直连目标 IP/域名的指定端口获取证书信息，提取 CN、SAN 域名、颁发者、有效期等。它是唯一一个需要 **IP/域名 + 端口** 双参数输入的渠道。迁移后纳入 `BaseChannelAdapter` 统一架构。

## What Changes

- 新建 `src/ip_info/channel/ssl_cert.py`，包含 `SslCertChannel` 类（继承 `BaseChannelAdapter`）
- 新建 `tests/unit/channel/test_ssl_cert.py`，包含完整单元测试
- 不修改 `legacy/` 中的任何文件

## Impact

- Affected specs: 依赖 `channel-layer-core` spec（`BaseChannelAdapter`、`ChannelError`）
- Affected code: `src/ip_info/channel/`（新增文件）、`tests/unit/channel/`（新增文件）

---

## ADDED Requirements

### Requirement: SslCertChannel 类

系统 SHALL 提供 `SslCertChannel` 类，继承 `BaseChannelAdapter`，封装 SSL 证书查询逻辑。

```python
class SslCertChannel(BaseChannelAdapter):
    channel_name = "ssl_cert"

    def __init__(self, port: int = 443, timeout: float = 5.0, openssl_timeout: float = 10.0): ...
    def _request(self, ip: str, **kwargs) -> str | None: ...
    def _parse(self, raw, ip: str) -> dict: ...
```

**构造函数约定**：
- `port`：默认连接端口，默认 443
- `timeout`：SSL 连接超时时间（秒），默认 5.0
- `openssl_timeout`：openssl 命令超时时间（秒），默认 10.0
- 不依赖 `config.Settings`，通过构造函数注入

**不覆盖 `_validate_key()`**：
- ssl_cert 不依赖 API Key / Cookie，无需预验证
- 使用基类默认的空实现，`validate()` 永远返回 `True`

---

### Requirement: _request — SSL 证书获取（S86、S92）

`_request(ip, **kwargs)` SHALL 通过 SSL 直连目标 IP/域名的指定端口，获取 DER 格式证书并转换为可读文本。端口通过 `kwargs["port"]` 传入，默认使用构造函数的 `port`。

#### Scenario: 成功获取证书文本（S86）
- **WHEN** SSL 连接成功且目标返回证书
- **THEN** 返回证书文本字符串（优先使用 `openssl x509 -text` 解析，不可用时回退 PEM 原文）

#### Scenario: 目标无 SSL 证书（S91）
- **WHEN** SSL 连接成功但 `getpeercert(binary_form=True)` 返回空
- **THEN** 返回 `None`（由 `_parse` 处理为 has_cert=False）

#### Scenario: 连接超时（S92）
- **WHEN** `socket.create_connection` 或 SSL 握手抛出 `socket.timeout`
- **THEN** 抛出 `ChannelError`，消息格式为 `"SSL 连接超时: {ip}:{port}"`

#### Scenario: 连接被拒绝（S92）
- **WHEN** 连接抛出 `ConnectionRefusedError`
- **THEN** 抛出 `ChannelError`，消息格式为 `"SSL 连接被拒绝: {ip}:{port}"`

#### Scenario: SSL 错误（S92）
- **WHEN** SSL 握手抛出 `ssl.SSLError`
- **THEN** 抛出 `ChannelError`，消息格式为 `"SSL 错误: {ip}:{port} - {error}"`

#### Scenario: 其他异常（S92、S93）
- **WHEN** 抛出非预期异常
- **THEN** 抛出 `ChannelError`，消息格式为 `"SSL 证书获取失败: {ip}:{port} - {error}"`

---

### Requirement: _parse — 证书文本解析（S87、S89）

`_parse(raw, ip)` SHALL 将 `_request` 返回的证书文本解析为结构化 dict。

#### Scenario: raw 为 None（无证书）（S91）
- **WHEN** `_request` 返回 `None`
- **THEN** 返回 dict：
  ```python
  {
      "query_target": ip,
      "port": port,  # 从 _request 传入
      "has_cert": False
  }
  ```

#### Scenario: 成功解析证书文本（S87、S89）
- **WHEN** `raw` 是证书文本字符串
- **THEN** 从文本中提取字段，返回 dict：
  ```python
  {
      "query_target": ip,
      "port": port,
      "has_cert": True,
      "subject_cn": str,          # Subject CN
      "issuer_cn": str,           # Issuer CN
      "not_before": str,          # Not Before
      "not_after": str,           # Not After
      "san_domains": list[str],   # SAN 域名列表
      "domains": list[str],       # CN + SAN 合并去重
  }
  ```

#### Scenario: CN 和 SAN 域名合并去重（S87）
- **WHEN** 证书同时包含 CN 和 SAN 域名
- **THEN** `domains` 字段包含 CN + 所有 SAN 域名，去重，CN 在前

#### Scenario: 证书缺少某些字段
- **WHEN** 证书文本中无 CN / SAN / Issuer 等字段
- **THEN** 对应字段为空字符串（subject_cn, issuer_cn, not_before, not_after）或空列表（san_domains, domains）

---

### Requirement: 端口传递机制

ssl_cert 是唯一需要端口的渠道。端口通过 `kwargs` 传递，不修改 `BaseChannelAdapter` 接口。

#### Scenario: fetch 传入 port 参数
- **WHEN** 调用 `fetch("example.com", port=8443)`
- **THEN** `_request` 使用 port=8443 进行 SSL 连接

#### Scenario: fetch 不传 port 参数使用默认值
- **WHEN** 调用 `fetch("8.8.8.8")`
- **THEN** `_request` 使用构造函数默认 port（443）

#### Scenario: _parse 需要知道端口号
- **WHEN** `_parse` 被调用时
- **THEN** 结果 dict 中包含 `port` 字段，记录实际使用的端口

**实现策略**：`_request` 将 port 存入返回结果或通过实例属性传递给 `_parse`。推荐方式：`_request` 返回的原始数据中附带 port 信息（如返回 dict `{"cert_text": ..., "port": port}`），或使用实例属性 `self._last_port` 在 `_parse` 中读取。

---

### Requirement: openssl 回退机制

证书文本解析优先使用 `openssl x509 -text` 命令获取人类可读格式。

#### Scenario: openssl 可用
- **WHEN** `openssl x509 -text -noout` 命令成功执行
- **THEN** 返回 openssl 输出的证书文本

#### Scenario: openssl 不可用（FileNotFoundError）
- **WHEN** 系统中未安装 openssl 命令
- **THEN** 回退返回 PEM 原文（base64 编码的证书）

#### Scenario: openssl 执行超时或异常
- **WHEN** openssl 命令超时或执行失败
- **THEN** 回退返回 PEM 原文

---

### Requirement: fetch 调用链完整性

`SslCertChannel` 继承 `BaseChannelAdapter.fetch()` 的标准调用链，无需覆盖。

#### Scenario: fetch 完整流程（有证书）
- **WHEN** 调用 `fetch("example.com", port=443, delay=0)`
- **THEN** 执行链路：`delay → _request(ip, port=443) → _parse(raw, ip) → setdefault(query_time)`
- **AND** 返回 dict 包含 `query_time` 字段（由基类注入）

#### Scenario: fetch 无证书
- **WHEN** `_request` 返回 `None`
- **THEN** `fetch()` 返回 `{"query_target": ip, "port": 443, "has_cert": False, "query_time": "..."}`

#### Scenario: fetch 网络错误透传 ChannelError
- **WHEN** `_request()` 抛出 `ChannelError`
- **THEN** `fetch()` 直接透传异常，不返回 dict

---

### Requirement: 满足 ChannelProtocol

#### Scenario: isinstance 检查通过
- **WHEN** 创建 `SslCertChannel()` 实例
- **THEN** `isinstance(instance, ChannelProtocol)` 返回 `True`

---

## 与 Legacy 的差异

| 项目 | Legacy | 新实现 |
|------|--------|--------|
| 结构 | 模块级函数 + `SslCertChannel` 类 | 仅 `SslCertChannel` 类（继承 `BaseChannelAdapter`） |
| Settings 依赖 | `from config import SslCertSettings as Settings` | **无依赖**，port/timeout 通过构造函数注入 |
| validate | 打印 "无需 Key 校验" | **不覆盖 `_validate_key()`**，validate() 永远返回 True |
| 网络错误信号 | `{"raw_error": True, ...}` dict | 抛出 `ChannelError` 异常 |
| 无证书信号 | `{"raw_error": True, "error_message": "no_cert"}` | `_request` 返回 `None`，`_parse` 生成 `has_cert=False` |
| 端口 | `fetch_channel(ip, port=443)` 函数参数 | `fetch(ip, port=443)` 通过 kwargs 传递 |
| delay / format_output | 模块级函数 | **基类统一提供** |
| CLI main() | 文件末尾 | **不在渠道层**，由上层处理 |
| 日志 | `get_channel_logger('ssl_cert')` | 基类不内置 logger，子类按需添加 |
| PRD 多端口 | S86/S90 提到端口列表 | **本期只支持单端口查询**，多端口由上层批量调用 |

## 关键设计决策

1. **端口通过 kwargs 传递**：不修改 `BaseChannelAdapter.fetch()` 签名，port 通过 `kwargs` 传入，与其他渠道的 timeout 传递方式一致
2. **ip 参数实际可以是域名**：`fetch("example.com", port=443)` 完全合法，`ip` 参数名来自基类但实际接受 IP 或域名（S88）
3. **_request 返回 cert_text 字符串或 None**：需要覆盖 `_parse` 来解析证书文本
4. **无证书返回 None 而非错误**：目标服务无 SSL 证书是正常情况（S91），返回 has_cert=False
5. **网络错误全部抛 ChannelError**：timeout / connection_refused / ssl_error / 其他异常统一为 ChannelError（S92）
6. **本期只支持单端口**：PRD S86/S90 提到端口列表，但 legacy 代码实际也是单端口查询，多端口由上层处理
7. **openssl 回退到 PEM**：openssl 不可用时不报错，回退到 PEM 原文（仍可提取基础信息）
8. **构造函数注入 port/timeout**：不依赖 Settings，默认 port=443, timeout=5.0, openssl_timeout=10.0
