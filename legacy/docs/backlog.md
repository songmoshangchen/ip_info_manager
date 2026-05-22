# 待办事项（非当前任务优先级）

## 代码清理

### 1. 删除 ChannelFetcher Protocol
- **文件**: `protocols.py:29-31`
- **影响范围**: 仅 `test_channel_base.py` 引用，生产代码零引用
- **操作**: 删除 `ChannelFetcher` 类定义 + 更新 `test_channel_base.py` 中 2 个相关测试
- **状态**: 待执行

### 2. trace_ip/pipeline.py Phase 5 硬编码导入
- **文件**: `scenarios/trace_ip/pipeline.py:12`
- **现状**: `from channel.port_scan import (validate_engine, fetch_channel)` 硬编码导入
- **目标**: 改为通过 `self._registry.get('port_scan')` 获取
- **状态**: 待执行

## 功能迁移

### 3. batch_rdns_ptr_concurrent.py 迁移到 BaseBatchQuery
- **文件**: `scripts/batch_rdns_ptr_concurrent.py`
- **难点**: 并发逻辑差异大，需设计 `ConcurrentBaseBatchQuery` 基类
- **状态**: 待设计

### 4. batch_port_scan.py 迁移到 BaseBatchQuery
- **文件**: `scripts/batch_port_scan.py`
- **难点**: 依赖外部 nmap 引擎，validate 逻辑特殊
- **状态**: 待设计

## 功能增强

### 5. create_default_registry() 容错
- **文件**: `protocols.py:186-208`
- **目标**: 某个渠道 ImportError 时提示并跳过，而非崩溃
- **状态**: 待实现

### 6. exclude_ips 集成到 BaseBatchQuery.run()
- **文件**: `scripts/base_batch.py`
- **关联**: Phase 7 bug 的修复方案
- **状态**: 待实现（当前任务 T5/T6 会处理）

## 待决策

### 7. excel_exporter.py 是否删除
- **文件**: `scenarios/trace_ip/excel_exporter.py`
- **现状**: 基本未使用，trace_utils 中的函数已从中提取
- **决策**: 用户考虑是否删除
