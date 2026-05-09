# 溯源 IP 处理流水线

当用户有一批 IP 需要溯源处理（自动采集、分类、深度查询、报告）时读取此文件。

## 决策树

```
用户说"我有一批 IP 要溯源处理"
  → 1. 确认项目名称（IP_TRACE_IP_PROJECT_NAME）
  → 2. 确认运行阶段（完整 / 从某阶段开始 / 只跑某阶段）
  → 3. 确认启用的渠道
  → 4. 生成运行命令并执行
  → 5. 运行中遇到异常 → 读取 references/troubleshooting.md
  → 6. 流水线完成后如需 AI 研判 → 见下方"AI 研判流程"

用户说"我需要补充溯源一些 IP"
  → 确认当前项目名称
  → 验证新 IP 文件（merge_ip_files.py）
  → 查看已有数据判断哪些 IP 是新的
  → 将新 IP 追加到原文件或单独运行，使用 --from-phase 跳过已完成阶段
```

## 项目名称配置

输出目录为 `data/trace_ip/{IP_TRACE_IP_PROJECT_NAME}/`。

```bash
python tools/config_tool.py set IP_TRACE_IP_PROJECT_NAME "0424攻击IP"
```

不同项目名互不干扰，各自独立的数据目录。

## 运行命令

```bash
python -m scenarios.trace_ip ips.txt                       # 完整流水线
python -m scenarios.trace_ip ips.txt --no-deep-query       # 只采集+分类，不深度查询
python -m scenarios.trace_ip ips.txt --from-phase 2         # 从阶段2开始
python -m scenarios.trace_ip ips.txt --only-phase 2         # 只执行分类阶段
python -m scenarios.trace_ip ips.txt --no-custom-rules      # 不加载外部规则
python -m scenarios.trace_ip ips.txt --custom-rules my.json # 使用指定规则文件
python -m scenarios.trace_ip ips.txt --channel-timeout 30   # 单渠道超时30秒
```

不确定参数时用 `python -m scenarios.trace_ip --help`。

## 流水线阶段

| 阶段 | 说明 | 使用渠道 | 输出 |
|------|------|---------|------|
| Phase 1 | 基础情报采集 | IPInfo + RDNS PTR（并行） | 数据写入 JSON |
| Phase 2 | 自动分类过滤 | 内置规则 + 自定义规则 | trace_classify 渠道 + .trace_filtered_ips + .unclassified_rdns + .unclassified_no_info |
| Phase 3 | 深度查询 | 爱站 + 站长之家 + Fofa Host（并行） | 数据写入 JSON |
| Phase 4 | 汇总报告 | — | .trace_report |
| Phase 5 | Word 报告 | docx_builder | .trace_report.docx（含溯源优先级分级） |

## Word 报告结构

Phase 5 生成的 Word 报告包含以下章节：

| 章节 | 内容 |
|------|------|
| 一、报告概述 | 分析目标、分析方法（多渠道关联分析）、数据源查询统计 |
| 二、处理概览 | 基础情报采集统计、自动分类统计、深度查询统计、待确认IP、价值分级统计 |
| 三、溯源优先级 | 决策树 P1-P4 分级 + IP 列表 + 动态溯源路径建议 |
| 四、AI研判结果 | 通过 ai_analysis 工具写入的研判结果（按 IP 展示详情） |
| 五、未识别RDNS记录 | 未匹配任何分类规则的 RDNS 主机名列表 |

## 溯源优先级决策树

Word 报告的第三章基于决策树模型对深度查询 IP 进行优先级分级，帮助分析师快速定位高价值溯源目标。

**判定维度（按优先级从高到低）：**

1. **是否有反查域名**（最直接的溯源线索，可通过 ICP 备案/WHOIS 定位持有者）
2. **是否有已知端口信息**（FOFA 等搜索引擎探测到的端口/服务，可排查服务泄露信息）
3. **是否为国内IP**（管辖权内可操作，同等条件下优先级更高）

**分级标准：**

| 级别 | 判定条件 | 溯源路径建议 |
|------|---------|------------|
| P1 核心溯源 | 有反查域名 + 国内IP | ICP备案查询域名持有者实名信息 |
| P2 重点溯源 | 有反查域名（国外），或无域名但有端口信息（国内） | WHOIS查询域名注册信息；排查端口服务泄露信息 |
| P3 辅助溯源 | 无域名但有端口信息（国外），或仅国内IP | 端口服务辅助分析；公开信息检索IP历史行为 |
| P4 暂缓 | 无域名、无端口、国外IP | 信息不足，建议持续监控 |

**同级别排序：** 按信息丰富度（域名数 + 端口数 + 分类权重）降序排列。

**价值分级：** 深度查询 IP 还会按数据可用性进行价值分级：
- 高价值：有深度查询数据（爱站/站长/Fofa）且为国内IP
- 中价值：有深度查询数据但为国外IP
- 低价值：所有深度查询渠道均无有效数据

**动态溯源路径：** 每个 IP 根据其实际数据情况生成个性化溯源建议（ICP备案/WHOIS查询、端口服务排查、公开信息检索）。

## 分类类别

| 类别 | 说明 | 是否深度查询 |
|------|------|-------------|
| cloud_provider | 云服务商（AWS/阿里云/腾讯云等） | ✅ |
| cdn | CDN/WAF 节点 | ❌ |
| crawler_scanner | 爬虫/扫描器 | ❌ |
| residential | 家用宽带 | ✅ |
| other | 未识别（需人工确认） | ✅ |

## 渠道配置

可通过 `.env` 环境变量控制各阶段渠道的启用/禁用：

```bash
python tools/config_tool.py set IP_TRACE_IP_PHASE1_IPINFO_ENABLED true
python tools/config_tool.py set IP_TRACE_IP_PHASE1_RDNS_PTR_ENABLED true
python tools/config_tool.py set IP_TRACE_IP_PHASE3_AIZHAN_ENABLED true
python tools/config_tool.py set IP_TRACE_IP_PHASE3_CHINAZ_ENABLED true
python tools/config_tool.py set IP_TRACE_IP_PHASE3_FOFA_HOST_ENABLED false  # 禁用
```

运行流水线时会显示每个渠道的启用/禁用状态。如果某阶段所有渠道都被禁用，会跳过或报错。

## 分类规则管理

- **内置规则**：`scenarios/trace_ip/classifiers/builtin_rules.json`（稳定，勿随意修改）
- **外部规则**：`scenarios/trace_ip/classifiers/custom_rules.json`（试运行，验证后合并到内置）

规则文件格式：

```json
{
  "category_key": {
    "label": "显示名称",
    "description": "类别说明",
    "need_deep_query": true,
    "patterns": [
      { "field": "rdns_ptr.hostname", "match": ".amazonaws.com", "type": "suffix", "note": "AWS Amazon 云服务" },
      { "field": "ipinfo_api.as_name", "match": "Amazon", "type": "contains", "note": "AWS Amazon 云服务" }
    ]
  }
}
```

- 匹配类型：`suffix`（后缀）、`contains`（包含）、`prefix`（前缀）、`exact`（精确）
- `note`（可选）：规则说明，分类结果中会在 `matched_by` 里输出此字段，便于分析人员快速理解匹配到的域名/ASN 含义

未识别的 RDNS 记录输出到 `.unclassified_rdns`，信息不足的 IP 输出到 `.unclassified_no_info`。

## 断点续跑

每个阶段完成后写入标记文件 `{project_name}.trace_phase{N}_done`。

- 使用 `--from-phase N` 跳过已完成阶段
- 支持 Ctrl+C 安全中断，自动保存进度
- 不同项目名互不干扰

## AI 研判流程

流水线完成后，对分类为 `other`、`cloud_provider`、`residential` 的 IP 可进行 AI 研判。

### 步骤 1：查看待研判数量

```bash
python tools/ai_analysis.py count
python tools/ai_analysis.py count --categories other
python tools/ai_analysis.py count --categories other,cloud_provider
```

### 步骤 2：批量获取待研判数据

```bash
python tools/ai_analysis.py batch
python tools/ai_analysis.py batch --size 20 --offset 10
python tools/ai_analysis.py batch --categories other,cloud_provider
```

### 步骤 3：分析并写入研判结果

分析完成后通过 writer.py 写入：

```bash
python writer.py add "<IP>" ai_analysis severity="高" action="保留" note="疑似攻击者VPS"
```

研判结果会自动展示在 Word 报告的 AI 研判章节中。

### 步骤 4：重新生成报告（可选）

写入研判结果后可重新运行报告阶段：

```bash
python -m scenarios.trace_ip ips.txt --only-phase 4
```

## 输出文件

所有输出在 `data/trace_ip/{IP_TRACE_IP_PROJECT_NAME}/` 目录下：

| 文件 | 说明 |
|------|------|
| `{name}.json` | 主数据文件 |
| `{name}.trace_filtered_ips` | 需要深度查询的 IP 列表 |
| `{name}.unclassified_rdns` | 未识别的 RDNS 记录 |
| `{name}.unclassified_no_info` | 信息不足的 IP |
| `{name}.trace_report` | 文本汇总报告 |
| `{name}.trace_report.docx` | Word 分析报告 |
| `{name}.trace_phase{N}_done` | 阶段完成标记 |
