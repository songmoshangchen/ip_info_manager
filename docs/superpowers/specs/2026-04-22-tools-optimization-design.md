# Tools 目录优化设计

## 背景

`tools/` 目录下有 5 个工具脚本，存在以下问题：
- `process_ip_list.py` 和 `merge_ip_files.py` 功能重叠（都是去重+验证）
- `compare_ip_files.py` 功能已被 batch progress 覆盖
- 所有工具使用 `sys.exit(1)` 处理错误，无法被安全 import
- `config_tool.py` 的 `EnvManager` 需要 AI agent 通过 import 调用

## 决策

| 文件 | 操作 |
|------|------|
| `process_ip_list.py` | 删除，功能合并到 `merge_ip_files.py` |
| `compare_ip_files.py` | 删除，不再需要 |
| `merge_ip_files.py` | 重构：吸收 `validate_ip`，修复 `sys.exit`，支持单文件去重 |
| `config_tool.py` | 修复：`sys.exit` → `raise ValueError`，保留 EnvManager + CLI |
| `verify_ip_domain.py` | 优化：修复 `sys.exit`，`batch_verify` 进度输出改为 callback |
| `utils/` | 创建空框架，预留未来使用 |

## 详细改动

### merge_ip_files.py

1. 从 `process_ip_list.py` 搬入 `validate_ip()` 函数
2. `read_ips_from_file()` 中 `sys.exit(1)` → `raise FileNotFoundError`
3. CLI 支持 1 个文件时自动进入去重+验证模式
4. `merge_and_dedup()` 和 `append_to_file()` 返回结构化 dict（不变）

### config_tool.py

1. `_validate_key()` 中 `sys.exit(1)` → `raise ValueError`
2. CLI 入口捕获 `ValueError` 打印错误信息
3. EnvManager 保留在 tools/ 下，AI agent 通过 import 使用

### verify_ip_domain.py

1. `load_ip_data()` 中 `sys.exit(1)` → `raise FileNotFoundError`
2. `batch_verify()` 新增 `progress_callback` 参数，移除内部 print
3. CLI 入口传入 callback 实现进度显示

### utils/ 框架

```
utils/
├── __init__.py      # 空文件
├── ip_utils.py      # 占位，未来放 IP 相关共享函数
└── file_utils.py    # 占位，未来放文件操作共享函数
```

## 不做的事情

- 不修改 reader.py / writer.py / trace_ip.py
- 不修改 channel/ 或 scripts/
- 不改变项目整体目录结构
