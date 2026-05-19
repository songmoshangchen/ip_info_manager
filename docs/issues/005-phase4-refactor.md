# Issue #5: Phase 4 DNS 验证重构

## What to build

简化 `pipeline.py` 的 `_phase4_dns_verify` (L675-L733) + `_do_dns_verify` (L745-L801)。

Phase 4 是唯一不走"逐 IP 循环"模式的 Phase，它先批量提取域名映射，再通过 `dns_batch_verify` 一次性并发验证所有域名。不适合用 PhaseRunner，但可以：
1. 将入口方法和实际逻辑合并为一个清晰的方法
2. 提取"加载进度 + JSON 补充"为与 PhaseRunner 兼容的格式
3. 简化 `force_dns_verify` 条件分支

## Acceptance criteria

- [ ] `_phase4_dns_verify` 和 `_do_dns_verify` 合并为一个方法
- [ ] 进度恢复逻辑与 PhaseRunner 风格一致
- [ ] Phase 4 行为与重构前完全一致
- [ ] 全量测试通过

## Blocked by

None - can start immediately
