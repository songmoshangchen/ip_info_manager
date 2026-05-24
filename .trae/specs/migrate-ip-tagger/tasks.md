# Tasks

- [x] Task 1: 创建 processors/tagger/ 目录结构
  - [x] 1.1 创建 `src/ip_info/processors/__init__.py`
  - [x] 1.2 创建 `src/ip_info/processors/tagger/__init__.py`

- [x] Task 2: 迁移 matcher.py（核心匹配算法）+ TDD 测试
  - [x] 2.1 编写 `tests/unit/processors/test_matcher.py` 测试（先写测试）
  - [x] 2.2 实现 `src/ip_info/processors/tagger/matcher.py`（ip_to_int, parse_entry_to_range, match_sorted_ips_streaming, _process_batch）

- [x] Task 3: 迁移 manifest.py（manifest 加载/验证）+ TDD 测试
  - [x] 3.1 编写 `tests/unit/processors/test_manifest.py` 测试（先写测试）
  - [x] 3.2 实现 `src/ip_info/processors/tagger/manifest.py`（load_manifest, validate_manifest）

- [x] Task 4: 实现 BatchTagger (runner.py) + TDD 测试
  - [x] 4.1 编写 `tests/unit/processors/test_runner.py` 测试（先写测试）
  - [x] 4.2 实现 `src/ip_info/processors/tagger/runner.py`（BatchTagger 类，实现 BatchRunner Protocol）

- [x] Task 5: 创建 CLI 脚本 `batch_tagger.py`
  - [x] 5.1 创建 `src/ip_info/batch/batch_tagger.py`

- [x] Task 6: 迁移配置文件 `config/ip_tagger/`
  - [x] 6.1 复制 `legacy/config/ip_tagger/` → `config/ip_tagger/`

- [x] Task 7: 运行全量测试 + ruff 检查
  - [x] 7.1 运行 `python -m pytest tests/unit/ -q`
  - [x] 7.2 运行 `ruff check src/ip_info/processors/`

# Task Dependencies
- Task 2, Task 3 可并行
- Task 4 依赖 Task 2, Task 3
- Task 5 依赖 Task 4
- Task 6 无依赖，可并行
- Task 7 依赖所有前置任务
