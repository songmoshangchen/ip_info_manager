## 功能检查

- [x] 目录结构：`pipeline/core/` 包含 builder.py, context.py, filter_ips.py, phase.py, pipeline.py
- [x] 目录结构：`pipeline/trace_steps/` 包含 phase1-4（原 phases/）
- [x] 导入路径全部更新：`pipeline.core.X` 和 `pipeline.trace_steps.X`
- [x] 全量测试通过（目录重构后）
- [x] `BatchStep` 协议定义在 `pipeline/core/batch_step.py`，含 `name` + `run() → BatchResult`
- [x] `BaseProcessor` 新增 `name` 属性，返回 `self.channel_name`
- [x] `BatchClassifier` 满足 `BatchStep` 协议（`isinstance` 为 True）
- [x] `ChannelBatchStep` 适配器存在于 `pipeline/core/channel_batch_step.py`
- [x] `ChannelBatchStep.run()` 返回 `BatchResult`
- [x] `ChannelBatchStep.name` 返回 `channel_name`
- [x] `ChannelBatchStep` 满足 `BatchStep` 协议
- [x] `BatchFactory` 存在于 `pipeline/core/batch_factory.py`
- [x] `_CHANNEL_MAP` 覆盖全部 10 个内置渠道
- [x] `_PROCESSOR_MAP` 覆盖 3 个处理器
- [x] `BatchFactory.try_create("unknown")` 返回 None
- [x] `BatchFactory.try_create("aizhan", ...)` 返回 ChannelBatchStep 实例
- [x] `BatchFactory.try_create("classify", ...)` 返回 BatchClassifier 实例
- [x] Phase 1-4 构造函数接收 BatchStep 实例，不直接依赖 channel/processor 类型
- [x] Phase 内部只编排 BatchStep 的执行顺序（并行/串行）
- [x] `run_pipeline.py` 使用 `BatchFactory.try_create()` 替代 `_try_channel()`
- [x] `quick_query.py` 使用 `BatchFactory.try_create()` 替代 `_try_channel()`
- [x] 两个脚本中 `_try_channel()` 函数定义已删除
- [x] `run_pipeline.py` 支持 `--only-phase N` 参数
- [x] `IPDataWriter` Protocol 包含 `add_or_update_ip_batch` 方法
- [x] `IPWriter.add_or_update_ip_batch()` 单次读+写完成批量更新
- [x] `InMemoryIPWriter` 实现了 `add_or_update_ip_batch`
- [x] `add_or_update_ip_batch([])` 返回 0，无文件 I/O
- [x] `PipelineBuilder.skip_dynamic_ips()` 自动注册动态 IP 过滤器
- [x] `self._skip_dynamic` 无用标记已移除
- [x] `run_pipeline.py` 使用 `builder.skip_dynamic_ips()` 替代手动注册过滤器

## 测试策略检查

- [ ] 每个 Task 2-8 的测试均经过 fake-driven-testing skill 审核
- [x] 测试中无 `unittest.mock.patch` 替换模块级属性（test_batch_factory.py 中 importlib mock 除外）
- [x] 测试中无 `MagicMock` 模拟协议行为
- [x] 使用 Fake 替身（FakeChannel, InMemoryIPWriter, FakeBatchStep）替代 mock
- [x] `FakeBatchStep` 类已定义，返回固定 BatchResult
- [x] 测试文件组织正确：`tests/unit/pipeline/core/` 和 `tests/unit/pipeline/trace_steps/`

## 最终验证

- [x] 全量测试（`pytest tests/`）通过
- [x] `ruff check` 通过
