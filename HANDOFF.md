# Handoff 文档 — ip_info_manager 重构项目

> 生成时间: 2026-05-25（第十次更新）
> 项目路径: `E:\12_trae_skills\ip_info_manager`

---

## 一、已完成工作总览

### 1. 存储层 ✅
- `src/ip_info/store/` — IPDataWriter/IPDataReader/DomainCache 协议 + JSON/InMemory 实现

### 2. 渠道层 ✅
- `src/ip_info/channel/` — BaseChannelAdapter + 10 个渠道 + ChannelConfig 配置系统
- fofa key 已更新为 `d6741fd4f6cae5736ea8b640ee242f51`（验证可用）

### 3. 通用工具层 ✅
- `src/ip_info/utils/` — `load_ips()`（含 # 注释行过滤）+ ProgressTracker 协议 + 实现

### 4. 批量查询层 ✅
- BaseBatchQuery（串行）+ run_concurrent（并发）+ BatchRunner Protocol
- 12 个 batch CLI 脚本

### 5. Processors 层 ✅

#### 5a. IP 标签打标 ✅
- `src/ip_info/processors/tagger/` — matcher.py + manifest.py + runner.py
- BatchTagger 实现 BatchRunner Protocol
- 59 个测试，config/ip_tagger/ 含 35 个威胁情报源

#### 5b. IP 自动分类 ✅
- `src/ip_info/processors/classifier/` — rules.py + engine.py + runner.py
- BatchClassifier 实现 BatchRunner Protocol
- 78 个测试，7 个分类类别，5 种匹配类型
- **不依赖 tagger**，只依赖 RDNS + ipinfo 查询结果

#### 5c. DNS 域名验证 ✅
- `src/ip_info/processors/dns_verify/` — verifier.py + extractor.py + runner.py
- BatchDnsVerify 实现 BatchRunner Protocol
- 48 个测试（含 3 个并发安全测试）
- **过期策略**：默认仅 WARNING 提示，不自动覆盖
- **--force N**：重新验证 N 天前的数据（0=全量）
- **DomainCache Protocol**：存储层域名缓存接口（get/set + threading.Lock）
- **日志分级**：无渠道数据→WARNING，有渠道但无域名→DEBUG

### 6. 测试现状

- **622 个测试全部通过**
- 运行命令：`python -m pytest tests/unit/ -q`
- pre-commit hooks：ruff-format + ruff + pytest(unit/store)

---

## 二、当前任务：IP 溯源工作流（Pipeline 编排层）

### Legacy 7 阶段流水线参考

| 阶段 | 功能 | 新架构对应 |
|------|------|-----------|
| Phase 1 | 基础情报采集 | batch_ipinfo_api + batch_rdns_ptr |
| Phase 2 | 分类 + 标签 + IP 过滤 | BatchClassifier + BatchTagger + 过滤逻辑 |
| Phase 3 | 深度查询（仅过滤后 IP） | batch_aizhan + batch_chinaz + batch_fofa_host |
| Phase 4 | DNS 域名验证 | BatchDnsVerify |
| Phase 5 | 端口扫描 | batch_nmap |
| Phase 6 | 汇总输出 | 待实现 |
| Phase 7 | 生成报告 | 待实现 |

### 已就绪的组件

所有 Phase 1-5 的底层组件已就绪：
- 10 个渠道适配器 + 12 个 batch 脚本
- 3 个 processors（tagger/classifier/dns_verify）
- 存储层（IPDataWriter/IPDataReader/DomainCache）
- 进度管理（ProgressTracker）

### 待实现

1. **Pipeline 编排框架**：阶段注册、顺序执行、from_phase/only_phase 控制
2. **IP 过滤链**：Phase 2 分类后过滤出 cloud_provider/residential/other
3. **Phase 6 汇总输出**：Reporter
4. **Phase 7 报告生成**：Word + Excel
5. **CLI 入口**：完整参数解析

### 未迁移的辅助模块

| 模块 | 优先级 | 说明 |
|------|--------|------|
| trace_utils.py | P1 | 溯源优先级决策树（P1-P4 分级）、域名/端口提取 |
| dns_verify.py | ✅ 已完成 | — |
| reporter.py | P1 | 文本汇总 + JSON 报告 |
| docx_builder.py | P1 | Word 报告生成器 |
| excel_exporter.py | P1 | Excel P1-P4 分级报告 |
| ip_tagger_updater.py | P2 | 标签源更新工具 |
| PidManager | P2 | 防止多实例同时运行 |

---

## 三、架构速览

```
src/ip_info/
  ├── utils/                      # 通用工具 ✅
  ├── store/                      # 存储层 ✅ (含 DomainCache Protocol)
  ├── channel/                    # 渠道层 ✅ (10 个渠道)
  ├── processors/                 # 非渠道批量处理器 ✅
  │   ├── tagger/                 # 标签打标 ✅
  │   ├── classifier/             # 自动分类 ✅
  │   └── dns_verify/             # DNS 域名验证 ✅
  ├── batch/                      # 批量查询层 ✅ (12 个脚本)
  └── pipeline/                   # 流水线层（待实现）
```

---

## 四、关键文件索引

| 文件 | 说明 |
|------|------|
| `CONTEXT.md` | 项目领域上下文 |
| `AGENTS.md` | Agent skills 入口 |
| `legacy/scenarios/trace_ip/pipeline.py` | 遗留 7 阶段流水线（迁移参考） |
| `legacy/scenarios/trace_ip/trace_utils.py` | 溯源优先级决策树（待迁移） |
| `legacy/scenarios/trace_ip/reporter.py` | 报告生成器（待迁移） |
| `src/ip_info/batch/core/runner.py` | BatchRunner Protocol |
| `src/ip_info/store/protocols.py` | IPDataWriter/IPDataReader/DomainCache 协议 |
| `src/ip_info/processors/dns_verify/runner.py` | BatchDnsVerify（参考实现） |

---

## 五、提交记录

```
7bb8e6f fix(dns_verify): 无渠道数据时 WARNING 告警
4d6d5aa test(dns_verify): 强化结果导向测试 + 补充无域名边界场景
198dfab test(dns_verify): 添加 DomainCache 并发安全测试
8cd04a4 fix(store): InMemoryDomainCache 添加 threading.Lock
72b4771 refactor(dns_verify): 过期仅提示不覆盖 + --force N + DomainCache Protocol
bdccd42 feat(dns_verify): 迁移 DNS 域名验证模块
0f8105d docs: 更新 HANDOFF.md
57f9d1c feat(classifier): 迁移 IP 自动分类模块
6854071 fix(utils): load_ips() 增加 # 注释行过滤
3bbae48 feat(tagger): 迁移 IP 标签打标模块
```

---

## 六、Git 提交规范

- 中文翻译的 conventional commit 格式
- 按逻辑分组提交，每个提交只做一件事
- PowerShell 用分号 `;` 分隔命令，`-m` 多次传 body

---

## 七、建议的下一步技能

- **brainstorming**: Pipeline 编排层的设计讨论
- **tdd**: Pipeline 编排层实现时使用 TDD
