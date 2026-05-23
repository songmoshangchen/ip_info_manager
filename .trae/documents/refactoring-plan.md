# ip_info_manager 重构方案（从零构建版）

> 核心理念：新文件夹起步，当前代码作为"知识库"参考，从最内层（存储层）逐步向外扩展，每步极小可验证。

---

## 一、总体策略

### 1.1 目录结构

```
ip_info_manager/
├── legacy/              # 当前全部代码移入（只读参考）
│   ├── channel/
│   ├── scripts/
│   ├── scenarios/
│   ├── ...
├── src/                 # 新代码（逐步构建）
│   └── ip_info/         # Python 包
│       ├── __init__.py
│       ├── store/       # 存储层（最内层，最先构建）
│       ├── channel/     # 渠道层
│       ├── batch/       # 批量查询层
│       └── pipeline/    # 流水线层
├── tests/               # 新测试（与 src/ 同步构建）
│   ├── unit/
│   └── integration/
├── pyproject.toml       # 包安装配置
└── docs/                # 设计文档
```

### 1.2 迁移原则

1. **每步只做一件事**：一个测试 → 一个实现 → 一个提交
2. **从内向外**：store → channel → batch → pipeline
3. **先协议后实现**：先定义 Protocol，再写测试替身，最后写真实实现
4. **旧代码只参考不 import**：禁止 `from legacy import ...`

---

## 二、分步计划（极小步骤）

### Step 0：Git 准备 + 目录隔离（`git-commit`）

**目的**：将当前代码隔离为只读参考，为新代码腾出空间。

#### Step 0.1：打 tag 标记当前状态
```bash
git tag legacy-start
git push --tags
```
- **验证**：`git tag -l` 能看到 `legacy-start`

#### Step 0.2：将当前代码移入 legacy/ 目录
```bash
# 移动所有源码目录（保留 tests/ 和 docs/ 不动）
mkdir legacy
git mv channel/ legacy/
git mv scripts/ legacy/
git mv scenarios/ legacy/
git mv tools/ legacy/
git mv utils/ legacy/
git mv config/ legacy/
git mv writer.py legacy/
git mv reader.py legacy/
git mv exporter.py legacy/
git mv protocols.py legacy/
git mv .env.example legacy/
git commit -m "chore: isolate current code into legacy/ dir"
```
- **验证**：`ls legacy/` 能看到所有旧文件，项目根目录只剩 `tests/`、`docs/`、`legacy/`、`.env` 等

#### Step 0.3：创建新目录结构
```bash
mkdir -p src/ip_info/store
mkdir -p src/ip_info/channel
mkdir -p src/ip_info/batch
mkdir -p src/ip_info/pipeline
touch src/ip_info/__init__.py
touch src/ip_info/store/__init__.py
touch src/ip_info/channel/__init__.py
touch src/ip_info/batch/__init__.py
touch src/ip_info/pipeline/__init__.py
touch tests/__init__.py
touch tests/conftest.py
git add src/ tests/
git commit -m "chore: initialize new source directory structure"
```
- **验证**：`ls src/ip_info/` 能看到 `store/`、`channel/`、`batch/`、`pipeline/`

#### Step 0.4：确认旧测试仍可运行
```bash
# 旧测试文件仍在 tests/，但它们 import 的路径变了
# 这一步先不动旧测试，它们会暂时失败（因为源码移到了 legacy/）
# 等新代码逐步替代后，旧测试自然被新测试替代
```
- **验证**：`ls tests/` 确认旧测试文件还在

---

### 第 1 层：存储层（store）（前置：`/spec` 提炼规格文档 → 你审核批准）

这是整个系统的核心，所有其他层都依赖它。

#### Step 1.1：项目骨架 + pyproject.toml（`brainstorming` → `setup-pre-commit`）
- 创建 `src/ip_info/__init__.py`
- 创建 `pyproject.toml`（`pip install -e .` 可用）
- 创建 `tests/conftest.py`
- **验证**：`pip install -e .` 成功，`import ip_info` 可用

#### Step 1.2：IPDataWriter 协议（`tdd` → `git-commit`）
- 创建 `src/ip_info/store/protocols.py`
- 定义 `IPDataWriter` Protocol（add_or_update_ip / delete_ip / delete_channel）
- **验证**：`isinstance()` 可用

#### Step 1.3：IPDataReader 协议（`tdd` → `git-commit`）
- 同文件，定义 `IPDataReader` Protocol（get_ip_data / get_channel_data / list_all_ips / list_ip_channels / search_ips_by_channel）
- **验证**：`isinstance()` 可用

#### Step 1.4：InMemoryIPWriter 测试替身（`tdd` → `git-commit`）
- RED：写测试 — 创建 IP、追加渠道、更新渠道、删除 IP、删除渠道
- GREEN：实现 InMemoryIPWriter
- **验证**：5+ 个测试通过

#### Step 1.5：InMemoryIPReader 测试替身（`tdd` → `git-commit`）
- RED：写测试 — 读取 IP、读取渠道、列出 IP、列出渠道、搜索
- GREEN：实现 InMemoryIPReader
- **验证**：5+ 个测试通过

#### Step 1.6：端到端读写一致性（`tdd` → `git-commit`）
- RED：写测试 — 通过 Writer 写入，通过 Reader 读回
- GREEN：确保 InMemoryIPWriter 也实现 Reader 接口
- **验证**：读写闭环测试通过

#### Step 1.7：异常行为测试（`tdd` → `git-commit`）
- RED：写测试 — 删除不存在的 IP/渠道、读取不存在的数据
- GREEN：确保返回 False/None/空列表
- **验证**：异常边界测试通过

#### Step 1.8：JSON 文件实现 — IPWriter（`tdd` → `git-commit`）
- RED：写测试 — 与 InMemory 版本行为一致，但持久化到 JSON 文件
- GREEN：实现 IPWriter（含线程锁）
- **验证**：文件 I/O 测试通过

#### Step 1.9：JSON 文件实现 — IPReader（`tdd` → `git-commit`）
- RED：写测试 — 从 JSON 文件读取
- GREEN：实现 IPReader
- **验证**：文件读取测试通过

#### Step 1.10：线程安全验证（`tdd` → `git-commit`）
- RED：写测试 — 并发写入不丢数据
- GREEN：确认 IPWriter 的 Lock 保护
- **验证**：并发测试通过

---

### 第 2 层：渠道层（channel）（前置：`/spec` 提炼规格文档 → 你审核批准）

依赖存储层的 Writer 协议。

#### Step 2.1：ChannelProtocol 协议（`tdd` → `git-commit`）
- 定义 channel_name / validate / fetch 三个接口
- **验证**：`isinstance()` 可用

#### Step 2.2：ChannelRegistry（`tdd` → `git-commit`）
- RED：写测试 — 注册/查找/列表/验证/委托 fetch
- GREEN：实现 ChannelRegistry
- **验证**：注册表测试通过

#### Step 2.3：InMemoryChannel 测试替身（`tdd` → `git-commit`）
- RED：写测试 — 可配置的 validate/fetch 行为
- GREEN：实现
- **验证**：替身测试通过

#### Step 2.4：渠道适配器基类（`brainstorming` → `tdd` → `git-commit`）
- 从 legacy 参考，提取通用模式（disabled 标志、validate 委托、fetch 委托）
- RED/GREEN 循环
- **验证**：基类测试通过

#### Step 2.5-N：逐个迁移渠道（每个渠道：`to-prd` → `tdd` → `git-commit`）
- 每个渠道：先用 `to-prd` 生成测试样例清单 → `tdd` 红-绿-重构 → `git-commit`
- 顺序：rdns_ptr（最简单）→ ipinfo_free → ipinfo_api → fofa_host → aizhan → chinaz → whois → ssl_cert → fofa_search → zoomeye → port_scan
- **每个渠道独立提交**

---

### 第 3 层：批量查询层（batch）（前置：`/spec` 提炼规格文档 → 你审核批准）

依赖存储层 + 渠道层。

#### Step 3.1：BaseBatchQuery 核心类 ✅ 已完成

- **规格文档**：`.trae/specs/build-batch-layer-core/spec.md`
- **设计决策**（brainstorming 讨论，用户确认）：

| 决策点 | 结论 | 理由 |
|--------|------|------|
| IP 列表加载 | 构造函数接受 `ips: list[str]`，文件加载由调用方负责 | 职责单一；测试友好；灵活 |
| 进度跟踪 | `ProgressTracker` 协议 + `InMemoryProgressTracker` / `FileProgressTracker` 实现 | 解耦；测试友好；可扩展 |
| 批次模式 | 不提供 `batch_mode`/`write_channels`，固定写入 `channel_name` | YAGNI；cross/standalone 仅 pipeline 使用，以后再加 |
| ETA 估算 | 不在 batch 层实现，`BatchResult` 只返回 `total_elapsed` | 不属于核心逻辑；后续可写工具模块 |
| 错误处理 | 所有 `ChannelError` 统一处理：不写入 store + 不标记进度 + 计入熔断 | 简化逻辑；错误通过日志记录；下次运行可重试 |
| 日志系统 | 各层独立用 `logging.getLogger(__name__)`，调用方配置 handler | Python 标准做法；解耦；测试友好 |

- **实际实现的子功能**：
  - ProgressTracker 协议 + InMemory/File 实现
  - BatchResult 数据类
  - BaseBatchQuery 构造函数（依赖注入 + IP 去重）
  - run() 核心循环（查询 → 写入 → 进度标记）
  - 错误处理（ChannelError 不写入 + ChannelPermanentError 终止 + disabled 检测）
  - 熔断保护（连续 N 次 ChannelError 触发）
  - 依赖检查（channel.disabled + validate）
  - 统计接口（BatchResult 返回值 + total_count/pending_count 属性）

- **与 legacy 的关键差异**：
  - ABC → 具体类（构造函数注入渠道，无需子类化）
  - error dict → 异常捕获（channel.fetch() 抛 ChannelError）
  - 移除了 PID 管理、KeyboardInterrupt、_print_result、_query_ip、_do_validate、_get_delay
  - 移除了 batch_mode、ETA 估算
  - self.run_stats dict → BatchResult 数据类返回值

- **新增文件**：
  - `src/ip_info/batch/protocols.py` — ProgressTracker 协议
  - `src/ip_info/batch/progress.py` — InMemoryProgressTracker + FileProgressTracker
  - `src/ip_info/batch/query.py` — BatchResult + BaseBatchQuery
  - `tests/unit/batch/test_progress.py` — 8 个测试
  - `tests/unit/batch/test_query.py` — 32 个测试（面向结果，不访问私有属性）

- **Git 提交**：4 个 commit
  - `feat(batch): 添加 ProgressTracker 协议 + InMemory/File 实现`
  - `feat(batch): 添加 BaseBatchQuery 核心类 + BatchResult 数据类`
  - `feat(batch): 更新 batch 包导出`
  - `test(batch): 面向结果修正 - 消除私有属性访问和中间过程验证`

#### Step 3.2-N：逐个迁移 batch 脚本（每个脚本：`tdd` → `git-commit`）
- 每个脚本：RED → GREEN → COMMIT
- 顺序与渠道迁移一致
- 每个 CLI 脚本负责：IP 文件加载/去重、日志 handler 配置、创建 BaseBatchQuery 实例并调用 run()

#### Step 3.x：无 Channel 的批量脚本（待定）

legacy 代码中存在不依赖 Channel 适配器的批量操作（如 tag 标注匹配等），后续考虑迁移为独立的批量脚本。这些脚本不关联 Channel，但复用 CLI 工具函数（IP 文件加载、日志配置等）。

**待确认**：具体脚本清单和实现方式，待从 legacy 代码中梳理后决定。

---

### 第 4 层：流水线层（pipeline）（前置：`/spec` 提炼规格文档 → 你审核批准）

依赖所有下层。

#### Step 4.1：PhaseRunner 通用骨架（`tdd` → `git-commit`）
- RED/GREEN 循环
- **验证**：PhaseRunner 单元测试通过

#### Step 4.2：ProgressManager（`tdd` → `git-commit`）
- RED/GREEN 循环
- **验证**：进度管理测试通过

#### Step 4.3-N：逐个 phase 迁移（每个 phase：`to-prd` → `tdd` → `git-commit`）
- 每个 phase：先用 `to-prd` 明确特征测试清单 → `tdd` 迁移实现 → `git-commit`
- **每个 phase 独立提交**

---

## 三、优先级总结

| 优先级 | 层级 | 步骤数 | 预估提交数 |
|--------|------|--------|-----------|
| **P-1** | Git 准备 + 目录隔离 | 4 | 2 |
| **P0** | 项目骨架 + pyproject.toml | 1 | 1 |
| **P1** | 存储层（协议+替身+实现） | 10 | 10 |
| **P2** | 渠道层（协议+注册表+11渠道） | 15 | 15 |
| **P3** | 批量查询层（基类+11脚本） | 20 | 20 |
| **P4** | 流水线层（PhaseRunner+7阶段） | 10 | 10 |

**总计约 56 个提交，每个提交只做一件事。**

---

## 四、验证标准

每步完成后必须满足：
1. `python -m pytest tests/ -q` — 全部通过
2. 无 `sys.path.insert` hack
3. 无 `from legacy import ...`
4. 新代码有对应测试覆盖

---

## 五、文档先行策略

### 5.1 核心原则：沿袭旧需求，你只做审核补充

**AI 负责从 legacy 代码提炼需求，你做决策和验收。**

工作流：
```
AI 从 legacy 代码 + 现有 PRD 提炼规格文档
    ↓
你审核（只看方向对不对，补充遗漏）
    ↓
确认后 TDD 编码
```

### 5.2 每个层级的文档产出

| 层级 | 文档 | 内容 | 产出方式 |
|------|------|------|---------|
| **store** | `docs/spec-store.md` | IPDataWriter/IPDataReader 接口规格 + 测试用例清单 | AI 从 `legacy/writer.py` + `legacy/reader.py` + `legacy/protocols.py` 提炼 |
| **channel** | `docs/spec-channel.md` | ChannelProtocol 接口 + 注册表行为 + 各渠道行为清单 | AI 从 `legacy/channel/` + `legacy/protocols.py` 提炼 |
| **batch** | `docs/spec-batch.md` | BaseBatchQuery 接口 + 各子功能规格 | AI 从 `legacy/scripts/base_batch.py` 提炼 |
| **pipeline** | `docs/spec-pipeline.md` | PhaseRunner + ProgressManager + 各 phase 规格 | AI 从 `legacy/scenarios/trace_ip/` 提炼 |

### 5.3 文档格式（模板）

每个 spec 文档包含：
```markdown
# [层级名称] 规格文档

## 接口定义
（从 legacy 提炼的 Protocol/类接口）

## 行为清单
（从 legacy 提炼的每个公开行为，编号标记）

## 测试用例清单
（每个行为对应的测试用例描述）

## 与 legacy 的差异
（迁移时计划改进的点，如异常策略、线程安全等）
```

### 5.4 你在文档环节的角色

| 动作 | 谁做 | 说明 |
|------|------|------|
| 提炼旧代码行为 | AI | 自动分析 legacy 代码，生成规格初稿 |
| 审核方向 | **你** | 确认接口和行为是否符合预期 |
| 补充遗漏 | **你** | 指出 AI 遗漏的边界情况 |
| 确认差异 | **你** | 决定哪些改进点要纳入，哪些暂缓 |
| 最终批准 | **你** | 确认后进入 TDD 编码 |

### 5.5 文档与 TDD 的关系

```
每个层级：
  /spec → AI 提炼规格文档 → 你审核批准
    ↓
  每个 Step：
    /plan → 1-3 步微计划
      ↓
    tdd → 红-绿-重构循环（按规格文档的测试用例清单执行）
      ↓
    git-commit → 规范化提交
```

---

## 六、与重构说明.md 的对应

| 重构说明原则 | 本方案落实 |
|-------------|-----------|
| 不要从零重写 | 不是重写，是逐步迁移（从 legacy 复制+适配） |
| 先封住老代码 | legacy/ 目录只读参考 |
| 小步快跑 | 每步一个测试→一个实现→一个提交 |
| AI 正确用法 | 每次只让 AI 帮一个函数或单测 |
| 特征测试 | 先用 legacy 的真实行为写测试，再迁移代码 |
| 绞杀者模式 | 新代码逐步替代旧代码，最终删除 legacy/ |

---

## 六、Skills 使用推荐

### 6.1 各阶段推荐 Skills 链

| 阶段 | 推荐 Skills 链 | 说明 |
|------|---------------|------|
| **Step 1.1 项目骨架** | `brainstorming` → 编码 | 用 brainstorming 确认包名、目录结构、依赖等基础决策 |
| **Step 1.2-1.3 协议定义** | `tdd` → `git-commit` | 先写 isinstance 测试，再定义 Protocol |
| **Step 1.4-1.7 测试替身** | `tdd` → `git-commit` | 纯 TDD 循环：写测试→实现→重构→提交 |
| **Step 1.8-1.10 文件实现** | `tdd` → `git-commit` | TDD 循环，含并发测试 |
| **Step 2.1-2.3 渠道协议+注册表** | `tdd` → `git-commit` | 协议和注册表是纯逻辑，TDD 最高效 |
| **Step 2.4 适配器基类** | `brainstorming` → `tdd` → `git-commit` | 先用 brainstorming 讨论适配器模式（disabled、异常策略），再 TDD |
| **Step 2.5-N 各渠道迁移** | `to-prd` → `tdd` → `git-commit`（每个渠道循环一次） | 每个渠道先用 to-prd 生成测试样例清单，再用 tdd 逐个实现 |
| **Step 3.1 BaseBatchQuery** | `to-prd` → `tdd` → `git-commit`（每个子功能循环一次） | 功能多，先用 to-prd 拆分测试清单，再逐个 tdd |
| **Step 3.2-N batch 脚本迁移** | `tdd` → `git-commit` | 简单继承模式，直接 tdd |
| **Step 4.1-4.2 PhaseRunner+Progress** | `tdd` → `git-commit` | 纯逻辑骨架 |
| **Step 4.3-N phase 迁移** | `to-prd` → `tdd` → `git-commit`（每个 phase 循环一次） | pipeline 最复杂，先用 to-prd 明确特征测试清单 |

### 6.2 内置命令使用时机

| 命令 | 使用时机 | 在本重构中的具体使用 |
|------|---------|---------------------|
| **`/plan`** | 每个新 Step 开始前 | 在每个 Step 开始时做极小的执行计划（1-3 步） |
| **`/spec`** | 每个层级开始前 | **核心环节**：AI 从 legacy 提炼规格文档 → 你审核批准后才开始 TDD |

### 6.3 特殊情况下的 Skills

| 情况 | 推荐 Skill | 说明 |
|------|-----------|------|
| 测试失败，不确定原因 | `diagnose` | 用严格诊断循环：复现→最小化→假设→修复 |
| 重构时测试全绿但想检查设计 | `grill-me` | 对当前层级的设计做压力测试 |
| 对话太长，上下文丢失 | `handoff` | 压缩上下文，开新对话继续 |
| 想省 token 做重复操作 | `caveman` | 批量迁移渠道时用超压缩模式 |
| 想把设计决策记录下来 | `obsidian-vault` | 保存到笔记系统持久化 |
| 工程化配置（pre-commit 等） | `setup-pre-commit` | 在 Step 1.1 完成后配置 |

---

## 七、模型选择建议

### 7.1 模型特性对比

| 特性 | glm-5.1 | glm-5-turbo |
|------|---------|-------------|
| **推理深度** | 强，适合复杂逻辑 | 中等 |
| **代码质量** | 高，边界处理更好 | 足够 |
| **速度** | 较慢 | 快 |
| **Token 成本** | 高 | 低 |
| **上下文理解** | 强，长上下文不丢信息 | 中等 |

### 7.2 各阶段推荐模型

| 阶段 | 推荐模型 | 理由 |
|------|---------|------|
| **Step 1.1 项目骨架** | **glm-5.1** | 包结构、pyproject.toml 配置需要一次性做对 |
| **Step 1.2-1.3 协议定义** | **glm-5-turbo** | Protocol 定义简单明确，turbo 足够 |
| **Step 1.4-1.7 测试替身** | **glm-5-turbo** | 重复模式（创建/追加/删除），turbo 高效 |
| **Step 1.8-1.10 文件实现** | **glm-5.1** | 文件 I/O + 线程安全，需要仔细处理边界 |
| **Step 2.1-2.3 渠道协议+注册表** | **glm-5-turbo** | 纯逻辑，模式明确 |
| **Step 2.4 适配器基类** | **glm-5.1** | 设计决策点（异常策略、disabled 模式），需要深度推理 |
| **Step 2.5-N 各渠道迁移** | **glm-5-turbo** | 批量重复操作（每个渠道模式一致），turbo 高效 |
| **Step 3.1 BaseBatchQuery** | **glm-5.1** | 最复杂的基类，9 个子功能需要仔细设计 |
| **Step 3.2-N batch 脚本** | **glm-5-turbo** | 简单继承模式 |
| **Step 4.1-4.2 PhaseRunner** | **glm-5.1** | 通用骨架设计需要深度推理 |
| **Step 4.3-N phase 迁移** | **glm-5.1** | pipeline 逻辑复杂，需要仔细处理进度/回查/写入 |

### 7.3 模型切换规则

**用 glm-5.1 的情况：**
- 🏗️ 设计决策（协议、基类、架构）
- 🔒 并发/线程安全代码
- 📐 复杂逻辑（熔断、进度管理、pipeline phase）
- 🐛 诊断难以复现的 bug（`diagnose` skill）
- 🤔 第一次做某类事情（没有先例参考）

**用 glm-5-turbo 的情况：**
- 🔄 重复模式迁移（批量迁移渠道、batch 脚本）
- ✅ 简单测试编写（创建/追加/删除）
- 📝 简单函数实现（get/set/list）
- 🚀 已有先例，照着做就行
- 💰 需要控制成本时

**经验法则：** 第一次做用 5.1，后续重复用 turbo。遇到 bug 切 5.1。
