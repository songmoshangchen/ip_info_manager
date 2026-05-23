# Tasks

- [ ] Task 1: 创建 CLI 工具函数
  - [ ] SubTask 1.1: 实现 `load_ip_file(path) -> tuple[list[str], dict]`（去重/跳空行/统计）
  - [ ] SubTask 1.2: 实现 `setup_batch_logging(channel_name, log_dir)`（控制台+RotatingFileHandler）
  - [ ] SubTask 1.3: 实现 `default_progress_file(storage_file, channel_name)`
  - [ ] SubTask 1.4: 写测试 — load_ip_file 去重/跳空行/FileNotFoundError、setup_batch_logging handler 配置/不重复添加、default_progress_file 路径生成
  - [ ] 验证: `python -m pytest tests/unit/batch/test_cli.py -v` 通过

- [ ] Task 2: 创建 batch_rdns_ptr CLI 脚本（最简单，作为模板）
  - [ ] SubTask 2.1: 创建 `src/ip_info/batch/scripts/batch_rdns_ptr.py`（argparse + load_ip_file + setup_logging + BaseBatchQuery）
  - [ ] SubTask 2.2: 写测试 — CLI 参数解析、端到端运行验证
  - [ ] 验证: rdns_ptr CLI 测试通过

- [ ] Task 3: 创建 batch_ipinfo_api CLI 脚本（有额外 --no-api 参数）
  - [ ] SubTask 3.1: 创建 `src/ip_info/batch/scripts/batch_ipinfo_api.py`
  - [ ] SubTask 3.2: 写测试 — --no-api 参数传递、端到端运行验证
  - [ ] 验证: ipinfo_api CLI 测试通过

- [ ] Task 4: 创建 batch_fofa_host CLI 脚本
  - [ ] SubTask 4.1: 创建脚本 + 测试
  - [ ] 验证: fofa_host CLI 测试通过

- [ ] Task 5: 创建 batch_aizhan CLI 脚本
  - [ ] SubTask 5.1: 创建脚本 + 测试
  - [ ] 验证: aizhan CLI 测试通过

- [ ] Task 6: 创建 batch_chinaz CLI 脚本
  - [ ] SubTask 6.1: 创建脚本 + 测试
  - [ ] 验证: chinaz CLI 测试通过

- [ ] Task 7: 创建 batch_ssl_cert CLI 脚本
  - [ ] SubTask 7.1: 创建脚本 + 测试
  - [ ] 验证: ssl_cert CLI 测试通过

- [ ] Task 8: 创建 batch_whois CLI 脚本
  - [ ] SubTask 8.1: 创建脚本 + 测试
  - [ ] 验证: whois CLI 测试通过

- [ ] Task 9: 创建 batch_zoomeye CLI 脚本
  - [ ] SubTask 9.1: 创建脚本 + 测试
  - [ ] 验证: zoomeye CLI 测试通过

- [ ] Task 10: 创建 batch_fofa_search CLI 脚本
  - [ ] SubTask 10.1: 创建脚本 + 测试
  - [ ] 验证: fofa_search CLI 测试通过

- [ ] Task 11: 集成验证
  - [ ] SubTask 11.1: 运行 `python -m pytest tests/unit/ -v` 确认全部测试通过
  - [ ] SubTask 11.2: 运行 `ruff check src/ tests/unit/` 确认无 lint 错误
  - [ ] 验证: 全量测试通过 + lint 通过

# Task Dependencies

- [Task 1] → [Task 2]（CLI 工具函数先于脚本）
- [Task 2] → [Task 3-10]（模板脚本先于其余脚本）
- [Task 3-10] → [Task 11]（集成验证在所有脚本完成后）
- Task 3-10 之间无依赖，可并行
