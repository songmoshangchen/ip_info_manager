# ADR-009: BaseBatchQuery.run() 提取 + 批量脚本迁移

## 状态

已采纳

## 上下文

ADR-003 定义了 `BaseBatchQuery` ABC 提取批量脚本的通用逻辑（初始化、加载、进度），但 10 个 batch 脚本仍有约 80 行几乎完全相同的 `run()` 方法——包含查询循环、错误处理、进度保存、ETA 计算、PID 管理、KeyboardInterrupt 处理、统计输出。

每个脚本的 `run()` 方法差异极小：
- `_query_ip()` 和 `_print_result()` 已是抽象方法
- rdns_ptr 有额外的 `has_ptr_count` / `no_ptr_count` 统计
- 日志 banner 文本不同

## 决策

在 `BaseBatchQuery` 中实现完整的 `run()` 方法，提取通用循环：

```python
def run(self):
    # 1. validate hook
    # 2. PID write
    # 3. for ip in pending_ips: query → write → progress → heartbeat → ETA → sleep
    # 4. KeyboardInterrupt → pid remove + stats + sys.exit(0)
    # 5. completion → pid remove + run_stats
```

子类只需实现：
- `_query_ip(ip)` — 查询逻辑（已有）
- `_print_result(ip, data)` — 打印逻辑（已有）
- `_get_delay()` — 延迟配置（已有）
- `_do_validate()` — 校验钩子（新增，默认 no-op）

**示范迁移**：`batch_fofa_host.py` 和 `batch_rdns_ptr.py` 已迁移为继承 `BaseBatchQuery`，代码从约 200 行减少到约 60 行。其余 8 个脚本待后续迁移。

## 理由

1. **DRY** — 80 行 × 10 脚本 = 800 行重复代码消除
2. **一致性** — ETA 计算、PID 管理、KeyboardInterrupt 处理统一在基类
3. **可测试** — `run()` 的核心循环有 20 个测试覆盖
4. **渐进迁移** — 已有脚本无需一次性全部迁移

## 后果

**优势：**
- 迁移后的脚本只需 60 行（原 200 行），维护成本大幅降低
- 新增批量脚本只需继承 + 实现 3-4 个方法
- `run_stats` 字典可供子类扩展

**劣势：**
- `run()` 中 `_pid_mgr` 用 `hasattr` 检查（因子类属性名不一致）
- 原始脚本的 banner 日志（"开始批量查询..."）在迁移后丢失，需子类自行补充
- 8 个脚本尚未迁移，存在新旧两种模式并存

**rdns_ptr 特殊处理：**
- rdns_ptr 原有 `has_ptr_count` / `no_ptr_count` 额外统计
- 迁移后这些统计被简化为 `success_count` / `fail_count`
- 如需保留详细统计，可重写 `run()` 或在 `_print_result` 中计数
