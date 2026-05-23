# Tasks — rdns_ptr 渠道迁移

- [x] Task 1: 创建 RdnsPtrChannel 类骨架
  - [x] 1.1: 创建 `src/ip_info/channel/rdns_ptr.py`，定义 `RdnsPtrChannel(BaseChannelAdapter)` 类
  - [x] 1.2: 实现 `__init__(self, timeout: float = 3.0)`
  - [x] 1.3: 实现 `_request(ip)` — DNS 反向解析 + 异常分层

- [x] Task 2: 编写 _request 测试（TDD RED）
  - [x] 2.1: 测试查询成功（有 PTR 记录）— 返回 hostname/aliases/ip_addresses/ptr_count/has_ptr=True
  - [x] 2.2: 测试无 PTR 记录（socket.herror）— 返回 has_ptr=False
  - [x] 2.3: 测试地址查询失败（socket.gaierror）— 返回 has_ptr=False
  - [x] 2.4: 测试 DNS 查询超时（socket.timeout）— 返回 has_ptr=False
  - [x] 2.5: 测试网络不可用（其他异常）— 抛 ChannelError

- [x] Task 3: 编写 fetch 集成测试
  - [x] 3.1: 测试 fetch 完整流程（delay → _request → query_time 注入）
  - [x] 3.2: 测试 fetch 透传 timeout 给 _request
  - [x] 3.3: 测试 fetch 网络错误透传 ChannelError

- [x] Task 4: 编写 ChannelProtocol 一致性测试
  - [x] 4.1: 测试 isinstance(instance, ChannelProtocol) 返回 True
  - [x] 4.2: 测试 validate() 返回 True（不覆盖 _validate_key）

- [x] Task 5: 运行全量测试 + pre-commit 检查

- [ ] Task 6: git-commit（含中文翻译）

# Task Dependencies
- Task 2 ~ 4 依赖 Task 1（类骨架）
- Task 5 依赖 Task 1 ~ 4
- Task 6 依赖 Task 5
