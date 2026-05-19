# Issue #1: 抽取 PhaseRunner 通用循环

## What to build

从 `pipeline.py` 的 Phase 1/3/5 中提取共享的"进度-查询-写入"循环骨架，创建 `scenarios/trace_ip/phase_runner.py`。

PhaseRunner 封装以下通用步骤：
1. 加载进度文件 → `load_completed(phase, channels)`
2. 从 JSON 补充已处理 IP → `processed_from_json`
3. 计算 `pending_ips = all_ips - processed`
4. 打印渠道状态
5. `with batch_writer: for ip in pending_ips:` 循环体
6. 每轮：查询 → 写入 → 进度记录 → 心跳 → ETA → delay
7. `reporter.record_phase`

每个 Phase 只需声明差异部分：IP 列表来源、渠道规格、settings 实例、JSON 补充逻辑、delay 策略。

## Acceptance criteria

- [ ] `phase_runner.py` 创建，含 `PhaseRunner` 类
- [ ] `PhaseRunner` 通过构造函数接收：ips, phase_num, channels, progress, batch_writer, pid_manager, reporter
- [ ] `PhaseRunner.run()` 方法执行完整的"进度-查询-写入"循环
- [ ] 查询逻辑通过回调/策略模式注入（每个 Phase 的查询方式不同）
- [ ] TDD 测试覆盖：进度恢复、跳过已处理 IP、ETA 计算、心跳更新
- [ ] 现有 pipeline.py 不改动（本 issue 只创建新模块，不修改旧代码）

## Blocked by

None - can start immediately
