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

### 快捷命令

等同于 `--only-phase N`，互斥不可同时使用，也不能与 `--only-phase` 同时使用：

```bash
python -m scenarios.ip_domain_lookup ips.txt --collect-only         # 只执行 Phase 1（域名收集）
python -m scenarios.ip_domain_lookup ips.txt --dns-verify-only      # 只执行 Phase 2（DNS 正向验证）
python -m scenarios.ip_domain_lookup ips.txt --summary-only         # 只执行 Phase 3（汇总报告）
python -m scenarios.ip_domain_lookup ips.txt --generate-report      # 只执行 Phase 4（生成 Word 报告）
```

不确定参数时用 `python -m scenarios.ip_domain_lookup --help`。

## 流水线阶段

| 阶段 | 说明 | 使用渠道 | 输出 |
|------|------|---------|------|
| Phase 1 | 域名收集 | RDNS + 爱站 + 站长之家 + ZoomEye + Fofa Search + SSL 证书（并行） | ip_domain_lookup 渠道写入 JSON |
| Phase 2 | DNS 正向验证 | — | verified_domains + summary 字段写入 JSON |
| Phase 3 | 汇总报告 | — | .domain_lookup_report + .domain_lookup_matched |
| Phase 4 | Word 报告 | docx_builder | .domain_lookup_report.docx |

### 依赖检查

Phase 4（生成 Word 报告）需要 `python-docx` 库。流水线启动时会自动检查：若 `python-docx` 未安装，Phase 4 将报错终止并提示安装命令 `pip install python-docx`。

## 域名提取与去重逻辑

Phase 1 收集各渠道返回的域名时，通过 `defaultdict(list)` 按域名聚合来源，实现多源去重——同一域名来自多个渠道时合并为一条记录，`sources` 字段记录所有来源渠道。各渠道的提取规则如下：

| 渠道 | 提取逻辑 | 过滤规则 |
|------|---------|---------|
| RDNS PTR | 提取 `hostname` 和 `aliases` | 无 |
| 爱站 / 站长之家 | 提取 `domains` 列表中的 `domain` 字段 | 无 |
| ZoomEye | 提取 `data[].domain`，逗号分隔拆分 | 过滤 `*` 开头的通配符域名 |
| FOFA Search | 提取 `domain` 字段；若 `host` 字段存在且域名未被 `domain` 字段覆盖，解析 URL 提取 hostname | 过滤纯 IP 地址、`*` 开头的通配符域名 |
| SSL 证书 | 提取 `domains` 列表（含 Subject CN + SAN） | 过滤 `*` 开头的通配符域名 |

## DNS 验证结果状态

Phase 2 对收集到的域名做 DNS 正向验证，检查域名是否仍解析到原始 IP：

| 状态 | 中文描述 | 说明 |
|------|---------|------|
| matched | 匹配 | 域名仍解析到原始 IP ✅ |
| changed | 变更 | 域名已解析到其他 IP 🔄 |
| unresolved | 无法解析 | DNS 解析失败（域名可能已过期）❌ |
| timeout | 超时 | DNS 解析超时 ⏱️ |
| error | 错误 | 其他错误 ⚠️ |

### DNS 验证 summary 字段

Phase 2 验证完成后，每个 IP 的 `ip_domain_lookup.summary` 字段记录各状态计数：

```json
{
  "matched": 3,
  "changed": 1,
  "unresolved": 0,
  "timeout": 0,
  "error": 0
}
```

## 渠道配置

可通过环境变量控制各采集渠道的启用/禁用：

```bash
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_RDNS_PTR_ENABLED true
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_AIZHAN_ENABLED true
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_CHINAZ_ENABLED true
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_ZOFEYE_ENABLED false  # 禁用
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_FOFA_SEARCH_ENABLED false  # 禁用
python tools/config_tool.py set IP_IP_DOMAIN_LOOKUP_SSL_CERT_ENABLED true
```

运行流水线时会显示已启用/已禁用的渠道状态。如果所有渠道都被禁用，流水线会报错退出。

### ZoomEye API Key 自动禁用机制

ZoomEye 渠道在配置启用（`IP_IP_DOMAIN_LOOKUP_ZOOMEYE_ENABLED=true`）的前提下，还会检查 API Key 是否已配置。若 `IP_ZOOMEYE_API_KEY` 为空或未设置，ZoomEye 渠道会被自动禁用并输出日志提示 `✗ ZoomEye 网络空间测绘: API Key 未配置，已禁用`，不会加入实际查询队列。

## 断点续跑

### 进度文件

Phase 1 和 Phase 2 支持断点续跑，进度文件命名如下：

| 阶段 | 进度文件 | 完成标记文件 |
|------|---------|------------|
| Phase 1 | `{prefix}.domain_lookup_phase1.progress` | `{prefix}.domain_lookup_phase1_done` |
| Phase 2 | `{prefix}.domain_lookup_phase2.progress` | `{prefix}.domain_lookup_phase2_done` |
| Phase 3 | 无 | 无 |
| Phase 4 | 无 | 无 |

- 进度文件记录已处理的 IP 列表（每行一个 IP），用于断点续跑
- 完成标记文件为空文件，仅用于标记阶段已完成
- Phase 3 和 Phase 4 执行速度快，无需进度文件

### is_phase_done 跳过机制

Phase 1 和 Phase 2 在执行前会检查完成标记文件是否存在（`is_phase_done`）。若标记文件已存在，该阶段直接跳过并输出日志 `阶段N已完成，跳过`。这确保了即使不使用 `--from-phase` 参数，重复运行流水线也不会重复执行已完成的阶段。

### 续跑方式

- 使用 `--from-phase N` 跳过已完成阶段（会清除后续阶段的标记文件）
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
| `{name}.domain_lookup_report` | 文本汇总报告（JSON 格式） |
| `{name}.domain_lookup_matched` | DNS 验证通过的 IP-域名对（Tab 分隔，每行格式：`IP\t域名`） |
| `{name}.domain_lookup_report.docx` | Word 分析报告 |
| `{name}.domain_lookup_phase1.progress` | Phase 1 进度文件（已处理 IP 列表） |
| `{name}.domain_lookup_phase2.progress` | Phase 2 进度文件（已处理 IP 列表） |
| `{name}.domain_lookup_phase1_done` | Phase 1 完成标记 |
| `{name}.domain_lookup_phase2_done` | Phase 2 完成标记 |

## Word 报告结构

Phase 4 生成的 Word 报告包含以下 6 个章节：

| 章节 | 标题 | 内容 |
|------|------|------|
| 一 | 报告概述 | 总 IP 数、候选域名数、分析说明 |
| 二 | 域名收集统计 | 各渠道收集域名数量统计表 |
| 三 | DNS 验证统计 | 各验证状态（匹配/变更/无法解析/超时/错误）的数量统计表 |
| 四 | 验证通过映射（按 IP 分表） | 每个 IP 单独列表，展示验证通过的域名 |
| 五 | 未通过验证域名 | 状态为 changed/unresolved/timeout/error 的域名汇总表（含原 IP、域名、验证状态、解析 IP） |
| 六 | IP 域名收集详情 | 所有 IP 的域名反查汇总统计表（候选域名数、匹配、变更、无法解析） |
