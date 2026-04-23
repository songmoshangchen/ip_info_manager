# IP 域名反查场景设计（Plan 1：现有渠道）

## 概述

场景名称：`ip_domain_lookup`

输入一批 IP，通过现有渠道收集候选域名，经 DNS 正向验证确认映射有效性，输出文本报告 + JSON 数据。

公司归属确认暂不实现，后续作为独立需求补充。

## 目录结构

```
scenarios/
└── ip_domain_lookup/
    ├── __init__.py              # 导出核心类
    ├── ip_domain_lookup.py      # CLI 入口（argparse）
    ├── pipeline.py              # 核心流水线（3 阶段）
    ├── dns_validator.py         # DNS 正向验证器（复用 verify_ip_domain 逻辑）
    ├── reporter.py              # 报告生成器（继承 BaseTraceReporter）
    └── progress.py              # 从 trace_ip.progress 导入共享类
```

## 三阶段流水线

### Phase 1：域名收集

并行调用现有渠道，为每个 IP 收集候选域名列表：

| 渠道 | 函数 | 说明 |
|------|------|------|
| RDNS PTR | `channel.rdns_ptr.fetch_channel` | 反向 DNS 解析获取 hostname |
| 爱站网 | `channel.aizhan.fetch_channel` | IP 反查域名 |
| 站长之家 | `channel.chinaz.fetch_channel` | IP 反查域名 |

域名提取逻辑：
- RDNS PTR：取 `hostname` 字段 + `aliases` 列表中的域名
- 爱站/站长：取 `domains` 列表中每个条目的 `domain` 字段
- 去重：同一 IP 内按域名去重，保留来源信息

存储格式（写入 JSON 的 `ip_domain_lookup` 字段）：
```json
{
  "ip_domain_lookup": {
    "collect_time": "2026-04-23T10:00:00",
    "candidates": [
      {"domain": "example.com", "sources": ["aizhan", "chinaz"]},
      {"domain": "api.example.com", "sources": ["rdns_ptr"]}
    ],
    "candidate_count": 2
  }
}
```

断点续跑：支持，通过 `ProgressManager` 记录已处理 IP。

### Phase 2：DNS 正向验证

对 Phase 1 收集的候选域名逐个做 DNS A 记录查询，验证域名是否指向目标 IP。

验证逻辑（复用 `tools/verify_ip_domain.py` 的核心函数）：
- `resolve_domain(domain, timeout)` → 返回域名解析到的 IP 列表
- 状态判定：
  - `matched`：域名解析结果包含目标 IP ✅
  - `changed`：域名解析到其他 IP（改绑）🔄
  - `unresolved`：域名无法解析（过期/注销）❌
  - `timeout`：DNS 查询超时 ⏱️

验证结果追加到 `ip_domain_lookup` 字段：
```json
{
  "ip_domain_lookup": {
    "collect_time": "...",
    "candidates": [...],
    "candidate_count": 2,
    "verify_time": "2026-04-23T10:05:00",
    "verified_domains": [
      {
        "domain": "example.com",
        "sources": ["aizhan", "chinaz"],
        "status": "matched",
        "resolved_ips": ["1.2.3.4"]
      },
      {
        "domain": "api.example.com",
        "sources": ["rdns_ptr"],
        "status": "changed",
        "resolved_ips": ["5.6.7.8"]
      }
    ],
    "summary": {
      "matched": 1,
      "changed": 1,
      "unresolved": 0,
      "timeout": 0
    }
  }
}
```

断点续跑：支持，通过 `ProgressManager` 记录已验证 IP。

### Phase 3：汇总报告

生成文本报告（日志输出）+ JSON 报告文件。

文本报告内容：
- 输入文件、总 IP 数
- 域名收集统计（每个渠道贡献域名数）
- DNS 验证统计（matched/changed/unresolved/timeout）
- 验证通过的域名清单（IP → 域名映射表）

JSON 报告文件：`{prefix}.domain_lookup_report`

报告模块保持简洁，继承 `BaseTraceReporter`，实现 `TextDomainLookupReporter`。

## 共享基础设施

从 `scenarios.trace_ip.progress` 导入，不重复实现：
- `ProgressManager`：进度文件 + 阶段标记文件管理
- `BatchIPWriter`：批量 JSON 写入

`dns_validator.py` 复用 `tools/verify_ip_domain.py` 的核心验证逻辑（`resolve_domain`、`verify_one`），通过 import 调用，不重复实现。

## CLI 参数

```
python -m scenarios.ip_domain_lookup.ip_domain_lookup <ip_file> [选项]

阶段控制：
  --from-phase {1,2,3}     从指定阶段开始
  --only-phase {1,2,3}     只执行指定阶段

超时控制：
  --channel-timeout SECS   单渠道查询超时（0=不限）
  --dns-timeout SECS       DNS 解析超时（默认 3s）
  --dns-concurrency N      DNS 并发线程数（默认 10）
```

## 数据流

```
IP 文件
  │
  ▼
Phase 1: 并行查询（RDNS + 爱站 + 站长）
  │  → 收集候选域名
  │  → 写入 JSON（ip_domain_lookup.candidates）
  │  → ProgressManager 记录进度
  ▼
Phase 2: DNS 正向验证
  │  → 读取 Phase 1 结果
  │  → socket.gethostbyname_ex() 逐域名验证
  │  → 更新 JSON（ip_domain_lookup.verified_domains + summary）
  │  → ProgressManager 记录进度
  ▼
Phase 3: 汇总报告
  │  → 日志输出统计
  │  → 保存 JSON 报告文件
  ▼
完成
```

## 错误处理

- 渠道查询失败：记录 `raw_error`，不影响其他渠道
- DNS 验证超时：标记 `timeout`，不阻塞后续域名
- JSON 文件损坏：`IPReader`/`IPWriter` 已有处理逻辑
- 用户中断（Ctrl+C）：flush 进度 + 批量写入，支持 `--from-phase` 续跑

## 后续扩展点

1. **新增渠道**（Plan 2）：Fofa IP 查询、ZoomEye、SSL 证书 → 实现后加入 Phase 1 渠道列表
2. **公司归属**：利用 IPInfo/Whois 数据，或 ICP 备案查询 → 可作为 Phase 4
3. **报告格式**：后续可加 Excel 导出或 kimi-docx 报告
