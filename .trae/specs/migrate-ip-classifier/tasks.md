# Tasks

- [x] Task 1: 创建 processors/classifier/ 目录结构
  - [x] 1.1 创建 `src/ip_info/processors/classifier/__init__.py`

- [x] Task 2: 迁移 rules.py（规则加载/合并）+ TDD 测试
  - [x] 2.1 编写 `tests/unit/processors/test_classifier_rules.py` 测试
  - [x] 2.2 实现 `src/ip_info/processors/classifier/rules.py`

- [x] Task 3: 迁移 engine.py（IPClassifier 匹配引擎）+ TDD 测试
  - [x] 3.1 编写 `tests/unit/processors/test_classifier_engine.py` 测试
  - [x] 3.2 实现 `src/ip_info/processors/classifier/engine.py`

- [x] Task 4: 实现 BatchClassifier (runner.py) + TDD 测试
  - [x] 4.1 编写 `tests/unit/processors/test_classifier_runner.py` 测试
  - [x] 4.2 实现 `src/ip_info/processors/classifier/runner.py`

- [x] Task 5: 创建 CLI 脚本 `batch_classifier.py`
  - [x] 5.1 创建 `src/ip_info/batch/batch_classifier.py`

- [x] Task 6: 迁移配置文件 `config/classifier/`
  - [x] 6.1 复制 `legacy/scenarios/trace_ip/classifiers/` → `config/classifier/`

- [x] Task 7: 运行全量测试 + ruff 检查

# Task Dependencies
- Task 2, Task 3 可并行
- Task 4 依赖 Task 2, Task 3
- Task 5 依赖 Task 4
- Task 6 无依赖，可并行
- Task 7 依赖所有前置任务
