# Tasks

- [x] Task 1: 修改 load_ips() 内置 IP 格式校验 + 测试 + git commit
  - [x] 1.1 更新 `tests/unit/utils/test_load_ips.py` 测试：混合有效/无效 IP、全部有效、全部无效、注释行不受影响
  - [x] 1.2 修改 `src/ip_info/utils/load_ips.py`：添加 ipaddress.ip_address() 校验，无效 IP 记录 WARNING
  - [x] 1.3 运行测试确认通过（含已有测试不回归）
  - [ ] 1.4 git commit

- [x] Task 2: 创建 pipeline/phases/ 目录结构
  - [x] 2.1 创建 `src/ip_info/pipeline/phases/__init__.py`（初始为空）

- [x] Task 3: TDD 实现 filter_ips_by_classification + 测试 + git commit
  - [x] 3.1 编写 `tests/unit/pipeline/test_filter_ips.py` 测试：正常过滤、全部被过滤、无分类数据 IP 默认保留
  - [x] 3.2 实现 `src/ip_info/pipeline/filter_ips.py`：从 reader 读取 classifier 数据，按 need_deep_query 过滤
  - [x] 3.3 运行测试确认通过
  - [ ] 3.4 git commit

- [x] Task 4: TDD 实现 SqliteDomainCache + 测试 + git commit
  - [x] 4.1 编写 `tests/unit/store/test_sqlite_cache.py` 测试：正常读写、不存在域名、覆盖写入、并发安全、数据库自动创建
  - [x] 4.2 实现 `src/ip_info/store/sqlite_cache.py`：threading.local + WAL 模式 + INSERT OR REPLACE
  - [x] 4.3 运行测试确认通过
  - [ ] 4.4 git commit

- [x] Task 5: TDD 实现 Phase 1 (BasicCollectPhase) + 测试 + git commit
  - [x] 5.1 编写测试：正常执行（mock ipinfo+rdns 渠道，验证 writer 数据）、空输入、渠道验证失败、两渠道都失败
  - [x] 5.2 实现 `src/ip_info/pipeline/phases/phase1_basic.py`：ThreadPoolExecutor 并行 BaseBatchQuery + run_concurrent
  - [x] 5.3 运行测试确认通过
  - [ ] 5.4 git commit

- [x] Task 6: TDD 实现 Phase 2 (ClassifyTagPhase) + 测试 + git commit
  - [x] 6.1 编写测试：分类+标签顺序执行（验证 writer 中 classifier/tagger 数据）、no_tagger=True、空输入
  - [x] 6.2 实现 `src/ip_info/pipeline/phases/phase2_classify.py`：BatchClassifier → BatchTagger
  - [x] 6.3 运行测试确认通过
  - [ ] 6.4 git commit

- [x] Task 7: TDD 实现 Phase 3 (DeepQueryPhase) + 测试 + git commit
  - [x] 7.1 编写测试：三渠道并行（mock aizhan/chinaz/fofa，验证 writer 数据）、空输入、部分渠道验证失败
  - [x] 7.2 实现 `src/ip_info/pipeline/phases/phase3_deep.py`：ThreadPoolExecutor 并行 BaseBatchQuery
  - [x] 7.3 运行测试确认通过
  - [ ] 7.4 git commit

- [x] Task 8: TDD 实现 Phase 4 (VerifyScanPhase) + 测试 + git commit
  - [x] 8.1 编写测试：DNS 验证 + Nmap 端口扫描并行（验证 domain_verify 和 port_scan 写入）、空输入、无 domain_cache
  - [x] 8.2 实现 `src/ip_info/pipeline/phases/phase4_verify_scan.py`：ThreadPoolExecutor 并行 BatchDnsVerify + run_concurrent(PortScanChannel)
  - [x] 8.3 运行测试确认通过
  - [ ] 8.4 git commit

- [x] Task 9: 更新 __init__.py 导出 + 运行全量测试 + ruff 检查 + git commit
  - [x] 9.1 更新 `src/ip_info/pipeline/phases/__init__.py` 导出所有 Phase 类
  - [x] 9.2 运行 `python -m pytest tests/unit/ -q` 全量测试（680 passed）
  - [x] 9.3 运行 `ruff check` + `ruff format` 检查
  - [ ] 9.4 git commit

# Task Dependencies
- Task 1 (load_ips) 和 Task 2 (目录结构) 必须最先完成
- Task 3 (filter_ips) 依赖 Task 2
- Task 4 (SqliteDomainCache) 可独立进行
- Task 5-8 可并行（各自独立的 Phase）
- Task 9 依赖所有前置任务

# 开发规范
- TDD：先写测试再写实现
- git-commit：每个逻辑单元完成后提交
- 测试策略：mock 到存储层为止，渠道查询使用 mock
- Phase 测试中渠道使用 MagicMock 模拟 BaseChannelAdapter
- 端口扫描使用 PortScanChannel（基于 python-nmap），不虚构其他端口扫描渠道
