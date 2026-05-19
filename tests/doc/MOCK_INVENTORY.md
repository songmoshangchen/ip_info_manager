# 测试 Mock 清单

本文档列出所有测试文件中 **mock/替身** 和 **未 mock（真实调用）** 的内容，方便排查测试样例。

## Mock 策略总览

| 策略 | 说明 | 使用场景 |
|------|------|---------|
| `InMemoryIPWriter` | 纯内存测试替身，实现 `IPDataWriter` + `IPDataReader` | PhaseRunner / Protocol 测试 |
| `InMemoryIPReader` | 纯内存测试替身，实现 `IPDataReader` | Reader 单元测试 |
| `InMemoryChannel` | 纯内存测试替身，实现 `ChannelProtocol` | ChannelRegistry / Pipeline 模式测试 |
| `unittest.mock.patch` | 替换模块级函数 | 渠道适配器的 `validate_channel_key` / `fetch_channel` / `validate_engine` / `requests.get` / `requests.post` / `requests.Session` / `socket.gethostbyaddr` / `subprocess.run` / `whois_query` |
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

### test_classifier.py (28 tests)

**Mock：**
- `tmp_path` — pytest 内置临时目录，用于创建 rules.json

**未 Mock：**
- `IPClassifier` — 测试目标本身
- `ClassifyResult` — 数据类
- `BeautifulSoup` — 不涉及，分类器不解析 HTML

**排查注意：**
- 1 个 xfail: 规则 JSON 缺少 `type` 字段时 `pattern['type']` KeyError
- 自定义规则通过 `tmp_path` 临时文件注入

---

### test_pipeline_exclude.py (13+1 tests)

**Mock：**
- `TraceIPPipeline.__new__` — 跳过 `__init__`，手动设置 `_output_dir`/`_prefix`/`_config`/`_reporter`
- `patch('pipeline.open', mock_open(...))` — 模拟 exclude IPs 文件
- `patch('pipeline._print_report_summary')` — 跳过报告打印

**未 Mock：**
- `_load_exclude_ips` — 测试目标本身
- 文件读取 — 通过 `mock_open` 模拟

**排查注意：**
- 1 个 skip: `_print_report_summary` 导入不存在的 `excel_exporter._trace_priority`
- 使用 `__new__` 模式而非 `__init__` 创建 Pipeline 实例

---

### test_fofa_host.py (20 tests)

**Mock：**
- `patch('channel.fofa_host.requests.get')` — mock HTTP 请求
- `patch('channel.fofa_host.Settings')` — mock 配置
- `patch('channel.fofa_host.validate_channel_key')` — mock 验证
- `patch('channel.fofa_host.fetch_channel')` — mock 获取
- `patch('channel.fofa_host.apply_delay')` — mock 延迟
- `MagicMock` — 模拟 response 对象

**未 Mock：**
- `request_channel` — 测试目标（除了在 fetch 测试中 mock）
- `format_output` — 直接测试
- `FofaHostChannel` — 适配器类

**排查注意：**
- mock `requests.get` 返回 `MagicMock`，需设置 `json.return_value` 和 `raise_for_status.return_value`
- 错误场景使用 `side_effect` 注入异常

---

### test_aizhan.py (31 tests)

**Mock：**
- `patch('channel.aizhan.requests.get')` — mock HTTP 请求
- `patch('channel.aizhan.Settings')` — mock 配置 (AizhanSettings)
- `patch('channel.aizhan.validate_channel_key')` — mock 验证
- `patch('channel.aizhan.fetch_channel')` — mock 获取
- `patch('channel.aizhan.apply_delay')` — mock 延迟

**未 Mock：**
- `parse_response` — 直接测试，使用 HTML 字符串
- `BeautifulSoup` — 真实调用解析 HTML

**排查注意：**
- 1 个 xfail: `ReadTimeout("Read timed out.")` 的错误消息不含 "timeout" 连续子串
- HTML 测试数据通过 `_make_html()` 辅助函数构造
- Cookie 验证测试 302 重定向 → SystemExit

---

### test_chinaz.py (23 tests)

**Mock：**
- `patch('channel.chinaz.requests.Session')` — mock Session 请求
- `patch('channel.chinaz.Settings')` — mock 配置 (ChinazSettings)
- `patch('channel.chinaz.requests.get')` — mock 验证时的 GET
- `patch('channel.chinaz.request_channel')` — mock 获取
- `patch('channel.chinaz.apply_delay')` — mock 延迟

**未 Mock：**
- `parse_response` — 直接测试
- `BeautifulSoup` — 真实调用

**排查注意：**
- 1 个 xfail: 同 aizhan 的 ReadTimeout 问题
- `request_channel` 使用 `requests.Session()`，mock 需替换 `requests.Session`
- Cookie 验证检查 `toolUserGrade` 和 `chinaz_zxuser` 两个必需字段

---

### test_ipinfo_api.py (22 tests)

**Mock：**
- `patch('channel.ipinfo_api.requests.get')` — mock HTTP 请求
- `patch('channel.ipinfo_api.Settings')` — mock 配置 (IpinfoSettings)
- `patch('channel.ipinfo_api._request_channel_api')` — mock API 模式内部函数
- `patch('channel.ipinfo_api._request_channel_noapi')` — mock NoAPI 模式内部函数
- `patch('channel.ipinfo_api.request_channel')` — mock 分发函数
- `patch('channel.ipinfo_api.apply_delay')` — mock 延迟

**未 Mock：**
- `_request_channel_api` — 直接测试（通过 mock requests.get）
- `_request_channel_noapi` — 直接测试（通过 mock requests.get）
- `request_channel` — 分发逻辑测试

**排查注意：**
- SDK 模式使用 `api.ipinfo.io/lite` + Bearer token
- 免费 API 使用 `ipinfo.io/{ip}/json`，无认证
- `validate_channel_key` 根据 token 是否存在走不同验证路径

---

### test_rdns_ptr.py (14 tests)

**Mock：**
- `patch('channel.rdns_ptr.socket.gethostbyaddr')` — mock DNS 查询
- `patch('channel.rdns_ptr.request_channel')` — mock 获取
- `patch('channel.rdns_ptr.apply_delay')` — mock 延迟

**未 Mock：**
- `request_channel` — 直接测试（通过 mock socket）
- `socket.setdefaulttimeout` — 真实调用（无副作用）

**排查注意：**
- herror = "查不到 PTR 记录"（正常），gaierror = "地址解析失败"
- timeout = "网络超时，需要重试" — 区分于 herror 的"确实没有记录"
- 其他异常 (OSError) 标记为 `raw_error=True`

---

### test_whois_query.py (20 tests)

**Mock：**
- `patch('channel.whois_query.whois_query')` — mock python-whois 库
- `patch('channel.whois_query.request_channel')` — mock 获取
- `patch('channel.whois_query.apply_delay')` — mock 延迟
- `MagicMock` — 模拟 whois 返回对象（含 domain_name/registrar 等属性）

**未 Mock：**
- `parse_response` — 直接测试
- `_make_whois_result()` — 辅助函数构造 mock whois 对象

**排查注意：**
- 1 个 xfail: `parse_response` 对空列表 `[]` 的 truthy 检查跳过字段
- whois 返回对象的字段可能是 str/list/None，parse_response 需处理所有情况
- `whois_query is None` 模拟库未安装

---

### test_ssl_cert.py (18 tests)

**Mock：**
- `patch('channel.ssl_cert._get_ssl_cert_text')` — mock SSL 连接
- `patch('channel.ssl_cert.request_channel')` — mock 获取
- `patch('channel.ssl_cert.apply_delay')` — mock 延迟

**未 Mock：**
- `_parse_domains` — 纯正则解析，直接测试
- `format_output` — 直接测试

**排查注意：**
- 1 个 xfail: issuer_cn 正则 `[^/\n,\s]+` 在空格处截断多词 CN
- SSL 错误类型: no_cert / connection_timeout / connection_refused / ssl_error
- 证书文本使用 `SAMPLE_CERT_TEXT` 常量

---

### test_port_scan.py (18 tests)

**Mock：**
- `patch('channel.port_scan.subprocess.run')` — mock nmap 执行
- `patch('channel.port_scan._try_nmap')` — mock nmap 检测
- `patch('channel.port_scan.request_channel')` — mock 获取
- `patch('channel.port_scan.apply_delay')` — mock 延迟

**未 Mock：**
- `parse_nmap_xml` — 纯 XML 解析，直接测试
- `format_output` / `format_output_error` — 直接测试

**排查注意：**
- 1 个 xfail: `parse_nmap_xml` 非法 portid (如 "abc") 导致 int() 异常
- XML 解析使用 `xml.etree.ElementTree.fromstring`
- `validate_engine` 先尝试 PATH 中的 "nmap"，再尝试配置路径

---

### test_fofa_search.py (16 tests)

**Mock：**
- `patch('channel.fofa_search.requests.get')` — mock HTTP 请求
- `patch('channel.fofa_search.Settings')` — mock 配置 (FofaSettings)
- `patch('channel.fofa_search.request_channel')` — mock 获取
- `patch('channel.fofa_search.apply_delay')` — mock 延迟

**未 Mock：**
- `request_channel` — 直接测试（通过 mock requests.get）
- `format_output` — 直接测试

**排查注意：**
- 与 fofa_host 共享 Settings，但使用不同的 API 端点 (`/api/v1/search/all`)
- 查询使用 base64 编码，`query_suffix` 参数追加到查询字符串
- `format_output` 额外设置 `fields` 字段（区别于 fofa_host）

---

### test_zoomeye.py (16 tests)

**Mock：**
- `patch('channel.zoomeye.requests.post')` — mock HTTP POST 请求
- `patch('channel.zoomeye.Settings')` — mock 配置 (ZoomeyeSettings)
- `patch('channel.zoomeye.request_channel')` — mock 获取
- `patch('channel.zoomeye.apply_delay')` — mock 延迟

**未 Mock：**
- `request_channel` — 直接测试（通过 mock requests.post）
- `format_output` — 直接测试

**排查注意：**
- 唯一使用 POST 请求的渠道（其他渠道使用 GET）
- API-KEY 通过 header 而非参数传递
- `validate_channel_key` 只检查 key 是否配置，不进行在线验证（避免消耗额度）

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
| test_classifier | 是 | `tmp_path` 创建临时 rules.json |
| test_pipeline_exclude | 否 | `mock_open` 模拟文件 |
| test_fofa_host | 否 | mock requests.get |
| test_aizhan | 否 | mock requests.get |
| test_chinaz | 否 | mock requests.Session |
| test_ipinfo_api | 否 | mock requests.get |
| test_rdns_ptr | 否 | mock socket.gethostbyaddr |
| test_whois_query | 否 | mock whois_query |
| test_ssl_cert | 否 | mock _get_ssl_cert_text |
| test_port_scan | 否 | mock subprocess.run |
| test_fofa_search | 否 | mock requests.get |
| test_zoomeye | 否 | mock requests.post |

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
7. **检查 HTTP mock 路径** — 渠道测试 mock 的是 `channel.xxx.requests.get/post`，不是 `requests.get/post`；chinaz 使用 `requests.Session`
8. **检查 xfail 测试** — 当前有 8 个 xfail 测试标记了已知生产 bug，如果这些测试突然通过，说明 bug 已被修复
9. **检查 Settings mock** — 渠道验证测试需要 mock `channel.xxx.Settings`（各渠道使用不同 Settings 类如 `FofaSettings`/`AizhanSettings` 等）
