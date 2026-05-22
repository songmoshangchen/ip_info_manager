# ADR-003: 多阶段流水线架构（Multi-Phase Pipeline）

## 状态

已采纳

## 上下文

IP 溯源和域名反查是复杂的多步骤流程，需要将多个采集、分析、验证步骤串联执行。需要设计一种可扩展的流水线架构。

## 决策

采用 **多阶段流水线架构**，每个场景定义多个 Phase，支持灵活的阶段控制。

### 溯源 IP 流水线（7 阶段）

```
Phase 1: 基础采集 (IPInfo + RDNS, 并行)
Phase 2: 分类过滤 + 标签打标
Phase 3: 深度查询 (爱站 + 站长 + Fofa Host, 并行)
Phase 4: DNS 域名正向验证
Phase 5: 端口扫描 (nmap, 默认关闭)
Phase 6: 汇总输出
Phase 7: Word + Excel 报告生成
```

### IP 域名反查流水线（4 阶段）

```
Phase 1: 域名收集 (6 渠道并行)
Phase 2: DNS 正向验证
Phase 3: 汇总报告
Phase 4: Word 报告
```

### 阶段控制机制

```python
# 完整执行（默认 Phase 1-5）
python -m scenarios.trace_ip ips.txt

# 只执行某个阶段
python -m scenarios.trace_ip ips.txt --only-phase 3

# 从某个阶段开始（断点续跑）
python -m scenarios.trace_ip ips.txt --from-phase 3

# 语义化快捷命令
python -m scenarios.trace_ip ips.txt --collect-only      # = --only-phase 1
python -m scenarios.trace_ip ips.txt --generate-report    # = --only-phase 7
```

## 理由

1. **灵活性** — 用户可按需执行特定阶段
2. **断点续跑** — 中断后从指定阶段继续
3. **可观测性** — 每个阶段有独立的进度文件和日志
4. **关注点分离** — 每个阶段职责单一

## 后果

**优势：**
- 长时间任务可安全中断恢复
- 可单独重跑某个阶段（如只生成报告）
- 阶段间通过 JSON 文件传递数据，解耦

**劣势：**
- `pipeline.py` 代码量大（~1180 行）
- 阶段间数据依赖通过文件系统，不够显式
- Phase 1-5 的进度跟踪逻辑高度重复（每个 Phase 都有断点续跑逻辑）
