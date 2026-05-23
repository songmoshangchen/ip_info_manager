# ChannelAdapter 配置系统增强规格文档

## Why

当前 ChannelAdapter 构造函数直接接收参数（key/cookie/timeout 等），不从 .env 读取。需要添加配置读取能力，使 CLI 脚本和 pipeline 层能通过"命令行 > .env > 默认值"的优先级获取配置。

## What Changes

- 新增 `src/ip_info/channel/config.py`：渠道配置基类 + 各渠道配置类（基于 pydantic-settings）
- 修改 `src/ip_info/channel/adapter.py`：`BaseChannelAdapter` 添加 `default_delay` 类属性
- 修改各 ChannelAdapter：构造函数支持从配置类读取默认值
- 新增 `tests/unit/channel/test_config.py`：配置系统测试
- 依赖：`pydantic-settings` 包（legacy 已使用，pyproject.toml 已有依赖）

## Impact

- Affected specs: channel-layer-core (BaseChannelAdapter)
- Affected code: `src/ip_info/channel/adapter.py`, `src/ip_info/channel/config.py` (new), 各渠道适配器

---

## ADDED Requirements

### Requirement: 渠道配置基类

系统 SHALL 在 `src/ip_info/channel/config.py` 中提供 `ChannelConfig` 基类，基于 `pydantic-settings` 的 `BaseSettings`，从 `.env` 文件读取配置。

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class ChannelConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="IP_",
        env_file=".env",
        extra="ignore",
    )
```

配置优先级（pydantic-settings 内置）：**环境变量 > .env 文件 > Field 默认值**

#### Scenario: 从 .env 读取配置

- **WHEN** `.env` 文件包含 `IP_FOFA_API_KEY=xxx`
- **THEN** `FofaHostConfig().fofa_api_key == "xxx"`

#### Scenario: .env 不存在时使用默认值

- **WHEN** `.env` 文件不存在且无环境变量
- **THEN** 配置类使用 Field 中定义的默认值

#### Scenario: 环境变量覆盖 .env

- **WHEN** 环境变量 `IP_FOFA_API_KEY=yyy` 已设置，.env 文件中也有 `IP_FOFA_API_KEY=xxx`
- **THEN** 环境变量优先，`FofaHostConfig().fofa_api_key == "yyy"`

---

### Requirement: 各渠道配置类

系统 SHALL 在 `src/ip_info/channel/config.py` 中为每个渠道提供独立的配置类，字段与 legacy `config.py` 保持一致。

| 配置类 | 必填字段 | 可选字段（含默认值） |
|--------|---------|---------------------|
| `RdnsConfig` | 无 | `rdns_query_timeout=1.5`, `rdns_query_delay=0.1` |
| `IpInfoApiConfig` | `ipinfo_access_token` | `ipinfo_query_timeout=30.0`, `ipinfo_query_delay=1.2` |
| `IpInfoFreeConfig` | 无 | `ipinfo_query_timeout=30.0`, `ipinfo_query_delay=1.2` |
| `FofaHostConfig` | `fofa_api_key` | `fofa_query_timeout=30.0`, `fofa_query_delay=2.0` |
| `FofaSearchConfig` | `fofa_api_key` | `fofa_query_timeout=30.0`, `fofa_query_delay=2.0` |
| `AizhanConfig` | `aizhan_cookie` | `aizhan_query_timeout=15.0`, `aizhan_query_delay=2.0` |
| `ChinazConfig` | 无 | `chinaz_cookie=""`, `chinaz_query_timeout=15.0`, `chinaz_query_delay=2.0` |
| `WhoisConfig` | 无 | `whois_query_timeout=2.0`, `whois_query_delay=0.5` |
| `SslCertConfig` | 无 | `ssl_cert_port=443`, `ssl_cert_timeout=5.0`, `ssl_cert_openssl_timeout=10.0`, `ssl_cert_query_delay=0.5` |
| `ZoomEyeConfig` | 无 | `zoomeye_api_key=""`, `zoomeye_query_timeout=30.0`, `zoomeye_query_delay=2.0` |
| `PortScanConfig` | 无 | `port_scan_nmap_path="nmap"`, `port_scan_timeout=90`, `port_scan_port_list="config/port_scan/top1000.txt"` |

每个配置类还继承 `ChannelConfig` 的通用字段：`storage_dir=""`, `storage_name="ip_data"`。

#### Scenario: 必填字段缺失

- **WHEN** `.env` 中没有 `IP_FOFA_API_KEY`，环境变量也没设置
- **THEN** 创建 `FofaHostConfig()` 抛出 `ValidationError`

#### Scenario: 可选字段使用默认值

- **WHEN** `.env` 中没有 `IP_RDNS_QUERY_DELAY`
- **THEN** `RdnsConfig().rdns_query_delay == 1.5`

---

### Requirement: BaseChannelAdapter.default_delay

系统 SHALL 在 `BaseChannelAdapter` 中添加 `default_delay` 类属性。

```python
class BaseChannelAdapter(ABC):
    channel_name: str = ""
    disabled: bool = False
    default_delay: float = 0
```

#### Scenario: 子类覆盖 default_delay

- **WHEN** `FofaHostChannel.default_delay = 2.0`
- **THEN** `FofaHostChannel().default_delay == 2.0`

#### Scenario: 默认值为 0

- **WHEN** 子类未覆盖 `default_delay`
- **THEN** `RdnsPtrChannel().default_delay == 0`

---

### Requirement: ChannelAdapter 构造函数支持配置类

各 ChannelAdapter 的构造函数 SHALL 支持从配置类实例读取默认值，同时允许显式参数覆盖。

优先级：**显式参数 > 配置类 > 代码默认值**

示例（以 FofaHostChannel 为例）：

```python
class FofaHostChannel(BaseChannelAdapter):
    channel_name = "fofa_host"
    default_delay = 2.0

    def __init__(
        self,
        key: str | None = None,
        timeout: float | None = None,
        config: FofaHostConfig | None = None,
    ):
        _config = config or FofaHostConfig()
        self._key = key or _config.fofa_api_key
        self._timeout = timeout if timeout is not None else _config.fofa_query_timeout
```

#### Scenario: 显式参数覆盖配置类

- **WHEN** `FofaHostChannel(key="manual_key", config=FofaHostConfig(fofa_api_key="env_key"))`
- **THEN** 使用 `key="manual_key"`（显式参数优先）

#### Scenario: 无显式参数时从配置类读取

- **WHEN** `FofaHostChannel(config=FofaHostConfig(fofa_api_key="env_key"))`
- **THEN** 使用 `key="env_key"`（配置类提供）

#### Scenario: 无配置类时自动从 .env 读取

- **WHEN** `FofaHostChannel()`（不传 config）
- **THEN** 自动创建 `FofaHostConfig()` 从 .env 读取

#### Scenario: timeout 为 0 时不被覆盖

- **WHEN** `FofaHostChannel(timeout=0)`
- **THEN** 使用 `timeout=0`（0 是合法值，不是 None）

---

## 与 legacy 的差异

| 方面 | Legacy | 新架构 |
|------|--------|--------|
| **配置来源** | 各脚本 `from channel.xxx import Settings` | ChannelAdapter 内置配置类 |
| **配置优先级** | .env > 代码默认值 | 显式参数 > .env > 代码默认值 |
| **delay 获取** | `Settings().fofa_query_delay` | `channel.default_delay` 或 `config.fofa_query_delay` |
| **配置类位置** | `legacy/config.py` 统一大文件 | `src/ip_info/channel/config.py` 统一大文件 |
| **配置类基类** | `BaseIPSettings(BaseSettings)` | `ChannelConfig(BaseSettings)` |
