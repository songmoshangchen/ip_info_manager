# 辅助工具

当用户需要使用辅助工具时读取此文件。包括 IP 文件处理、进度管理、域名验证、AI 研判、Word 报告生成。

## 决策树

```
用户需要合并/去重/验证 IP 文件 → merge_ip_files.py
用户需要管理 .progress 进度文件 → progress_tool.py
用户需要验证域名是否仍解析到原 IP → verify_ip_domain.py
用户需要 AI 研判辅助（筛选待研判 IP） → ai_analysis.py
用户需要生成 Word 报告 → docx_builder.py（通过流水线自动调用）
用户需要查看任务运行状态/进度/ETA → status_tool.py
用户需要清理残留 PID 文件 → status_tool.py cleanup
```

## IP 文件合并/去重/验证（merge_ip_files.py）

### 单文件去重验证

```bash
python tools/merge_ip_files.py ips.txt
python tools/merge_ip_files.py ips.txt --show-invalid  # 显示被排除的无效 IP
```

### 多文件合并去重

```bash
python tools/merge_ip_files.py file1.txt file2.txt file3.txt -o merged.txt
```

### 追加模式

将来源文件中不重复的有效 IP 追加到目标文件：

```bash
python tools/merge_ip_files.py base.txt source1.txt source2.txt -a
```

支持 IPv4 和 IPv6 格式验证。

## 进度文件管理（progress_tool.py）

### 从 JSON 生成 progress 文件

将已有渠道数据的 IP 标记为已完成（适用于重新跑批量脚本时跳过已有数据）：

```bash
python tools/progress_tool.py generate data/ip_data.json --channel fofa_host
python tools/progress_tool.py generate data/ip_data.json --channel fofa_host -o custom.progress
```

### 删除指定 IP 的进度记录

使指定 IP 可以重新查询：

```bash
python tools/progress_tool.py remove data/ip_data.fofa_host.progress 1.2.3.4 5.6.7.8
python tools/progress_tool.py remove data/ip_data.fofa_host.progress --from-file ips.txt
```

## IP-域名映射验证（verify_ip_domain.py）

验证 IP 反查到的域名是否仍然解析到原始 IP。此工具可独立于流水线使用，也可在溯源流水线 Phase 3 中自动调用。

```bash
python tools/verify_ip_domain.py data/ip_data.json                     # 验证所有渠道域名
python tools/verify_ip_domain.py data/ip_data.json --channel aizhan    # 仅验证爱站渠道
python tools/verify_ip_domain.py data/ip_data.json --dry-run           # 仅验证不写回
python tools/verify_ip_domain.py data/ip_data.json --show-all          # 显示全部结果
python tools/verify_ip_domain.py data/ip_data.json --concurrency 20    # 20线程并发
```

验证结果状态：`matched`（仍指向原 IP）、`changed`（指向其他 IP）、`unresolved`（解析失败）

验证结果默认写回 JSON 文件的 `domain_verify` 字段，使用 `--dry-run` 可只看结果不写入。

DNS 验证核心逻辑位于 `utils/dns_verify.py` 共享模块，溯源流水线和域名反查流水线共用。

## 任务状态查询（status_tool.py）

查看流水线或批量查询任务的运行状态、进度和预计剩余时间（ETA）。

### 查看溯源流水线状态

```bash
python tools/status_tool.py trace_ip
```

### 查看 IP 域名反查状态

```bash
python tools/status_tool.py ip_domain_lookup
```

### 查看批量查询状态

```bash
python tools/status_tool.py batch
```

### 清理残留 PID 文件

任务异常终止后，PID 文件可能残留。清理后可正常重新启动：

```bash
python tools/status_tool.py cleanup trace_ip
python tools/status_tool.py cleanup ip_domain_lookup
python tools/status_tool.py cleanup batch
```

### 状态说明

流水线共 7 个阶段（Phase 1-7），status_tool 会显示当前执行到的阶段及进度。

| 状态 | 含义 |
|------|------|
| 🟢 运行中 | 任务正在执行，心跳正常 |
| ⏳ 疑似卡死 | 进程存在但心跳超过 120 秒未更新 |
| ⚠️ 异常终止 | PID 文件存在但进程已不存在 |
| ⬜ 未运行 | 未发现 PID 文件，任务未启动或已完成 |

## Excel 报告生成（excel_exporter.py）

这是库模块，不直接命令行运行。被 trace_ip 场景的 pipeline 在 Phase 5 自动调用。

- 需安装 `openpyxl`（`pip install openpyxl`）
- 未安装时流水线自动跳过 Excel 生成，不影响 Word 报告和其他功能
- 生成 P1-P4 四个 sheet，含自动筛选、冻结首行、自动列宽

## Word 报告生成（docx_builder.py）

这是库模块，不直接命令行运行。被 trace_ip 和 ip_domain_lookup 两个场景的 reporter 调用。

- 需安装 `python-docx`（`pip install python-docx`）
- Phase 5 必需依赖，未安装时报错退出
- 排版规范：宋体正文 + 黑体标题 + 三线表 + A4 公文版心

## AI 研判辅助（ai_analysis.py）

从溯源 IP 数据中筛选待 AI 研判的 IP（按分类过滤：other/cloud_provider/residential），批量输出供人工或 AI 分析。研判结果通过 `writer.py` 写入后，Word 报告会自动展示 AI 研判结果章节。

### 查看待研判数量

```bash
python tools/ai_analysis.py count
python tools/ai_analysis.py count --categories other
python tools/ai_analysis.py count --categories other,cloud_provider
```

### 批量获取待研判数据

```bash
python tools/ai_analysis.py batch
python tools/ai_analysis.py batch --size 20 --offset 10
python tools/ai_analysis.py batch --categories other,cloud_provider
```

### 写入研判结果

分析完成后通过 writer.py 写入：

```bash
python writer.py add "<IP>" ai_analysis net_type="阿里云ECS" trace_value="高" action="保留" note="疑似攻击者VPS"
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--size` | 每批读取数量（默认 10） |
| `--offset` | 偏移量（默认 0） |
| `--categories` | 筛选分类，逗号分隔（默认 other,cloud_provider,residential） |
