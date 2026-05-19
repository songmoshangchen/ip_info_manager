# Issue #3: Phase 3 改用 PhaseRunner

## 状态

**已决定保留现状** — 同 Issue #2。

## What to build

将 `pipeline.py` 的 `_phase3_deep_query` (L463-L671) 改为使用 `PhaseRunner`。

Phase 3 的差异部分：
- IP 来源：`filtered_ips`（从 `.trace_filtered_ips` 文件读取）
- 渠道：`aizhan`, `chinaz`, `fofa_host`（并行查询）
- Settings：`AizhanSettings`, `ChinazSettings`, `FofaSettings`
- JSON 补充：检查任一启用渠道有数据即可
- 前置跳过：`no_deep_query` 配置
- delay：同 Phase 1

## Acceptance criteria

- [ ] `_phase3_deep_query` 改为调用 `PhaseRunner.run()`
- [ ] Phase 3 行为与重构前完全一致
- [ ] pipeline.py 中 Phase 3 代码量从 ~210 行降至 ~50 行
- [ ] 全量测试通过

## Blocked by

- Issue #1 (PhaseRunner 通用循环)
