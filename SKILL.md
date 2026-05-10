---
name: ip-info-manager
description: IP 信息管理工具，用于批量采集、存储、查询和导出 IP 地址的多维度情报信息。当用户需要查询 IP 信息、批量处理 IP 列表、导出 IP 数据到 Excel、对 IP 进行情报分析（Fofa/IPInfo/RDNS/Whois/爱站/站长之家/ZoomEye/SSL证书）、管理 IP 数据库、溯源IP处理、IP自动分类、攻击IP分析、IP域名反查、域名DNS验证、溯源优先级分级、攻击IP排序、IP标签打标、威胁情报匹配、IP信誉查询时使用此 skill。即使用户只是提到 "IP 查询"、"IP 信息"、"攻击 IP"、"威胁情报"、"IP 归属"、"IP 反查"、"批量查 IP"、"IP 导出"、"IP 反查域名"、"域名绑定"、"溯源"、"IP 分类"、"云主机识别"、"扫描器识别"、"溯源优先级"、"攻击排序"、"IP标签"、"标签打标"、"IP信誉"、"威胁情报匹配" 等关键词，也应触发此 skill。
---

# IP Info Manager

本 skill 封装了一套完整的 IP 信息管理工作流。遇到用户请求时，根据下方功能路由表读取对应的 references/ 文件获取详细操作步骤。

**核心原则：所有操作都应通过项目提供的工具（writer.py / reader.py / config_tool.py 等）完成，不要直接编辑 .env 文件，不要修改源代码。**

## 功能路由表

根据用户的意图，读取对应的 references/ 文件获取决策树和完整命令：

| 用户意图 | 参考文档 | 关键工具 |
|---------|---------|---------|
| 首次安装、环境搭建、依赖安装、凭证配置 | references/setup.md | tools/config_tool.py |
| 查看、添加、删除、搜索、导出 IP 数据 | references/data-management.md | writer.py, reader.py, exporter.py |
| 查询单个 IP 的渠道情报（Fofa/IPInfo/RDNS 等） | references/channel-query.md | channel/*.py |
| 批量查询一批 IP（某个渠道） | references/batch-query.md | scripts/batch_*.py |
| 溯源 IP 自动化处理（采集→标签打标→分类→深度查询→溯源优先级分级→报告→AI研判） | references/trace-ip-pipeline.md | scenarios/trace_ip/ |
| IP 域名反查 + DNS 正向验证 | references/ip-domain-lookup-pipeline.md | scenarios/ip_domain_lookup/ |
| IP 文件合并/去重、进度管理、域名验证 | references/tools.md | tools/*.py |
| 查看任务运行状态、进度、ETA | references/tools.md | tools/status_tool.py |
| 更新 API Key / Cookie、调整查询间隔 | references/config.md | tools/config_tool.py |
| 采集异常、凭证失效、限频报错 | references/troubleshooting.md | — |

## 项目结构

```
ip_info_manager/
├── .env / .env.example       # 环境变量（通过 config_tool.py 管理）
├── config.py                 # 配置管理（Pydantic Settings）
├── writer.py                 # IP 数据写入
├── reader.py                 # IP 数据读取（含 Excel 导出）
├── channel/                  # 9 个数据采集渠道
├── scripts/                  # 10 个批量查询脚本
├── scenarios/trace_ip/       # 溯源 IP 流水线（5 阶段 + 标签打标）
├── scenarios/ip_domain_lookup/ # IP 域名反查流水线（4 阶段）
├── tools/                    # 辅助工具（config/merge/progress/verify/ai_analysis/docx_builder/status_tool）
├── utils/                    # 通用工具（file_utils/ip_utils/pid_manager）
└── data/                     # 数据存储根目录
```

## 数据存储路径

**所有命令必须在项目根目录 `ip_info_manager/` 下执行**，否则会找不到模块。AI 启动命令时务必设置 `cwd` 为项目根目录。

- **channel/batch 通用数据**：`data/{IP_STORAGE_DIR}/{IP_STORAGE_NAME}.json`
- **溯源 IP 场景数据**：`data/trace_ip/{IP_TRACE_IP_PROJECT_NAME}/`
- **IP 域名反查数据**：`data/ip_domain_lookup/{IP_IP_DOMAIN_LOOKUP_PROJECT_NAME}/`

## 快捷命令

流水线支持语义化参数别名，比 `--only-phase N` 更直观：

| 快捷命令 | 等同于 | 说明 |
|---------|--------|------|
| `--collect-only` | `--only-phase 1` | 只执行基础采集 |
| `--classify-only` | `--only-phase 2` | 只执行分类过滤（仅溯源流水线） |
| `--deep-query-only` | `--only-phase 3` | 只执行深度查询（仅溯源流水线） |
| `--summary-only` | `--only-phase 4` | 只执行汇总输出 |
| `--generate-report` | `--only-phase 5` | 只生成报告（Word + Excel） |

## AI 异步执行模式

长时间任务（溯源流水线、域名反查、批量查询）执行时间可能很长，AI 应使用异步模式管理：

### 推荐流程

1. **启动任务**：用 `blocking=false` 启动命令，不等待完成
2. **查看进度**：用 `python tools/status_tool.py trace_ip` 查看运行状态、进度和 ETA
3. **等待完成**：根据 ETA 定期查看状态，直到任务完成
4. **继续操作**：任务完成后继续后续步骤

### 状态查询命令

```bash
python tools/status_tool.py trace_ip              # 溯源流水线
python tools/status_tool.py ip_domain_lookup      # 域名反查
python tools/status_tool.py batch                 # 批量查询
python tools/status_tool.py cleanup trace_ip      # 清理残留 PID
```

### 状态说明

| 状态 | 含义 |
|------|------|
| 🟢 运行中 | 任务正在执行，心跳正常 |
| ⏳ 疑似卡死 | 进程存在但心跳超过 120 秒未更新 |
| ⚠️ 异常终止 | PID 文件存在但进程已不存在，可断点续跑 |
| ⬜ 未运行 | 任务未启动或已完成 |
