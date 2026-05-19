# Issue #7: Phase 6/7 简化 + pipeline.py 最终清理

## What to build

在 Issue #2-#6 全部完成后，对 pipeline.py 进行最终清理：

1. Phase 6 (`_phase6_summary`) 已是一行委托，无需改动
2. Phase 7 (`_phase7_generate_reports`) 中的 `_load_exclude_ips` 和 `_print_report_summary` 可提取为独立方法或移入 reporter
3. 删除 pipeline.py 中已被 PhaseRunner 替代的冗余代码
4. 更新 CONTEXT.md 中的目录结构说明
5. 最终验证：全流程端到端测试

## Acceptance criteria

- [ ] pipeline.py 总行数从 ~1180 行降至 ~500 行以下
- [ ] Phase 6/7 逻辑清晰，无冗余
- [ ] CONTEXT.md 更新（新增 phase_runner.py、trace_utils.py、channel/base.py、protocols.py）
- [ ] 全量测试通过（81+ tests）
- [ ] 手动端到端验证：`python -m scenarios.trace_ip` 可正常执行

## Blocked by

- Issue #2 (Phase 1 改用 PhaseRunner)
- Issue #3 (Phase 3 改用 PhaseRunner)
- Issue #4 (Phase 5 改用 PhaseRunner)
- Issue #5 (Phase 4 DNS 验证重构)
- Issue #6 (reporter/excel_exporter 迁移)
