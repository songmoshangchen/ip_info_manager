---
type: task-plan
date: 2026-05-19
tags: [ip_info_manager, 测试, 核查, 重构]
baseline: 261 passed, 1 warning (dateutil DeprecationWarning)
---

# 任务拆解计划：ip_info_manager 重构后测试核查

## 一、任务概述

- **任务名称**: 核查重构后 mock 数据和测试样例的有效性、可用性、有意义性
- **最终交付物**: 一份核查报告（问题清单+修复建议），以及补充的测试用例
- **预估总时长**: 8-14小时（跨多个工作日）
- **关键路径**: 回顾设计意图 → 审查现有测试 → 发现盲区 → 补充测试 → 文档更新

## 二、前置条件

- [x] Windows端 ip_info_manager 项目可运行（pytest全绿：261 passed）
- [x] 能读取项目源码和测试文件
- [ ] 你能提供重构时的设计意图和边界case想法

## 三、推荐 Skills

| Skill | 用在哪个阶段 | 理由 |
|-------|------------|------|
| **diagnose** | T5（分析 Phase 7 exclude_ips bug） | 严格诊断循环：复现→最小化→假设→埋点→修复→回归测试 |
| **tdd** | T6/T7（补充缺失测试） | 红-绿-重构循环，确保新测试质量 |
| **grill-me** / **grill-with-docs** | T1/T2（设计意图梳理和覆盖差距分析） | 对设计意图做压力测试，发现遗漏的边界 case |
| **improve-codebase-architecture** | T3/T4 之后（如果测试结构需要重构） | 基于项目领域语言发现测试架构改进机会 |
| **git-commit** | 每完成一个子任务后 | 规范化提交 |
| **handoff** | 如果会话太长需要交接 | 压缩上下文 |
| **caveman** | 排查过程中大量重复操作时 | 省 token |

## 四、审查分批策略

按**风险等级**和**模块依赖关系**将 13 个测试文件分成 **5 批**：

```
批次 1（纯函数/无依赖）—— 最安全，热身
  ├── test_trace_utils.py          (26 tests) — 纯函数，无 mock
  ├── test_channel_base.py         (10 tests) — 纯函数，无 mock
  └── test_config.py               (25 tests) — 环境变量测试

批次 2（测试替身自身）—— 理解 mock 基础
  ├── test_in_memory_writer.py     (9 tests)
  ├── test_in_memory_reader.py     (17 tests)
  └── test_protocol_conformance.py (8 tests)

批次 3（Protocol/Registry 核心）—— 重点审查
  ├── test_channel_protocol.py     (36 tests) — patch 使用多
  ├── test_channel_registry.py     (46 tests) — patch 使用多，create_default_registry 有风险
  └── test_pipeline_registry.py    (8 tests)

批次 4（业务循环核心）—— 重点审查
  ├── test_batch_run.py            (36 tests) — Dummy 替身多，真实 sleep
  ├── test_base_batch.py           (14 tests) — __new__ 模式
  └── test_phase_runner.py         (10 tests)

批次 5（文件 I/O）—— 需要特别注意
  └── test_progress.py             (11 tests) — 真实文件读写
```

### 各批次审查要点

#### 批次 1：纯函数（热身，建立审查节奏）

| 审查维度 | 具体检查项 |
|---------|-----------|
| Mock 一致性 | 基本无 mock，重点关注返回值类型是否与生产代码一致 |
| 业务意义 | test_trace_utils 的 26 个测试是否覆盖了所有 9 个共享函数的边界 case |
| 冗余/合并 | test_config 25 个测试是否有重复模式可以参数化 |
| 缺失场景 | `is_china_ip` 是否覆盖了 `country_code` 为 None 的情况？`sort_key` 是否覆盖了相同优先级的排序？ |

**需要对照的源文件：**
- `scenarios/trace_ip/trace_utils.py`
- `channel/base.py`
- `config.py`

#### 批次 2：测试替身（理解 mock 基础设施）

| 审查维度 | 具体检查项 |
|---------|-----------|
| 替身 vs 生产代码差异 | `InMemoryIPWriter` 的 `get_all()` 不属于 Protocol，是否会导致测试通过但生产代码失败？ |
| 行为一致性 | `delete_ip` / `delete_channel` 的返回值语义是否与 `IPWriter` 一致？ |
| Protocol 兼容性 | 如果 Protocol 新增方法，替身是否会自动失效？ |

**需要对照的源文件：**
- `protocols.py`（Protocol 定义 + InMemory 替身）
- `writer.py`（IPWriter 真实实现）
- `reader.py`（IPReader 真实实现）

#### 批次 3：Protocol/Registry（重点，patch 使用最多）

| 审查维度 | 具体检查项 |
|---------|-----------|
| patch 路径正确性 | `patch('channel.fofa_host.validate_channel_key')` 路径是否正确？是否需要完整模块路径？ |
| return_value 结构 | `patch(..., return_value=expected)` 的 `expected` 是否匹配真实 API 响应？ |
| side_effect 场景 | `SystemExit(1)` 和 `ConnectionError` 是否覆盖了所有真实失败模式？ |
| 适配器数量 | 10 个渠道中只有 7 个在 registry 测试中验证，另外 3 个在 protocol 测试中，是否有遗漏？ |
| 参数化机会 | 7 个适配器的测试模式完全相同，是否可以合并为参数化测试？ |

**需要对照的源文件：**
- `protocols.py`（ChannelProtocol + ChannelRegistry）
- `channel/*.py`（全部 10 个渠道的 validate_channel_key + fetch_channel）

#### 批次 4：业务循环核心（Dummy 替身审查）

| 审查维度 | 具体检查项 |
|---------|-----------|
| DummyWriter 遗漏 | `_DummyWriter` 只记录 writes 列表，是否遗漏了写入失败、并发写入等场景？ |
| __new__ 模式风险 | 跳过 `__init__` 的 `__new__` + 手动属性设置，是否可能遗漏必要属性？ |
| delay 真实 sleep | 只有 1 个测试设了 `delay=0.05`，是否足够验证延迟逻辑？ |
| exclude_ips 路径 | `BaseBatchQuery.run()` 中 exclude_ips 的逻辑是否被任何测试覆盖？（T5 重点） |

**需要对照的源文件：**
- `scripts/base_batch.py`
- `scenarios/trace_ip/phase_runner.py`

#### 批次 5：文件 I/O（风险最高）

| 审查维度 | 具体检查项 |
|---------|-----------|
| 临时文件清理 | `tempfile.mkdtemp()` 是否正确清理？ |
| 并发安全 | 文件读写测试是否考虑并发场景？ |
| 编码问题 | Windows 下文件路径和编码是否有问题？ |

**需要对照的源文件：**
- `scenarios/trace_ip/progress.py`

## 五、任务清单

### 阶段一：回顾设计意图与梳理现有覆盖 (预估 2-3h)

#### T1: 逐模块列出重构设计意图 ⭐ Must
- **产出**: 每个重构模块的设计意图清单
- **时长**: 1-2h
- **依赖**: 无
- **验收标准**:
  - [ ] 覆盖全部9个重构项（Protocol/ChannelRegistry/PhaseRunner/BaseBatchQuery/trace_utils等）
  - [ ] 每项记录：设计目标、关键边界case、当时考虑过但没写进测试的场景
- **执行提示**: 按模块逐个回忆重构时的想法，可以分多次聊

#### T2: 对照TESTING.md和MOCK_INVENTORY.md标记覆盖缺口 ⭐ Must
- **产出**: 覆盖差距表（模块 vs 已有测试 vs 缺失场景）
- **时长**: 1h
- **依赖**: T1
- **验收标准**:
  - [ ] 列出所有有测试的模块和对应测试数
  - [ ] 列出所有无测试的模块（classifier/reporter/excel_exporter/tools/各渠道内部逻辑）
  - [ ] 将T1中的设计意图与现有测试逐条对照，标记未覆盖的场景

### 阶段二：审查现有测试质量 (预估 3-5h)

#### T3: 审查mock返回值与生产代码的一致性 ⭐ Must
- **产出**: mock数据问题清单
- **时长**: 2-3h
- **依赖**: T2
- **验收标准**:
  - [ ] 逐文件检查 `patch(..., return_value=...)` 的返回值是否匹配真实API响应结构
  - [ ] 检查 `InMemoryIPWriter` vs `IPWriter` 行为差异（get_all()额外方法、内存vs文件）
  - [ ] 检查 `_DummyWriter` 是否遗漏了IPWriter的关键行为（如写入失败场景）
  - [ ] 标记所有发现的不一致
- **执行提示**: 重点看MOCK_INVENTORY.md中"测试替身与生产代码差异"那张表
- **执行方式**: 按 5 批策略执行，批次 1 → 2 → 3 → 4 → 5

#### T4: 审查测试用例的业务意义 ⭐ Must
- **产出**: 无意义/冗余测试清单 + 建议删除/合并列表
- **时长**: 1-2h
- **依赖**: T2
- **验收标准**:
  - [ ] 逐文件检查261个测试是否验证了有意义的业务行为
  - [ ] 标记纯机械测试（如只验证setter/getter、无断言的测试）
  - [ ] 标记可以通过参数化合并的重复测试（如7个适配器的相同测试模式）
  - [ ] 对每个被标记的测试给出：保留/合并/删除建议

#### T5: 分析已知bug为何未被测试捕获 ⭐ Must
- **产出**: Phase 7 exclude_ips bug的根因分析 + 具体缺失测试描述
- **时长**: 1h
- **依赖**: T2
- **推荐 Skill**: diagnose
- **验收标准**:
  - [ ] 明确哪个模块/函数/逻辑路径有bug
  - [ ] 说明为什么现有261个测试都没有覆盖到这个路径
  - [ ] 写出应该补写的测试用例描述

### 阶段三：补充缺失测试 (预估 3-5h)

#### T6: 补充高优先级模块的缺失测试 ⭐ Must
- **产出**: 新测试文件/用例代码
- **时长**: 2-3h
- **依赖**: T2, T3
- **推荐 Skill**: tdd
- **验收标准**:
  - [ ] classifier.py — 覆盖7类分类边界case（含exclude_ips过滤逻辑）
  - [ ] reporter.py 或 excel_exporter.py 至少一个 — 验证报告输出格式
  - [ ] Phase 7 exclude_ips过滤 — 端到端测试（从pipeline到报告输出）
  - [ ] 所有新测试通过pytest
- **执行提示**: 优先修已知bug的测试，其次是重构核心模块

#### T7: 补充渠道内部逻辑测试 ⭐ Should
- **产出**: 至少2个渠道的request_channel/parse_response测试
- **时长**: 2h
- **依赖**: T3
- **推荐 Skill**: tdd
- **验收标准**:
  - [ ] 选择2个高价值渠道（如fofa_host、aizhan）
  - [ ] 用mock HTTP response测试parse_response的解析逻辑
  - [ ] 覆盖异常响应（空数据、格式错误、超时）

#### T8: （可选）运行变异测试量化测试有效性 ⭐ Could
- **产出**: mutation score报告
- **时长**: 1-2h
- **依赖**: T6
- **验收标准**:
  - [ ] 安装并运行mutmut
  - [ ] 对核心模块运行变异测试
  - [ ] 记录mutation score，标记未被杀死的变异
- **风险**: mutmut可能在Windows环境有兼容问题，备选用cosmic-ray

### 阶段四：收尾 (预估 1h)

#### T9: 更新TESTING.md和MOCK_INVENTORY.md ⭐ Must
- **产出**: 更新后的测试文档
- **时长**: 30min
- **依赖**: T6
- **验收标准**:
  - [ ] TESTING.md新增文件条目
  - [ ] MOCK_INVENTORY.md新增mock条目
  - [ ] 删除/合并的测试在文档中有说明

#### T10: 最终pytest全绿验证 ⭐ Must
- **产出**: 全部测试通过的截图/日志
- **时长**: 15min
- **依赖**: T6, T9
- **验收标准**:
  - [ ] `python -m pytest tests/ -v -p no:dash` 全部通过
  - [ ] 总测试数 = 261 + 新增测试数

## 六、并行机会

- T3（审查mock）和 T4（审查业务意义）可以同时进行（都只依赖T2）
- T5（已知bug分析）和 T4 可以并行
- T7（渠道测试）和 T9（文档更新）可以并行

## 七、里程碑

- M1: 设计意图梳理完成 + 覆盖差距表产出 — 阶段一结束
- M2: 现有测试质量审查完成 + 问题清单产出 — 阶段二结束
- M3: 补充测试完成 + 全绿通过 — 阶段三结束
- M4: 文档更新 + 最终验证 — 交付

## 八、基线状态

- **运行命令**: `python -m pytest tests/ -v -p no:dash`
- **结果**: 261 passed, 1 warning in 8.90s
- **Warning**: dateutil DeprecationWarning（第三方库问题，非项目代码）
- **测试文件**: 13 个
- **Python 版本**: 3.12+
- **运行环境**: Windows 11

## 九、T1 设计意图访谈记录

### 9.1 ChannelProtocol + ChannelRegistry

**设计目标：**
- Channel 是"单条渠道查询单个 IP"的最小单元：IP → 处理层 → 存储
- 三步走：传入 IP → 特定处理（格式化数据直接解析 / 网页需匹配裁剪 / 失败判断）→ 调用存储模块
- `validate()` 返回 bool 统一接口，不区分 API key / cookie / 外部引擎等不同认证方式

**已知的不足（用户确认）：**
- port_scan 的 validate 使用 `validate_engine()` 而非 `validate_channel_key()`，Protocol 层面未区分这种特殊性
- `create_default_registry()` 如果某个渠道 ImportError 会直接崩溃，未做容错
- 适配器测试是 AI 生成的，缺：apikey 不正确、cookie 失效、网络异常等真实失败场景

**当时考虑过但没做的：**
- 渠道依赖检查（调用前判断依赖包是否存在，不存在则提示并跳过）
- 参数化测试合并（7 个适配器的相同测试模式）

**检查结论：**
- `ChannelFetcher` Protocol：生产代码**零引用**，只有 `test_channel_base.py` 使用，可安全删除
- Pipeline 迁移状态：
  - `trace_ip/pipeline.py` — 大部分已迁移，但 Phase 5 (port_scan) 仍有 `from channel.port_scan import ...` 硬编码
  - `ip_domain_lookup/pipeline.py` — 已完全迁移

### 9.2 BaseBatchQuery + 批量脚本迁移

**设计目标：**
- 从 9 个批量脚本中提取通用 validate/PID/ETA/统计循环
- 子类只需实现 `_query_ip` / `_print_result` / `_get_delay`（可选）

**已知的不足（用户确认）：**
- **exclude_ips 功能不存在于 run() 中**——这是后来添加的功能，没有集成到 BaseBatchQuery。这是 Phase 7 bug 的根因线索
- 用户不了解 `__new__` 测试模式，未评估测试与真实代码的差异风险
- `batch_rdns_ptr_concurrent.py` 和 `batch_port_scan.py` 未迁移（优先级低，已记录待办）

**当时考虑过但没做的：**
- exclude_ips 过滤逻辑（当时还没这个功能）
- ConcurrentBaseBatchQuery 抽象（并发版脚本差异大）

### 9.3 PhaseRunner

**设计目标：**
- 从 pipeline.py 的重复代码中提取的"进度检测 → 查询 → 写入"骨架
- 通用阶段循环，不绑定具体渠道

**当时考虑过但没做的：**
- `_build_channel_specs()` 只返回 `[{channel: ch}]`，未考虑让每个 spec 携带不同参数（apikey/timeout 等）。用户希望通过配置文件实现，使用时引导使用者调用配置修改工具

### 9.4 trace_utils（Reporter 领域逻辑分离）

**设计目标：**
- 从 reporter.py 和 excel_exporter.py 中发现重复逻辑，提取为 9 个共享函数

**已知的不足（用户确认）：**
- 用户**没考虑字段缺失时的健壮性**（如 `is_china_ip()` 中 `country_code` 为 None 而非 ''）
- excel_exporter.py **基本没使用**，用户在考虑是否删除

### 9.5 IPDataWriter / IPDataReader Protocol

**设计目标：**
- 两者都有：方便单元测试（InMemory 替身）+ 未来考虑替换为 SQLite
- 目前主要用于测试替身

### 9.6 Pydantic V2 迁移

**设计目标：**
- pytest 报 DeprecationWarning，AI 自动修复的

### 9.7 classifier.py（非重构项，但相关）

**设计目标：**
- 7 类分类规则，支持 5 种匹配类型

**已知的不足（用户确认）：**
- **测试为 0**，没考虑边界 case（规则为空、字段路径不存在、regex 无效、多规则同时匹配优先级）

### 9.8 整体发现

| 发现 | 严重度 | 影响 |
|------|--------|------|
| exclude_ips 未集成到 BaseBatchQuery.run() | 高 | Phase 7 bug 的直接原因 |
| 适配器测试为 AI 生成，缺真实失败场景 | 中 | 无法捕获 apikey/cookie/网络问题 |
| classifier.py 零测试 | 中 | 分类规则变更无保护 |
| ChannelFetcher 可安全删除 | 低 | 代码清理 |
| trace_ip/pipeline.py Phase 5 硬编码导入 | 低 | 未完全迁移到 registry |
| trace_utils 函数未考虑字段缺失 | 中 | 可能导致 None vs '' 比较 bug |
| excel_exporter 可能删除 | 低 | 影响测试范围 |
| `__new__` 测试模式用户不了解 | 中 | 测试有效性存疑 |

## 十、T2 覆盖差距表

### 10.1 总体统计

| 类别 | 源文件总数 | 有直接测试 | 无测试 | 覆盖率 |
|------|-----------|-----------|--------|--------|
| 根目录 | 5 | 4 | 1 | 80% |
| channel/ | 12 | 1 | 11 | 8% |
| scenarios/trace_ip/ | 10 | 4 | 6 | 40% |
| scenarios/ip_domain_lookup/ | 7 | 0 | 7 | 0% |
| scripts/ | 12 | 1 | 11 | 8% |
| tools/ | 9 | 0 | 9 | 0% |
| utils/ | 6 | 0 | 6 | 0% |
| **合计** | **62** | **10** | **52** | **16%** |

> 注：channel/*.py 的适配器类通过 test_channel_protocol.py/test_channel_registry.py 间接测试了 validate/fetch 委托，但内部逻辑（request_channel/parse_response）零覆盖。

### 10.2 有测试模块的覆盖详情

#### protocols.py — 4 个测试文件覆盖

| 组件 | 测试文件 | 测试数 | 覆盖内容 | 缺失场景 |
|------|---------|--------|---------|---------|
| IPDataWriter Protocol | test_protocol_conformance | 2 | isinstance + 方法存在 | 无 |
| IPDataReader Protocol | test_protocol_conformance | 2 | isinstance + 方法存在 | 无 |
| InMemoryIPWriter | test_in_memory_writer | 9 | add/delete 全部路径 | `get_all()` 非 Protocol 方法无测试 |
| InMemoryIPReader | test_in_memory_reader | 17 | 全部 5 个方法 + 边界 | 无 |
| ChannelProtocol | test_channel_protocol | 5 | 结构 + isinstance | 无 |
| InMemoryChannel | test_channel_protocol | 8 | validate/fetch/不可变性 | 无 |
| ChannelRegistry | test_channel_registry | 20 | register/get/list/validate/fetch | 并发注册、fetch 返回值结构验证 |
| create_default_registry | test_channel_registry | 5 | 10 渠道注册验证 | ImportError 容错（未实现） |
| 10 个适配器 | test_channel_protocol + test_channel_registry | 23 | isinstance + validate + fetch 委托 | 真实 API 场景（apikey/cookie/网络异常） |

#### config.py — 1 个测试文件覆盖

| 组件 | 测试数 | 覆盖内容 | 缺失场景 |
|------|--------|---------|---------|
| BaseIPSettings | 4 | model_config / env_file / extra | 无 |
| 11 个 Settings 子类 | 11 | 继承关系 | 各子类特有字段验证（如 FofaSettings 的 apikey 格式） |
| 验证器 | 6 | storage_dir 验证 | 其他自定义验证器（如有） |
| 默认值/环境变量 | 4 | 默认值 / env_prefix | 复杂环境变量覆盖场景 |

#### channel/base.py — 1 个测试文件覆盖

| 组件 | 测试数 | 覆盖内容 | 缺失场景 |
|------|--------|---------|---------|
| apply_delay | 3 | delay=0/>0/<0 | delay 为极大值、浮点精度 |
| format_output | 5 | setdefault/保留/空/错误 | 嵌套 dict、data 中已有 query_time |
| ChannelFetcher | 2 | isinstance + callable | **可删除**（ChannelFetcher deprecated） |

#### scenarios/trace_ip/trace_utils.py — 1 个测试文件覆盖

| 组件 | 测试数 | 覆盖内容 | 缺失场景 |
|------|--------|---------|---------|
| is_china_ip | 4 | CN/China/非中国/无ipinfo | country_code=None 而非 ''、country 含 'China' 但不是中国（如 China Town） |
| extract_all_domains | 4 | 正常/去重/无数据/空域名 | source 字段缺失、domain 为 None、超大列表 |
| extract_fofa_ports | 3 | 正常/报错/无fofa | ports 格式异常、products 为空 |
| has_domains / has_ports | 4 | True/False | 无（简单委托函数） |
| trace_priority | 6 | P1-P4 | info 为空 dict、只有 ipinfo_api 无其他渠道 |
| cat_display | 3 | 有note/other/无note | matched_by 为空列表、category 不在 LABEL_MAP |
| trace_action | 3 | CN域名/外网域名/无 | 同时有域名和端口 |
| sort_key | 1 | 降序 | 相同优先级的排序、无 trace_classify 字段 |

#### scripts/base_batch.py — 2 个测试文件覆盖

| 组件 | 测试数 | 覆盖内容 | 缺失场景 |
|------|--------|---------|---------|
| _load_ip_file | 3 | 去重/空行/计数 | 文件不存在（sys.exit）、编码异常 |
| _load_progress | 2 | 有/无进度文件 | 进度文件损坏 |
| _load_pending_ips | 2 | 合并去重/全部已处理 | 空 IP 文件 |
| channel_name | 1 | 默认/自定义 | 无 |
| _get_delay | 2 | 属性名/默认值 | settings 无对应属性 |
| _is_error | 2 | raw_error/error | data 不是 dict、嵌套 error |
| progress_file | 2 | 路径生成 | 无 |
| run() | 15 | 查询/PID/延迟/统计/validate | **exclude_ips 过滤**（T5 重点）、写入失败、文件满 |

#### scenarios/trace_ip/phase_runner.py — 1 个测试文件覆盖

| 组件 | 测试数 | 覆盖内容 | 缺失场景 |
|------|--------|---------|---------|
| __init__ | 1 | 存储配置 | 无 |
| compute_processed_from_store | 3 | 全处理/部分/空 | store 异常 |
| get_pending_ips | 3 | 排除/全处理/合并进度 | 空 IP 列表 |
| run | 4 | 查询/跳过/写入/None和空dict | query_fn 抛异常、store 写入失败 |

#### scenarios/trace_ip/progress.py — 1 个测试文件覆盖

| 组件 | 测试数 | 覆盖内容 | 缺失场景 |
|------|--------|---------|---------|
| ChannelLevelProgress | 11 | record/load/clear/多IP多渠道 | 并发读写、磁盘满、文件权限 |

### 10.3 无测试模块清单（按优先级排序）

#### P0 — 影响核心业务逻辑（T6 必须覆盖）

| 模块 | 路径 | 风险说明 | T1 关联发现 |
|------|------|---------|------------|
| **classifier.py** | scenarios/trace_ip/classifier.py | 7 类分类 + 5 种匹配，零测试，规则变更无保护 | 用户确认没考虑边界 case |
| **pipeline.py (trace_ip)** | scenarios/trace_ip/pipeline.py | 7 阶段流水线核心，exclude_ips bug 所在地 | exclude_ips 未集成到 BaseBatchQuery |
| **reporter.py (trace_ip)** | scenarios/trace_ip/reporter.py | 报告生成逻辑，依赖 trace_utils | trace_utils 字段缺失健壮性未验证 |

#### P1 — 渠道内部逻辑（T7 应覆盖）

| 模块 | 路径 | 风险说明 |
|------|------|---------|
| **channel/fofa_host.py** | channel/fofa_host.py | API 渠道，parse_response 解析 FOFA JSON |
| **channel/aizhan.py** | channel/aizhan.py | 爬虫渠道，parse_response 解析 HTML |
| **channel/chinaz.py** | channel/chinaz.py | 爬虫渠道，parse_response 解析 HTML |
| **channel/fofa_search.py** | channel/fofa_search.py | API 渠道 |
| **channel/ipinfo_api.py** | channel/ipinfo_api.py | API 渠道（SDK） |
| **channel/rdns_ptr.py** | channel/rdns_ptr.py | DNS 反查 |
| **channel/ssl_cert.py** | channel/ssl_cert.py | SSL 证书查询 |
| **channel/whois_query.py** | channel/whois_query.py | WHOIS 查询 |
| **channel/zoomeye.py** | channel/zoomeye.py | API 渠道 |
| **channel/port_scan.py** | channel/port_scan.py | 外部引擎（nmap），validate 逻辑特殊 |

#### P2 — 工具层（可后续补充）

| 模块 | 路径 | 风险说明 |
|------|------|---------|
| tools/config_tool.py | tools/config_tool.py | 配置管理 CLI |
| tools/ip_tagger.py | tools/ip_tagger.py | IP 威胁标签 |
| tools/ip_tagger_updater.py | tools/ip_tagger_updater.py | 标签源更新 |
| tools/docx_builder.py | tools/docx_builder.py | Word 报告引擎 |
| tools/status_tool.py | tools/status_tool.py | 任务状态查询 |
| tools/progress_tool.py | tools/progress_tool.py | 进度文件管理 |
| tools/merge_ip_files.py | tools/merge_ip_files.py | IP 文件合并 |
| tools/verify_ip_domain.py | tools/verify_ip_domain.py | IP-域名验证 |
| tools/ai_analysis.py | tools/ai_analysis.py | AI 研判 |

#### P3 — 工具库层（可后续补充）

| 模块 | 路径 | 风险说明 |
|------|------|---------|
| utils/dns_verify.py | utils/dns_verify.py | DNS 验证底层 |
| utils/ip_utils.py | utils/ip_utils.py | IP 格式验证 |
| utils/file_utils.py | utils/file_utils.py | 文件读写工具 |
| utils/logger_utils.py | utils/logger_utils.py | 日志配置 |
| utils/pid_manager.py | utils/pid_manager.py | PID 文件管理 |

#### P4 — 脚本层（子类薄层，优先级最低）

| 模块 | 路径 | 风险说明 |
|------|------|---------|
| scripts/batch_*.py (9个) | scripts/batch_*.py | 继承 BaseBatchQuery，子类只实现 _query_ip/_print_result |
| scripts/batch_rdns_ptr_concurrent.py | scripts/batch_rdns_ptr_concurrent.py | 并发版，未迁移到 BaseBatchQuery |

#### P5 — 其他场景

| 模块 | 路径 | 风险说明 |
|------|------|---------|
| scenarios/ip_domain_lookup/* (7个) | scenarios/ip_domain_lookup/ | 域名反查流水线，整体无测试 |
| scenarios/trace_ip/excel_exporter.py | scenarios/trace_ip/excel_exporter.py | 用户考虑删除 |
| scenarios/trace_ip/trace_ip.py | scenarios/trace_ip/trace_ip.py | CLI 入口 |
| exporter.py | exporter.py | Excel 导出 |

### 10.4 T1 设计意图 vs 现有测试逐条对照

| T1 设计意图 | 对应测试 | 覆盖状态 | 缺失说明 |
|------------|---------|---------|---------|
| Channel 最小单元：IP→处理→存储 | test_channel_protocol (36) | ⚠️ 部分 | 只测了 validate/fetch 委托，request_channel/parse_response 未测 |
| validate() 统一 bool 接口 | test_channel_protocol + test_channel_registry | ✅ 已覆盖 | 但只测了 SystemExit/Exception，缺真实失败场景 |
| ChannelRegistry 注册/查找/验证 | test_channel_registry (20) | ✅ 已覆盖 | 缺 ImportError 容错测试 |
| create_default_registry 10 渠道 | test_channel_registry (5) | ✅ 已覆盖 | 缺部分渠道导入失败场景 |
| BaseBatchQuery 通用循环 | test_batch_run (15) | ⚠️ 部分 | **缺 exclude_ips 过滤** |
| PhaseRunner 进度→查询→写入 | test_phase_runner (10) | ✅ 已覆盖 | 缺 query_fn 异常 |
| trace_utils 9 个共享函数 | test_trace_utils (26) | ⚠️ 部分 | 缺字段缺失健壮性（None vs ''） |
| Protocol 可替换性（测试替身） | test_protocol_conformance (8) | ✅ 已覆盖 | 无 |
| Pydantic V2 SettingsConfigDict | test_config (25) | ✅ 已覆盖 | 无 |
| IPWriter/Reader Protocol 兼容 | test_protocol_conformance (8) | ✅ 已覆盖 | 无 |
| classifier.py 7 类分类 | 无 | ❌ 未覆盖 | 零测试 |
| 渠道依赖检查（未实现） | 无 | ❌ 未实现 | 功能本身未实现 |
| exclude_ips 过滤（未集成） | 无 | ❌ 未集成 | 功能本身未集成到 BaseBatchQuery |

### 10.5 关键数字

- **总源文件**: 62 个
- **有直接测试**: 10 个（16%）
- **测试文件**: 13 个
- **测试用例**: 261 个
- **T1 设计意图项**: 13 项
- **已覆盖**: 5 项（38%）
- **部分覆盖**: 4 项（31%）
- **未覆盖**: 4 项（31%）

## 十一、T5 exclude_ips bug 根因分析

### 11.1 Bug 描述

**现象**: 使用 trace_ip 流水线时，agent 经常忘记传 `--exclude-ips` 参数，导致报告包含已溯源的 IP。此外，用户不确定 exclude_ips 在哪些环节生效。

**发现方式**: 运行时发现。

### 11.2 exclude_ips 的完整影响链

```
┌──────────────────────────────────────────────────────────────────┐
│  Phase 1-6: self._ips 贯穿全部阶段                               │
│  exclude_ips 完全不参与数据采集、分类、查询                        │
│                                                                  │
│  Phase 1: 基础采集 (ipinfo_api + rdns_ptr)     ← 不受影响        │
│  Phase 2: 分类过滤 (classifier)                ← 不受影响        │
│  Phase 3: 深度查询 (aizhan/chinaz/fofa_host)   ← 不受影响        │
│  Phase 4: DNS 验证                             ← 不受影响        │
│  Phase 5: 端口扫描                             ← 不受影响        │
│  Phase 6: 汇总                                 ← 不受影响        │
│                                                                  │
│  Phase 7: 报告生成                                               │
│  ├── _load_exclude_ips()          读取排除文件 + 计算有效集合     │
│  ├── reporter.generate_docx_report()  Word 报告过滤 ✅           │
│  ├── generate_trace_excel()           Excel 报告过滤 ✅          │
│  └── _print_report_summary()          控制台摘要过滤 ✅          │
│                                                                  │
│  原始 JSON 数据文件: 不受影响（exclude 只在报告层过滤）           │
└──────────────────────────────────────────────────────────────────┘
```

### 11.3 两个层面的问题

#### 问题 A：使用性问题（主要问题）

| 问题 | 说明 |
|------|------|
| `--exclude-ips` 是可选参数 | agent 使用时经常忘记传 |
| 没有默认排除文件 | 每次必须手动指定文件路径 |
| 没有使用引导 | 缺少命令行输出引导使用者 |

**修复建议**：
1. 添加默认排除文件路径（如 `data/exclude_ips.txt`）
2. `--exclude-ips` 参数变为附加文件（合并默认 + 附加）
3. 如果默认文件存在，自动加载并提示

#### 问题 B：exclude 只在报告层生效（设计局限）

| 环节 | exclude 是否生效 | 影响 |
|------|-----------------|------|
| Phase 1-6 数据采集 | ❌ 不生效 | 被排除的 IP 仍会消耗 API 配额和查询时间 |
| Phase 7 Word 报告 | ✅ 生效 | 报告中不显示被排除的 IP |
| Phase 7 Excel 报告 | ✅ 生效 | 报告中不显示被排除的 IP |
| Phase 7 控制台摘要 | ✅ 生效 | 摘要中不计入被排除的 IP |
| 原始 JSON 数据 | ❌ 不生效 | 被排除的 IP 数据仍然存在于 JSON 中 |

**这意味着**：exclude_ips 只影响"最终呈现"，不影响"数据采集过程"。如果需要跳过已溯源 IP 的采集（节省 API 配额），需要在 Phase 1-6 的 IP 列表中过滤。

### 11.4 为什么 261 个测试都没有捕获？

**根因：exclude_ips 逻辑完全在 pipeline.py 中，而 pipeline.py 的测试覆盖为零。**

| 测试文件 | 覆盖范围 | 是否涉及 exclude_ips |
|---------|---------|---------------------|
| test_phase_runner.py | PhaseRunner（通用循环） | ❌ PhaseRunner 不知道 exclude_ips |
| test_batch_run.py | BaseBatchQuery.run() | ❌ run() 中没有 exclude_ips 逻辑 |
| test_trace_utils.py | trace_utils（纯函数） | ❌ 纯函数不涉及 exclude_ips |
| test_pipeline_registry.py | ChannelRegistry 集成 | ❌ 只测 registry 模式 |
| 其他 9 个测试文件 | 不涉及 pipeline | ❌ |

**具体缺失路径**：
1. `TraceIPPipeline._phase7_generate_reports()` — 零测试
2. `TraceIPPipeline._load_exclude_ips()` — 零测试
3. `Reporter.generate_docx_report(exclude_info=...)` — 零测试
4. `generate_trace_excel(exclude_info=...)` — 零测试
5. `TraceIPPipeline._print_report_summary(exclude_info=...)` — 零测试

### 11.5 应该补写的测试用例

#### 测试文件：test_pipeline_exclude.py（新建）

```
1. _load_exclude_ips — 文件不存在 → 返回 None
2. _load_exclude_ips — 文件为空 → 返回 None
3. _load_exclude_ips — 文件有 IP 但不在数据中 → 返回 None
4. _load_exclude_ips — 文件有 IP 且在数据中 → 返回正确的 exclude_info
5. _load_exclude_ips — 部分在数据中 → 只返回有效的 IP
6. _load_exclude_ips — 编码/格式异常 → 异常处理
7. _phase7_generate_reports — 无 exclude → 报告包含全部 IP
8. _phase7_generate_reports — 有 exclude → 报告不包含被排除的 IP
9. _phase7_generate_reports — exclude 后 P1 统计正确
10. reporter.generate_docx_report — exclude_info 过滤验证
11. generate_trace_excel — exclude_info 过滤验证
12. _print_report_summary — exclude 后摘要数字正确
```

#### 测试文件：test_exclude_ips_integration.py（端到端，可选）

```
1. 完整流水线 + exclude → 报告不包含被排除 IP
2. 完整流水线 + exclude → JSON 数据仍包含被排除 IP
3. 完整流水线 + 默认排除文件 → 自动加载验证
```

### 11.6 diagnose 结论

| 项目 | 结论 |
|------|------|
| Bug 类型 | 使用性问题 + 设计局限 |
| 根因 | pipeline.py 零测试覆盖；exclude_ips 只在报告层生效 |
| 影响范围 | Phase 7 报告生成（Word/Excel/摘要） |
| 优先修复 | ① 添加默认排除文件 + 使用引导 ② 补写 _load_exclude_ips 测试 |
| 架构建议 | 如需在采集阶段跳过已溯源 IP，需在 Phase 1-6 的 IP 列表中添加过滤逻辑 |

## 十二、T3 Mock 一致性审查报告

### 12.1 审查范围与结论

| 批次 | 测试文件 | Mock 类型 | 发现问题数 | 整体评价 |
|------|---------|----------|-----------|---------|
| 批次 1 | test_trace_utils / test_channel_base / test_config | 无 mock | 0 | ✅ 无问题 |
| 批次 2 | test_in_memory_* / test_protocol_conformance | 测试替身 | 1（低） | ✅ 高一致性 |
| 批次 3 | test_channel_protocol / test_channel_registry / test_pipeline_registry | patch | 3（中） | ⚠️ return_value 简化 |
| 批次 4 | test_batch_run / test_base_batch / test_phase_runner | Dummy 替身 | 4（中高） | ⚠️ 有关键遗漏 |
| 批次 5 | test_progress | 无 mock | 0 | ✅ 无问题 |

### 12.2 批次 2：InMemory 替身审查

**结论：替身与生产代码行为一致性非常高。**

所有 8 个 Protocol 方法（add_or_update_ip / delete_ip / delete_channel / get_ip_data / get_channel_data / list_all_ips / list_ip_channels / search_ips_by_channel）的核心逻辑完全匹配，返回值语义一致。

| # | 发现 | 严重度 | 说明 |
|---|------|--------|------|
| 1 | `get_all()` 返回可变内部引用 | 🟡 低 | `return self._store` 而非 `return dict(self._store)`，测试可修改内部状态。实际测试中未发生误用，但违反封装原则 |
| 2 | `get_all()` 不属于任何 Protocol | 🟡 低 | 仅作为测试探针方法，生产代码无对应。test_in_memory_writer.py 中 7 处使用、test_in_memory_reader.py 中 1 处使用 |
| 3 | 异常路径无法覆盖 | 🟡 低 | InMemory 替身不涉及文件 I/O，无法模拟写入失败、磁盘满、编码异常等生产场景 |

### 12.3 批次 3：patch mock 审查

**结论：所有 10 个渠道的 return_value 均为真实返回值的简化子集，不存在字段名错误或类型不匹配。但普遍缺少关键字段。**

#### 12.3.1 return_value 结构对比

| # | 渠道 | expected 字段数 | 真实返回字段数 | 缺失关键字段 | 严重度 |
|---|------|---------------|--------------|-------------|--------|
| 1 | fofa_host | 2 | 5+ | ports, host, protocol 等 | 🟡 低 |
| 2 | aizhan | 2 | 6 | location, isp, domain_count, **query_time** | 🟠 中 |
| 3 | port_scan | 2 | 9 | engine, scan_time, host_alive, total_scanned, open_count 等 | 🟡 低 |
| 4 | chinaz | 2 | 5 | location, isp, **query_time** | 🟠 中 |
| 5 | fofa_search | 2 | 7+ | **query_time**, fields | 🟠 中 |
| 6 | zoomeye | 2 | 5+ | **query_time** | 🟠 中 |
| 7 | rdns_ptr | 2 | 7 | query_ip, **query_time**, aliases, ip_addresses, ptr_count | 🟠 中 |
| 8 | whois | 2 | 4+ | query_target, **query_time**, whois_data 子字段 | 🟡 低 |
| 9 | ssl_cert | 2 | 9 | ip, port, issuer_cn, not_before, not_after, san_domains, **query_time** | 🟡 低 |
| 10 | ipinfo_api | 2 | 8+ | **query_time**, city, region, loc, org, timezone | 🟠 中 |

#### 12.3.2 关键发现

**发现 1：`query_time` 在 9/10 个渠道中缺失**

`query_time` 是 `format_output()` 通过 `setdefault` 注入的通用字段，在真实返回中必定存在。测试 mock 中只有 fofa_host 包含了它（因为测试是手写的）。这不影响当前测试（只验证委托模式），但**如果未来有人基于 mock 理解真实返回结构，会得到不完整的认知**。

**发现 2：patch 路径正确性**

所有 patch 路径（如 `patch('channel.fofa_host.validate_channel_key')`）在测试运行时能正确找到目标函数，因为测试文件通过 `sys.path.insert(0, ...)` 设置了正确的模块搜索路径。

**发现 3：side_effect 覆盖度**

当前覆盖的失败模式：
- `SystemExit(1)` — validate_channel_key 失败时 sys.exit(1)
- `ConnectionError` — 网络异常

未覆盖的失败模式：
- `ValueError` / `KeyError` — API 返回格式异常
- `TimeoutError` — 请求超时（不同于 ConnectionError）
- `json.JSONDecodeError` — 响应解析失败

### 12.4 批次 4：Dummy 替身审查

**结论：Dummy 替身有效覆盖了核心路径，但有关键遗漏。**

#### 12.4.1 _DummyWriter vs IPWriter

| # | 维度 | _DummyWriter | IPWriter | 差异 | 严重度 |
|---|------|-------------|---------|------|--------|
| 1 | 方法覆盖 | add_or_update_ip | add_or_update_ip, delete_ip, delete_channel, _load_data, _save_data, _init_storage | Dummy 只实现 1 个方法，但 run() 只调用 add_or_update_ip，够用 | 🟢 无影响 |
| 2 | 返回值 | 始终返回 True | 始终返回 True | 一致 | 🟢 无影响 |
| 3 | 写入失败 | 不可能失败 | 文件 I/O 可能失败（权限、磁盘满、编码异常） | **无法测试写入失败路径** | 🔴 高 |
| 4 | storage_file 属性 | 有 | 有 | 一致 | 🟢 无影响 |

#### 12.4.2 _DummyPid vs PidManager

| # | 维度 | _DummyPid | PidManager | 差异 | 严重度 |
|---|------|----------|-----------|------|--------|
| 1 | 方法覆盖 | write_pid, update_heartbeat, remove_pid | write_pid, update_heartbeat, remove_pid, read_pid, pid_file 属性 | Dummy 覆盖了 run() 使用的全部方法 | 🟢 无影响 |
| 2 | 文件操作 | 无 | 真实文件读写 | 无法测试 PID 文件损坏/权限问题 | 🟡 低 |
| 3 | 参数传递 | 忽略所有参数 | 记录参数到 _pid_data | 测试只验证"被调用"，不验证参数内容 | 🟡 低 |

#### 12.4.3 _DummyLogger vs logging.Logger

| # | 维度 | _DummyLogger | logging.Logger | 差异 | 严重度 |
|---|------|-------------|---------------|------|--------|
| 1 | 方法覆盖 | info, warning, debug, error | info, warning, debug, error + 更多 | 覆盖了全部测试中使用的级别 | 🟢 无影响 |
| 2 | 格式化 | 不格式化 | 会格式化 (%-style) | 测试不依赖格式化输出 | 🟢 无影响 |

#### 12.4.4 `__new__` + 手动属性设置模式

`_build_batch()` 使用 `__new__` 跳过 `BaseBatchQuery.__init__()`，然后手动设置属性。与 `__init__` 对比：

| __init__ 设置的属性 | __new__ 测试中是否设置 | 如果遗漏的影响 |
|--------------------|---------------------|--------------|
| ip_file | ✅ 设置 | — |
| channel_name | ✅ 设置 | — |
| no_validate | ✅ 设置 | — |
| load_stats | ✅ 设置 | — |
| pending_ips | ✅ 设置 | — |
| settings | ❌ 未设置 | `_get_delay()` 通过 settings 读取延迟，但测试中 `_get_delay` 被重写 |
| ip_writer | ❌ __init__ 中不设置 | 由子类在 run() 前设置，测试中手动设置 |
| logger | ❌ __init__ 中不设置 | 由子类设置，测试中手动设置 |
| _pid_mgr | ❌ __init__ 中不设置 | 由子类设置，测试中手动设置 |

**关键风险**：如果 `BaseBatchQuery.__init__()` 未来新增属性初始化，`_build_batch()` 不会自动同步，可能遗漏。但当前 `__init__` 的所有必要属性都已覆盖。

#### 12.4.5 PhaseRunner 测试中的 InMemoryIPWriter

PhaseRunner 测试中 InMemoryIPWriter 同时作为 writer 和 reader（data_store），而生产代码中 PhaseRunner 使用的是 IPWriter（只写）+ IPReader（只读）的组合。

| 差异 | 说明 | 严重度 |
|------|------|--------|
| 读写一体 vs 读写分离 | 生产中 writer 和 reader 是不同对象，测试中是同一个 | 🟡 低（不影响逻辑） |
| query_fn 返回 None/空dict | 测试覆盖了这两种情况，与生产代码行为一致 | 🟢 无影响 |

### 12.5 问题汇总（按严重度排序）

| # | 问题 | 严重度 | 影响范围 | 修复建议 |
|---|------|--------|---------|---------|
| 1 | _DummyWriter 无法模拟写入失败 | 🔴 高 | test_batch_run | 添加 add_or_update_ip 的 side_effect 参数，支持模拟返回 False 或抛异常 |
| 2 | 9/10 渠道 mock 缺少 query_time | 🟠 中 | test_channel_* | 在 return_value 中补充 query_time 字段，或在测试注释中注明是简化版 |
| 3 | side_effect 只覆盖 SystemExit + ConnectionError | 🟠 中 | test_channel_* | 补充 TimeoutError / json.JSONDecodeError / ValueError 等异常场景 |
| 4 | __new__ 模式与 __init__ 不同步风险 | 🟡 低 | test_batch_run | 添加注释说明哪些属性被跳过，或在 __init__ 变更时检查测试 |
| 5 | get_all() 返回可变引用 | 🟡 低 | test_in_memory_writer | 改为 `return dict(self._store)` |
| 6 | PidManager 参数传递被忽略 | 🟡 低 | test_batch_run | 可选：验证 write_pid 参数内容 |

## 十三、T4 测试业务意义审查报告

### 13.1 总体统计

| 文件 | 测试数 | 高价值 | 中价值 | 低价值 | 保留 | 合并 | 删除 |
|------|--------|--------|--------|--------|------|------|------|
| test_trace_utils.py | 26 | 17 | 6 | 3 | 20 | 6→3 | 0 |
| test_channel_base.py | 10 | 2 | 6 | 2 | 7 | 3→1 | 2 |
| test_config.py | 25 | 5 | 7 | 13 | 14 | 10→2 | 0 |
| test_in_memory_writer.py | 9 | 4 | 3 | 2 | 7 | 1 | 1 |
| test_in_memory_reader.py | 17 | 4 | 8 | 5 | 12 | 3 | 2 |
| test_protocol_conformance.py | 8 | 0 | 4 | 4 | 4 | 0 | 4 |
| test_channel_protocol.py | 36 | 4 | 30 | 2 | 14 | 18→4 | 8 |
| test_channel_registry.py | 46 | 9 | 30 | 7 | 14 | 27→3 | 9 |
| test_pipeline_registry.py | 8 | 4 | 4 | 0 | 4 | 0 | 4 |
| test_batch_run.py | 36 | 6 | 10 | 20 | 11 | 6→2 | 18 |
| test_base_batch.py | 14 | 4 | 7 | 3 | 8 | 4→1 | 5 |
| test_phase_runner.py | 10 | 6 | 3 | 1 | 8 | 2→1 | 2 |
| test_progress.py | 11 | 8 | 3 | 0 | 11 | 0 | 0 |
| **合计** | **256** | **73** | **121** | **62** | **134** | **80→17** | **55** |

> 注：合并列格式为"合并数→目标函数数"，删除含参数化压缩。

**压缩后预计测试数：134 + 17 ≈ 151 个**（从 256 降至 ~151，压缩率 41%）

### 13.2 关键发现

#### 发现 1：最大重复区域——适配器测试（可压缩 ~35 个）

**涉及文件**：test_channel_protocol.py + test_channel_registry.py

10 个渠道适配器的测试模式完全同构：
- `isinstance(ch, ChannelProtocol)` + `ch.channel_name == 'xxx'`
- `validate` 成功/失败/异常 3 个分支
- `fetch` 委托验证

建议用 `@pytest.mark.parametrize` 合并为 3 个参数化测试函数（satisfies_protocol / fetch_delegates / validate），每个函数包含 10 组参数。

#### 发现 2：第二大重复——迁移验证测试（可压缩 18 个）

**涉及文件**：test_batch_run.py

9 个渠道脚本的 `inherits_base_batch` + `channel_name` 测试完全同构，应合并为 1 个参数化测试。

#### 发现 3：纯机械验证测试（应删除 ~12 个）

| 文件 | 测试 | 删除原因 |
|------|------|---------|
| test_channel_base.py | #1-2 ChannelFetcher isinstance/hasattr | Protocol 定义变更自然报错，运行时断言无价值 |
| test_protocol_conformance.py | #1-4 isinstance/hasattr | 已被 #5-#8 功能测试完全覆盖 |
| test_batch_run.py | #19 has_run_method | 继承 ABC 必然有 run() |
| test_batch_run.py | #9 heartbeat计数 | 只验证调用次数，无业务意义 |
| test_batch_run.py | #14 elapsed≥0 | 几乎不可能失败的断言 |
| test_base_batch.py | #12-14 ABC实例化 | Python ABC 语言特性保证 |
| test_phase_runner.py | #1 init存储配置 | 纯赋值验证 |

#### 发现 4：test_progress.py 质量最高

11 个测试全部有意义，覆盖了 record/load/clear/兼容四大循环，无需删减。

#### 发现 5：最有价值的 3 个测试（守护非直觉行为）

| 测试 | 文件 | 守护的行为 |
|------|------|-----------|
| test_add_or_update_ip_overwrites_existing_channel | test_in_memory_writer.py | 同名渠道**整体替换**而非 merge |
| test_list_ip_channels_excludes_ip_key | test_in_memory_reader.py | `ip` 元数据键被过滤，不是渠道 |
| test_run_removes_pid_on_keyboard_interrupt | test_batch_run.py | Ctrl+C 中断不留僵尸 PID |

### 13.3 参数化合并建议（详细方案）

#### 合并组 1：10 个适配器 satisfies_protocol + channel_name

```python
ADAPTERS = [
    ("channel.fofa_host", "FofaHostChannel", "fofa_host"),
    ("channel.aizhan", "AizhanChannel", "aizhan"),
    ("channel.port_scan", "PortScanChannel", "port_scan"),
    ("channel.chinaz", "ChinazChannel", "chinaz"),
    ("channel.fofa_search", "FofaSearchChannel", "fofa_search"),
    ("channel.zoomeye", "ZoomeyeChannel", "zoomeye"),
    ("channel.rdns_ptr", "RdnsPtrChannel", "rdns_ptr"),
    ("channel.whois_query", "WhoisChannel", "whois"),
    ("channel.ssl_cert", "SslCertChannel", "ssl_cert"),
    ("channel.ipinfo_api", "IpinfoApiChannel", "ipinfo_api"),
]

@pytest.mark.parametrize("module,cls_name,expected", ADAPTERS)
def test_adapter_satisfies_protocol(module, cls_name, expected):
    mod = importlib.import_module(module)
    ch = getattr(mod, cls_name)()
    assert isinstance(ch, ChannelProtocol)
    assert ch.channel_name == expected
```

**影响**：压缩 ~17 个 isinstance/channel_name 测试 → 1 个参数化测试

#### 合并组 2：7 个适配器 fetch_delegates

```python
FETCH_ADAPTERS = ADAPTERS  # 同上

@pytest.mark.parametrize("module,cls_name", FETCH_ADAPTERS)
def test_adapter_fetch_delegates(module, cls_name):
    mod = importlib.import_module(module)
    ch = getattr(mod, cls_name)()
    expected = {'test': True}
    with patch(f"{module}.fetch_channel", return_value=expected):
        result = ch.fetch('1.2.3.4', key='test')
        assert result == expected
```

**影响**：压缩 ~10 个 fetch 测试 → 1 个参数化测试

#### 合并组 3：9 个迁移验证

```python
MIGRATED = [
    ("batch_fofa_host", "BatchFofaHostQuery", "fofa_host"),
    ("batch_rdns_ptr", "BatchRDNSQuery", "rdns_ptr"),
    # ... 共 9 组
]

@pytest.mark.parametrize("module,cls_name,expected", MIGRATED)
def test_batch_migration(module, cls_name, expected):
    mod = importlib.import_module(f"scripts.{module}")
    cls = getattr(mod, cls_name)
    assert issubclass(cls, BaseBatchQuery)
    assert cls.channel_name == expected
```

**影响**：压缩 18 个迁移测试 → 1 个参数化测试

#### 合并组 4：9 个 Settings 子类继承

```python
SETTINGS = [
    ("Settings",), ("FofaSettings",), ("IpinfoSettings",),
    ("AizhanSettings",), ("ChinazSettings",), ("WhoisSettings",),
    ("RdnsSettings",), ("ZoomeyeSettings",), ("SslCertSettings",),
    ("TraceIPSettings",), ("IPDomainLookupSettings",), ("IpTaggerSettings",),
]

@pytest.mark.parametrize("cls_name", SETTINGS)
def test_settings_inherits_base(cls_name):
    assert issubclass(getattr(config, cls_name), BaseIPSettings)
```

**影响**：压缩 9 个继承测试 → 1 个参数化测试

### 13.4 各文件详细建议

| 文件 | 建议 |
|------|------|
| test_trace_utils.py | has_domains/has_ports 4 个测试是薄包装函数的布尔测试，可合并 |
| test_channel_base.py | 删除 ChannelFetcher 相关 2 个测试（ChannelFetcher 将被清理） |
| test_config.py | 9 个 issubclass 测试参数化合并；安全验证部分保留 |
| test_in_memory_writer.py | 删除 return_true 测试（硬编码无意义） |
| test_in_memory_reader.py | 删除 2 个纯 Python 语义测试（空 dict/空 store） |
| test_protocol_conformance.py | 删除 4 个 isinstance/hasattr，保留 4 个功能集成测试 |
| test_channel_protocol.py | 18 个同构适配器测试 → 3 个参数化函数；保留集成测试 |
| test_channel_registry.py | 27 个同构测试 → 3 个参数化函数；删除 5 个重复 create_default_registry 测试 |
| test_pipeline_registry.py | 删除 4 个与 registry 单元测试重复的测试，保留 4 个端到端 |
| test_batch_run.py | 18 个迁移测试 → 1 个参数化函数；删除 3 个低价值 run() 测试 |
| test_base_batch.py | 删除 3 个 ABC 测试 + 合并 4 个 _is_error 为参数化 |
| test_phase_runner.py | 删除 init 测试 + 合并 None/空 dict 为参数化 |
| test_progress.py | **无需修改**，质量最高 |

## 十四、下一步行动

**T1 已完成** ✅
**T2 已完成** ✅
**T5 已完成** ✅
**T3 已完成** ✅
**T4 已完成** ✅

**下一步**: 阶段二完成（M2），进入阶段三 T6（补充高优先级测试）
