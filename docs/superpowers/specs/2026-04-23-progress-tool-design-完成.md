# Progress 文件管理工具设计

## 背景

`.progress` 文件用于批量查询的断点续查。当 progress 文件丢失、或从外部获取了已有 JSON 数据但没有对应 progress 文件时，重新跑批量查询会造成重复工作。需要一个工具从 JSON 数据反推进度，以及从 progress 中精确删除指定 IP。

## 文件

`tools/progress_tool.py`

## 命令

### generate

从 JSON 数据文件中提取某渠道已有数据的 IP 列表，生成 progress 文件。

```bash
python tools/progress_tool.py generate <json_file> --channel <channel> [-o <output>]
```

**参数**：
- `json_file`：JSON 数据文件路径（如 `data/ip_data.json`）
- `--channel`：渠道名称（如 `fofa`、`aizhan` 等）
- `-o / --output`：输出路径，默认 `<json_file>.<channel>.progress`

**流程**：
1. 用 `IPReader`（from `reader.py`）加载 JSON
2. 调用 `search_ips_by_channel(channel)` 获取含该渠道数据的 IP 列表
3. 将 IP 列表写入 progress 文件（每行一个 IP）
4. 输出报告：JSON 总 IP 数、含该渠道的 IP 数、输出路径

### remove

从指定 progress 文件中删除 IP。

```bash
python tools/progress_tool.py remove <progress_file> [ip1 ip2 ...] [--from-file <file>]
```

**参数**：
- `progress_file`：progress 文件路径
- `ip1 ip2 ...`：要删除的 IP（可选）
- `--from-file`：从文件读取要删除的 IP，每行一个（可选）

两种输入方式可同时使用，合并去重后处理。

**流程**：
1. 读取 progress 文件内容 → `set`
2. 收集要删除的 IP（来自命令行参数 + `--from-file` 文件）
3. 从 set 中移除
4. 将剩余 IP 写回 progress 文件
5. 输出报告：原数量、删除数量、剩余数量

## 复用

- `IPReader` 类（`reader.py`）：加载 JSON、按渠道搜索 IP
- 遵循 `config_tool.py` 的 argparse 子命令风格

## 不包含

- 不做 `--dry-run` 预览模式（操作简单可逆，无必要）
- 不做渠道名枚举校验（progress 是纯文件操作，不需要知道有哪些渠道）
- 不抽取共享模块（当前仅一处复用 `IPReader`，暂不提前抽象）
