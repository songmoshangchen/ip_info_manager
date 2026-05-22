# Handoff 文档 — ip_info_manager 重构项目

> 生成时间: 2026-05-22
> 项目路径: `E:\12_trae_skills\ip_info_manager`

---

## 一、项目概况

**ip_info_manager** 是一个 IP 信息管理工具，正在从 legacy 代码重构为新架构。采用"从内向外、逐步迁移"策略，已完成存储层、渠道层、批量查询层核心。

### 重构策略
- 新文件夹起步（`src/ip_info/`），legacy 代码作为只读参考
- 从最内层（存储层）逐步向外扩展
- 每步极小可验证：一个测试 → 一个实现 → 一个提交
- 先协议后实现，TDD 红-绿-重构循环

### 总体架构
```
src/ip_info/
├── store/       # 存储层 ✅ 已完成
├── channel/     # 渠道层 ✅ 已完成
├── batch/       # 批量查询层（核心已完成，CLI 脚本待做）
└── pipeline/    # 流水线层（未开始）
```

---

## 二、已完成工作

### 第 1 层：存储层 ✅
- `IPDataWriter` / `IPDataReader` 协议
- `InMemoryIPWriter` / `InMemoryIPReader` 测试替身
- `IPWriter` / `IPReader` JSON 文件实现（含线程锁）
- 对应测试全部通过

### 第 2 层：渠道层 ✅
- `ChannelProtocol` / `ChannelFetcher` 协议
- `ChannelRegistry` 注册表
- `BaseChannelAdapter` 抽象基类（disabled 标志、validate/fetch 委托）
- 11 个渠道适配器全部实现：
  - `RdnsPtrChannel`（RDNS 反向解析）
  - `IpinfoApiChannel`（IPInfo API 版）
  - `IpinfoFreeChannel`（IPInfo 免费版）
  - `FofaHostChannel`（FOFA 主机查询）
  - `FofaSearchChannel`（FOFA 搜索）
  - `AizhanChannel`（爱站网）
  - `ChinazChannel`（站长之家）
  - `WhoisQueryChannel`（Whois 查询）
  - `SslCertChannel`（SSL 证书查询）
  - `PortScanChannel`（端口扫描）
  - `InMemoryChannel`（测试替身）
- 对应测试全部通过

### 第 3 层：批量查询层（核心） ✅
- **规格文档**: `.trae/specs/build-batch-layer-core/spec.md`
- **核心文件**:
  - `src/ip_info/batch/protocols.py` — ProgressTracker 协议
  - `src/ip_info/batch/progress.py` — InMemoryProgressTracker + FileProgressTracker
  - `src/ip_info/batch/query.py` — BatchResult 数据类 + BaseBatchQuery 具体类
- **关键设计决策**:
  - BaseBatchQuery 是具体类（构造函数注入渠道，非 ABC）
  - 所有 ChannelError 统一处理：不写入 store + 不标记进度 + 计入熔断
  - ChannelPermanentError 导致渠道 disabled 后终止查询
  - 熔断保护：连续 N 次 ChannelError 后自动停止
  - 测试面向结果：不访问私有属性，通过 BatchResult 和 writer.writes 验证
- **测试**: `tests/unit/batch/test_progress.py`（8个）+ `tests/unit/batch/test_query.py`（32个）

### 日志系统设计 ✅
- 各层独立使用 `logging.getLogger(__name__)`
- 由调用方配置 handler（控制台 + 文件）
- 不在库代码中配置 handler

---

## 三、待做工作（按优先级排序）

### P0: 配置系统实现（add-channel-config）

**规格文档**: `.trae/specs/add-channel-config/spec.md`

**目的**: 让 ChannelAdapter 能从 `.env` 文件读取配置，支持"显式参数 > .env > 默认值"优先级。

**具体工作**:

1. **添加 `pydantic-settings` 依赖**到 `pyproject.toml`
   - 当前 `pyproject.toml` 缺少运行时依赖声明
   - 需添加 `pydantic-settings` 和其他运行时依赖（`requests`, `beautifulsoup4`, `python-whois`, `python-nmap`）

2. **新增 `src/ip_info/channel/config.py`**
   - `ChannelConfig` 基类（基于 `pydantic-settings.BaseSettings`，env_prefix="IP_"）
   - 11 个渠道配置类（如 `RdnsConfig`, `FofaHostConfig`, `IpInfoApiConfig` 等）
   - 每个配置类的字段与 legacy `config.py` 保持一致

3. **修改 `src/ip_info/channel/adapter.py`**
   - 添加 `default_delay: float = 0` 类属性到 `BaseChannelAdapter`

4. **修改 11 个 ChannelAdapter 构造函数**
   - 当前构造函数示例: `FofaHostChannel(key: str, timeout: float = 30.0)` — key 是必填的
   - 改为: `FofaHostChannel(key: str | None = None, timeout: float | None = None, config: FofaHostConfig | None = None)`
   - 优先级: 显式参数 > config 对象 > 代码默认值
   - 注意 `timeout=0` 是合法值，要用 `if timeout is not None` 而非 `if timeout`

5. **新增测试** `tests/unit/channel/test_config.py`

6. **更新 `src/ip_info/channel/__init__.py`** 导出配置类

**各渠道当前构造函数签名**（需要改造的）:

| 渠道 | 当前签名 | 必填字段 |
|------|---------|---------|
| `RdnsPtrChannel` | `(timeout=3.0)` | 无 |
| `IpinfoApiChannel` | `(token: str, timeout=30.0)` | token |
| `IpinfoFreeChannel` | `(timeout=30.0)` | 无 |
| `FofaHostChannel` | `(key: str, timeout=30.0)` | key |
| `FofaSearchChannel` | `(key: str, timeout=30.0)` | key |
| `AizhanChannel` | `(cookie: str, timeout=15.0)` | cookie |
| `ChinazChannel` | `(cookie: str, timeout=15.0)` | cookie |
| `WhoisQueryChannel` | `(timeout=10.0)` | 无 |
| `SslCertChannel` | `(port=443, timeout=5.0, openssl_timeout=10.0)` | 无 |
| `PortScanChannel` | `(nmap_path="nmap", timeout=30.0)` | 无 |

**渠道配置类字段**（详见 spec）:

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

每个配置类还继承通用字段：`storage_dir=""`, `storage_name="ip_data"`。

---

### P1: 批量 CLI 脚本（build-batch-scripts）

**规格文档**: `.trae/specs/build-batch-scripts/spec.md`

**前置依赖**: 配置系统完成

**具体工作**:

1. **新增 `src/ip_info/batch/cli.py`** — CLI 工具函数
   - `load_ip_file(path) -> (list[str], dict)` — 加载去重 IP 列表
   - `setup_batch_logging(channel_name)` — 配置控制台 + 文件 handler
   - `default_progress_file(storage_file, channel_name) -> str` — 生成进度文件路径

2. **新增 `scripts/` 目录**（项目根目录，不在 src 内）

3. **9 个 CLI 脚本**:

| 脚本 | 渠道适配器 | 额外参数 | 备注 |
|------|-----------|---------|------|
| `batch_rdns_ptr.py` | `RdnsPtrChannel` | `--workers N` | 支持并发 |
| `batch_ipinfo_api.py` | `IpinfoApiChannel` | 无 | |
| `batch_ipinfo_free.py` | `IpinfoFreeChannel` | 无 | ipinfo 拆分 |
| `batch_fofa_host.py` | `FofaHostChannel` | 无 | |
| `batch_fofa_search.py` | `FofaSearchChannel` | 无 | |
| `batch_aizhan.py` | `AizhanChannel` | 无 | |
| `batch_chinaz.py` | `ChinazChannel` | 无 | |
| `batch_whois.py` | `WhoisQueryChannel` | 无 | |
| `batch_ssl_cert.py` | `SslCertChannel` | 无 | |

**不写**: zoomeye（无适配器）、port_scan（legacy 也没有）

4. **RDNS 并发**: `batch_rdns_ptr.py` 通过 `--workers N` + `concurrent.futures.ThreadPoolExecutor` 实现，不修改 BaseBatchQuery

5. **CLI 脚本模板**:
```python
def main():
    args = parse_args()
    setup_batch_logging(CHANNEL_NAME)
    ips, stats = load_ip_file(args.ip_file)
    channel = XxxChannel()  # 自动从 .env 读取
    writer = IPWriter(...)
    tracker = FileProgressTracker(...)
    query = BaseBatchQuery(
        channel_name=CHANNEL_NAME, channel=channel,
        writer=writer, ips=ips, delay=channel.default_delay,
        no_validate=args.no_validate, progress_tracker=tracker,
    )
    result = query.run()
```

---

### P2: 流水线层（未开始）
- PhaseRunner + ProgressManager + 各 phase
- 参考重构方案 Step 4

---

## 四、关键设计决策汇总

| 决策点 | 结论 | 理由 |
|--------|------|------|
| IP 列表加载 | 构造函数接受 `ips: list[str]`，文件加载由调用方 | 职责单一 |
| 进度跟踪 | ProgressTracker 协议 + File 实现 | 解耦 + 测试友好 |
| 批次模式 | 不提供 batch_mode，固定写入 channel_name | YAGNI |
| ETA 估算 | 不在 batch 层实现 | 不属于核心逻辑 |
| 错误处理 | ChannelError 不写入 + 不标记进度 + 计入熔断 | 简化逻辑 |
| 日志系统 | `logging.getLogger(__name__)`，调用方配 handler | Python 标准 |
| 配置优先级 | 显式参数 > .env > 默认值 | pydantic-settings |
| CLI 位置 | `scripts/`（项目根目录），不在 src 内 | 应用层 vs 库代码 |
| RDNS 并发 | CLI 层 ThreadPoolExecutor，不改 BaseBatchQuery | 不污染核心 |

---

## 五、测试原则

- **面向结果**：不访问私有属性（`_xxx`），通过公开返回值（BatchResult、writer.writes）验证行为
- **协议驱动**：先定义 Protocol，再写测试替身和真实实现
- **TDD 红-绿-重构**：先写测试再实现

---

## 六、验证标准

每步完成后：
1. `python -m pytest tests/ -q` — 全部通过
2. 无 `sys.path.insert` hack
3. 无 `from legacy import ...`
4. 新代码有对应测试覆盖

---

## 七、推荐 Skills

| 任务 | 推荐 Skill |
|------|-----------|
| 配置系统实现 | `tdd` → `git-commit` |
| CLI 脚本实现 | `tdd` → `git-commit`（批量重复，可用 `caveman` 省 token） |
| 遇到 bug | `diagnose` |

---

## 八、Git 提交规范

- 中文翻译的 conventional commit 格式
- 按逻辑分组提交
- 每个提交只做一件事

---

## 九、关键文件索引

| 文件 | 说明 |
|------|------|
| `.trae/documents/refactoring-plan.md` | 重构总方案（含完成状态） |
| `.trae/specs/add-channel-config/` | 配置系统规格（**待实现**） |
| `.trae/specs/build-batch-scripts/` | CLI 脚本规格（**待实现**） |
| `.trae/specs/build-batch-layer-core/` | 批量查询核心规格（已完成） |
| `src/ip_info/channel/adapter.py` | BaseChannelAdapter（需加 default_delay） |
| `src/ip_info/batch/query.py` | BaseBatchQuery 核心 |
| `pyproject.toml` | 缺少运行时依赖，需补充 |
