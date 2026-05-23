# Tasks — ipinfo_free 渠道迁移

- [x] Task 1: 创建 IpinfoFreeChannel 类骨架
  - [x] 1.1: 创建 `src/ip_info/channel/ipinfo_free.py`，定义 `IpinfoFreeChannel(BaseChannelAdapter)` 类
  - [x] 1.2: 实现 `__init__(self, timeout: float = 30.0)`
  - [x] 1.3: 实现 `_request(ip)` — HTTP GET + 状态码异常分层

- [x] Task 2: 编写 _request 测试（TDD RED）
  - [x] 2.1: 测试查询成功（HTTP 200）— 返回 API JSON dict
  - [x] 2.2: 测试网络超时（requests.Timeout）— 抛 ChannelError
  - [x] 2.3: 测试连接失败（requests.ConnectionError）— 抛 ChannelError
  - [x] 2.4: 测试请求限流（HTTP 429）— 抛 ChannelPermanentError + disabled=True
  - [x] 2.5: 测试其他 HTTP 错误（HTTP 500）— 抛 ChannelError
  - [x] 2.6: 测试其他非预期异常 — 抛 ChannelError

- [x] Task 3: 编写 fetch 集成测试
  - [x] 3.1: 测试 fetch 完整流程（delay → _request → query_time 注入）
  - [x] 3.2: 测试 fetch 透传 timeout 给 _request
  - [x] 3.3: 测试 fetch 网络错误透传 ChannelError
  - [x] 3.4: 测试 fetch 限流时设 disabled=True

- [x] Task 4: 编写 ChannelProtocol 一致性测试
  - [x] 4.1: 测试 isinstance(instance, ChannelProtocol) 返回 True
  - [x] 4.2: 测试 validate() 返回 True（不覆盖 _validate_key）

- [x] Task 5: 运行全量测试 + pre-commit 检查

- [ ] Task 6: git-commit（含中文翻译）

# Task Dependencies
- Task 2 ~ 4 依赖 Task 1（类骨架）
- Task 5 依赖 Task 1 ~ 4
- Task 6 依赖 Task 5
