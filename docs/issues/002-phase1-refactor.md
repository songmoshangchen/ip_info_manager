# Issue #2: Phase 1 改用 PhaseRunner

## 状态

**已决定保留现状** — Phase 1/3/5 的差异（JSON检查逻辑、进度记录策略、渠道规格构建）足够大，强行统一反而增加复杂度。PhaseRunner 保留给未来新 Phase 使用。

## What to build

将 `pipeline.py` 的 `_phase1_collect_basic` (L192-L354) 改为使用 Issue #1 创建的 `PhaseRunner`。

Phase 1 的差异部分：
- IP 来源：`self._ips`（全量）
- 渠道：`ipinfo_api`, `rdns_ptr`（并行查询）
- Settings：`IpinfoSettings`, `RdnsSettings`
- JSON 补充：检查两渠道均有数据
- delay：`max_delay = max(delays)` 后 `time.sleep`

## Acceptance criteria

- [ ] `_phase1_collect_basic` 改为调用 `PhaseRunner.run()`
- [ ] Phase 1 行为与重构前完全一致（通过手动运行对比验证）
- [ ] pipeline.py 中 Phase 1 代码量从 ~160 行降至 ~40 行
- [ ] 全量测试通过

## Blocked by

- Issue #1 (PhaseRunner 通用循环)
