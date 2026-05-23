# 批量查询层规格文档（脚本 + 核心库扩展）

## Why

将 legacy 的 batch 脚本迁移到新架构。batch 层包含两部分：
- **核心库**（`src/ip_info/batch/`）：已完成 BaseBatchQuery、BatchResult、ProgressTracker，本 spec 新增并发查询函数
- **脚本入口**（`scripts/`）：每个脚本负责参数解析、IP 文件加载、日志配置、组装查询并调用

**前置依赖**：需要先完成 ChannelAdapter 配置系统增强（添加 .env 读取 + `default_delay` 属性），参见 `.trae/specs/add-channel-config/`。

## What Changes

- 新增 `src/ip_info/batch/concurrent.py`：并发查询函数 `run_concurrent()`
- 新增 `src/ip_info/store/` 接口扩展：IPWriter 提供 `progress_tracker()` 方法
- 新增 `scripts/` 目录：10 个批量查询脚本入口（项目根目录，不在 src 内）
- 新增 `tests/unit/batch/test_concurrent.py`：并发查询测试
- 新增 `tests/unit/batch/scripts/` 目录：批量查询脚本测试

## Impact

- Affected specs: build-batch-layer-core (BaseBatchQuery, BatchResult, ProgressTracker), build-store-layer (IPWriter 接口扩展)
- Affected code: `src/ip_info/batch/concurrent.py` (new), `src/ip_info/store/json_store.py` (扩展 progress_tracker), `src/ip_info/store/in_memory.py` (扩展 progress_tracker), `scripts/` (new)

---

## 层间接口

> 本 spec 属于 batch 层。batch 层已完成的核心（BaseBatchQuery、BatchResult、ProgressTracker）在 `.trae/specs/build-batch-layer-core/` 中定义，本 spec 补充并发查询和脚本入口。

### batch 层提供的接口（供 pipeline / 外部脚本调用）

| 模块 | 接口 | 签名 | 说明 |
|------|------|------|------|
| `batch/query.py` | `BaseBatchQuery` | 构造 + `run() -> BatchResult` | 批量查询核心（已完成） |
| `batch/query.py` | `BatchResult` | 数据类 | 查询结果统计（已完成） |
| `batch/protocols.py` | `ProgressTracker` | 协议（is_processed / mark_processed） | 进度跟踪协议（已完成） |
| `batch/progress.py` | `FileProgressTracker` | `(file_path: str)` | 文件持久化进度跟踪（已完成） |
| `batch/progress.py` | `InMemoryProgressTracker` | `()` | 内存进度跟踪（已完成） |
| `batch/concurrent.py` | `run_concurrent` | `(ips, channel, writer, channel_name, workers, delay, no_validate, progress_tracker, ...) -> BatchResult` | 并发批量查询（**新增**） |

### batch 层依赖的接口（从其他层消费）

| 来源层 | 接口 | 签名 | 说明 |
|--------|------|------|------|
| store | `IPWriter.__init__` | `(storage_file: str)` | 创建数据写入器 |
| store | `IPWriter.progress_tracker` | `(channel_name: str) -> ProgressTracker` | 获取进度跟踪器（**新增**） |
| store | `IPWriter.add_or_update_ip` | `(ip, channel_name, data) -> bool` | 写入 IP 渠道数据 |
| channel | `XxxChannel.__init__` | `(xxx=None, config=None)` | 创建渠道适配器（自动从 .env 读取） |
| channel | `BaseChannelAdapter.default_delay` | `float` 属性 | 渠道默认请求间隔 |
| channel | `BaseChannelAdapter.validate` | `() -> bool` | 验证渠道配置是否有效（如 API key） |
| channel | `BaseChannelAdapter.fetch` | `(ip: str, **kwargs) -> dict` | 查询 IP 数据 |

---

## ADDED Requirements

### Requirement: 并发批量查询函数

系统 SHALL 提供 `run_concurrent()` 函数，为支持并发的渠道提供多线程批量查询能力。

```python
def run_concurrent(
    ips: list[str],
    channel: BaseChannelAdapter,
    writer: IPDataWriter,
    channel_name: str,
    *,
    workers: int = 1,
    delay: float = 0,
    no_validate: bool = False,
    progress_tracker: ProgressTracker | None = None,
    max_consecutive_network_failures: int = 5,
) -> BatchResult:
```

实现方式：使用 `concurrent.futures.ThreadPoolExecutor`，封装熔断保护和进度跟踪。不修改 `BaseBatchQuery`。

当 `workers <= 1` 时，退化为 `BaseBatchQuery.run()` 单线程模式。

#### Scenario: 单线程退化

- **WHEN** 调用 `run_concurrent(..., workers=1)`
- **THEN** 行为与 `BaseBatchQuery.run()` 一致

#### Scenario: 多线程查询

- **WHEN** 调用 `run_concurrent(..., workers=20)`
- **THEN** 使用 20 个线程并发查询，结果写入同一个 store，熔断和进度跟踪正常工作

#### Scenario: 熔断保护

- **WHEN** 并发查询中连续 N 次 ChannelError
- **THEN** 取消剩余待查询 IP，返回 `BatchResult(stopped_early=True)`

---

### Requirement: 进度跟踪器由存储层提供

IPWriter SHALL 提供 `progress_tracker(channel_name: str) -> ProgressTracker` 方法，为指定渠道返回进度跟踪器。脚本不直接构造 `FileProgressTracker`，也不拼接进度文件路径——进度存储方式是存储层的实现细节。

- `IPWriter`（JSON 文件实现）返回 `FileProgressTracker`，路径规则为 `{storage_file去掉.json}.{channel_name}.progress`
- `InMemoryIPWriter` 返回 `InMemoryProgressTracker`
- 未来其他存储实现自行决定进度存储方式

#### Scenario: IPWriter 返回文件进度跟踪器

- **WHEN** `IPWriter(storage_file="data/ip_data.json").progress_tracker("fofa_host")`
- **THEN** 返回 `FileProgressTracker`，其文件路径为 `"data/ip_data.fofa_host.progress"`

#### Scenario: InMemoryIPWriter 返回内存进度跟踪器

- **WHEN** `InMemoryIPWriter().progress_tracker("fofa_host")`
- **THEN** 返回 `InMemoryProgressTracker`

---

### Requirement: 脚本位置

批量查询脚本 SHALL 放在项目根目录的 `scripts/` 下，不在 `src/ip_info/` 内。理由：脚本是 batch 层的应用入口，不是库代码。

```
ip_info_manager/
├── scripts/                    # 批量查询脚本（batch 层入口）
│   ├── batch_rdns_ptr.py
│   ├── batch_ipinfo_api.py
│   ├── batch_ipinfo_free.py
│   ├── batch_fofa_host.py
│   ├── batch_nmap.py
│   └── ...
├── src/ip_info/                # 库代码
│   ├── store/
│   ├── channel/
│   ├── batch/                  # batch 层核心库
│   │   ├── query.py            # BaseBatchQuery + BatchResult
│   │   ├── concurrent.py       # run_concurrent()
│   │   ├── protocols.py        # ProgressTracker 协议
│   │   ├── progress.py         # File/InMemory 进度跟踪
│   │   └── ...
│   └── pipeline/
```

---

### Requirement: 批量查询脚本模板

每个批量查询脚本 SHALL 遵循统一模板。参数解析和日志配置直接在脚本内完成，不依赖额外的 CLI/Utils 模块。

**普通脚本模板**（6 个不支持并发的渠道）：

```python
# scripts/batch_xxx.py

import argparse
import logging
import sys

from ip_info.batch import BaseBatchQuery
from ip_info.channel import XxxChannel
from ip_info.store import IPWriter

CHANNEL_NAME = "xxx"
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description=f"批量 {CHANNEL_NAME} 查询")
    parser.add_argument("ip_file", help="IP 文件路径")
    parser.add_argument("--no-validate", action="store_true", help="跳过渠道验证")
    return parser.parse_args()

def main():
    args = parse_args()
    # 日志配置（脚本内直接完成）
    ...

    # IP 文件加载（脚本内直接完成）
    ...

    channel = XxxChannel()
    writer = IPWriter(...)
    tracker = writer.progress_tracker(CHANNEL_NAME)

    query = BaseBatchQuery(
        channel_name=CHANNEL_NAME,
        channel=channel,
        writer=writer,
        ips=ips,
        delay=channel.default_delay,
        no_validate=args.no_validate,
        progress_tracker=tracker,
    )
    result = query.run()

if __name__ == "__main__":
    main()
```

**并发脚本模板**（4 个支持并发的渠道）：

```python
# scripts/batch_rdns_ptr.py（并发示例）

import argparse
import logging
import sys

from ip_info.batch import run_concurrent
from ip_info.channel import RdnsPtrChannel
from ip_info.store import IPWriter

CHANNEL_NAME = "rdns_ptr"
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description=f"批量 {CHANNEL_NAME} 查询")
    parser.add_argument("ip_file", help="IP 文件路径")
    parser.add_argument("--no-validate", action="store_true", help="跳过渠道验证")
    parser.add_argument("--workers", type=int, default=1, help="并发线程数")
    return parser.parse_args()

def main():
    args = parse_args()
    # 日志配置 + IP 文件加载
    ...

    channel = RdnsPtrChannel()
    writer = IPWriter(...)
    tracker = writer.progress_tracker(CHANNEL_NAME)

    result = run_concurrent(
        ips=ips,
        channel=channel,
        writer=writer,
        channel_name=CHANNEL_NAME,
        workers=args.workers,
        delay=channel.default_delay,
        no_validate=args.no_validate,
        progress_tracker=tracker,
    )

if __name__ == "__main__":
    main()
```

---

### Requirement: 脚本清单（10 个）

| 脚本 | 渠道适配器 | 额外 CLI 参数 | 查询方式 |
|------|-----------|-------------|---------|
| `batch_rdns_ptr.py` | `RdnsPtrChannel` | `--workers N` | `run_concurrent()` |
| `batch_ipinfo_api.py` | `IpInfoApiChannel` | 无 | `BaseBatchQuery.run()` |
| `batch_ipinfo_free.py` | `IpInfoFreeChannel` | 无 | `BaseBatchQuery.run()` |
| `batch_fofa_host.py` | `FofaHostChannel` | 无 | `BaseBatchQuery.run()` |
| `batch_fofa_search.py` | `FofaSearchChannel` | 无 | `BaseBatchQuery.run()` |
| `batch_aizhan.py` | `AizhanChannel` | 无 | `BaseBatchQuery.run()` |
| `batch_chinaz.py` | `ChinazChannel` | 无 | `BaseBatchQuery.run()` |
| `batch_whois.py` | `WhoisQueryChannel` | `--workers N` | `run_concurrent()` |
| `batch_ssl_cert.py` | `SslCertChannel` | `--workers N` | `run_concurrent()` |
| `batch_nmap.py` | `PortScanChannel` | `--workers N` | `run_concurrent()` |

**不写的脚本**：
- `batch_zoomeye.py`：当前没有 ZoomEye 渠道适配器

---

## 与 legacy 的差异

| 方面 | Legacy | 新架构 |
|------|--------|--------|
| **脚本位置** | `legacy/scripts/` | `scripts/`（项目根目录） |
| **脚本性质** | 子类化 BaseBatchQuery（ABC） | 实例化 BaseBatchQuery 或调用 run_concurrent() |
| **IP 加载** | BaseBatchQuery 内部 `_load_ip_file()` | 脚本内直接完成 |
| **日志** | `get_batch_logger()` 全局函数 | 脚本内直接配置 `logging` |
| **进度跟踪** | 依赖 `ip_writer.storage_file` 拼接文件路径 | `writer.progress_tracker(channel_name)` 由存储层封装 |
| **PID 管理** | 每个脚本创建 PidManager | **移除** |
| **delay** | 脚本直接读取 `Settings().xxx_delay` | `channel.default_delay` |
| **_print_result** | 每个脚本自定义打印格式 | **移除**（通过日志和 BatchResult 替代） |
| **并发支持** | 仅 RDNS 有独立并发脚本 | `run_concurrent()` 统一提供，4 个脚本使用 |
| **ipinfo** | 单一脚本 `--no-api` 切换 | 拆分为 `batch_ipinfo_api.py` + `batch_ipinfo_free.py` |
| **nmap** | 无独立脚本 | `batch_nmap.py`（关联 `PortScanChannel`） |
| **CLI/Utils 模块** | 无 | **不提供**，脚本自行处理参数解析和日志配置 |
