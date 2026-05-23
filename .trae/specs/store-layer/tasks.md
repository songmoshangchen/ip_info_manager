# Tasks

## Skills 链总览

> 对应重构方案第六节 "Skills 使用推荐"，每个 Task 标注应使用的 Skill 链。

| Task | 重构方案对应步骤 | 推荐 Skill 链 |
|------|-----------------|--------------|
| Task 1 | Step 1.1 项目骨架 | `brainstorming` → 编码 → `setup-pre-commit` |
| Task 2 | Step 1.2-1.3 协议定义 | `tdd` → `git-commit` |
| Task 3 | Step 1.4 InMemoryIPWriter | `tdd` → `git-commit` |
| Task 4 | Step 1.5 InMemoryIPReader | `tdd` → `git-commit` |
| Task 5 | Step 1.5 批量查询扩展 | `tdd` → `git-commit` |
| Task 6 | Step 1.6 读写一致性 | `tdd` → `git-commit` |
| Task 7 | Step 1.7 异常边界 | `tdd` → `git-commit` |
| Task 8 | Step 1.8 JSON IPWriter | `tdd` → `git-commit` |
| Task 9 | Step 1.9 JSON IPReader | `tdd` → `git-commit` |
| Task 10 | Step 1.10 线程安全 | `tdd` → `git-commit` |
| Task 11 | 统一导出 + 一致性 | `tdd` → `git-commit` |

---

- [x] Task 1: 创建 pyproject.toml 项目骨架 [Skill: `brainstorming` → 编码 → `setup-pre-commit`]
  - [x] SubTask 1.1: 使用 `brainstorming` skill 确认包名、依赖、目录结构等基础决策
  - [x] SubTask 1.2: 创建 `pyproject.toml`，配置 `src/ip_info` 为包源（编码）
  - [x] SubTask 1.3: 验证 `pip install -e .` 成功，`import ip_info` 可用
  - [x] SubTask 1.4: 使用 `setup-pre-commit` skill 配置 Python pre-commit hooks（ruff + pytest，排除 legacy/）

- [x] Task 2: 定义 IPDataWriter 和 IPDataReader Protocol [Skill: `tdd` → `git-commit`]
  - [x] SubTask 2.1: 使用 `tdd` skill — RED：创建 `tests/unit/store/test_protocols.py`，编写 isinstance 测试
  - [x] SubTask 2.2: 使用 `tdd` skill — GREEN：创建 `src/ip_info/store/protocols.py`，定义两个 Protocol（`@runtime_checkable`）
  - [x] SubTask 2.3: 使用 `git-commit` skill 提交（commit message 含中文翻译）

- [x] Task 3: 实现 InMemoryIPWriter 测试替身 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 3.1: 使用 `tdd` skill — RED：创建 `tests/unit/store/test_in_memory_writer.py`，编写测试（创建 IP、追加渠道、覆盖渠道、删除 IP、删除渠道、异常返回 False）
  - [x] SubTask 3.2: 使用 `tdd` skill — GREEN：创建 `src/ip_info/store/in_memory.py`，实现 `InMemoryIPWriter`
  - [x] SubTask 3.3: 使用 `git-commit` skill 提交

- [x] Task 4: 实现 InMemoryIPReader 测试替身 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 4.1: 使用 `tdd` skill — RED：创建 `tests/unit/store/test_in_memory_reader.py`，编写测试（读取 IP、读取渠道、列出 IP、列出渠道、搜索、空数据）
  - [x] SubTask 4.2: 使用 `tdd` skill — GREEN：在 `src/ip_info/store/in_memory.py` 中添加 `InMemoryIPReader`
  - [x] SubTask 4.3: 使用 `git-commit` skill 提交

- [x] Task 5: 实现批量查询接口 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 5.1: 使用 `tdd` skill — RED：创建 `tests/unit/store/test_batch_query.py`，编写测试（get_ips_data 批量获取、空列表、list_all_ips_data 无排除、排除部分 IP、排除不存在的 IP）
  - [x] SubTask 5.2: 使用 `tdd` skill — GREEN：在 InMemoryIPWriter、InMemoryIPReader 中实现 `get_ips_data` 和 `list_all_ips_data`
  - [x] SubTask 5.3: 使用 `git-commit` skill 提交

- [x] Task 6: 读写一致性测试 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 6.1: 使用 `tdd` skill — RED：创建 `tests/unit/store/test_read_write_consistency.py`，验证 InMemoryIPWriter 同时实现 Reader 接口
  - [x] SubTask 6.2: 使用 `tdd` skill — GREEN：确认 InMemoryIPWriter 实现了 IPDataReader 所有方法（含批量查询），必要时补充实现
  - [x] SubTask 6.3: 使用 `git-commit` skill 提交

- [x] Task 7: 异常边界行为测试 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 7.1: 使用 `tdd` skill — RED：在已有测试文件中补充边界测试（删除不存在 IP/渠道、读取不存在数据、搜索无匹配）
  - [x] SubTask 7.2: 使用 `tdd` skill — GREEN：确认所有边界情况返回 False/None/空列表，必要时修复
  - [x] SubTask 7.3: 使用 `git-commit` skill 提交

- [x] Task 8: JSON 文件 IPWriter 实现 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 8.1: 使用 `tdd` skill — RED：创建 `tests/unit/store/test_json_writer.py`，编写测试（文件/目录自动创建、写入、删除 IP、删除渠道、IO 异常透传）
  - [x] SubTask 8.2: 使用 `tdd` skill — GREEN：创建 `src/ip_info/store/json_store.py`，实现 `IPWriter` 类（含 `threading.Lock`，不依赖 Settings）
  - [x] SubTask 8.3: 使用 `git-commit` skill 提交

- [x] Task 9: JSON 文件 IPReader 实现 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 9.1: 使用 `tdd` skill — RED：创建 `tests/unit/store/test_json_reader.py`，编写测试（从文件读取、文件不存在时返回空、端到端读写闭环、批量查询闭环）
  - [x] SubTask 9.2: 使用 `tdd` skill — GREEN：在 `src/ip_info/store/json_store.py` 中实现 `IPReader` 类（含批量查询）
  - [x] SubTask 9.3: 使用 `git-commit` skill 提交

- [x] Task 10: 线程安全验证 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 10.1: 使用 `tdd` skill — RED：创建 `tests/unit/store/test_json_threadsafe.py`，编写并发写入测试（10 线程 × 5 IP = 50 条无丢失）
  - [x] SubTask 10.2: 使用 `tdd` skill — GREEN：确认 `IPWriter` 的 Lock 保护正确，必要时修复
  - [x] SubTask 10.3: 使用 `git-commit` skill 提交

- [x] Task 11: 统一导出 + 协议一致性测试 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 11.1: 更新 `src/ip_info/store/__init__.py`，统一导出所有公开类
  - [x] SubTask 11.2: 使用 `tdd` skill — RED：创建 `tests/unit/store/test_protocol_conformance.py`，验证所有实现满足对应 Protocol
  - [x] SubTask 11.3: 使用 `tdd` skill — GREEN：确保 isinstance 检查全部通过
  - [x] SubTask 11.4: 使用 `git-commit` skill 提交

# Task Dependencies

- [Task 1] 无前置依赖，最先执行
- [Task 2] 依赖 [Task 1]
- [Task 3] 依赖 [Task 2]
- [Task 4] 依赖 [Task 2]
- [Task 5] 依赖 [Task 3, Task 4]
- [Task 6] 依赖 [Task 3, Task 4, Task 5]
- [Task 7] 依赖 [Task 3, Task 4]
- [Task 8] 依赖 [Task 2]
- [Task 9] 依赖 [Task 2, Task 8]
- [Task 10] 依赖 [Task 8]
- [Task 11] 依赖 [Task 3, Task 4, Task 8, Task 9]

# Skill 使用说明

> 对应重构方案 6.1 节 "各阶段推荐 Skills 链"

- **`brainstorming`**：在 Task 1 开始前，确认包名、目录结构、依赖等基础决策
- **`setup-pre-commit`**：在 Task 1 完成后配置 pre-commit hooks（Husky + lint-staged）
- **`tdd`**：Task 2-11 的核心 Skill，每个 Task 都走 RED → GREEN → REFACTOR 循环
- **`git-commit`**：每个 Task 完成后使用，生成规范化的 commit message（含中文翻译）
- **`diagnose`**：如遇测试失败且原因不明时使用（重构方案 6.3 节）
- **`grill-me`**：如测试全绿但想检查设计质量时使用（重构方案 6.3 节）
