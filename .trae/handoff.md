# Handoff: 测试替身重构完成

## 项目概况

IP 信息采集流水线，4 阶段架构：
- Phase 1: 基础情报采集 (ipinfo_api, rdns_ptr)
- Phase 2: 分类+标签 (classifier, tagger)
- Phase 3: 深度查询 (aizhan, chinaz, fofa_host) — 并发
- Phase 4: 验证+扫描 (dns_verify, port_scan/nmap) — 并发

## 当前状态

892 测试全部通过（865 单元 + 27 集成）。测试替身重构已完成，Mock 内省断言和私有方法调用已消除。

```
issues/
├── 008-add-fscan-channel.md     ← ❌ 未开始（用户说排到最后）
├── 015-pipeline-builder.md      ← ⚠️ 部分完成（Builder+脚本迁移完成，渠道注册表自动发现未做）
└── 016-trace-judge-excel.md     ← ❌ 未开始
```

## 已完成：架构深化（Spec: arch-deepening）

| # | 重构 | 状态 | 关键变更 |
|---|------|------|----------|
| 1 | 合并 Pipeline 双生子 | ✅ | Builder 构建完整 Pipeline，删除简单 dataclass |
| 2 | Phase 构造函数去重 | ✅ | context 必填，移除 writer/reader/progress_tracker/domain_cache 独立参数 |
| 3 | 渠道禁用逻辑统一 | ✅ | Phase 内不再检查 channel.disabled，统一由 run_concurrent 处理 |
| 4 | BatchTagger 修复 | ✅ | 显式 `self._reader.get_channel_data()` 替代 `getattr(self._writer, ...)` |
| 5 | InMemoryIPWriter 去冗余 | ✅ | 移除 4 个读取方法，统一使用 InMemoryIPReader |
| 6 | flush_progress 统一 | ✅ | 提取 `flush_progress()` 公共工具函数 |
| 7 | Builder 内化 filter + 脚本迁移 | ✅ | `with_filter()` + run_pipeline.py 用 Builder 重写 |

## 已完成：测试替身重构（fdt-refactor-mock-to-fake）

| # | 重构 | 变更 | 影响文件 |
|---|------|------|----------|
| 1 | Mock 内省断言消除 | `BatchDnsVerify` 新增 `batch_verify_fn` 可注入参数；10 处 `assert_called_once`/`assert_not_called`/`call_count` 替换为结果导向验证 | test_dns_runner.py, test_dns_verify_only.py, test_domain_trace.py, runner.py |
| 2 | _validate_key → validate() | 21 处 `_validate_key()` 调用改为 `validate()`，断言从 `pytest.raises(ChannelPermanentError)` 改为 `assert result is False` + `assert channel.disabled is True` | test_aizhan.py, test_chinaz.py, test_fofa_search.py, test_fofa_host.py, test_ipinfo_api.py |
| 3 | _request → fetch() | 56 处 `_request()` 调用改为 `fetch()`，成功场景验证 `query_time` + 业务字段 | test_aizhan.py, test_chinaz.py, test_fofa_search.py, test_fofa_host.py, test_ipinfo_api.py, test_ssl_cert.py, test_ipinfo_free.py, test_rdns_ptr.py, test_whois_query.py |
| 4 | _parse → fetch() | 10 处 `_parse()` 调用改为通过 `fetch()` 间接测试（mock requests.get 返回 HTML） | test_aizhan.py, test_chinaz.py |
| 5 | 私有属性 → fetch() | 4 处 `_arguments`/`_port_list` 直接读取改为通过 `fetch()` + 验证 nmap.scan 调用参数 | test_port_scan.py |

**保留的 mock 内省断言**（合理场景）：
- `test_adapter.py` 中 `time.sleep` — 验证"未发生"只能靠内省
- `test_port_scan.py` 中 `nmap.scan.call_args` — 验证内部协议参数传递
- `test_dns_verifier.py` 中 `socket.setdefaulttimeout` — 验证内部配置传递

## 剩余架构机会

| # | 问题 | 优先级 | 说明 |
|---|------|--------|------|
| 8 | Phase 双层 run() 抽象职责模糊 | P2 | Phase 2/4 的 run() 只是薄包装，转换 BatchResult→PhaseResult |
| 9 | 渠道注册表自动发现 | P2 | `_try_channel()` if-elif 硬编码仍在 run_pipeline.py |
| 10 | IPDataWriter 缺少批量操作 | P2 | 1000 IP = 1000 次全量 JSON 读写 |

## 后续测试改进计划

### P1: vcr.py 替换手工 mock response

**目标**：录制真实 API 响应作为 fixture，替代当前 `MagicMock` 手工构造 response。

| Channel | 当前方式 | vcr.py 收益 |
|---------|---------|------------|
| ipinfo_api / ipinfo_free | MagicMock 返回 JSON | 录制真实响应，验证字段完整性 |
| fofa_search / fofa_host | MagicMock 返回 JSON | Fofa 响应结构复杂，录制更可靠 |
| aizhan / chinaz | MagicMock 返回 HTML | HTML 结构易变，录制真实响应更可靠 |
| ssl_cert / rdns_ptr | patch socket 调用 | 不适合 vcr.py，保持现有 mock |

**实施要点**：
- 安装 `vcrpy` + `pytest-recording`
- 为每个 HTTP Channel 创建 cassette fixture（`tests/cassettes/`）
- 定期（月度）重新录制，验证服务商是否变更响应格式
- 可替代 Sandbox API 方案实现端到端测试

### P1: freezegun 替换 time.sleep mock

**目标**：
- 替换 `patch("time.sleep")`，验证时间字段（`query_time`）更精确
- 跳过 `time.sleep(n)` 减少测试时间

**实施要点**：
- 安装 `freezegun`
- 替换 `test_adapter.py` 中的 `patch("ip_info.channel.adapter.time.sleep")`
- 对 `query_time` 字段做精确断言而非仅检查存在性

### P2: 端到端测试

**前提**：当前批量查询和 Pipeline 未暴露 CLI/API 接口，后续写完需要端到端测试。

**实施要点**：
- CLI 入口完成后，编写 `tests/e2e/` 测试套件
- 使用 vcr.py cassette 回放真实 API 响应
- 验证完整流程：CLI 参数 → Pipeline 执行 → 输出文件/数据库

### P2: 性能/负载测试 & 边界条件系统测试

**待评估**：
- 是否需要 `pytest-benchmark` 做性能测试（1000+ IP 场景）
- 是否需要 `Hypothesis` 做属性测试（HTML/JSON 解析边界条件）
- 是否需要边界条件系统测试（网络中断恢复、超大响应体等）

## 测试替身策略（更新后）

| 类型 | 使用位置 |
|------|----------|
| Fake | FakeChannel (test_phases, test_builder, test_phase_data_flow, test_domain_trace), _FakeChannel/_FakeWriter (test_query, test_concurrent), FakePhase (test_pipeline), InMemoryIPWriter/Reader (集成测试) |
| Stub | _fake_batch_verify (test_dns_runner, test_dns_verify_only, test_domain_trace) |
| Mock | patch(requests.get) — channel HTTP 测试, patch(nmap.PortScanner) — port_scan, patch(socket) — rdns_ptr/ssl_cert/dns_verifier, patch(time.sleep) — adapter delay |

## 技术栈

- Python 3.12+, pytest (`pytest tests/`)
- 892 测试通过 (865 单元 + 27 集成)
- pre-commit hooks: ruff-format + ruff-check
- Spec 文档: `.trae/specs/arch-deepening/` (全部完成)

## 建议使用的 Skills

- `fake-driven-testing` — 集成测试策略
- `tdd` — 开发循环
- `git-commit` — 提交
