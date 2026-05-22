# ADR-007: 完整版 ChannelProtocol

## 状态

已采纳

## 上下文

ADR-002 定义了渠道模板模式（模块级函数），但缺少代码层面的接口约束。最小化 `ChannelFetcher` Protocol（仅 `__call__`）无法表达渠道的完整能力：名称、校验、采集。Pipeline 通过硬编码导入使用渠道，无法在测试中注入 mock 渠道。

10 个渠道存在 7 种架构模式（API Key / 爬虫 / API 双模式 / 本地命令 / Socket / SSL / 第三方库），参数差异大但核心行为一致：校验可用性 → 采集数据。

## 决策

定义 `ChannelProtocol`（`@runtime_checkable`），包含 3 个成员：

```python
@runtime_checkable
class ChannelProtocol(Protocol):
    channel_name: str
    def validate(self) -> bool: ...
    def fetch(self, ip: str, **kwargs) -> dict: ...
```

每个渠道模块底部新增适配器类，包装现有模块级函数：

| 适配器 | channel_name | validate() 策略 |
|--------|-------------|----------------|
| `FofaHostChannel` | `'fofa_host'` | catch SystemExit + Exception |
| `AizhanChannel` | `'aizhan'` | catch SystemExit + Exception |
| `PortScanChannel` | `'port_scan'` | `validate_engine() is not None` + catch Exception |

`validate()` 返回 `bool`（而非 sys.exit），使渠道校验可测试。

`InMemoryChannel` 作为测试替身，支持配置 channel_name / validate_result / fetch_result，记录 fetch 调用。

## 理由

1. **可测试性** — `validate()` 返回 bool，适配器 catch 异常，无需真实网络
2. **结构化子类型** — Protocol 不要求继承，任何有 channel_name + validate + fetch 的类都满足
3. **渐进迁移** — 适配器包装现有函数，不修改原函数签名和行为
4. **为 ⑥ 渠道注册表铺路** — 注册表只需收集 ChannelProtocol 实例

## 后果

**优势：**
- Pipeline 可通过 ChannelProtocol 接口使用渠道，无需硬编码导入
- 测试中可用 InMemoryChannel 替代真实渠道
- 新增渠道只需实现 3 个成员即可自动可用

**劣势：**
- 适配器是薄包装层，增加了间接调用（性能影响可忽略）
- `channel_name: str` 是类注解，`isinstance()` 不检查属性存在（仅检查方法）
- 其余 7 个渠道尚未创建适配器（待 ⑥ 渠道注册表时统一处理）

**与旧 ChannelFetcher 的关系：**
- `ChannelFetcher`（仅 `__call__`）保留，标记为 deprecated
- `ChannelProtocol` 是 `ChannelFetcher` 的超集
- 满足 `ChannelProtocol` 的类不自动满足 `ChannelFetcher`（因为 `fetch` ≠ `__call__`）
