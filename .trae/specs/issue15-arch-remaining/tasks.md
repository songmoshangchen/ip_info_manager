# Tasks

## 开发方法论

每个 Task（Task 2-8）遵循 **TDD + Fake-Driven Testing** 循环：
1. **TDD Red** → 使用 `tdd` skill 编写失败测试
2. **FDT 审核** → 使用 `fake-driven-testing` skill 审查测试质量
3. **如发现问题** → 使用 `fdt-refactor-mock-to-fake` skill 修复 → 重新审核
4. **审核通过** → 使用 `tdd` skill 编写实现代码（Green + Refactor）
5. **验证** → 运行全量测试

---

- [x] Task 1: 目录重构 — pipeline/core/ + pipeline/trace_steps/
  - [x] 1.1: 创建 `pipeline/core/` 目录，将 `pipeline/*.py`（builder, context, filter_ips, phase, pipeline）移入
  - [x] 1.2: 将 `pipeline/phases/` 重命名为 `pipeline/trace_steps/`
  - [x] 1.3: 更新 `pipeline/__init__.py` 和 `pipeline/core/__init__.py` 的导出
  - [x] 1.4: 更新 `pipeline/trace_steps/__init__.py` 的导出
  - [x] 1.5: 全局搜索替换导入路径 `pipeline.X` → `pipeline.core.X`，`pipeline.phases.X` → `pipeline.trace_steps.X`
  - [x] 1.6: 运行全量测试 `pytest tests/` 确认无回归（943 passed）
  - [x] 1.7: 运行 `ruff check` 确认 lint 通过

- [x] Task 2: BatchStep 协议 + BaseProcessor 适配
  - [x] 2.1: **TDD Red** — 编写测试：ChannelBatchStep 满足 BatchStep 协议、BatchClassifier 满足 BatchStep 协议、name 属性返回 channel_name
  - [x] 2.2: **FDT 审核** — 使用 fake-driven-testing skill 审查测试质量（通过，无 mock/patch）
  - [x] 2.3: **TDD Green** — 创建 `pipeline/core/batch_step.py`（BatchStep 协议），在 `BaseProcessor` 新增 `name` 属性
  - [x] 2.4: 运行测试确认通过（950 passed）

- [x] Task 3: ChannelBatchStep 适配器
  - [x] 3.1: **TDD Red** — 编写测试：run() 返回 BatchResult、name 返回 channel_name、delay 默认使用 channel.default_delay、isinstance(step, BatchStep) 为 True
  - [x] 3.2: **FDT 审核** — 使用 fake-driven-testing skill 审查测试质量（通过，使用 FakeChannel + InMemory）
  - [x] 3.3: **TDD Green** — 创建 `pipeline/core/channel_batch_step.py`
  - [x] 3.4: 运行测试确认通过（957 passed）

- [x] Task 4: BatchFactory 自动发现
  - [x] 4.1: **TDD Red** — 编写测试：创建渠道 BatchStep、创建处理器 BatchStep、未知名称返回 None、初始化失败返回 None、列出全部 batch 名称
  - [x] 4.2: **FDT 审核** — 使用 fake-driven-testing skill 审查测试质量（通过，仅 init_failure 用 patch 测试异常路径）
  - [x] 4.3: **TDD Green** — 创建 `pipeline/core/batch_factory.py`（_CHANNEL_MAP + _PROCESSOR_MAP + try_create()）
  - [x] 4.4: 运行测试确认通过（968 passed）

- [x] Task 5: Phase 迁移到 BatchStep
  - [x] 5.1: **TDD Red** — 编写测试：Phase 1 接收 BatchStep 列表并行执行、Phase 2 接收 classify + tagger 步骤、Phase 3 接收 BatchStep 列表并行执行、Phase 4 接收 dns_verify + port_scan 并行执行
  - [x] 5.2: **FDT 审核** — 使用 fake-driven-testing skill 审查测试质量（通过，使用 FakeBatchStep）
  - [x] 5.3: **TDD Green** — 重构 Phase 1-4 构造函数接收 BatchStep 实例
  - [x] 5.4: 运行全量测试确认无回归（985 passed）

- [x] Task 6: 脚本迁移 + --only-phase
  - [x] 6.1: 更新 `run_pipeline.py` — 使用 BatchFactory 创建 BatchStep，传递给 Phase
  - [x] 6.2: 更新 `quick_query.py` — 使用 BatchFactory 创建 BatchStep
  - [x] 6.3: 删除两个脚本中的 `_try_channel()` 函数定义
  - [x] 6.4: 在 `run_pipeline.py` 中添加 `--only-phase N` 参数
  - [x] 6.5: 将 `--only-phase` 传递给 `pipeline.run(only_phase=N)`
  - [x] 6.6: 运行全量测试确认无回归（985 passed）

- [x] Task 7: IPDataWriter 批量操作
  - [x] 7.1: **TDD Red** — 编写测试：批量写入多个 IP、空列表返回 0 且无 I/O、验证只有 1 次文件读+写
  - [x] 7.2: **FDT 审核** — 使用 fake-driven-testing skill 审查测试质量（通过，使用 tempfile + InMemory）
  - [x] 7.3: **TDD Green** — 在 IPWriter 实现 add_or_update_ip_batch()、Protocol 新增方法、InMemoryIPWriter 同步实现
  - [x] 7.4: 运行全量测试确认无回归（991 passed）

- [x] Task 8: skip_dynamic_ips() 实际生效
  - [x] 8.1: **TDD Red** — 编写测试：调用后自动注册过滤器、未调用则无过滤器
  - [x] 8.2: **FDT 审核** — 使用 fake-driven-testing skill 审查测试质量（通过，使用 InMemoryIPWriter）
  - [x] 8.3: **TDD Green** — 修改 skip_dynamic_ips() 自动注册过滤器、移除 _skip_dynamic 标记、简化 run_pipeline.py
  - [x] 8.4: 运行全量测试确认无回归（994 passed, ruff passed）

# Task Dependencies

- Task 1（目录重构）必须最先完成，后续所有 Task 基于新目录结构
- Task 2（BatchStep 协议）无前置依赖（基于 Task 1 后的新目录）
- Task 3（ChannelBatchStep）依赖 Task 2
- Task 4（BatchFactory）依赖 Task 2 + Task 3
- Task 5（Phase 迁移）依赖 Task 4
- Task 6（脚本迁移）依赖 Task 5
- Task 7（IPDataWriter 批量操作）独立，可与 Task 2-4 并行
- Task 8（skip_dynamic_ips）依赖 Task 1，可与 Task 2-4 并行
