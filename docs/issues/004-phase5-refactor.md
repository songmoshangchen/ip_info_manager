# Issue #4: Phase 5 改用 PhaseRunner

## 状态

**已决定保留现状** — 同 Issue #2。

## What to build

将 `pipeline.py` 的 `_phase5_port_scan` (L805-L1005) 改为使用 `PhaseRunner`。

Phase 5 的差异部分：
- IP 来源：`filtered_ips`
- 渠道：`port_scan`（单渠道，但支持 ThreadPoolExecutor 并发）
- Settings：`TraceIPSettings` (port_scan_*)
- JSON 补充：检查 `port_scan` 键存在且无 `error`
- 前置跳过：`no_port_scan` + nmap 可用性验证
- 特殊：串行/并发双分支、历史端口合并、内部函数 `_scan_one_ip`
- 无逐 IP delay

## Acceptance criteria

- [ ] `_phase5_port_scan` 改为调用 `PhaseRunner.run()`
- [ ] Phase 5 行为与重构前完全一致（含串行/并发双分支）
- [ ] pipeline.py 中 Phase 5 代码量从 ~200 行降至 ~60 行
- [ ] 全量测试通过

## Blocked by

- Issue #1 (PhaseRunner 通用循环)
