# Phase 1-4 具体阶段逻辑 Spec

## Why

Pipeline 编排框架已就绪，需要实现 Phase 1-4 的具体阶段逻辑，将 store/channel/batch/processors 各层组件串联为完整的 IP 溯源工作流。每个 Phase 需要明确：内部数据流、渠道/处理器如何创建和调用、阶段间数据传递方式。

## What Changes

- 修改 `src/ip_info/utils/load_ips.py` — `load_ips()` 内置 IP 格式校验，过滤无效格式 IP 并记录 WARNING
- 新建 `src/ip_info/pipeline/phases/__init__.py` — 导出所有 Phase 类
- 新建 `src/ip_info/pipeline/phases/phase1_basic.py` — BasicCollectPhase
- 新建 `src/ip_info/pipeline/phases/phase2_classify.py` — ClassifyTagPhase
- 新建 `src/ip_info/pipeline/phases/phase3_deep.py` — DeepQueryPhase
- 新建 `src/ip_info/pipeline/phases/phase4_verify_scan.py` — VerifyScanPhase（DNS 验证 + Nmap 端口扫描并行）
- 新建 `src/ip_info/pipeline/filter_ips.py` — `filter_ips_by_classification()` 过滤函数
- 新建 `src/ip_info/store/sqlite_cache.py` — SqliteDomainCache
- 新建 `tests/unit/pipeline/test_phases.py` — Phase 1-4 测试
- 新建 `tests/unit/pipeline/test_filter_ips.py` — 过滤函数测试
- 新建 `tests/unit/store/test_sqlite_cache.py` — SQLite 缓存测试

## Impact

- Affected specs: build-pipeline-framework (Phase Protocol)
- Affected code: `src/ip_info/utils/load_ips.py`（修改）, `src/ip_info/pipeline/phases/`（新建）, `src/ip_info/pipeline/filter_ips.py`（新建）, `src/ip_info/store/sqlite_cache.py`（新建）

---

## ADDED Requirements

### Requirement: load_ips() 内置 IP 格式校验

`load_ips()` SHALL 在加载 IP 列表时自动校验 IP 格式，过滤无效格式 IP：

```python
def load_ips(file_path: str) -> list[str]:
    """从文件加载 IP 列表。

    处理 UTF-8 BOM、去空行、去重、过滤注释行、校验 IP 格式。
    无效格式的 IP 会被过滤并记录 WARNING 日志。
    """
```

**校验逻辑**：使用 `ipaddress.ip_address()` 校验，仅支持 IPv4/IPv6 地址格式。无效 IP 记录 WARNING 日志后跳过。

**设计理由**：IP 格式校验是工作流框架的基础能力，所有工作流都需要，应内置在 `load_ips()` 中而非依赖调用方额外处理。

#### Scenario: 混合有效和无效 IP
- **WHEN** 文件内容为 `1.2.3.4\nabc\n999.999.999.999\n8.8.8.8`
- **THEN** 返回 `["1.2.3.4", "8.8.8.8"]`，WARNING 日志记录 `abc` 和 `999.999.999.999`

#### Scenario: 全部有效
- **WHEN** 文件内容为 `1.2.3.4\n8.8.8.8`
- **THEN** 返回 `["1.2.3.4", "8.8.8.8"]`，无 WARNING

#### Scenario: 全部无效
- **WHEN** 文件内容为 `abc\nnot_an_ip`
- **THEN** 返回 `[]`，WARNING 日志记录所有无效 IP

#### Scenario: 注释行和空行不受影响
- **WHEN** 文件内容为 `# comment\n\n1.2.3.4`
- **THEN** 返回 `["1.2.3.4"]`，注释行和空行正常过滤

---

### Requirement: IP 分类过滤函数 (filter_ips_by_classification)

系统 SHALL 提供 `filter_ips_by_classification()` 函数，作为 Phase 2 和 Phase 3 之间的脚本动作，从 store 读取分类结果，筛选需要深度查询的 IP。

```python
def filter_ips_by_classification(
    ips: list[str],
    reader: IPDataReader,
) -> list[str]:
    """根据分类结果过滤 IP，返回需要深度查询的 IP 列表。

    保留 need_deep_query=True 的 IP（cloud_provider/residential/other），
    过滤 need_deep_query=False 的 IP（invalid_rdns/cdn/crawler_scanner）。
    无分类数据的 IP 默认保留。
    """
```

**过滤规则**：
| 分类 | need_deep_query | 处理 |
|------|----------------|------|
| cloud_provider | True | 保留 |
| residential | True | 保留 |
| other（默认） | True | 保留 |
| invalid_rdns | False | 过滤 |
| cdn | False | 过滤 |
| crawler_scanner | False | 过滤 |

**设计理由**：过滤是一个脚本动作（决定哪些 IP 继续），不是渠道收集。它与深度查询有前后依赖关系——必须先确定 IP 列表，才能执行深度查询。因此独立为函数而非 Phase。

#### Scenario: 正常过滤
- **WHEN** 输入 3 个 IP，其中 1 个 cdn、1 个 cloud_provider、1 个 other
- **THEN** 返回 cloud_provider 和 other 的 IP

#### Scenario: 全部被过滤
- **WHEN** 所有 IP 都是 invalid_rdns/cdn/crawler_scanner
- **THEN** 返回空列表

#### Scenario: 无分类数据的 IP
- **WHEN** 某些 IP 在 store 中无 classifier 渠道数据
- **THEN** 该 IP 默认保留

---

### Requirement: Phase 1 — 基础情报采集 (BasicCollectPhase)

系统 SHALL 提供 `BasicCollectPhase` 类，实现 Phase Protocol。

**构造函数**：
```python
class BasicCollectPhase:
    def __init__(
        self,
        ips: list[str],
        writer: IPDataWriter,
        reader: IPDataReader,
        ipinfo_channel: BaseChannelAdapter,
        rdns_channel: BaseChannelAdapter,
        *,
        no_validate: bool = False,
        rdns_workers: int = 1,
    ):
```

**内部逻辑**：
1. 空输入检查：ips 为空时返回 `PhaseResult(success=True, message="无 IP 需处理")`
2. 使用 `ThreadPoolExecutor` 并行执行两个渠道批量查询：
   - **ipinfo_api**：`BaseBatchQuery(channel_name="ipinfo_api", channel=ipinfo_channel, writer=writer, ips=ips, no_validate=no_validate).run()`
   - **rdns_ptr**：`run_concurrent(ips=ips, channel=rdns_channel, writer=writer, channel_name="rdns_ptr", workers=rdns_workers, no_validate=no_validate)`
3. 两个渠道各自批量处理**所有 IP**，全部完成后返回
4. 渠道验证失败（`channel.disabled=True`）时跳过该渠道，记录 WARNING，继续执行其他渠道
5. 汇总两个 BatchResult，写入 PhaseResult：
   - `success`：至少一个渠道成功即为 True
   - `message`：格式 `"ipinfo_api: {n}成功, rdns_ptr: {m}成功"`
   - `data["ipinfo_result"]` / `data["rdns_result"]`：各自的 BatchResult

#### Scenario: 正常执行
- **WHEN** 调用 `BasicCollectPhase(ips, writer, reader, ipinfo_ch, rdns_ch).run()`
- **THEN** ipinfo_api 和 rdns_ptr 各自批量处理所有 IP，结果通过 writer 写入 store

#### Scenario: 空输入
- **WHEN** IP 列表为空
- **THEN** 返回 PhaseResult(success=True, message="无 IP 需处理")

#### Scenario: 渠道验证失败
- **WHEN** ipinfo_channel.validate() 后 channel.disabled=True
- **THEN** 跳过 ipinfo_api 渠道，记录 WARNING，rdns_ptr 正常执行

#### Scenario: 两个渠道都失败
- **WHEN** 两个渠道都 disabled 或都返回 fail_count > 0 且 success_count == 0
- **THEN** 返回 PhaseResult(success=False, message="所有渠道查询失败")

---

### Requirement: Phase 2 — 分类 + 标签 (ClassifyTagPhase)

系统 SHALL 提供 `ClassifyTagPhase` 类，实现 Phase Protocol。

**构造函数**：
```python
class ClassifyTagPhase:
    def __init__(
        self,
        ips: list[str],
        writer: IPDataWriter,
        reader: IPDataReader,
        rules_dir: str,
        tagger_config_dir: str,
        *,
        no_tagger: bool = False,
        tagger_level: int | None = None,
    ):
```

**内部逻辑**：
1. 空输入检查
2. **分类**：`BatchClassifier(ips, writer, reader, rules_dir).run()` — 对所有 IP 执行分类
3. **标签打标**（除非 `no_tagger=True`）：`BatchTagger(ips, writer, tagger_config_dir, level=tagger_level).run()`
4. 返回 PhaseResult，**不包含过滤逻辑**（过滤由 `filter_ips_by_classification()` 函数完成）

#### Scenario: 正常执行
- **WHEN** 调用 `ClassifyTagPhase(ips, writer, reader, rules_dir, tagger_config_dir).run()`
- **THEN** 先分类，再标签，结果写入 store

#### Scenario: no_tagger=True
- **WHEN** 传入 no_tagger=True
- **THEN** 跳过标签打标步骤，只执行分类

#### Scenario: 空输入
- **WHEN** ips 为空
- **THEN** 返回 PhaseResult(success=True, message="无 IP 需分类")

---

### Requirement: Phase 3 — 深度查询 (DeepQueryPhase)

系统 SHALL 提供 `DeepQueryPhase` 类，实现 Phase Protocol。此阶段仅对过滤后的 IP 执行多渠道深度收集。

**构造函数**：
```python
class DeepQueryPhase:
    def __init__(
        self,
        ips: list[str],
        writer: IPDataWriter,
        reader: IPDataReader,
        aizhan_channel: BaseChannelAdapter,
        chinaz_channel: BaseChannelAdapter,
        fofa_channel: BaseChannelAdapter,
        *,
        no_validate: bool = False,
    ):
```

**内部逻辑**：
1. 空输入检查：ips 为空时返回 `PhaseResult(success=True, message="无 IP 需深度查询")`
2. 使用 `ThreadPoolExecutor` 并行执行三个渠道批量查询：
   - **aizhan**：`BaseBatchQuery(channel_name="aizhan", channel=aizhan_channel, writer=writer, ips=ips, no_validate=no_validate).run()`
   - **chinaz**：`BaseBatchQuery(channel_name="chinaz", channel=chinaz_channel, writer=writer, ips=ips, no_validate=no_validate).run()`
   - **fofa_host**：`BaseBatchQuery(channel_name="fofa_host", channel=fofa_channel, writer=writer, ips=ips, no_validate=no_validate).run()`
3. 三个渠道各自批量处理**所有传入的 IP**，全部完成后返回
4. 渠道验证失败时跳过该渠道，记录 WARNING
5. 汇总三个 BatchResult

**注意**：此 Phase 不负责过滤，过滤由调用方在创建 Phase 3 之前通过 `filter_ips_by_classification()` 完成。

#### Scenario: 正常执行
- **WHEN** 调用 `DeepQueryPhase(filtered_ips, writer, reader, aizhan_ch, chinaz_ch, fofa_ch).run()`
- **THEN** 三个渠道各自批量处理所有 IP，结果写入 store

#### Scenario: 空输入
- **WHEN** ips 为空（所有 IP 被过滤）
- **THEN** 返回 PhaseResult(success=True, message="无 IP 需深度查询")

#### Scenario: 部分渠道验证失败
- **WHEN** aizhan 渠道 disabled
- **THEN** 跳过 aizhan，chinaz 和 fofa_host 正常执行

---

### Requirement: Phase 4 — 验证 + Nmap 扫描 (VerifyScanPhase)

系统 SHALL 提供 `VerifyScanPhase` 类，实现 Phase Protocol。DNS 域名验证和 Nmap 端口扫描无冲突，并行执行。

**构造函数**：
```python
class VerifyScanPhase:
    def __init__(
        self,
        ips: list[str],
        writer: IPDataWriter,
        reader: IPDataReader,
        nmap_channel: PortScanChannel,
        *,
        domain_cache=None,  # DomainCache Protocol
        force_days: int | None = None,
        max_age_days: int = 7,
        dns_timeout: float = 3.0,
        dns_concurrency: int = 10,
        nmap_workers: int = 1,
        no_validate: bool = False,
    ):
```

**内部逻辑**：
1. 空输入检查
2. 使用 `ThreadPoolExecutor` 并行执行两个任务：
   - **DNS 验证**：`BatchDnsVerify(ips, writer, reader, domain_cache=domain_cache, force_days=force_days, max_age_days=max_age_days, timeout=dns_timeout, concurrency=dns_concurrency).run()`
   - **Nmap 端口扫描**：`run_concurrent(ips=ips, channel=nmap_channel, writer=writer, channel_name="port_scan", workers=nmap_workers, no_validate=no_validate)`
3. 两个任务各自批量处理所有 IP，全部完成后返回
4. 汇总两个结果，写入 PhaseResult

**端口扫描说明**：使用 `PortScanChannel`（基于 python-nmap 库），扫描参数为 `-sT -T4 -Pn --open`。`nmap_channel` 参数类型明确为 `PortScanChannel`，不虚构其他端口扫描渠道。

#### Scenario: 正常执行
- **WHEN** 调用 `VerifyScanPhase(ips, writer, reader, nmap_ch, domain_cache=cache).run()`
- **THEN** DNS 验证和 Nmap 端口扫描并行执行，结果写入 store

#### Scenario: 空 IP 列表
- **WHEN** ips 为空
- **THEN** 返回 PhaseResult(success=True, message="无 IP 需验证/扫描")

#### Scenario: 无 domain_cache
- **WHEN** domain_cache=None
- **THEN** DNS 验证不使用缓存，Nmap 扫描正常执行

---

### Requirement: 阶段间数据流

Pipeline 的阶段间数据流如下：

```
load_ips() → [有效IP列表]
    ↓
Phase 1: 基础情报采集 (ipinfo_api + rdns_ptr)
    ↓
Phase 2: 分类 + 标签 (BatchClassifier + BatchTagger)
    ↓
filter_ips_by_classification() → [filtered_ips]  ← 脚本动作，非 Phase
    ↓
Phase 3: 深度查询 (aizhan + chinaz + fofa_host)  ← 仅处理 filtered_ips
    ↓
Phase 4: 验证 + Nmap 扫描 (BatchDnsVerify + PortScanChannel)  ← 仅处理 filtered_ips
```

**关键点**：
1. `filter_ips_by_classification()` 是 Phase 2 和 Phase 3 之间的脚本动作，不是 Phase
2. Phase 3 和 Phase 4 的 `ips` 参数由调用方通过 `filter_ips_by_classification()` 的返回值决定
3. Phase 自身不关心 IP 来源，只负责执行渠道查询

**Pipeline 使用示例**：
```python
# 加载 IP（内置格式校验）
ips = load_ips("ips.txt")

# Phase 1-2：全量 IP
pipeline = Pipeline()
pipeline.register(BasicCollectPhase(ips, writer, reader, ipinfo_ch, rdns_ch))
pipeline.register(ClassifyTagPhase(ips, writer, reader, rules_dir, tagger_config_dir))
result = pipeline.run()

# 过滤：脚本动作
filtered_ips = filter_ips_by_classification(ips, reader)

# Phase 3-4：仅过滤后的 IP
pipeline2 = Pipeline()
pipeline2.register(DeepQueryPhase(filtered_ips, writer, reader, aizhan_ch, chinaz_ch, fofa_ch))
pipeline2.register(VerifyScanPhase(filtered_ips, writer, reader, nmap_ch, domain_cache=cache))
result2 = pipeline2.run()
```

> 注意：当前 Pipeline.run() 不支持阶段间自动传递 filtered_ips。这需要 CLI 脚本手动编排，或后续增强 Pipeline 类。本次实现中，Phase 类本身是独立的，不依赖 Pipeline 的自动传递。

---

### Requirement: SqliteDomainCache 实现

系统 SHALL 提供 `SqliteDomainCache` 类，实现 DomainCache Protocol。

**SQLite Schema**：
```sql
CREATE TABLE IF NOT EXISTS domain_cache (
    domain TEXT PRIMARY KEY,
    data TEXT NOT NULL,          -- JSON 序列化的 dict
    updated_at TEXT NOT NULL     -- ISO 8601 时间戳
);
```

**构造函数**：
```python
class SqliteDomainCache:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._local = threading.local()  # 每线程独立连接
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接（线程安全）。"""
        ...

    def _init_db(self):
        """创建表和索引。"""
        ...
```

**方法实现**：
- `get(domain) -> dict | None`：查询 domain，反序列化 JSON 返回；不存在返回 None
- `set(domain, data) -> None`：INSERT OR REPLACE，序列化 data 为 JSON，更新 updated_at

**线程安全策略**：
- 使用 `threading.local()` 为每个线程创建独立的 `sqlite3.Connection`
- SQLite WAL 模式启用并发读
- 写操作依赖 SQLite 自身的锁机制（INSERT OR REPLACE 是原子的）

#### Scenario: 正常读写
- **WHEN** 调用 `cache.set("example.com", {"status": "matched"})` 后 `cache.get("example.com")`
- **THEN** 返回 `{"status": "matched"}`

#### Scenario: 不存在的域名
- **WHEN** 调用 `cache.get("notexist.com")`
- **THEN** 返回 None

#### Scenario: 覆盖写入
- **WHEN** 对同一域名调用两次 set
- **THEN** 第二次覆盖第一次，updated_at 更新

#### Scenario: 并发安全
- **WHEN** 多线程同时读写
- **THEN** 无数据丢失，无异常，每个线程使用独立连接

#### Scenario: 数据库文件自动创建
- **WHEN** db_path 指向不存在的文件
- **THEN** 自动创建数据库文件和表结构

---

### Requirement: 测试策略 — Mock 到存储层

所有 Phase 测试 SHALL 遵循以下策略：

1. **存储层**：使用 `InMemoryIPWriter` / `InMemoryIPReader`（已实现）
2. **渠道层**：使用 `unittest.mock.MagicMock` 模拟 `BaseChannelAdapter`，mock `fetch()` 和 `validate()` 方法
3. **DomainCache**：使用 `InMemoryDomainCache`（Phase 4 测试），`SqliteDomainCache` 单独测试
4. **不发起真实网络请求**：所有渠道查询通过 mock 返回预设数据

**测试文件组织**：
- `tests/unit/pipeline/test_phases.py` — Phase 1-4 所有测试
- `tests/unit/pipeline/test_filter_ips.py` — filter_ips_by_classification 测试
- `tests/unit/store/test_sqlite_cache.py` — SqliteDomainCache 测试

**测试数据流验证**：
- Phase 1：验证 `writer.get_channel_data(ip, "ipinfo_api")` 和 `writer.get_channel_data(ip, "rdns_ptr")` 返回预期数据
- Phase 2：验证 `writer.get_channel_data(ip, "classifier")` 和 `writer.get_channel_data(ip, "tagger")` 包含分类/标签结果
- filter_ips_by_classification：验证返回的 IP 列表正确过滤
- Phase 3：验证 `writer.get_channel_data(ip, "aizhan")` 等渠道数据
- Phase 4：验证 `writer.get_channel_data(ip, "domain_verify")` 和 `writer.get_channel_data(ip, "port_scan")` 包含正确结果

---

### Requirement: 开发流程

实现过程 SHALL 遵循 TDD + git-commit 循环：
1. 先写测试，再写实现
2. 每个逻辑单元完成后 git commit
3. 测试全部 mock 到存储层（InMemoryIPWriter/InMemoryIPReader）
4. Phase 测试中渠道查询使用 mock，不发起真实网络请求
5. ruff 格式检查通过

---

## REMOVED Requirements

### Requirement: Phase 6-7 报告生成
**Reason**: 本次只实现 Phase 1-4，报告生成后续 spec
**Migration**: 下一个 spec

### Requirement: PidManager
**Reason**: 不在本次范围
**Migration**: 后续按需添加
