# Handoff 文档 — ip_info_manager 重构项目

> 生成时间: 2026-05-24（第八次更新）
> 项目路径: `E:\12_trae_skills\ip_info_manager`

---

## 一、已完成工作总览

### 1. 存储层 ✅
- `src/ip_info/store/` — IPDataWriter/IPDataReader 协议 + JSON/InMemory 实现

### 2. 渠道层 ✅
- `src/ip_info/channel/` — BaseChannelAdapter + 10 个渠道 + ChannelConfig 配置系统
- `validate()` 失败时输出具体异常信息（不再笼统说"可能原因"）
- ipinfo_free/ipinfo_api: 过滤 `readme` 字段
- rdns_ptr: 仅保留 `hostname` + `has_ptr`
- whois_query: `status`/`dnssec` 空值不写入

### 3. 通用工具层 ✅
- `src/ip_info/utils/` — `load_ips()`（含 # 注释行过滤）+ ProgressTracker 协议 + 实现

### 4. 批量查询层 ✅

**关键特性**：
- 三种执行模式 Protocol：串行（BaseBatchQuery）、并发（run_concurrent）、批量（BulkRunner 预留）
- 并发模式：`done_count` 共享变量（lock 保护），进度计数器
- 日志格式统一：`[渠道] 进度: n/total - 查询成功/失败: ip [- 错误信息]`
- `BatchResult`：`success_count`/`fail_count`/`skip_count`/`total_elapsed`/`stopped_early`/`stop_reason`
- 渠道禁用：pending IP 计为失败，validate() 输出具体原因
- 已查询 IP：通过 ProgressTracker 跳过，计入 `skip_count`
- 熔断保护：连续失败达到阈值自动停止

### 5. IP 标签打标模块 ✅

- `src/ip_info/processors/tagger/` — matcher.py + manifest.py + runner.py
- `BatchTagger` 实现 BatchRunner Protocol
- 59 个测试（matcher 29 + manifest 10 + runner 20）
- `config/ip_tagger/` — manifest.json + 35 个威胁情报源文件
- CLI: `python -m ip_info.batch.batch_tagger ip_file --storage-file data/test.json --level 1`

### 6. 渠道验证诊断结果

| 渠道 | 状态 | 原因 |
|------|------|------|
| aizhan | ✅ 已修复 | Cookie 过期，`.env` 已更新新 Cookie |
| fofa_host | ❌ 账号被封 | `[820016] 违反服务协议被暂停`，需更换 Key |
| fofa_search | ❌ 账号被封 | 同上 |
| 其余 7 个 | ✅ 正常 | — |

### 7. 提交记录

```
6854071 fix(utils): load_ips() 增加 # 注释行过滤
3bbae48 feat(tagger): 迁移 IP 标签打标模块到 processors/tagger/
e850f9c fix(channel): validate() 输出具体失败原因
cc82a2e refactor(batch): 串行模式合并日志为单行进度格式
2ff60f3 feat(batch): 添加 skip_count 字段, 已查询 IP 计为跳过
f10a1c0 fix(batch): 渠道禁用时将 pending IP 计为失败
eaef555 feat(batch): 添加并发进度计数器 + 日志回归测试 + BatchRunner Protocol
dc61cc8 feat(batch): 添加逐 IP 进度日志 (issue #03)
4aaecb1 fix: whois 空值过滤 + 渠道禁用警告 (issue #02)
6fa48d1 refactor: 重构目录结构 + 修复 BOM 污染 (issue #01)
13d222b refactor(channel): 精简渠道输出字段
fc29e09 feat(scripts): 添加 10 个批量查询脚本
```

---

## 二、当前任务：迁移 IP 自动分类模块

### 设计方案（已审批）

将遗留代码 `legacy/scenarios/trace_ip/classifier.py` 迁移到新架构，作为 `processors/classifier/` 模块。

#### 目录结构

```
src/ip_info/
  processors/
    classifier/                   # IP 自动分类（新建）
      __init__.py
      rules.py                    # 规则加载/合并（从 legacy 迁入）
      engine.py                   # IPClassifier 核心匹配引擎（从 legacy 迁入）
      runner.py                   # BatchClassifier 类，实现 BatchRunner Protocol
  batch/
    batch_classifier.py           # CLI 脚本入口（新增）
config/
  classifier/                     # 分类规则文件（从 legacy 迁入）
    builtin_rules.json            # 内置规则（7 个分类类别）
    custom_rules.json             # 自定义规则（用户扩展）
```

#### 核心类：BatchClassifier

```python
class BatchClassifier:
    """IP 自动分类批量处理器，实现 BatchRunner Protocol"""

    def __init__(self, ips, writer, reader, rules_dir, custom_rules_path=None):
        ...

    def run(self) -> BatchResult:
        # 1. 加载 builtin + custom 规则
        # 2. 逐 IP 从 reader 读取全量数据
        # 3. 跳过没有数据的 IP
        # 4. 规则匹配分类
        # 5. 通过 writer 写入 "classifier" 渠道
        # 6. 返回 BatchResult
```

#### 数据流

```
IP 文件 → load_ips() → BatchClassifier.run()
                           ↓
                    从 IPDataReader 读取每个 IP 的全量数据
                    (跳过 store 中没有数据的 IP)
                           ↓
                    builtin_rules.json + custom_rules.json
                           ↓
                    规则匹配 (suffix/contains/prefix/exact/regex)
                           ↓
                    IPDataWriter.add_or_update_ip(ip, "classifier", result)
                           ↓
                    BatchResult(success_count=N, skip_count=M)
```

#### 关键设计决策

1. **每次全量重处理**：不使用 ProgressTracker，每次运行都重新分类所有 IP（纯内存计算，极快）
2. **接收 IP 文件 + 从 store 读取**：和 tagger 统一入口，但跳过 store 中没有数据的 IP
3. **分类结果写入 `"classifier"` 渠道**：`{"category": "cloud_provider", "label": "云服务商", "description": "...", "matched_by": [...], "need_deep_query": true, "classify_time": "..."}`
4. **规则文件独立**：`config/classifier/builtin_rules.json` + `config/classifier/custom_rules.json`
5. **不依赖 tagger**：classifier 只依赖 RDNS + ipinfo 查询结果，与 tagger 无关
6. **7 个分类类别**：invalid_rdns、cloud_provider、cdn、crawler_scanner、residential、excluded_domain、other
7. **5 种匹配类型**：suffix、contains、prefix、exact、regex
8. **first-match 策略**：规则按 OrderedDict 顺序匹配，第一个命中即返回

#### 遗留代码参考

| 遗留文件 | 迁移目标 | 说明 |
|----------|----------|------|
| `legacy/scenarios/trace_ip/classifier.py` | `processors/classifier/` | 核心逻辑拆分到 rules.py/engine.py/runner.py |
| `legacy/scenarios/trace_ip/classifiers/builtin_rules.json` | `config/classifier/builtin_rules.json` | 内置分类规则 |
| `legacy/scenarios/trace_ip/classifiers/custom_rules.json` | `config/classifier/custom_rules.json` | 自定义分类规则 |
| `legacy/tests/test_classifier.py` | `tests/unit/processors/test_*.py` | 测试参考 |

#### 不迁移的部分

- `ClassifyResult.to_dict()` — 改用普通 dict 构建，不单独建 dataclass
- `_builtin_count` 跟踪 — 简化规则来源标记，统一为 `"rule_source": "builtin"/"custom"`

---

## 三、待做工作

### P0: 迁移 IP 自动分类模块（当前任务）

按 TDD 方式实现：
1. 创建 `processors/classifier/` 目录结构
2. 迁移 `rules.py`（规则加载/合并）+ 测试
3. 迁移 `engine.py`（IPClassifier 匹配引擎）+ 测试
4. 实现 `BatchClassifier`（runner.py）+ 测试
5. 创建 CLI 脚本 `batch_classifier.py`
6. 迁移配置文件 `config/classifier/`
7. 运行全量测试 + ruff 检查

### P1: BulkRunner 批量模式（预留）

```
BatchRunner (Protocol)
├── BaseBatchQuery    — 串行（已实现）
├── run_concurrent()  — 并发（已实现）
├── BatchTagger       — 标签打标（已实现）
├── BatchClassifier   — 自动分类（即将实现）
└── BulkRunner        — 批量 API（待实现）
```

### P2: 标签源更新工具迁移

- `legacy/tools/ip_tagger_updater.py` → 独立工具脚本
- 支持从 GitHub/Git 下载更新威胁情报文件

### P3: 流水线层（未开始）

---

## 四、架构速览

```
src/ip_info/
  ├── utils/                      # 通用工具 ✅
  │   ├── load_ips.py             # load_ips() — BOM + 去重 + 去空行 + #注释过滤
  │   └── progress.py             # ProgressTracker 协议 + File/InMemory 实现
  ├── store/                      # 存储层 ✅
  │   ├── json_store.py           # IPWriter + IPReader + progress_tracker()
  │   └── in_memory.py            # InMemoryIPWriter + progress_tracker()
  ├── channel/                    # 渠道层 ✅
  │   ├── adapter.py              # BaseChannelAdapter + validate() + disabled
  │   ├── config.py               # ChannelConfig + 11 个配置类
  │   └── *.py                    # 10 个具体渠道
  ├── processors/                 # 非渠道批量处理器 ✅
  │   ├── tagger/                 # 标签打标 ✅
  │   │   ├── matcher.py          # 流式双指针匹配算法
  │   │   ├── manifest.py         # manifest 加载/验证
  │   │   └── runner.py           # BatchTagger（实现 BatchRunner Protocol）
  │   └── classifier/             # 自动分类（即将实现）
  │       ├── rules.py            # 规则加载/合并
  │       ├── engine.py           # IPClassifier 匹配引擎
  │       └── runner.py           # BatchClassifier（实现 BatchRunner Protocol）
  ├── batch/                      # 批量查询层 ✅
  │   ├── core/                   # 核心逻辑
  │   │   ├── query.py            # BaseBatchQuery + BatchResult（串行）
  │   │   ├── concurrent.py       # run_concurrent()（并发，含进度计数器）
  │   │   └── runner.py           # BatchRunner Protocol（鸭子类型）
  │   └── batch_*.py              # 10 个脚本入口 + batch_tagger.py + batch_classifier.py
  └── pipeline/                   # 流水线层（未开始）
```

---

## 五、测试现状

- **475+ 测试全部通过**（含 tagger 59 个测试）
- 运行命令：`python -m pytest tests/unit/ -q`
- pre-commit hooks：ruff-format + ruff + pytest(unit/store)

---

## 六、关键文件索引

| 文件 | 说明 |
|------|------|
| `CONTEXT.md` | 项目领域上下文 |
| `AGENTS.md` | Agent skills 入口 |
| `.trae/documents/refactoring-plan.md` | 重构总方案 |
| `legacy/scenarios/trace_ip/classifier.py` | 遗留分类器代码（迁移源） |
| `legacy/scenarios/trace_ip/classifiers/builtin_rules.json` | 内置分类规则（迁移源） |
| `legacy/scenarios/trace_ip/classifiers/custom_rules.json` | 自定义分类规则（迁移源） |
| `legacy/tests/test_classifier.py` | 遗留分类器测试（参考） |
| `src/ip_info/batch/core/runner.py` | BatchRunner Protocol |
| `src/ip_info/batch/core/query.py` | BaseBatchQuery + BatchResult |
| `src/ip_info/store/protocols.py` | IPDataWriter/IPDataReader 协议 |
| `src/ip_info/processors/tagger/runner.py` | BatchTagger（参考实现） |

---

## 七、Git 提交规范

- 中文翻译的 conventional commit 格式
- 按逻辑分组提交
- 每个提交只做一件事
- PowerShell 不支持 `&&` 和 HEREDOC，用分号 `;` 分隔命令，`-m` 多次传 body

---

## 八、建议的下一步技能

- **tdd**: 迁移 classifier 模块时使用 TDD 方式（先写测试再实现）
- **brainstorming**: 如果迁移过程中发现需要新的设计决策
