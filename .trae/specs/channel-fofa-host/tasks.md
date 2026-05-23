# Tasks — fofa_host 渠道迁移

- [x] Task 1: 创建 FofaHostChannel 类骨架
  - [x] 1.1: 创建 `src/ip_info/channel/fofa_host.py`
  - [x] 1.2: 实现 `__init__(self, key: str, timeout: float = 30.0)`
  - [x] 1.3: 实现 `_validate_key()`
  - [x] 1.4: 实现 `_request(ip)` — 双层错误检查

- [x] Task 2: 编写 _validate_key 测试（TDD RED）
  - [x] 2.1-2.4: 全部完成

- [x] Task 3: 编写 _request 测试（TDD RED）
  - [x] 3.1-3.7: 全部完成

- [x] Task 4: 编写 fetch 集成测试
  - [x] 4.1-4.3: 全部完成

- [x] Task 5: 编写 validate + ChannelProtocol 一致性测试
  - [x] 5.1-5.3: 全部完成

- [x] Task 6: 运行全量测试 + pre-commit 检查

- [x] Task 7: git-commit（含中文翻译）
