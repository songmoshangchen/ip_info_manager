# Tasks

## Skills 链总览

> 对应重构方案第六节 "Skills 使用推荐"，Step 2.1-2.4

| Task | 重构方案对应步骤 | 推荐 Skill 链 |
|------|-----------------|--------------|
| Task 1 | Step 2.1 ChannelProtocol 协议 | `tdd` → `git-commit` |
| Task 2 | Step 2.1 ChannelError 异常体系 | `tdd` → `git-commit` |
| Task 3 | Step 2.2 ChannelRegistry | `tdd` → `git-commit` |
| Task 4 | Step 2.3 InMemoryChannel | `tdd` → `git-commit` |
| Task 5 | Step 2.4 BaseChannelAdapter | `brainstorming` → `tdd` → `git-commit` |
| Task 6 | 统一导出 + 协议一致性 | `tdd` → `git-commit` |

---

- [x] Task 1: 定义 ChannelProtocol 和 ChannelFetcher 协议 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 1.1: 使用 `tdd` skill — RED：创建 `tests/unit/channel/test_protocols.py`，编写 isinstance 测试
  - [x] SubTask 1.2: 使用 `tdd` skill — GREEN：创建 `src/ip_info/channel/protocols.py`，定义两个 Protocol
  - [x] SubTask 1.3: 使用 `git-commit` skill 提交

- [x] Task 2: 定义 ChannelError 异常体系 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 2.1: 使用 `tdd` skill — RED：创建 `tests/unit/channel/test_errors.py`
  - [x] SubTask 2.2: 使用 `tdd` skill — GREEN：创建 `src/ip_info/channel/errors.py`
  - [x] SubTask 2.3: 使用 `git-commit` skill 提交

- [x] Task 3: 实现 ChannelRegistry 注册表 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 3.1: 使用 `tdd` skill — RED：创建 `tests/unit/channel/test_registry.py`
  - [x] SubTask 3.2: 使用 `tdd` skill — GREEN：创建 `src/ip_info/channel/registry.py`
  - [x] SubTask 3.3: 使用 `git-commit` skill 提交

- [x] Task 4: 实现 InMemoryChannel 测试替身 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 4.1: 使用 `tdd` skill — RED：创建 `tests/unit/channel/test_in_memory_channel.py`
  - [x] SubTask 4.2: 使用 `tdd` skill — GREEN：创建 `src/ip_info/channel/in_memory.py`
  - [x] SubTask 4.3: 使用 `git-commit` skill 提交

- [x] Task 5: 实现 BaseChannelAdapter 适配器基类 [Skill: `brainstorming` → `tdd` → `git-commit`]
  - [x] SubTask 5.1: 使用 `brainstorming` skill 确认 6 个设计决策（异常模式、_request 返回值、调用链、delay 处理、disabled 管理、日志策略）
  - [x] SubTask 5.2: 使用 `tdd` skill — RED：创建 `tests/unit/channel/test_adapter.py`，13 个测试
  - [x] SubTask 5.3: 使用 `tdd` skill — GREEN：创建 `src/ip_info/channel/adapter.py`
  - [x] SubTask 5.4: 使用 `git-commit` skill 提交

- [x] Task 6: 统一导出 + 协议一致性测试 [Skill: `tdd` → `git-commit`]
  - [x] SubTask 6.1: 更新 `src/ip_info/channel/__init__.py`，统一导出 7 个公开类
  - [x] SubTask 6.2: 使用 `tdd` skill — RED：创建 `tests/unit/channel/test_protocol_conformance.py`
  - [x] SubTask 6.3: 使用 `tdd` skill — GREEN：isinstance 检查全部通过
  - [x] SubTask 6.4: 使用 `git-commit` skill 提交

# Task Dependencies

- [Task 1] 依赖 [store-layer] 完成
- [Task 2] 无前置依赖（可与 Task 1 并行）
- [Task 3] 依赖 [Task 1, Task 2]
- [Task 4] 依赖 [Task 1, Task 2]
- [Task 5] 依赖 [Task 1, Task 2]
- [Task 6] 依赖 [Task 1, Task 2, Task 3, Task 4, Task 5]

# Skill 使用说明

> 对应重构方案 6.1 节 "各阶段推荐 Skills 链"

- **`tdd`**：Task 1-6 的核心 Skill，每个 Task 都走 RED → GREEN → REFACTOR 循环
- **`brainstorming`**：Task 5 开始前，确认适配器基类设计决策
- **`git-commit`**：每个 Task 完成后使用，生成规范化的 commit message（含中文翻译）
- **`diagnose`**：如遇测试失败且原因不明时使用
