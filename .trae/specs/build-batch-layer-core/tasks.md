# Tasks

- [x] Task 1: 创建 ProgressTracker 协议 + InMemoryProgressTracker
  - [x] SubTask 1.1: 创建 `tests/unit/batch/__init__.py` 和 `tests/unit/batch/conftest.py`（autouse mock `ip_info.channel.adapter.time.sleep`）
  - [x] SubTask 1.2: 在 `src/ip_info/batch/protocols.py` 中定义 `ProgressTracker` Protocol（`is_processed(ip) -> bool`、`mark_processed(ip) -> None`）
  - [x] SubTask 1.3: 在 `src/ip_info/batch/progress.py` 中实现 `InMemoryProgressTracker`
  - [x] SubTask 1.4: 写测试 — isinstance 检查、mark_processed + is_processed、未标记返回 False
  - 验证: `python -m pytest tests/unit/batch/ -v` 通过

- [x] Task 2: 创建 FileProgressTracker
  - [x] SubTask 2.1: 在 `src/ip_info/batch/progress.py` 中实现 `FileProgressTracker`（追加写入 + 读取进度文件）
  - [x] SubTask 2.2: 写测试 — 持久化到文件、文件不存在时所有 IP 未处理、重新创建实例后能读取进度
  - 验证: FileProgressTracker 测试通过

- [x] Task 3: 创建 BatchResult 数据类 + BaseBatchQuery 骨架
  - [x] SubTask 3.1: 在 `src/ip_info/batch/query.py` 中创建 `BatchResult` 数据类
  - [x] SubTask 3.2: 创建 `BaseBatchQuery.__init__()` 接收构造函数参数，内部去重 IP 列表，计算 pending_ips
  - [x] SubTask 3.3: 写测试 — BatchResult 默认值、构造函数参数存储、IP 去重、total_count/pending_count 属性
  - 验证: 骨架测试通过

- [x] Task 4: 核心 run() 循环（成功路径 + 延迟控制）
  - [x] SubTask 4.1: 实现 `run()` 基本循环 — for ip in pending_ips → channel.fetch(ip, delay=self._delay) → writer.add_or_update_ip
  - [x] SubTask 4.2: 写测试 — 查询所有 pending IP、写入正确 channel_name、写入正确 data、delay 参数传递
  - 验证: 基本 run() 循环测试通过

- [x] Task 5: 进度跟踪集成
  - [x] SubTask 5.1: 在 run() 循环中集成 progress_tracker — 排除已处理 IP、查询完成后标记
  - [x] SubTask 5.2: 写测试 — 无 tracker 时处理全部 IP、有 tracker 时排除已处理 IP、成功查询标记进度、ChannelError 不标记进度、ChannelPermanentError 不标记进度
  - 验证: 进度跟踪集成测试通过

- [x] Task 6: 错误处理
  - [x] SubTask 6.1: 在 run() 循环中捕获 ChannelError — 不写入 store，计为 failure，增加熔断计数，通过日志记录
  - [x] SubTask 6.2: 在 run() 循环中捕获 ChannelPermanentError — 检测 disabled，立即终止，返回 stopped_early=True
  - [x] SubTask 6.3: 写测试 — 成功写入、ChannelError 不写入、ChannelPermanentError 终止并跳过后续 IP、非 ChannelError 异常传播
  - 验证: 错误处理测试通过

- [x] Task 7: 熔断保护
  - [x] SubTask 7.1: 在 run() 循环中增加连续 ChannelError 计数器，达到阈值时终止
  - [x] SubTask 7.2: 写测试 — 连续 5 次 ChannelError 触发熔断、成功重置计数、自定义阈值
  - 验证: 熔断保护测试通过

- [x] Task 8: 依赖检查
  - [x] SubTask 8.1: 在 run() 开头检查 channel.disabled — 为 True 则跳过所有查询
  - [x] SubTask 8.2: 当 no_validate=False 时调用 channel.validate()
  - [x] SubTask 8.3: 写测试 — disabled=True 跳过查询、no_validate=False 调用 validate、no_validate=True 跳过 validate
  - 验证: 依赖检查测试通过

- [x] Task 9: 集成验证 + BatchResult 统计
  - [x] SubTask 9.1: 确保 run() 返回正确填充的 BatchResult（success_count、fail_count、total_elapsed、stopped_early、stop_reason）
  - [x] SubTask 9.2: 写集成测试 — 完整流程（构造 → 排除已处理 → 查询 → 写入 → 进度标记 → 统计）
  - [x] SubTask 9.3: 运行 `python -m pytest tests/unit/ -v` 确认全部 307+ 测试通过（含新测试）
  - [x] SubTask 9.4: 运行 `ruff check src/ tests/unit/` 确认无 lint 错误
  - 验证: 全量测试通过 + lint 通过

# Task Dependencies

- [Task 1] → [Task 2]（协议先于实现）
- [Task 1] → [Task 3]（ProgressTracker 协议先于 BaseBatchQuery 构造函数）
- [Task 3] → [Task 4]（骨架先于 run 循环）
- [Task 4] → [Task 5]（基本 run 循环先于进度集成）
- [Task 4] → [Task 6]（基本 run 循环先于错误处理）
- [Task 6] → [Task 7]（错误检测先于熔断保护）
- [Task 4] → [Task 8]（基本 run 循环先于依赖检查）
- [Task 5, 6, 7, 8] → [Task 9]（集成验证在所有功能完成后）
