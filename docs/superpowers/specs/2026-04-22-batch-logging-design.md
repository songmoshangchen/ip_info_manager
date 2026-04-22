# batch_*.py 日志系统设计

## 背景

`scripts/batch_*.py` 全部 7 个批处理脚本目前使用 `print()` 输出所有信息，存在以下问题：

- 无日志级别控制，无法区分调试信息、警告和错误
- 无日志文件输出，诊断信息跑完即丢失
- 批量查询数千 IP 后，失败原因难以复现和定位
- 无查询耗时记录、无详细错误堆栈

## 方案选择

选择 Python 标准 `logging` 模块 + 公共 Logger 工具类，理由：

- 标准库零依赖
- Logger 层级机制天然解决 scripts/channel 重复输出问题
- 天然支持多 Handler（终端 + 文件）
- 渐进式改造，channel 层后续接入零冲突

## Logger 层级架构

```
ip_info_manager (根 logger, 不直接使用)
├── ip_info_manager.scripts              ← scripts 层
│   ├── ip_info_manager.scripts.aizhan
│   ├── ip_info_manager.scripts.chinaz
│   ├── ip_info_manager.scripts.fofa
│   ├── ip_info_manager.scripts.ipinfo_api
│   ├── ip_info_manager.scripts.rdns_ptr
│   ├── ip_info_manager.scripts.rdns_ptr_concurrent
│   └── ip_info_manager.scripts.whois
│
└── ip_info_manager.channel              ← channel 层 (第二阶段)
    ├── ip_info_manager.channel.aizhan
    ├── ip_info_manager.channel.chinaz
    └── ...
```

### Handler 分配策略

| Logger 层级 | 终端 Handler | 文件 Handler | 说明 |
|---|---|---|---|
| `ip_info_manager.scripts` | INFO 级别 | DEBUG 级别 | 终端显示用户进度，文件记录完整调试信息 |
| `ip_info_manager.channel` | 无 | DEBUG 级别 | 只写文件，避免和 scripts 层重复打印 |

## 公共日志工具模块

新建 `scripts/logger_utils.py`，提供两个核心函数：

### `get_batch_logger(channel_name)`

为 batch 脚本创建预配置的 logger。

- Logger 名称: `ip_info_manager.scripts.<channel_name>`
- 终端 Handler: INFO 级别，简洁格式 `[HH:MM:SS] [LEVEL] 消息`
- 文件 Handler: DEBUG 级别，详细格式 `[YYYY-MM-DD HH:MM:SS] [LEVEL] [模块名] 消息`
- `propagate=False`，避免重复输出

### `get_channel_logger(channel_name)`

为 channel 模块创建 logger（第二阶段使用）。

- Logger 名称: `ip_info_manager.channel.<channel_name>`
- 无终端 Handler
- 文件 Handler: DEBUG 级别

### 日志文件配置

- 路径: `data/logs/<channel_name>.log`
- 使用 `RotatingFileHandler`，单文件最大 10MB，保留 3 个备份
- 文件名示例: `fofa.log`、`fofa.log.1`、`fofa.log.2`、`fofa.log.3`
- 追加写入，不覆盖

## print() → logger 替换策略

### 日志级别规范

| 级别 | 使用场景 | 终端显示 |
|---|---|---|
| `DEBUG` | 查询耗时、数据详情、内部状态 | 不显示 |
| `INFO` | 进度、成功结果、启动/完成信息 | 显示 |
| `WARNING` | 查询失败但可继续（网络超时、被封等） | 显示 |
| `ERROR` | 致命错误（文件不存在、Key 无效等） | 显示 |

### 替换对照表

| 原 print() | 替换为 |
|---|---|
| `print(f"开始批量查询 XXX 信息")` | `logger.info("开始批量查询 XXX 信息")` |
| `print(f"[{n}/{total}] 正在查询: {ip}")` | `logger.info(f"[{n}/{total}] 正在查询: {ip}")` |
| `print(f"✅ {result}")` | `logger.info(f"✅ {result}")` |
| `print(f"❌ {error}")` | `logger.warning(f"❌ {error}")` |
| `print(f"错误: 找不到文件")` | `logger.error(f"错误: 找不到文件")` |
| `print(f"查询已中断！")` | `logger.info(f"查询已中断！")` |
| `print(f"批量查询完成！")` | `logger.info(f"批量查询完成！")` |

### 新增调试信息

| 信息 | 级别 | 位置 | 具体内容 |
|---|---|---|---|
| 单次查询耗时 | `DEBUG` | `run()` 循环内，`_query_ip()` 返回后 | `logger.debug(f"查询 {ip} 耗时: {elapsed:.3f}s")` |
| 批量查询总耗时 | `INFO` | `run()` 结束汇总区 | `logger.info(f"总耗时: {total_elapsed:.2f}s")` |
| IP 数据写入详情 | `DEBUG` | `run()` 循环内，`ip_writer.add_or_update_ip()` 后 | `logger.debug(f"已写入 {ip} 的 {channel_name} 数据")` |

## 分步实施计划

### 第一阶段：scripts 层（本次实施）

| 步骤 | 内容 | Commit 消息 |
|---|---|---|
| 1 | 新建 `scripts/logger_utils.py` | `feat(scripts): 添加公共日志工具模块` |
| 2 | 改造 `scripts/_template.py` | `refactor(scripts): 更新批量查询模板，使用 logging 替代 print` |
| 3a | 改造 `batch_fofa.py` | `feat(scripts): fofa 批量查询添加日志输出` |
| 3b | 改造 `batch_ipinfo_api.py` | `feat(scripts): ipinfo 批量查询添加日志输出` |
| 3c | 改造 `batch_aizhan.py` | `feat(scripts): aizhan 批量查询添加日志输出` |
| 3d | 改造 `batch_chinaz.py` | `feat(scripts): chinaz 批量查询添加日志输出` |
| 3e | 改造 `batch_rdns_ptr.py` | `feat(scripts): rdns_ptr 批量查询添加日志输出` |
| 3f | 改造 `batch_rdns_ptr_concurrent.py` | `feat(scripts): rdns_ptr 并发批量查询添加日志输出` |
| 3g | 改造 `batch_whois.py` | `feat(scripts): whois 批量查询添加日志输出` |

### 第二阶段：channel 层（后续实施）

- 各 channel 模块引入 `get_channel_logger()`
- 替换 `print()` 为 `logger.debug()`
- 终端不输出，仅写入日志文件
- 与 scripts 层日志去重：channel 层 logger 不设终端 Handler

## 约束

- 使用 Python 标准 `logging` 模块，不引入第三方依赖
- 使用 `git-commit` 技能提交，commit 消息使用中文
- 每步一个 commit，不一口气提交
- `data/logs/` 目录加入 `.gitignore`
