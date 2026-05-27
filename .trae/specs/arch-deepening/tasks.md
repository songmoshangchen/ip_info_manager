# Tasks

- [x] Task 1: 合并 Pipeline 双生子 — PipelineBuilder 构建完整 Pipeline
  - [x] 1.1: 修改 `PipelineBuilder.build()` 返回 `pipeline.py` 的 `Pipeline` 实例
  - [x] 1.2: 删除 `builder.py` 中的简单 `Pipeline` dataclass
  - [x] 1.3: 更新 `test_builder.py` 适配新 Pipeline 返回类型
  - [x] 1.4: 运行全量测试确认无回归

- [x] Task 2: Phase 构造函数去重 — 只接受 context + 特有参数
  - [x] 2.1: 修改 Phase 1-4 构造函数，移除 `writer`/`reader`/`progress_tracker`/`domain_cache` 独立参数，`context` 变为必填
  - [x] 2.2: Phase 从 `self._context` 获取 writer/reader/progress_tracker/domain_cache
  - [x] 2.3: 更新所有测试文件适配新构造函数签名
  - [x] 2.4: 运行全量测试确认无回归

- [x] Task 3: 渠道禁用逻辑统一到 run_concurrent
  - [x] 3.1: 删除 Phase 1/3 中的 `channel.disabled` 检查和日志逻辑
  - [x] 3.2: 确保 `run_concurrent()` 已有完整的禁用处理和日志
  - [x] 3.3: 更新相关测试（移除 Phase 层的 disabled 日志断言）
  - [x] 3.4: 运行全量测试确认无回归

- [x] Task 4: BatchTagger 修复 — 使用显式 reader
  - [x] 4.1: 修改 `BatchTagger._read_channel_data()` 使用 `self._reader.get_channel_data()`
  - [x] 4.2: 添加测试验证 accumulate 模式在纯 writer 下正常工作
  - [x] 4.3: 运行全量测试确认无回归

- [x] Task 5: flush_progress 统一工具函数
  - [x] 5.1: 在 `utils/progress.py` 中添加 `flush_progress(tracker)` 函数
  - [x] 5.2: 替换 `batch/core/query.py`、`batch/core/concurrent.py`、`processors/core/base.py` 中的 `_try_flush`
  - [x] 5.3: 运行全量测试确认无回归

- [x] Task 6: InMemoryIPWriter 去冗余
  - [x] 6.1: 从 `InMemoryIPWriter` 移除 `get_ip_data`/`get_channel_data`/`list_all_ips`/`list_ip_channels` 读取方法
  - [x] 6.2: 更新所有测试中 `writer.get_channel_data()` → 使用独立 `InMemoryIPReader`
  - [x] 6.3: 运行全量测试确认无回归

- [x] Task 7: PipelineBuilder 内化 filter_ips + run_pipeline.py 迁移
  - [x] 7.1: `PipelineBuilder` 新增 `with_filter()` 方法注册阶段间过滤器
  - [x] 7.2: `Pipeline.build()` 或 `Pipeline.run()` 在 Phase 间自动执行过滤器
  - [x] 7.3: 用 `PipelineBuilder` 重写 `run_pipeline.py`
  - [x] 7.4: 运行全量测试确认无回归

# Task Dependencies

- Task 1 → Task 7（Builder 先合并，再内化 filter）
- Task 2 → Task 7（Phase 构造函数先简化，再迁移脚本）
- Task 3, 4, 5, 6 可与 Task 1/2 并行
- Task 7 依赖 Task 1 + Task 2
