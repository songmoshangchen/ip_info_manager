# Tasks

- [x] Task 1: 创建 pipeline/ 目录结构
  - [x] 1.1 创建 `src/ip_info/pipeline/__init__.py`
  - [x] 1.2 创建 `tests/unit/pipeline/__init__.py`

- [x] Task 2: TDD 实现 Phase Protocol + PhaseResult + 测试 + git commit
  - [x] 2.1 编写 `tests/unit/pipeline/test_phase.py` 测试（先写测试）
  - [x] 2.2 实现 `src/ip_info/pipeline/phase.py`
  - [x] 2.3 git commit

- [x] Task 3: TDD 实现 Pipeline 编排器 + PipelineResult + 测试 + git commit
  - [x] 3.1 编写 `tests/unit/pipeline/test_pipeline.py` 测试（先写测试）
  - [x] 3.2 实现 `src/ip_info/pipeline/pipeline.py`
  - [x] 3.3 git commit

- [x] Task 4: 运行全量测试 + ruff 检查 + git commit

# Task Dependencies
- Task 2 先行（Phase Protocol 定义）
- Task 3 依赖 Task 2
- Task 4 依赖所有前置任务

# 开发规范
- TDD：先写测试再写实现
- git-commit：每个逻辑单元完成后提交
- 测试策略：mock 到存储层为止，使用 InMemoryIPWriter/InMemoryIPReader
