# 架构分析报告：Deepening Opportunities

> 基于 `improve-codebase-architecture` skill 分析，2026-05-18

## 分析方法

阅读了项目全部核心源代码（~30 个文件），结合 CONTEXT.md 领域术语和 docs/adr/ 架构决策记录，
识别代码库中的架构摩擦点：浅层模块、紧耦合、重复代码、不可测试的接口。

---

## 候选 ①：`TraceIPPipeline` 是上帝类（~1180 行）

**涉及文件：** `scenarios/trace_ip/pipeline.py`

**问题：** Pipeline 一个类承担了 7 个阶段的全部逻辑。每个 Phase 1/3/4/5 都重复了相同的模式：
加载进度 → 检查 JSON 已有数据 → 计算待处理 IP → 遍历查询 → 保存进度 → 更新心跳 → 计算 ETA。
这段"进度-查询-写入"循环在 pipeline.py 中出现了 **4 次**，每次约 80-120 行，只有渠道名和 settings 不同。

**提议：** 抽取一个 **PhaseRunner** 深层模块，封装"进度恢复 + 渠道并行查询 + 批量写入 + ETA"的通用循环。
每个 Phase 只需声明"我用哪些渠道、哪些 settings"。

**收益：**
- **Locality** — 进度/查询/写入的 bug 集中在一个模块，而非散布在 4 个 Phase 方法中
- **可测试性** — 可以 mock PhaseRunner 来测试单个 Phase 的业务逻辑，无需真实网络/文件 IO
- pipeline.py 从 ~1180 行降到 ~400 行

---

## 候选 ②：10 个批量脚本（`scripts/batch_*.py`）大量复制粘贴

**涉及文件：** `scripts/batch_fofa_host.py`、`scripts/batch_rdns_ptr.py` 等 10 个文件

**问题：** `BatchFofaHostQuery` 和 `BatchRDNSQuery` 的代码几乎完全相同
（`_load_ip_file`、`_load_progress`、`_save_progress`、`_load_pending_ips`、ETA 计算、
KeyboardInterrupt 处理、PID 管理）。唯一的差异是：调用哪个 `fetch_channel`、用哪个 Settings、打印什么结果。
10 个脚本意味着同样的逻辑 **复制了 10 份**。

**提议：** 抽取一个 **BaseBatchRunner** 基类或通用函数，封装所有通用逻辑。
每个渠道的批量脚本只需定义差异部分（fetch_func、settings_cls、print_result）。

**收益：**
- **Locality** — 进度管理、ETA 计算、中断处理只需维护一处
- **可测试性** — 基类逻辑写一次测试，10 个脚本都受益
- 新增批量脚本从 ~200 行降到 ~30 行

---

## 候选 ③：`IPWriter` / `IPReader` 没有接口缝隙（Seam） ⭐ 最优先

**涉及文件：** `writer.py`、`reader.py`

**问题：** IPWriter 和 IPReader 直接操作 JSON 文件，没有任何抽象接口。
所有依赖它们的模块（channel、pipeline、batch scripts）都通过 `from writer import IPWriter` 硬编码。
**无法在测试中注入 mock 存储**，导致当前整个项目只有 1 个测试文件（test_progress.py）。

**提议：** 定义 `IPDataReader` / `IPDataWriter` 协议（Protocol），让 IPReader/IPWriter 实现它。
同时提供一个 `InMemoryIPStore` 用于测试。

**收益：**
- **真正的 seam** — 两个 adapter（文件存储 vs 内存存储）= 真正的接口缝隙
- **可测试性飞跃** — 所有 channel、pipeline、batch 都可以在无文件 IO 的环境下测试
- 这是整个 TDD 重构的 **前置条件**

---

## 候选 ④：Channel 模块没有共享协议

**涉及文件：** `channel/_template.py` 及所有 `channel/*.py`

**问题：** `_template.py` 定义了 5 部分结构，但这只是文档约定，没有代码层面的约束。
每个 channel 文件是独立模块函数的集合，没有共享接口。
Pipeline 中通过 `from channel.fofa_host import fetch_channel as fetch_fofa_host` 硬编码导入。

**提议：** 定义 `ChannelProtocol`（Python Protocol），每个 channel 实现它。
Pipeline 通过注册/查找而非硬编码导入。

**收益：**
- **可测试性** — 可以用 mock channel 测试 pipeline，无需真实网络请求
- **可扩展性** — 新增 channel 自动可用，无需修改 pipeline
- **删除测试** — 如果删除某个 channel，pipeline 不需要任何改动

---

## 候选 ⑤：`reporter.py` 混合了领域逻辑和展示逻辑

**涉及文件：** `scenarios/trace_ip/reporter.py`（~800 行）

**问题：** TextTraceReporter 同时包含：
- **领域逻辑**：`_extract_all_domains()`、`_is_china_ip()`、`_has_ports()`、`_trace_priority()`
- **展示逻辑**：800 行的 `generate_docx_report()` 方法

`excel_exporter.py` 也独立实现了 `_trace_priority()` 和 `_extract_all_domains()`——
同一个领域函数被复制了两份。

**提议：** 将领域逻辑抽取到 **IPInfoExtractor** 模块。
Reporter 和 ExcelExporter 都依赖它。

**收益：**
- **Locality** — 优先级计算逻辑只维护一处
- **可测试性** — 纯函数可以独立测试
- 消除 reporter.py 和 excel_exporter.py 之间的逻辑重复

---

## 候选 ⑥：Pipeline 的渠道配置硬编码

**涉及文件：** `scenarios/trace_ip/pipeline.py` 顶部导入

**问题：** Pipeline 顶部硬编码了渠道导入，每个 Phase 方法中渠道的启用/禁用通过布尔字段控制，
但渠道的"存在"是编译时绑定的。

**提议：** 通过渠道注册表（Channel Registry）或依赖注入，让 Phase 在运行时查找可用渠道。

**收益：**
- 新增渠道时无需修改 pipeline.py
- 可以在测试中注入受限渠道集合
- 与候选 ④ 配合形成完整的渠道抽象层

---

## 候选 ⑦：`apply_delay()` / `format_output()` 在每个 channel 中重复

**涉及文件：** 所有 `channel/*.py`

**问题：** `apply_delay(delay)` 和 `format_output(data)` 在每个 channel 中都是完全相同的实现。
`sys.path.insert(0, ...)` 也是每个文件重复。

**提议：** 提取到 channel 基类或工具函数中。

**收益：**
- 消除 10 份相同代码
- 可测试性提升（delay 可以被 mock）

---

## 候选优先级矩阵

| # | 候选 | 影响范围 | 可测试性提升 | TDD 前置依赖 |
|---|------|---------|-------------|-------------|
| ① | Pipeline 上帝类拆分 | 极大 | ⭐⭐⭐⭐⭐ | 依赖 ③ |
| ② | 批量脚本去重 | 大 | ⭐⭐⭐⭐ | 依赖 ③ |
| **③** | **IPWriter/Reader 接口缝隙** | **全局** | **⭐⭐⭐⭐⭐** | **无（最优先）** |
| ④ | Channel Protocol | 大 | ⭐⭐⭐⭐ | 可与 ③ 并行 |
| ⑤ | Reporter 领域逻辑分离 | 中 | ⭐⭐⭐ | 独立 |
| ⑥ | 渠道注册表 | 中 | ⭐⭐⭐ | 依赖 ④ |
| ⑦ | channel 公共函数提取 | 小 | ⭐⭐ | 独立 |

## 建议实施顺序

```
③ → ④/⑦ → ⑤ → ① → ② → ⑥
```

③ 是整个 TDD 重构的基础——没有可 mock 的存储层，其他模块的测试都难以编写。
