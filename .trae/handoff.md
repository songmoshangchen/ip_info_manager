# Handoff: 架构深化优化完成

## 项目概况

IP 信息采集流水线，4 阶段架构：
- Phase 1: 基础情报采集 (ipinfo_api, rdns_ptr)
- Phase 2: 分类+标签 (classifier, tagger)
- Phase 3: 深度查询 (aizhan, chinaz, fofa_host) — 并发
- Phase 4: 验证+扫描 (dns_verify, port_scan/nmap) — 并发

## 当前状态

892 测试全部通过（865 单元 + 27 集成）。架构深化优化 7 项全部完成 (commit c537775)。

```
issues/
├── 008-add-fscan-channel.md     ← ❌ 未开始（用户说排到最后）
├── 015-pipeline-builder.md      ← ⚠️ 部分完成（Builder+脚本迁移完成，渠道注册表自动发现未做）
└── 016-trace-judge-excel.md     ← ❌ 未开始
```

## 已完成的架构深化（Spec: arch-deepening）

| # | 重构 | 状态 | 关键变更 |
|---|------|------|----------|
| 1 | 合并 Pipeline 双生子 | ✅ | Builder 构建完整 Pipeline，删除简单 dataclass |
| 2 | Phase 构造函数去重 | ✅ | context 必填，移除 writer/reader/progress_tracker/domain_cache 独立参数 |
| 3 | 渠道禁用逻辑统一 | ✅ | Phase 内不再检查 channel.disabled，统一由 run_concurrent 处理 |
| 4 | BatchTagger 修复 | ✅ | 显式 `self._reader.get_channel_data()` 替代 `getattr(self._writer, ...)` |
| 5 | InMemoryIPWriter 去冗余 | ✅ | 移除 4 个读取方法，统一使用 InMemoryIPReader |
| 6 | flush_progress 统一 | ✅ | 提取 `flush_progress()` 公共工具函数 |
| 7 | Builder 内化 filter + 脚本迁移 | ✅ | `with_filter()` + run_pipeline.py 用 Builder 重写 |

## 剩余架构机会

| # | 问题 | 优先级 | 说明 |
|---|------|--------|------|
| 8 | Phase 双层 run() 抽象职责模糊 | P2 | Phase 2/4 的 run() 只是薄包装，转换 BatchResult→PhaseResult |
| 9 | 渠道注册表自动发现 | P2 | `_try_channel()` if-elif 硬编码仍在 run_pipeline.py |
| 10 | IPDataWriter 缺少批量操作 | P2 | 1000 IP = 1000 次全量 JSON 读写 |

## 测试遗留问题

| 类别 | 数量 | 优先级 | 文件 |
|------|------|--------|------|
| Mock 内省断言 | 9 处 | P0 | test_dns_runner (5), test_adapter (1), test_port_scan (2), test_dns_verifier (1) |
| Channel 私有方法调用 | ~92 处 | P1 | test_aizhan (15), test_fofa_search (15), test_chinaz (12), test_fofa_host (12), test_ipinfo_api (12), test_ssl_cert (6), test_ipinfo_free (7), test_rdns_ptr (5), test_whois_query (4), test_port_scan (4) |
| 缺失集成场景 | 3 个 | P2 | Phase 失败重试 / 并发写入一致性 / SQLite 跨进程 |
| batch/core/runner.py 无测试 | — | P2 | 核心调度器无直接测试 |

## 测试替身策略

| 类型 | 使用位置 |
|------|----------|
| Fake | FakeChannel (test_phases, test_builder, test_phase_data_flow, test_domain_trace), _FakeChannel/_FakeWriter (test_query, test_concurrent), FakePhase (test_pipeline), InMemoryIPWriter/Reader (集成测试) |
| Stub | _fake_batch_verify (test_domain_trace, test_dns_verify_only) |
| Mock | patch(requests.get) — channel 测试, patch(BatchDnsVerify) — Phase 4, patch(BatchClassifier/Tagger) — Phase 2, MagicMock(nmap.PortScanner) — port_scan |

## 技术栈

- Python 3.12+, pytest (`pytest tests/`)
- 892 测试通过 (865 单元 + 27 集成)
- pre-commit hooks: ruff-format + ruff-check
- Spec 文档: `.trae/specs/arch-deepening/` (全部完成)

## 建议使用的 Skills

- `fdt-refactor-mock-to-fake` — Channel 测试重构（消除 92 处私有方法调用）
- `fake-driven-testing` — 集成测试策略
- `tdd` — 开发循环
- `git-commit` — 提交
