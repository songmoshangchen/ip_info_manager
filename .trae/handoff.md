# Handoff: RDNS 分类闭环管理

## 项目概况

IP 信息采集流水线，4 阶段架构：
- Phase 1: 基础情报采集 (ipinfo_api, rdns_ptr)
- Phase 2: 分类+标签 (classifier, tagger)
- Phase 3: 深度查询 (aizhan, chinaz, fofa_host) — 并发
- Phase 4: 验证+扫描 (dns_verify, port_scan/nmap) — 并发

## 当前状态

941 测试全部通过，ruff lint 全部通过。

```
issues/
├── 008-add-fscan-channel.md     ← ❌ 未开始（用户说排到最后）
├── 015-pipeline-builder.md      ← ⚠️ 部分完成（Builder+脚本迁移完成，渠道注册表自动发现未做）
├── 016-trace-judge-excel.md     ← ✅ 已完成
└── 017-trace-judge-excel-lessons.md ← ✅ 已完成（实战心得）
```

## 已完成：RDNS 分类闭环管理

### 设计文档

`docs/superpowers/specs/2026-05-28-rdns-classify-management-design.md`

### 核心功能

Export → 人工审查 → Import 闭环，将"其他"分类的 RDNS 逐步消化到 `builtin_rules.json`（通用规则）和 `custom_rules.json`（异常规则）。

### 新增/修改文件

| 文件 | 说明 |
|------|------|
| `src/ip_info/export/rdns_classify_excel.py` | 导出模块：从存储层读数据 → 生成 Excel |
| `src/ip_info/export/rdns_classify_import.py` | 导入核心：`merge_rules` 纯函数 + `import_rdns_rules` I/O 层 |
| `scripts/import_rdns_rules.py` | CLI 入口脚本 |
| `tests/unit/export/test_rdns_classify.py` | 20 个行为测试（不测私有函数） |
| `src/ip_info/pipeline/phases/phase2_classify.py` | 增加 output_dir/prefix 参数，分类后自动导出 |
| `scripts/run_pipeline.py` | 传入 output_dir/prefix |

### 架构设计

```
export/rdns_classify_excel.py
├── export_unclassified_rdns(reader, output_dir, prefix, rules_dir) → int
├── _extract_unclassified_hostnames(reader) → list[str]
├── _load_builtin_samples(rules_dir) → list[dict]
├── _generate_example_hostname(pattern) → str
├── _build_sheet1(ws, hostnames)
└── _build_sheet2(ws, samples)

export/rdns_classify_import.py
├── validate_row(row, existing_categories) → list[str]    ← 纯函数
├── merge_rules(rows, existing_categories, custom_rules)   ← 纯函数
│       → tuple[OrderedDict, list[str]]
└── import_rdns_rules(excel_path, rules_dir, dry_run)      ← I/O 层
        → tuple[int, list[str]]
```

### Excel 格式

**Sheet 1: 未分类RDNS** — 10 列
- is_sample（说明/样例/空）| hostname | field | category | match_type | match_value | note | new_label | new_description | new_need_deep_query
- 预填说明行 + 样例行 + 数据行
- 样例行覆盖所有 6 个现有 category + 1 个新分类样例

**Sheet 2: 参考样例** — 从 builtin_rules.json 提取，按 category 分组

### 集成点

- `phase2_classify.py` — 分类完成后自动调用 `export_unclassified_rdns()`，有未分类时打印提示
- `run_pipeline.py` — 传入 `output_dir` 和 `prefix`

### 测试策略

- 20 个行为测试，全部通过公共接口验证
- 不测试任何私有函数（`_` 前缀）
- `merge_rules` 为纯函数，测试零 I/O（内存数据）
- Excel 读取用 `_find_col(headers, name)` 动态定位列
- `_make_reader()` 直接用 dict 构造 `InMemoryIPReader`，不访问私有属性

### TDD 重构记录

初始实现后进行了 TDD 重构：
1. 删除了对 `_extract_unclassified_hostnames`、`_generate_example_hostname`、`_load_builtin_samples` 私有函数的测试（12 个）
2. `merge_rules` 从 `merge_rules(rows, rules_dir)` 重构为 `merge_rules(rows, existing_categories, custom_rules)` 纯函数
3. `_make_store` 改为 `_make_reader`，不再访问 `writer._store` 私有属性
4. 新增 `test_mixed_valid_and_invalid_rows` 行为测试

## 剩余架构机会

| # | 问题 | 优先级 | 说明 |
|---|------|--------|------|
| 8 | Phase 双层 run() 抽象职责模糊 | P2 | Phase 2/4 的 run() 只是薄包装 |
| 9 | 渠道注册表自动发现 | P2 | `_try_channel()` if-elif 硬编码 |
| 10 | IPDataWriter 缺少批量操作 | P2 | 1000 IP = 1000 次全量 JSON 读写 |

## 后续测试改进计划

### P1: vcr.py 替换手工 mock response

| Channel | 当前方式 | vcr.py 收益 |
|---------|---------|------------|
| ipinfo_api / ipinfo_free | MagicMock 返回 JSON | 录制真实响应，验证字段完整性 |
| fofa_search / fofa_host | MagicMock 返回 JSON | Fofa 响应结构复杂，录制更可靠 |
| aizhan / chinaz | MagicMock 返回 HTML | HTML 结构易变，录制真实响应更可靠 |
| ssl_cert / rdns_ptr | patch socket 调用 | 不适合 vcr.py，保持现有 mock |

### P1: freezegun 替换 time.sleep mock

- 替换 `patch("time.sleep")`，验证 `query_time` 更精确
- 跳过 `time.sleep(n)` 减少测试时间

### P2: 端到端测试

- CLI 入口完成后，编写 `tests/e2e/` 测试套件
- 使用 vcr.py cassette 回放真实 API 响应

## 测试替身策略

| 类型 | 使用位置 |
|------|----------|
| Fake | FakeChannel (test_phases, test_builder, test_phase_data_flow, test_domain_trace), InMemoryIPReader (test_rdns_classify, test_trace_judge_excel), InMemoryIPWriter/Reader (集成测试) |
| Stub | _fake_batch_verify (test_dns_runner, test_dns_verify_only, test_domain_trace) |
| Mock | patch(requests.get) — channel HTTP 测试, patch(nmap.PortScanner) — port_scan, patch(socket) — rdns_ptr/ssl_cert/dns_verifier, patch(time.sleep) — adapter delay |

## 技术栈

- Python 3.12+, pytest (`pytest tests/`)
- 941 测试全部通过
- pre-commit hooks: ruff-format + ruff-check
- Spec 文档: `.trae/specs/arch-deepening/` (全部完成)

## 建议使用的 Skills

- `tdd` — 开发循环（先写测试再写代码）
- `git-commit` — 提交
- `fake-driven-testing` — 集成测试策略
