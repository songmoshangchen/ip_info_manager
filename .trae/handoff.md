# Handoff: 第二轮审查完成

## 项目概况

IP 信息采集流水线，4 阶段架构：
- Phase 1: 基础情报采集 (ipinfo_api, rdns_ptr)
- Phase 2: 分类+标签 (classifier, tagger)
- Phase 3: 深度查询 (aizhan, chinaz, fofa_host) — 并发
- Phase 4: 验证+扫描 (dns_verify, port_scan/nmap) — 并发

## 当前状态

882 测试通过。Issues 目录：

```
issues/
├── 008-add-fscan-channel.md    ← ❌ 未开始（排到最后）
└── 015-pipeline-builder.md     ← ⚠️ 部分完成（Builder 已实现，run_pipeline 未迁移）
```

009-014 已完成并删除。

## Issue 015 剩余工作

- `run_pipeline.py` 简化为 Builder 调用
- 渠道注册表自动发现替代 `_try_channel()` 硬编码
- filter_ips 逻辑集成到 Builder 中

## 第二轮审查发现

详见 `docs/architecture-and-test-audit.md`

### 架构深化机会（10 项）

| # | 问题 | 优先级 |
|---|------|--------|
| 1 | Pipeline 双生子：两个 Pipeline 类，Builder 与脚本脱节 | P0 |
| 2 | PipelineContext 浅层透传：Phase 构造函数仍然臃肿 | P0 |
| 3 | Phase 内重复渠道禁用检查与 run_concurrent 重叠 | P1 |
| 4 | BatchTagger 鸭子类型读取 — 接缝泄漏 | P1 |
| 5 | InMemoryIPWriter 实现了完整 IPDataReader | P2 |
| 6 | _try_flush 模式三处重复 | P2 |
| 7 | filter_ips.py 游离于 Pipeline 之外 | P1 |
| 8 | Phase 双层 run() 抽象职责模糊 | P2 |
| 9 | run_pipeline.py 是上帝脚本 | P1 |
| 10 | IPDataWriter 缺少批量操作 | P2 |

### 测试遗留问题

| 类别 | 数量 | 优先级 |
|------|------|--------|
| Mock 内省断言 (test_dns_runner) | 5 处 | P0 |
| Channel 私有方法调用 | 20+ 处 | P1 |
| port_scan 私有属性读取 | 4 处 | P1 |
| 缺失集成场景 (失败重试/并发写入) | 3 个 | P2 |
| 无测试模块 (context/runner) | 2 个 | P2 |

## 技术栈

- Python 3.12+, pytest (`pytest tests/`)
- 882 测试通过（849 单元 + 33 集成）
- pre-commit hooks: ruff-format + ruff-check

## 建议使用的 Skills

- `fdt-refactor-mock-to-fake` — Channel 测试重构
- `fake-driven-testing` — 集成测试策略
- `improve-codebase-architecture` — 架构深化
- `tdd` — 开发循环
- `git-commit` — 提交
