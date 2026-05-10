# IP 域名反查流水线

当用户需要批量查询 IP 绑定域名并进行 DNS 正向验证时读取此文件。

## 决策树

```
用户说"我有一批 IP 要反查域名"
  → 1. 确认项目名称（IP_IP_DOMAIN_LOOKUP_PROJECT_NAME）
  → 2. 确认运行阶段（完整 / 从某阶段开始 / 只跑某阶段）
  → 3. 确认启用的渠道（6 个可选）
  → 4. 生成运行命令并执行
  → 5. 运行中遇到异常 → 读取 references/troubleshooting.md
```

## 项目名称配置

输出目录为 `data/ip_domain_lookup/{IP_IP_DOMAIN_LOOKUP_PROJECT_NAME}/`。

```bash
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_PROJECT_NAME "report_test"
```

不同项目名互不干扰，各自独立的数据目录。

## 运行命令

```bash
python -m scenarios.ip_domain_lookup ips.txt                       # 完整流水线
python -m scenarios.ip_domain_lookup ips.txt --from-phase 2         # 从阶段2开始
python -m scenarios.ip_domain_lookup ips.txt --only-phase 1         # 只执行域名收集
python -m scenarios.ip_domain_lookup ips.txt --channel-timeout 30   # 单渠道超时30秒
python -m scenarios.ip_domain_lookup ips.txt --dns-timeout 5        # DNS超时5秒
python -m scenarios.ip_domain_lookup ips.txt --dns-concurrency 20   # DNS并发20线程
```

不确定参数时用 `python -m scenarios.ip_domain_lookup --help`。

## 流水线阶段

| 阶段 | 说明 | 使用渠道 | 输出 |
|------|------|---------|------|
| Phase 1 | 域名收集 | RDNS + 爱站 + 站长之家 + ZoomEye + Fofa Search + SSL 证书（并行） | ip_domain_lookup 渠道写入 JSON |
| Phase 2 | DNS 正向验证 | — | verified_domains 字段写入 JSON |
| Phase 3 | 汇总报告 | — | .domain_lookup_report + .domain_lookup_matched |
| Phase 4 | Word 报告 | docx_builder | .domain_lookup_report.docx |

## DNS 验证结果状态

Phase 2 对收集到的域名做 DNS 正向验证，检查域名是否仍解析到原始 IP：

| 状态 | 说明 |
|------|------|
| matched | 域名仍解析到原始 IP ✅ |
| changed | 域名已解析到其他 IP 🔄 |
| unresolved | DNS 解析失败（域名可能已过期）❌ |
| timeout | DNS 解析超时 |
| error | 其他错误 |

## 渠道配置

可通过环境变量控制各采集渠道的启用/禁用：

```bash
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_RDNS_PTR_ENABLED true
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_AIZHAN_ENABLED true
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_CHINAZ_ENABLED true
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_ZOOMEYE_ENABLED false  # 禁用
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_FOFA_SEARCH_ENABLED false  # 禁用
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_SSL_CERT_ENABLED true
```

运行流水线时会显示已启用/已禁用的渠道状态。如果所有渠道都被禁用，流水线会报错退出。

## 断点续跑

每个阶段完成后写入标记文件 `{project_name}.domain_lookup_phase{N}_done`。

- 使用 `--from-phase N` 跳过已完成阶段
- 支持 Ctrl+C 安全中断
- 运行前自动显示断点进度：`发现进度文件: 已处理 124/167 (74.3%)，将从断点继续`

## 任务状态查询

流水线运行时会自动写入 PID 文件，可通过 `status_tool.py` 查看运行状态：

```bash
python tools/status_tool.py ip_domain_lookup              # 查看运行状态、进度、ETA
python tools/status_tool.py cleanup ip_domain_lookup      # 清理残留 PID 文件
```

## 输出文件

所有输出在 `data/ip_domain_lookup/{IP_IP_DOMAIN_LOOKUP_PROJECT_NAME}/` 目录下：

| 文件 | 说明 |
|------|------|
| `{name}.json` | 主数据文件（含域名收集和验证结果） |
| `{name}.domain_lookup_report` | 文本汇总报告 |
| `{name}.domain_lookup_matched` | DNS 验证匹配的域名列表 |
| `{name}.domain_lookup_report.docx` | Word 分析报告 |
| `{name}.domain_lookup_phase{N}_done` | 阶段完成标记 |
