# ADR-005: 断点续查机制（Checkpoint Resume）

## 状态

已采纳

## 上下文

批量查询和流水线任务可能运行数小时，网络中断、凭证失效、手动中断等情况常见。需要支持从断点恢复执行，避免重复工作。

## 决策

采用 **多层断点续查机制**：

### 1. 阶段级进度（Phase Progress）

每个有 IO 操作的阶段维护一个进度文件：

```
{prefix}.trace_phase{N}.progress    # 阶段进度
```

### 2. 渠道级进度（Channel Progress）

每个阶段内的每个渠道独立跟踪：

```
{prefix}.trace_phase{N}.{channel}.progress    # 渠道进度
```

### 3. JSON 智能断点

即使进度文件丢失，也能从 JSON 数据文件中恢复：

```python
# 检查 IP 是否已有该阶段的完整数据
ip_data = self._ip_reader.get_ip_data(ip)
if 'ipinfo_api' not in ip_data or 'raw_error' in ip_data.get('ipinfo_api', {}):
    has_phase1_data = False
```

### 4. BatchIPWriter 批量写入

使用上下文管理器确保数据安全写入：

```python
with self._batch_writer:
    for ip in ips:
        self._batch_writer.add(ip, channel, data)
        self._batch_writer.flush_batch()   # 每 IP 刷盘
```

### 5. 进度管理 API

```python
class ProgressManager:
    def record(ip, phase, channel=None)    # 记录完成
    def load_completed(phase, channels)    # 加载已完成 IP 集合
    def flush()                            # 刷盘到文件
    def clear_from(phase)                  # 清理指定阶段及之后的进度
```

## 理由

1. **可靠性** — 三层恢复机制（进度文件 → 渠道进度 → JSON 数据）
2. **细粒度** — 渠道级进度避免"一个渠道失败导致整个阶段重跑"
3. **性能** — 批量写入减少 IO，但每 IP 刷盘保证最小数据丢失
4. **安全性** — KeyboardInterrupt 时自动保存进度

## 后果

**优势：**
- 中断恢复粒度细到单个 IP 的单个渠道
- 渠道级交集逻辑确保所有渠道都完成后才跳过
- 向后兼容：无渠道文件时退化为阶段级进度

**劣势：**
- 进度文件数量较多（每个阶段 × 每个渠道）
- 进度文件是纯文本追加写入，无校验和
- pipeline.py 中断点检查逻辑重复（每个 Phase 都有类似的 processed 逻辑）
