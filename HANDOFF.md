# Handoff 文档 — ip_info_manager 重构项目

> 生成时间: 2026-05-26（第十二次更新）
> 项目路径: `E:\12_trae_skills\ip_info_manager`

---

## 一、已完成工作总览

### 1. 存储层 ✅
- `src/ip_info/store/` — IPDataWriter/IPDataReader/DomainCache 协议 + JSON/InMemory 实现
- **DomainCache 具体实现未写**（计划用 SQLite，目前只有 InMemoryDomainCache）

### 2. 渠道层 ✅
- `src/ip_info/channel/` — BaseChannelAdapter + 10 个渠道 + ChannelConfig 配置系统
- fofa key 已更新为 `d6741fd4f6cae5736ea8b640ee242f51`（验证可用）

### 3. 通用工具层 ✅
- `src/ip_info/utils/` — `load_ips()`（含 # 注释行过滤）+ ProgressTracker 协议 + 实现

### 4. 批量查询层 ✅
- BaseBatchQuery（串行）+ run_concurrent（并发）+ BatchRunner Protocol
- 13 个 batch CLI 脚本（含 batch_dns_verify）

### 5. Processors 层 ✅
- **tagger**: BatchTagger（59 测试），流式双指针匹配，35 个威胁情报源
- **classifier**: BatchClassifier（78 测试），7 类规则，5 种匹配，全量重处理
- **dns_verify**: BatchDnsVerify（48 测试），过期仅提示/--force N/DomainCache Protocol/并发安全

### 6. Pipeline 编排框架 ✅
- `src/ip_info/pipeline/phase.py` — Phase Protocol + PhaseResult
- `src/ip_info/pipeline/pipeline.py` — Pipeline 类 + PipelineResult
- 15 个测试，支持 register/run/from_phase/only_phase/skip_phases/失败停止

### 7. 测试现状
- **637 个测试全部通过**
- 运行命令：`python -m pytest tests/unit/ -q`

---

## 二、当前任务：实现 Phase 1-5 具体阶段逻辑

### Spec 状态
- **已创建**：`.trae/specs/implement-pipeline-phases/` — spec.md / tasks.md / checklist.md
- **待审批**：用户尚未确认 spec

### Phase 1-5 设计概要

| Phase | 类名 | 内部逻辑 | 阶段内执行方式 |
|-------|------|---------|--------------|
| 1 | BasicCollectPhase | ipinfo_api + rdns_ptr | ThreadPoolExecutor 并行 BaseBatchQuery/run_concurrent |
| 2 | ClassifyFilterPhase | BatchClassifier → BatchTagger → need_deep_query 过滤 | 顺序执行，输出 filtered_ips |
| 3 | DeepQueryPhase | aizhan + chinaz + fofa_host | ThreadPoolExecutor 并行 BaseBatchQuery |
| 4 | DnsVerifyPhase | 委托 BatchDnsVerify | 单处理器批量 |
| 5 | PortScanPhase | 委托 run_concurrent | 并发查询 |

### 关键设计决策

1. **Phase 构造函数接收渠道实例**：Phase 不负责创建渠道，由调用方（CLI 脚本）注入
2. **阶段间数据传递**：Phase 2 的 `PhaseResult.data["filtered_ips"]` 传递给 Phase 3-5
3. **过滤逻辑**：`need_deep_query == True` 的 IP 保留（cloud_provider/residential/other），过滤掉 invalid_rdns/cdn/crawler_scanner
4. **测试策略**：mock 到存储层，渠道使用 MagicMock 模拟
5. **SqliteDomainCache**：threading.local + WAL 模式 + INSERT OR REPLACE

### 分类规则（need_deep_query 映射）

| 分类 | need_deep_query | Phase 2 过滤 |
|------|----------------|-------------|
| cloud_provider | True | 保留 |
| residential | True | 保留 |
| other（默认） | True | 保留 |
| invalid_rdns | False | 过滤 |
| cdn | False | 过滤 |
| crawler_scanner | False | 过滤 |

---

## 三、架构速览

```
src/ip_info/
  ├── utils/                      # 通用工具 ✅
  ├── store/                      # 存储层 ✅ (DomainCache SQLite 实现待写)
  ├── channel/                    # 渠道层 ✅ (10 个渠道)
  ├── processors/                 # 非渠道批量处理器 ✅
  │   ├── tagger/                 # 标签打标 ✅
  │   ├── classifier/             # 自动分类 ✅
  │   └── dns_verify/             # DNS 域名验证 ✅
  ├── batch/                      # 批量查询层 ✅ (13 个脚本)
  └── pipeline/                   # 流水线层
      ├── phase.py                # Phase Protocol + PhaseResult ✅
      ├── pipeline.py             # Pipeline 编排器 ✅
      └── phases/                 # 具体阶段实现（待实现）
          ├── __init__.py
          ├── phase1_basic.py     # BasicCollectPhase
          ├── phase2_classify.py  # ClassifyFilterPhase
          ├── phase3_deep.py      # DeepQueryPhase
          ├── phase4_dns.py       # DnsVerifyPhase
          └── phase5_portscan.py  # PortScanPhase
```

---

## 四、关键文件索引

| 文件 | 说明 |
|------|------|
| `.trae/specs/implement-pipeline-phases/spec.md` | Phase 1-5 详细 spec（待审批） |
| `.trae/specs/implement-pipeline-phases/tasks.md` | 7 个任务分解 |
| `.trae/specs/implement-pipeline-phases/checklist.md` | 26 个验证点 |
| `src/ip_info/pipeline/phase.py` | Phase Protocol + PhaseResult |
| `src/ip_info/pipeline/pipeline.py` | Pipeline 编排器 |
| `src/ip_info/store/protocols.py` | IPDataWriter/IPDataReader/DomainCache 协议 |
| `src/ip_info/store/in_memory.py` | InMemoryIPWriter/InMemoryIPReader/InMemoryDomainCache |
| `src/ip_info/batch/core/query.py` | BaseBatchQuery + BatchResult |
| `src/ip_info/batch/core/concurrent.py` | run_concurrent 并发查询 |
| `src/ip_info/processors/classifier/runner.py` | BatchClassifier |
| `src/ip_info/processors/tagger/runner.py` | BatchTagger |
| `src/ip_info/processors/dns_verify/runner.py` | BatchDnsVerify |
| `config/classifier/builtin_rules.json` | 分类规则（7 类，need_deep_query 映射） |
| `legacy/scenarios/trace_ip/pipeline.py` | 遗留 7 阶段流水线（迁移参考） |

---

## 五、提交记录

```
0f91417 feat(pipeline): 实现 Pipeline 编排框架 (TDD)
3fc8456 docs: 更新 HANDOFF.md
7bb8e6f fix(dns_verify): 无渠道数据时 WARNING 告警
4d6d5aa test(dns_verify): 强化结果导向测试
198dfab test(dns_verify): 添加 DomainCache 并发安全测试
8cd04a4 fix(store): InMemoryDomainCache 添加 threading.Lock
72b4771 refactor(dns_verify): 过期仅提示不覆盖 + --force N + DomainCache Protocol
bdccd42 feat(dns_verify): 迁移 DNS 域名验证模块
57f9d1c feat(classifier): 迁移 IP 自动分类模块
3bbae48 feat(tagger): 迁移 IP 标签打标模块
```

---

## 六、Git 提交规范

- 中文翻译的 conventional commit 格式
- 按逻辑分组提交，每个提交只做一件事
- PowerShell 用分号 `;` 分隔命令，`-m` 多次传 body

---

## 七、建议的下一步技能

- **tdd**: Phase 1-5 实现时使用 TDD
- **brainstorming**: DomainCache SQLite 实现设计（如需进一步讨论）
