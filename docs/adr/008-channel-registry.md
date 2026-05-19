# ADR-008: 渠道注册表（Channel Registry）

## 状态

已采纳

## 上下文

ADR-007 定义了完整版 `ChannelProtocol`，10 个渠道模块各自有适配器类。但 Pipeline 仍然通过 `from channel.xxx import fetch_channel as fetch_xxx` 硬编码导入渠道（编译时绑定），无法在运行时动态查找或替换渠道。

两个 Pipeline 文件（trace_ip / ip_domain_lookup）各自维护一套渠道导入列表，新增渠道时需要修改所有 Pipeline 文件。

## 决策

引入 `ChannelRegistry` 类，提供渠道的注册、查找、验证、采集统一入口：

```python
class ChannelRegistry:
    def register(channel: ChannelProtocol) -> None    # 注册渠道
    def get(name: str) -> ChannelProtocol | None       # 按名查找
    def list_names() -> list[str]                      # 列出所有名称
    def list_channels() -> list[ChannelProtocol]       # 列出所有实例
    def validate_all() -> dict[str, bool]              # 批量验证
    def validate(name: str) -> bool                    # 单个验证
    def fetch(name: str, ip: str, **kwargs) -> dict    # 按名采集
```

`create_default_registry()` 工厂函数自动注册全部 10 个内置渠道适配器。

10 个适配器一览：

| 适配器类 | channel_name | validate 策略 |
|----------|-------------|--------------|
| `FofaHostChannel` | `fofa_host` | catch SystemExit + Exception |
| `FofaSearchChannel` | `fofa_search` | catch SystemExit + Exception |
| `AizhanChannel` | `aizhan` | catch SystemExit + Exception |
| `ChinazChannel` | `chinaz` | catch SystemExit + Exception |
| `ZoomeyeChannel` | `zoomeye` | catch SystemExit + Exception |
| `RdnsPtrChannel` | `rdns_ptr` | catch SystemExit + Exception |
| `WhoisChannel` | `whois` | catch SystemExit + Exception |
| `SslCertChannel` | `ssl_cert` | catch SystemExit + Exception |
| `IpinfoApiChannel` | `ipinfo_api` | catch SystemExit + Exception |
| `PortScanChannel` | `port_scan` | validate_engine() is not None |

## 理由

1. **解耦** — Pipeline 不再硬编码导入，通过注册表查找渠道
2. **可测试** — 测试中注册 InMemoryChannel 即可替代真实渠道
3. **可扩展** — 新增渠道只需创建适配器 + 注册，无需修改 Pipeline
4. **统一验证** — `validate_all()` 一行检查所有渠道可用性

## 后果

**优势：**
- 新增渠道时 Pipeline 无需任何改动
- 测试中可注入受限渠道集合
- 渠道可用性检查从分散的 sys.exit 变为集中的 bool 返回

**劣势：**
- `create_default_registry()` 延迟导入 10 个模块，首次调用有加载开销
- 适配器是薄包装层，增加了间接调用（性能影响可忽略）
- Pipeline 尚未迁移到使用 ChannelRegistry（需后续重构）

**与 Pipeline 的集成路径：**
```python
# 旧方式（硬编码）
from channel.fofa_host import fetch_channel as fetch_fofa_host
result = fetch_fofa_host(ip='1.2.3.4', key=settings.fofa_api_key)

# 新方式（注册表）
reg = create_default_registry()
result = reg.fetch('fofa_host', ip='1.2.3.4', key=settings.fofa_api_key)
```
