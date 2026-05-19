# 测试 Mock 清单

本文档列出所有测试文件中 **mock/替身** 和 **未 mock（真实调用）** 的内容，方便排查测试样例。

## Mock 策略总览

| 策略 | 说明 | 使用场景 |
|------|------|---------|
| `InMemoryIPWriter` | 纯内存测试替身，实现 `IPDataWriter` + `IPDataReader` | PhaseRunner / Protocol 测试 |
| `InMemoryIPReader` | 纯内存测试替身，实现 `IPDataReader` | Reader 单元测试 |
| `InMemoryChannel` | 纯内存测试替身，实现 `ChannelProtocol` | ChannelRegistry / Pipeline 模式测试 |
| `unittest.mock.patch` | 替换模块级函数 | 渠道适配器的 `validate_channel_key` / `fetch_channel` / `validate_engine` |
| `_DummyWriter` | 内联轻量替身 | BaseBatchQuery.run() 测试 |
| `_DummyPid` | 内联轻量替身 | BaseBatchQuery.run() PID 管理测试 |
| `_DummyLogger` | 内联轻量替身 | BaseBatchQuery.run() 日志测试 |
| `_ConcreteBatch` | 内联子类替身 | BaseBatchQuery.run() 测试 |
| `FakeSettings` | 内联轻量替身 | BaseBatchQuery._get_delay() 测试 |
| `DummyBatch` | 内联子类替身 | BaseBatchQuery 各方法测试 |
| `monkeypatch` | pytest 内置环境变量 mock | config.py 环境变量测试 |
| `tmp_path` | pytest 内置临时目录 | 文件 I/O 测试 |

---

## 逐文件 Mock 详情

### test_in_memory_writer.py (9 tests)

**Mock：** 无外部 mock，直接测试 `InMemoryIPWriter` 替身自身行为

**未 Mock：**
- `InMemoryIPWriter` — 这是测试目标本身，不是 mock

**排查注意：**
- `InMemoryIPWriter` 同时实现了 `IPDataWriter` 和 `IPDataReader`，但 `get_all()` 不属于 Protocol 接口
- 测试不涉及文件系统，纯内存操作

---

### test_in_memory_reader.py (17 tests)

**Mock：** 无外部 mock，直接测试 `InMemoryIPReader` 替身自身行为

**未 Mock：**
- `InMemoryIPReader` — 测试目标本身
- `InMemoryIPWriter` — 仅用于 fixture 构造测试数据（`populated_reader` fixture）

**排查注意：**
- `InMemoryIPReader` 通过 dict 初始化，与 `InMemoryIPWriter.get_all()` 配合
- 测试不涉及文件系统

---

### test_protocol_conformance.py (8 tests)

**Mock：** 无

**未 Mock：**
- `IPDataWriter` / `IPDataReader` / `ChannelProtocol` — Protocol 定义本身
- `InMemoryIPWriter` / `InMemoryIPReader` / `InMemoryChannel` — 验证它们满足 Protocol

**排查注意：**
- 测试 `isinstance()` 运行时检查，依赖 `@runtime_checkable` 装饰器
- 如果 Protocol 定义变更（如新增方法），这些测试会失败

---

### test_channel_base.py (10 tests)

**Mock：** 无

**未 Mock：**
- `channel.base.apply_delay` — 实际调用 `time.sleep()`
- `channel.base.format_output` — 实际调用

**排查注意：**
- `apply_delay` 测试会真正 sleep，可能较慢
- `format_output` 测试依赖 `data.setdefault()` 行为

---

### test_channel_protocol.py (36 tests)

**Mock：** 无

**未 Mock：**
- `InMemoryChannel` — 测试目标本身
- `ChannelProtocol` — Protocol 定义

**排查注意：**
- 测试 `InMemoryChannel` 的 `validate()` / `fetch()` 行为
- 测试 `isinstance(channel, ChannelProtocol)` 运行时检查

---

### test_channel_registry.py (46 tests)

**Mock：** 无

**未 Mock：**
- `ChannelRegistry` — 测试目标本身
- `InMemoryChannel` — 作为注册的渠道替身

**排查注意：**
- 测试 `register()` 的 `isinstance` 类型检查
- 测试 `validate_all()` / `fetch()` / `get()` / `list_names()` 等方法
- 不涉及真实渠道（FofaHostChannel 等）

---

### test_batch_run.py (36 tests)

**Mock：**
- `_DummyWriter` — 替代 `IPWriter`，内存存储
- `_DummyPid` — 替代 `PidManager`，空操作
- `_DummyLogger` — 替代日志，空操作
- `_ConcreteBatch` — 继承 `BaseBatchQuery` 的测试子类

**未 Mock：**
- `BaseBatchQuery.__init__` — 真实调用，需要 `ip_file` 存在
- `time.sleep()` — 真实调用（但 delay 设为 0）

**排查注意：**
- 测试创建临时 IP 文件（通过 `tmp_path`）
- `_ConcreteBatch` 通过 `__new__` + 手动属性设置模式创建
- `_get_delay` 在 `_ConcreteBatch` 中读取 `self._test_delay`

---

### test_trace_utils.py (26 tests)

**Mock：** 无

**未 Mock：**
- `trace_utils` 中的 9 个共享域函数 — 直接测试

**排查注意：**
- 纯函数测试，无副作用

---

### test_phase_runner.py (10 tests)

**Mock：**
- `InMemoryIPWriter` — 同时作为 writer 和 reader

**未 Mock：**
- `PhaseRunner` — 测试目标本身

**排查注意：**
- `InMemoryIPWriter` 需要同时支持 writer 和 reader 接口
- 测试覆盖进度回调、查询、写入循环

---

### test_base_batch.py (14 tests)

**Mock：**
- `DummyBatch` — 内联子类替身
- `FakeSettings` — 内联设置替身

**未 Mock：**
- `BaseBatchQuery` 各方法 — 直接测试

**排查注意：**
- 使用 `tmp_path` 创建临时 IP 文件

---

### test_config.py (25 tests)

**Mock：**
- `monkeypatch` — 设置/清除环境变量
- `BaseIPSettings(_env_file=None)` — 禁用 `.env` 文件读取

**未 Mock：**
- `BaseIPSettings` — 测试目标本身
- Pydantic V2 验证逻辑

**排查注意：**
- 必须使用 `_env_file=None` 避免读取项目 `.env` 文件
- 测试 `model_config = SettingsConfigDict(...)` 配置

---

### test_pipeline_registry.py (8 tests)

**Mock：**
- `InMemoryChannel` — 替代真实渠道
- `ChannelRegistry` — 真实注册表，但注册的是 InMemoryChannel

**未 Mock：**
- `ChannelRegistry` — 测试目标本身

**排查注意：**
- 测试 Pipeline 通过 `registry.get('xxx').fetch()` 调用渠道
- 不涉及真实渠道实现

---

### test_progress.py (11 tests)

**Mock：** 无

**未 Mock：**
- `ProgressManager` — 测试目标本身
- 文件系统 I/O — 真实写入临时目录

**排查注意：**
- 使用 `tempfile.mkdtemp()` 创建临时目录
- 测试真实文件读写，需要清理

---

## 关键依赖关系

```
InMemoryIPWriter ──→ 实现 IPDataWriter + IPDataReader
InMemoryIPReader ──→ 实现 IPDataReader
InMemoryChannel  ──→ 实现 ChannelProtocol
ChannelRegistry  ──→ 依赖 ChannelProtocol (isinstance 检查)
BaseBatchQuery   ──→ 依赖 IPWriter, PidManager, Logger (测试中用 Dummy 替身)
PhaseRunner      ──→ 依赖 IPDataWriter + IPDataReader (测试中用 InMemoryIPWriter)
Pipeline         ──→ 依赖 ChannelRegistry (测试中用 InMemoryChannel)
```

---

## 文件 I/O 依赖

| 测试文件 | 是否需要文件系统 | 说明 |
|---------|---------------|------|
| test_in_memory_writer | 否 | 纯内存 |
| test_in_memory_reader | 否 | 纯内存 |
| test_protocol_conformance | 否 | 纯类型检查 |
| test_channel_base | 否 | 纯函数 |
| test_channel_protocol | 否 | 纯内存 |
| test_channel_registry | 否 | 纯内存 |
| test_batch_run | 是 | `tmp_path` 创建临时 IP 文件 |
| test_trace_utils | 否 | 纯函数 |
| test_phase_runner | 否 | 纯内存 |
| test_base_batch | 是 | `tmp_path` 创建临时 IP 文件 |
| test_config | 否 | `_env_file=None` |
| test_pipeline_registry | 否 | 纯内存 |
| test_progress | 是 | `tempfile.mkdtemp()` 创建临时目录 |

---

## `unittest.mock.patch` 使用详情

以下测试使用了 `unittest.mock.patch` 替换模块级函数：

### test_channel_protocol.py

| 被替换的函数 | 替换方式 | 测试场景 |
|-------------|---------|---------|
| `channel.fofa_host.validate_channel_key` | `patch(...)` 无副作用 | validate 成功 → True |
| `channel.fofa_host.validate_channel_key` | `patch(..., side_effect=SystemExit(1))` | validate 失败 → False |
| `channel.fofa_host.validate_channel_key` | `patch(..., side_effect=ConnectionError)` | validate 异常 → False |
| `channel.fofa_host.fetch_channel` | `patch(..., return_value=expected)` | fetch 委托 |
| `channel.aizhan.validate_channel_key` | 同上 3 种 | validate 成功/失败/异常 |
| `channel.aizhan.fetch_channel` | `patch(..., return_value=expected)` | fetch 委托 |
| `channel.port_scan.validate_engine` | `patch(..., return_value='/usr/bin/nmap')` | 引擎可用 → True |
| `channel.port_scan.validate_engine` | `patch(..., return_value=None)` | 引擎不可用 → False |
| `channel.port_scan.validate_engine` | `patch(..., side_effect=OSError)` | 异常 → False |
| `channel.port_scan.fetch_channel` | `patch(..., return_value=expected)` | fetch 委托 |

### test_channel_registry.py

| 被替换的函数 | 替换方式 | 测试场景 |
|-------------|---------|---------|
| `channel.chinaz.validate_channel_key` | `patch(..., side_effect=SystemExit(1))` | validate 失败 |
| `channel.chinaz.fetch_channel` | `patch(..., return_value=expected)` | fetch 委托 |
| `channel.fofa_search.validate_channel_key` | `patch(..., side_effect=SystemExit(1))` | validate 失败 |
| `channel.fofa_search.fetch_channel` | `patch(..., return_value=expected)` | fetch 委托 |
| `channel.zoomeye.validate_channel_key` | `patch(..., side_effect=SystemExit(1))` | validate 失败 |
| `channel.zoomeye.fetch_channel` | `patch(..., return_value=expected)` | fetch 委托 |
| `channel.rdns_ptr.validate_channel_key` | `patch(...)` | validate 成功 |
| `channel.rdns_ptr.fetch_channel` | `patch(..., return_value=expected)` | fetch 委托 |
| `channel.whois_query.validate_channel_key` | `patch(..., side_effect=SystemExit(1))` | validate 失败 |
| `channel.whois_query.fetch_channel` | `patch(..., return_value=expected)` | fetch 委托 |
| `channel.ssl_cert.validate_channel_key` | `patch(...)` | validate 成功 |
| `channel.ssl_cert.fetch_channel` | `patch(..., return_value=expected)` | fetch 委托 |
| `channel.ipinfo_api.validate_channel_key` | `patch(..., side_effect=SystemExit(1))` | validate 失败 |
| `channel.ipinfo_api.fetch_channel` | `patch(..., return_value=expected)` | fetch 委托 |

### test_pipeline_registry.py

| 被替换的函数 | 替换方式 | 测试场景 |
|-------------|---------|---------|
| `channel.fofa_host.fetch_channel` | `patch(..., return_value=expected)` | registry.fetch 委托 |
| `channel.fofa_host.validate_channel_key` | `patch(...)` | registry.validate 成功 |
| `channel.fofa_host.validate_channel_key` | `patch(..., side_effect=SystemExit(1))` | registry.validate 失败 |

---

## 未 Mock 的真实调用（可能影响测试稳定性的部分）

| 测试文件 | 真实调用 | 风险等级 | 说明 |
|---------|---------|---------|------|
| test_channel_base | `time.sleep()` | 低 | delay=0.1 时有真实等待，但测试验证 elapsed |
| test_batch_run | `time.sleep()` | 低 | delay 默认 0，仅 1 个测试设 0.05 |
| test_batch_run | `BaseBatchQuery.__init__` | 中 | 需要 `ip_file` 存在，通过 `tmp_path` 保证 |
| test_base_batch | `BaseBatchQuery.__new__` | 中 | 手动设置属性，跳过 `__init__` |
| test_config | `BaseIPSettings()` | 低 | 用 `_env_file=None` 隔离 |
| test_progress | 文件系统 I/O | 低 | 使用 `tempfile.mkdtemp()` 隔离 |
| test_channel_registry | `create_default_registry()` | 中 | 真实导入 10 个渠道模块，依赖模块可导入 |

---

## 测试替身（Test Double）与生产代码差异

| 替身 | 对应生产代码 | 差异 |
|------|------------|------|
| `InMemoryIPWriter` | `IPWriter` | 内存存储 vs JSON 文件；`get_all()` 额外方法 |
| `InMemoryIPReader` | `IPReader` | 内存存储 vs JSON 文件；构造方式不同（dict vs storage_dir） |
| `InMemoryChannel` | `FofaHostChannel` 等 | 不调用真实 API；`fetch_calls` 额外属性；`validate()` 可配置 |
| `_DummyWriter` | `IPWriter` | 只记录 writes 列表，无持久化 |
| `_DummyPid` | `PidManager` | 只记录状态标志，无文件操作 |
| `_DummyLogger` | `logging.Logger` | 只记录 messages 列表，无格式化/输出 |
| `FakeSettings` | `Settings` | 硬编码属性，无环境变量读取 |
| `DummyBatch` | `BatchFofaHostQuery` 等 | 空实现 `_query_ip`/`_print_result`，无真实查询 |

---

## 排查指南

### 测试失败时按以下顺序排查

1. **检查 mock 是否正确替换** — `patch` 路径是否正确（必须是 `channel.xxx.validate_channel_key`，不是 `protocols.validate_channel_key`）
2. **检查替身是否完整实现 Protocol** — `InMemoryIPWriter` 必须同时实现 `IPDataWriter` 和 `IPDataReader` 的所有方法
3. **检查文件系统依赖** — `test_batch_run` 和 `test_base_batch` 需要 `tmp_path`，`test_progress` 需要 `tempfile.mkdtemp()`
4. **检查环境变量** — `test_config` 需要 `_env_file=None` 隔离，否则会读取 `.env` 文件
5. **检查 `create_default_registry()` 导入** — 需要 10 个渠道模块都可导入，如果缺少依赖会导致 `ImportError`
6. **检查 `__new__` 模式** — `test_batch_run` 和 `test_base_batch` 使用 `__new__` + 手动属性设置，跳过 `__init__`
