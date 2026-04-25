# 辅助工具

当用户需要使用辅助工具时读取此文件。包括 IP 文件处理、进度管理、域名验证、Word 报告生成。

## 决策树

```
用户需要合并/去重/验证 IP 文件 → merge_ip_files.py
用户需要管理 .progress 进度文件 → progress_tool.py
用户需要验证域名是否仍解析到原 IP → verify_ip_domain.py
用户需要生成 Word 报告 → docx_builder.py（通过流水线自动调用）
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

验证 IP 反查到的域名是否仍然解析到原始 IP。此工具可独立于流水线使用。

```bash
python tools/verify_ip_domain.py data/ip_data.json                     # 验证所有渠道域名
python tools/verify_ip_domain.py data/ip_data.json --channel aizhan    # 仅验证爱站渠道
python tools/verify_ip_domain.py data/ip_data.json --dry-run           # 仅验证不写回
python tools/verify_ip_domain.py data/ip_data.json --show-all          # 显示全部结果
python tools/verify_ip_domain.py data/ip_data.json --concurrency 20    # 20线程并发
```

验证结果状态：`matched`（仍指向原 IP）、`changed`（指向其他 IP）、`unresolved`（解析失败）

验证结果默认写回 JSON 文件的 `domain_verify` 字段，使用 `--dry-run` 可只看结果不写入。

## Word 报告生成（docx_builder.py）

这是库模块，不直接命令行运行。被 trace_ip 和 ip_domain_lookup 两个场景的 reporter 调用。

- 需安装 `python-docx`（`pip install python-docx`）
- 未安装时流水线自动跳过报告生成阶段，不影响其他功能
- 排版规范：宋体正文 + 黑体标题 + 三线表 + A4 公文版心
